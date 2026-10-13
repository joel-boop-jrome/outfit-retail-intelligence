"""
Member 1 module: CV & Virtual Try-On
-------------------------------------
Step 1: Pose extraction with MediaPipe + body-shape classification from
landmark ratios. No manual measurements needed -- everything is derived
from relative distances between shoulder / waist / hip landmarks.

Usage:
    from cv_vto.body_shape import BodyShapeEstimator

    estimator = BodyShapeEstimator()
    shape, ratios = estimator.classify_from_frame(frame_bgr)

Run as a script to test on your webcam:
    python -m cv_vto.body_shape
"""
from dataclasses import dataclass
from typing import Optional, Tuple, Dict

import numpy as np

from cv_vto.silhouette import measure_widths

try:
    from cv_vto.mp_compat import import_mediapipe
    mp = import_mediapipe()
except ImportError as e:  # pragma: no cover
    raise ImportError(
        "mediapipe is required for body_shape.py. Install with "
        "`pip install mediapipe`."
    ) from e


# MediaPipe Pose landmark indices we care about (33-point model)
LEFT_SHOULDER, RIGHT_SHOULDER = 11, 12
LEFT_HIP, RIGHT_HIP = 23, 24
LEFT_ELBOW, RIGHT_ELBOW = 13, 14


@dataclass
class BodyRatios:
    shoulder_width: float
    hip_width: float
    waist_width: float
    shoulder_to_hip: float
    # True when the three widths were measured from the person's silhouette (or supplied
    # by a client). False when the waist had to be guessed from shoulders and hips.
    waist_measured: bool = True
    # Distance between the two shoulder joints (normalised). The T-shirt size thresholds
    # were set against this number, so size estimation keeps using it.
    joint_shoulder_width: Optional[float] = None

    @property
    def size_width(self) -> float:
        return self.joint_shoulder_width if self.joint_shoulder_width else self.shoulder_width

    def as_dict(self) -> Dict[str, float]:
        return {
            "shoulder_width": self.shoulder_width,
            "hip_width": self.hip_width,
            "waist_width": self.waist_width,
            "shoulder_to_hip_ratio": self.shoulder_to_hip,
            "waist_measured": self.waist_measured,
        }


# Classification thresholds (front-view silhouette widths). They are starting points:
# run `python -m cv_vto.evaluate_shapes` on your own labelled photos to check and tune them.
SHOULDER_HIP_TOLERANCE = 0.07   # shoulders and hips count as "equal" within 7%
WAIST_DEFINED_RATIO = 0.80      # waist <= 80% of the narrower of shoulders/hips => defined waist


class BodyShapeEstimator:
    """
    Extracts pose landmarks and classifies body shape into one of:
    hourglass, rectangle, inverted_triangle, pear.

    Waist: MediaPipe Pose has no waist landmark, so the widths are measured from the
    person's silhouette (the pose model's segmentation mask) at the shoulder, waist and
    hip heights, with the arms painted out (see cv_vto/silhouette.py). If the mask or
    the torso is not usable, the waist is only estimated from shoulders and hips and
    `BodyRatios.waist_measured` is False; in that case hourglass and rectangle cannot be
    told apart, so the result is "rectangle" (no defined waist detected).
    """

    def __init__(self, min_detection_confidence: float = 0.5,
                 min_tracking_confidence: float = 0.5,
                 use_segmentation: bool = True,
                 model_complexity: int = 1,
                 static_image_mode: bool = False):
        self._mp_pose = mp.solutions.pose
        self.pose = self._mp_pose.Pose(
            static_image_mode=static_image_mode,
            model_complexity=model_complexity,
            enable_segmentation=use_segmentation,
            smooth_segmentation=use_segmentation and not static_image_mode,
            min_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence,
        )

    def close(self):
        self.pose.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def extract_landmarks(self, frame_bgr: np.ndarray):
        """Runs MediaPipe Pose on a BGR frame, returns landmarks or None."""
        import cv2
        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        results = self.pose.process(frame_rgb)
        if not results.pose_landmarks:
            return None
        return results.pose_landmarks.landmark

    def analyze(self, frame_bgr: np.ndarray):
        """Runs Pose once; returns (landmarks or None, segmentation mask or None)."""
        import cv2
        results = self.pose.process(cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB))
        if not results.pose_landmarks:
            return None, None
        return results.pose_landmarks.landmark, getattr(results, "segmentation_mask", None)

    @staticmethod
    def _dist(a, b) -> float:
        return float(np.hypot(a.x - b.x, a.y - b.y))

    @staticmethod
    def _estimate_waist(shoulder_w: float, hip_w: float) -> float:
        # Fallback only, used when no silhouette is available -- see class docstring.
        return (shoulder_w + hip_w) / 2.0 * 0.9

    def compute_ratios(self, landmarks, mask: Optional[np.ndarray] = None) -> Optional[BodyRatios]:
        """Widths from the silhouette when a mask is given, otherwise from joint distances."""
        try:
            ls, rs = landmarks[LEFT_SHOULDER], landmarks[RIGHT_SHOULDER]
            lh, rh = landmarks[LEFT_HIP], landmarks[RIGHT_HIP]
        except (IndexError, TypeError):
            return None

        joint_shoulder = self._dist(ls, rs)
        joint_hip = self._dist(lh, rh)
        if joint_hip == 0:
            return None

        widths = measure_widths(mask, landmarks) if mask is not None else None
        if widths is not None and widths.hip > 0:
            return BodyRatios(
                shoulder_width=widths.shoulder, hip_width=widths.hip, waist_width=widths.waist,
                shoulder_to_hip=widths.shoulder / widths.hip,
                waist_measured=True, joint_shoulder_width=joint_shoulder,
            )
        return BodyRatios(
            shoulder_width=joint_shoulder, hip_width=joint_hip,
            waist_width=self._estimate_waist(joint_shoulder, joint_hip),
            shoulder_to_hip=joint_shoulder / joint_hip,
            waist_measured=False, joint_shoulder_width=joint_shoulder,
        )

    @staticmethod
    def classify(ratios: BodyRatios, tolerance: float = SHOULDER_HIP_TOLERANCE,
                 waist_ratio: float = WAIST_DEFINED_RATIO) -> str:
        """
        Classifies body shape from shoulder / waist / hip widths.

            shoulders wider than hips (by more than the tolerance) -> inverted_triangle
            hips wider than shoulders                              -> pear
            shoulders ~ hips and a clearly narrower waist          -> hourglass
            shoulders ~ hips and no clearly narrower waist         -> rectangle

        If the waist was not measured (ratios.waist_measured is False) the hourglass /
        rectangle question cannot be answered, so shoulders ~ hips returns "rectangle".
        """
        s, w, h = ratios.shoulder_width, ratios.waist_width, ratios.hip_width
        if h <= 0:
            return "rectangle"
        ratio = s / h
        if ratio > 1 + tolerance:
            return "inverted_triangle"
        if ratio < 1 / (1 + tolerance):
            return "pear"
        if ratios.waist_measured and w <= min(s, h) * waist_ratio:
            return "hourglass"
        return "rectangle"

    def classify_from_frame(self, frame_bgr: np.ndarray
                             ) -> Tuple[Optional[str], Optional[BodyRatios]]:
        landmarks, mask = self.analyze(frame_bgr)
        if landmarks is None:
            return None, None
        ratios = self.compute_ratios(landmarks, mask)
        if ratios is None:
            return None, None
        if not ratios.waist_measured:
            return None, ratios   # silhouette unusable: do not guess a shape
        return self.classify(ratios), ratios


