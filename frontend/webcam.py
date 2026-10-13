"""
In-browser webcam for the Streamlit shopper tab.

Uses streamlit-webrtc: the browser streams camera frames to this process, `BodyShapeProcessor.recv`
runs MediaPipe Pose on each frame, shows a "head goes here" circle and distance hints, draws the
selected shirt on the shopper, and keeps a steady T-shirt size estimate for the page to read.
(The class keeps its old name so app.py and the tests need no change.)
"""
import threading
from typing import Optional

import av
import cv2

from cv_vto.body_shape import BodyShapeEstimator, SIZE_CHEST_INCHES, estimate_tshirt_size
from cv_vto.garment_overlay import GarmentOverlay
from cv_vto.mp_compat import import_mediapipe
from cv_vto.stance import (HEAD_CIRCLE, SizeStabilizer, check_placement, torso_length, torso_range_from)

mp = import_mediapipe()


class BodyShapeProcessor:
    """Implements the streamlit-webrtc VideoProcessor interface (recv)."""

    def __init__(self):
        # The size only needs joint positions, so the (slower) body silhouette is switched off.
        self._estimator = BodyShapeEstimator(use_segmentation=False)
        self._drawing = mp.solutions.drawing_utils
        self._pose_connections = mp.solutions.pose.POSE_CONNECTIONS
        self._stabilizer = SizeStabilizer(estimate_tshirt_size)
        self._lock = threading.Lock()
        self.latest_size: Optional[str] = None
        self.in_position = False
        self.progress = 0.0
        self._last_torso: Optional[float] = None
        self.torso_target: Optional[float] = None       # set by calibrate() or from the page
        # set from the Streamlit page on each rerun
        self.garment_path: Optional[str] = None
        self.show_skeleton: bool = False
        self._overlays = {}

    def _overlay(self):
        path = self.garment_path
        if not path:
            return None
        if path not in self._overlays:
            try:
                self._overlays[path] = GarmentOverlay(path)
            except (FileNotFoundError, ValueError):
                self._overlays[path] = None
        return self._overlays[path]

    def calibrate(self) -> Optional[float]:
        """Call while the person stands 120 cm from the camera. Returns the torso size recorded, or None."""
        with self._lock:
            if self._last_torso is None:
                return None
            self.torso_target = self._last_torso
            self._stabilizer.reset()
            return self.torso_target

    def _draw_guide(self, img, ok: bool, message: str, reading):
        h, w = img.shape[:2]
        colour = (60, 200, 60) if ok else (40, 140, 240)           # BGR: green when in place, orange otherwise
        hx, hy, hr = HEAD_CIRCLE
        cv2.circle(img, (int(hx * w), int(hy * h)), int(hr * h), colour, 3)
        cv2.putText(img, "head", (int(hx * w) - 24, int(hy * h) + 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, colour, 1)
        font = cv2.FONT_HERSHEY_SIMPLEX
        cv2.rectangle(img, (0, 0), (w, 34), (0, 0, 0), -1)
        cv2.putText(img, message, (12, 24), font, 0.65, colour, 2)
        if ok and not reading.locked:                               # progress bar while measuring
            bw = int(0.4 * w)
            x0, y0 = (w - bw) // 2, h - 28
            cv2.rectangle(img, (x0, y0), (x0 + bw, y0 + 12), (200, 200, 200), 1)
            cv2.rectangle(img, (x0, y0), (x0 + int(bw * reading.progress), y0 + 12), colour, -1)
        if reading.locked:
            cv2.rectangle(img, (0, h - 40), (w, h), (0, 0, 0), -1)
            inches = SIZE_CHEST_INCHES.get(reading.size, "")
            cv2.putText(img, f"Size {reading.size}  -  chest {inches} in", (12, h - 12), font, 0.8, (0, 255, 255), 2)

    def recv(self, frame: "av.VideoFrame") -> "av.VideoFrame":
        img = frame.to_ndarray(format="bgr24")
        img = cv2.flip(img, 1)  # mirror view, like a mirror/selfie camera
        rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        results = self._estimator.pose.process(rgb)

        placement_ok, message, shoulder_w = False, "stand back about 120 cm, head in the circle", None
        torso = None
        if results.pose_landmarks:
            lm = results.pose_landmarks.landmark
            torso = torso_length(lm)
            placement = check_placement(lm, torso_range_from(self.torso_target))
            placement_ok, message = placement.ok, placement.message
            if placement_ok:
                shoulder_w = float(((lm[11].x - lm[12].x) ** 2 + (lm[11].y - lm[12].y) ** 2) ** 0.5)
            overlay = self._overlay()
            if overlay is not None:
                img = overlay.apply(img, lm)
            if self.show_skeleton:
                self._drawing.draw_landmarks(img, results.pose_landmarks, self._pose_connections)

        reading = self._stabilizer.update(shoulder_w, placement_ok)
        if placement_ok and reading.locked:
            message = f"size {reading.size}  (hold still)"
        with self._lock:
            self.latest_size = reading.size
            self.in_position, self.progress = placement_ok, reading.progress
            self._last_torso = torso
        self._draw_guide(img, placement_ok, message, reading)
        return av.VideoFrame.from_ndarray(img, format="bgr24")

    def read(self):
        """(shape, size). Shape is no longer read from the camera, so it is always None."""
        with self._lock:
            return None, self.latest_size
