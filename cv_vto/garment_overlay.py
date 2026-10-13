"""
Member 1 module: 2D Virtual Try-On garment overlay.

Warps a transparent PNG garment onto a person's shoulder/hip keypoints
using an affine transform, and alpha-blends it onto the live frame.

Usage:
    from cv_vto.garment_overlay import GarmentOverlay

    overlay = GarmentOverlay("assets/garments/tshirt_01.png")
    output_frame = overlay.apply(frame_bgr, landmarks)
"""
from typing import Optional

import numpy as np


class GarmentOverlay:
    def __init__(self, garment_png_path: str, smoothing: float = 0.6,
                 min_visibility: float = 0.5):
        """
        smoothing: 0 = no smoothing, closer to 1 = steadier but laggier.
        min_visibility: skip the overlay if shoulders/hips are less visible
        than this (MediaPipe visibility score), so the garment doesn't snap
        onto guessed positions.
        """
        import cv2
        self.smoothing = smoothing
        self.min_visibility = min_visibility
        self._prev_dst = None
        self.cv2 = cv2
        garment = cv2.imread(garment_png_path, cv2.IMREAD_UNCHANGED)
        if garment is None:
            raise FileNotFoundError(f"Could not load garment image: {garment_png_path}")
        if garment.shape[2] != 4:
            raise ValueError(
                "Garment image must be a PNG with an alpha channel (RGBA)."
            )
        self.garment = garment
        h, w = garment.shape[:2]
        # Reference points on the *garment* image: left shoulder, right
        # shoulder, and a bottom-center hem point. Adjust these to match
        # where the garment's own shoulder seams sit in pixel space.
        self.src_points = np.float32([
            [w * 0.20, h * 0.12],  # left shoulder
            [w * 0.80, h * 0.12],  # right shoulder
            [w * 0.50, h * 0.95],  # hem center
        ])

    def apply(self, frame_bgr: np.ndarray, landmarks) -> np.ndarray:
        """
        landmarks: MediaPipe pose landmark list (normalized 0-1 coords).
        Returns a new frame with the garment alpha-blended on top.
        """
        cv2 = self.cv2
        h_frame, w_frame = frame_bgr.shape[:2]

        LEFT_SHOULDER, RIGHT_SHOULDER = 11, 12
        LEFT_HIP, RIGHT_HIP = 23, 24
        try:
            ls = landmarks[LEFT_SHOULDER]
            rs = landmarks[RIGHT_SHOULDER]
            lh = landmarks[LEFT_HIP]
            rh = landmarks[RIGHT_HIP]
        except (IndexError, TypeError):
            return frame_bgr

        if min(getattr(p, "visibility", 1.0) for p in (ls, rs, lh, rh)) < self.min_visibility:
            self._prev_dst = None
            return frame_bgr

        dst_points = np.float32([
            [ls.x * w_frame, ls.y * h_frame],
            [rs.x * w_frame, rs.y * h_frame],
            [((lh.x + rh.x) / 2) * w_frame, ((lh.y + rh.y) / 2) * h_frame],
        ])
        # exponential smoothing so the garment doesn't jitter with pose noise
        if self._prev_dst is not None and self.smoothing > 0:
            dst_points = self.smoothing * self._prev_dst + (1 - self.smoothing) * dst_points
        self._prev_dst = dst_points.copy()

        matrix = cv2.getAffineTransform(self.src_points, dst_points)
        warped = cv2.warpAffine(
            self.garment, matrix, (w_frame, h_frame),
            flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT,
            borderValue=(0, 0, 0, 0),
        )

        return self._alpha_blend(frame_bgr, warped)

    @staticmethod
    def _alpha_blend(background: np.ndarray, foreground_rgba: np.ndarray) -> np.ndarray:
        alpha = foreground_rgba[:, :, 3:4].astype(np.float32) / 255.0
        fg_rgb = foreground_rgba[:, :, :3].astype(np.float32)
        bg_rgb = background.astype(np.float32)
        blended = fg_rgb * alpha + bg_rgb * (1 - alpha)
        return blended.astype(np.uint8)


def _webcam_demo(garment_path: str):  # pragma: no cover - manual/interactive test
    import cv2
    from cv_vto.body_shape import BodyShapeEstimator

    overlay = GarmentOverlay(garment_path)
    cap = cv2.VideoCapture(0)
    with BodyShapeEstimator() as estimator:
        while cap.isOpened():
            ok, frame = cap.read()
            if not ok:
                break
            landmarks = estimator.extract_landmarks(frame)
            if landmarks is not None:
                frame = overlay.apply(frame, landmarks)
            cv2.imshow("Virtual Try-On - press q to quit", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python -m cv_vto.garment_overlay <path_to_garment.png>")
    else:
        _webcam_demo(sys.argv[1])