# Shoulder width is in MediaPipe's normalized [0, 1] frame coordinates, not
# real-world cm, so this size estimate is only meaningful at a roughly
# consistent camera distance (upper body framed from about arm's length).
# Thresholds are a starting guess -- tune against measured shoulder widths
# once you have real garment-fit data.
TSHIRT_SIZE_THRESHOLDS = [
    (0.18, "S"),
    (0.22, "M"),
    (0.26, "L"),
    (0.30, "XL"),
]


# The team's size chart: size -> (chest inches, inch range, cm range, fit preference).
SIZE_CHART = {
    "S": (32, "31-33 in", "80-85 cm", "Slim frames, fitted style"),
    "M": (36, "35-37 in", "90-95 cm", "Average build, versatile fit"),
    "L": (40, "39-41 in", "100-105 cm", "Broader build, everyday comfort"),
    "XL": (44, "43-45 in", "110-115 cm", "Relaxed fit, layering"),
    "XXL": (48, "47-49 in", "120-125 cm", "Plus-size comfort, oversized look"),
}
SIZE_CHEST_INCHES = {k: v[0] for k, v in SIZE_CHART.items()}


def size_with_number(size: str) -> str:
    """'L' -> 'L (chest 40 in, 100-105 cm)'. Approximate: a guide, not a tape measure."""
    row = SIZE_CHART.get(size)
    return f"{size} (chest {row[0]} in, {row[2]})" if row else size


def size_fit_note(size: str) -> str:
    row = SIZE_CHART.get(size)
    return row[3] if row else ""


def estimate_tshirt_size(shoulder_width: float) -> str:
    """Rough T-shirt size estimate from normalized shoulder width."""
    for threshold, size in TSHIRT_SIZE_THRESHOLDS:
        if shoulder_width < threshold:
            return size
    return "XXL"


def _webcam_demo():  # pragma: no cover - manual/interactive test
    import cv2

    mp_drawing = mp.solutions.drawing_utils
    mp_pose = mp.solutions.pose

    cap = cv2.VideoCapture(0)
    with BodyShapeEstimator() as estimator:
        while cap.isOpened():
            ok, frame = cap.read()
            if not ok:
                break
            results = estimator.pose.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            shape = None
            size = None
            if results.pose_landmarks:
                ratios = estimator.compute_ratios(results.pose_landmarks.landmark,
                                                  getattr(results, "segmentation_mask", None))
                if ratios:
                    shape = estimator.classify(ratios)
                    size = estimate_tshirt_size(ratios.size_width)
                mp_drawing.draw_landmarks(
                    frame, results.pose_landmarks, mp_pose.POSE_CONNECTIONS,
                    landmark_drawing_spec=mp_drawing.DrawingSpec(
                        color=(0, 255, 0), thickness=2, circle_radius=2),
                    connection_drawing_spec=mp_drawing.DrawingSpec(
                        color=(255, 255, 255), thickness=1),
                )
            cv2.putText(frame, shape or "no person detected", (20, 40),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 2)
            if size:
                cv2.putText(frame, f"T-shirt size: {size}", (20, 80),
                            cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 255), 2)
            cv2.imshow("Body Shape Estimator - press q to quit", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    _webcam_demo()
