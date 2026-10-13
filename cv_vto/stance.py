"""
Where to stand, and a steady T-shirt size once you are there (no camera or MediaPipe needed, so it is testable).

Distance
    The size is calibrated for standing about 120 cm (4 ft) from the camera, upper body in view.
    A camera cannot measure metres, so we use how big your torso (shoulder line to hip line) looks:
    when it fills about 38-52% of the picture height you are at roughly 120 cm on a typical laptop camera.
    Every camera is different, so the page has a "Calibrate at 120 cm" button: stand 120 cm away
    (measure once with a tape), press it, and that torso size becomes the target for your camera.

Steadiness
    A single frame is noisy, so a size between two letters flickers. We therefore
      1. collect measurements only while the person is in place,
      2. take the MEDIAN of the last ~40 shoulder widths,
      3. show a size only after 25 good frames (progress bar), and
      4. change the shown size only if a new one wins 12 updates in a row.
    Stepping out of place for about 1.5 s clears the reading.
"""
from collections import deque
from dataclasses import dataclass
from statistics import median
from typing import Callable, Optional, Tuple

DEFAULT_TORSO_RANGE = (0.38, 0.52)       # torso length as a fraction of frame height, at about 120 cm
CALIBRATION_BAND = 0.08                  # +/- 8% around a calibrated torso length
CENTER_X = 0.5
CENTER_TOLERANCE = 0.10                  # how far (fraction of frame width) from the middle is allowed
HEAD_CIRCLE = (0.5, 0.15, 0.065)         # x, y, radius (fraction of height) of the "head goes here" circle


def torso_range_from(target: Optional[float]) -> Tuple[float, float]:
    if not target:
        return DEFAULT_TORSO_RANGE
    return target * (1 - CALIBRATION_BAND), target * (1 + CALIBRATION_BAND)


def torso_length(lm) -> Optional[float]:
    try:
        return (lm[23].y + lm[24].y) / 2 - (lm[11].y + lm[12].y) / 2
    except (IndexError, TypeError):
        return None


@dataclass
class Placement:
    ok: bool
    message: str


def check_placement(lm, torso_range: Tuple[float, float] = DEFAULT_TORSO_RANGE, vis_min: float = 0.5) -> Placement:
    """lm: pose landmarks (normalised x/y/visibility) indexable by MediaPipe pose index."""
    try:
        ls, rs, lh, rh, nose = lm[11], lm[12], lm[23], lm[24], lm[0]
    except (IndexError, TypeError):
        return Placement(False, "stand in front of the camera")
    if min(ls.visibility, rs.visibility) < vis_min:
        return Placement(False, "show your shoulders to the camera")
    if min(lh.visibility, rh.visibility) < vis_min:
        return Placement(False, "step back a little, hips must be in view")
    cx = (ls.x + rs.x + lh.x + rh.x) / 4
    torso = torso_length(lm)
    if torso < torso_range[0]:
        return Placement(False, "come a little closer (about 120 cm)")
    if torso > torso_range[1]:
        return Placement(False, "step back a little (about 120 cm)")
    if cx < CENTER_X - CENTER_TOLERANCE:      # on a mirrored view, left on screen -> move right
        return Placement(False, "move a little to your right")
    if cx > CENTER_X + CENTER_TOLERANCE:
        return Placement(False, "move a little to your left")
    if nose.y < 0.02 or nose.y > 0.40:
        return Placement(False, "raise or lower the camera so your head is in the circle")
    return Placement(True, "hold still")


@dataclass
class Reading:
    size: Optional[str] = None
    progress: float = 0.0           # 0..1 while collecting
    locked: bool = False            # True once a steady size is available


class SizeStabilizer:
    def __init__(self, size_fn: Callable[[float], str], window: int = 40, min_samples: int = 25,
                 switch_after: int = 12, lost_after: int = 45):
        self.size_fn = size_fn
        self.window, self.min_samples, self.switch_after, self.lost_after = window, min_samples, switch_after, lost_after
        self.reset()

    def reset(self):
        self._widths = deque(maxlen=self.window)
        self._size: Optional[str] = None
        self._challenger: Optional[str] = None
        self._streak = 0
        self._lost = 0

    def update(self, shoulder_width: Optional[float], in_position: bool) -> Reading:
        """shoulder_width: distance between the shoulder joints (fraction of frame width), or None."""
        if shoulder_width is None or not in_position:
            self._lost += 1
            if self._lost >= self.lost_after:
                self.reset()
            return self._reading()
        self._lost = 0
        self._widths.append(shoulder_width)
        if len(self._widths) >= self.min_samples:
            candidate = self.size_fn(median(self._widths))
            if self._size is None:
                self._size = candidate
            elif candidate == self._size:
                self._challenger, self._streak = None, 0
            else:
                self._streak = self._streak + 1 if candidate == self._challenger else 1
                self._challenger = candidate
                if self._streak >= self.switch_after:
                    self._size, self._challenger, self._streak = candidate, None, 0
        return self._reading()

    def _reading(self) -> Reading:
        return Reading(size=self._size, progress=min(1.0, len(self._widths) / self.min_samples),
                       locked=self._size is not None)
