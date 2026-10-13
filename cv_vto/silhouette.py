"""
Measure chest/shoulder, waist and hip widths from a person-segmentation mask.

Why this exists
---------------
MediaPipe Pose gives joint positions (shoulder, hip, elbow...), but it has NO waist
landmark, and joint centres sit inside the body, so distances between them are far
narrower than the real body (the two hip joints are only about half a hip-width
apart). The pose model can also return a segmentation mask: a picture of the
person's silhouette. Measuring the silhouette's width at three heights gives real
widths, the same way a tailor reads chest, waist and hip:

    chest/shoulder : widest row from 25% to 40% of the way down from the shoulder
                     line to the hip line (below the armpits)
    waist          : narrowest row between 55% and 72% of that distance
    hip            : widest row from just above the hip landmarks to 15% of the
                     torso length below them

Arms: with the arms slightly away from the body (like an "A"), the rows above are
simply the torso. If the arms hang against the body they merge with it, so the
elbow landmarks are used to detect that and the arm segments (shoulder -> elbow ->
wrist) are painted out of the mask first. That repair is approximate; asking the
user to stand with arms a little away from their sides is more accurate.

This module has no MediaPipe dependency: it takes a mask and landmark-like objects
(anything with .x .y and optionally .visibility), so it is easy to unit-test with
drawn silhouettes.
"""
from dataclasses import dataclass
from typing import Optional, Tuple

import numpy as np

LEFT_SHOULDER, RIGHT_SHOULDER = 11, 12
LEFT_ELBOW, RIGHT_ELBOW = 13, 14
LEFT_WRIST, RIGHT_WRIST = 15, 16
LEFT_HIP, RIGHT_HIP = 23, 24

SHOULDER_BAND = (0.25, 0.40)   # fractions of torso length below the shoulder line (chest, below the armpits)
WAIST_BAND = (0.55, 0.72)      # fractions of torso length below the shoulder line
HIP_BAND = (-0.05, 0.15)       # fractions of torso length around the hip line
ARM_THICKNESS = 0.24           # arm stroke width as a fraction of shoulder-joint distance
MASK_THRESHOLD = 0.5
PLAUSIBLE_SHOULDER_HIP = (0.6, 1.7)   # outside this range the measurement is rejected
MIN_TORSO_PX = 40              # ignore very small / distant people


@dataclass
class BodyWidths:
    shoulder: float            # all widths are fractions of the frame width
    waist: float
    hip: float
    rows: Tuple[int, int, int]  # pixel rows used: shoulder, waist, hip (for drawing/debug)


def _px(lm, w, h):
    return np.array([lm.x * w, lm.y * h], dtype=np.float32)


def _visible(lm, minimum=0.3) -> bool:
    return getattr(lm, "visibility", 1.0) >= minimum


def remove_arms(mask: np.ndarray, landmarks, w: int, h: int, shoulder_px: float) -> np.ndarray:
    """Return a copy of the binary mask with both arms painted out."""
    import cv2
    out = mask.copy()
    thickness = max(3, int(ARM_THICKNESS * shoulder_px))
    for s, e, wr in ((LEFT_SHOULDER, LEFT_ELBOW, LEFT_WRIST), (RIGHT_SHOULDER, RIGHT_ELBOW, RIGHT_WRIST)):
        try:
            pts = [landmarks[i] for i in (s, e, wr)]
        except (IndexError, TypeError):
            continue
        shoulder_p, elbow_p, wrist_p = (_px(p, w, h) for p in pts)
        hand_p = wrist_p + 0.4 * (wrist_p - elbow_p)   # the hand continues past the wrist landmark
        segments = [(pts[0], pts[1], shoulder_p, elbow_p), (pts[1], pts[2], elbow_p, hand_p)]
        for a, b, pa, pb in segments:
            if _visible(a) and _visible(b):
                cv2.line(out, (int(pa[0]), int(pa[1])), (int(pb[0]), int(pb[1])), 0, thickness)
    return out


def _run_edges(row: np.ndarray, x_center: float, search: int):
    """(left, right) pixel edges of the run of True pixels containing (or nearest to) x_center."""
    n = row.shape[0]
    x = int(round(x_center))
    if x < 0 or x >= n:
        return None
    if not row[x]:
        left = np.flatnonzero(row[max(0, x - search):x])
        right = np.flatnonzero(row[x:min(n, x + search + 1)])
        if left.size == 0 and right.size == 0:
            return None
        if left.size and (right.size == 0 or (x - (max(0, x - search) + left[-1])) <= right[0]):
            x = max(0, x - search) + int(left[-1])
        else:
            x = x + int(right[0])
    lo = x
    while lo > 0 and row[lo - 1]:
        lo -= 1
    hi = x
    while hi < n - 1 and row[hi + 1]:
        hi += 1
    return lo, hi


def _band_widths(mask: np.ndarray, y0: float, y1: float, x_at, search: int):
    widths = []
    for y in range(int(round(min(y0, y1))), int(round(max(y0, y1))) + 1):
        if 0 <= y < mask.shape[0]:
            edges = _run_edges(mask[y], x_at(y), search)
            if edges is not None:
                widths.append(edges[1] - edges[0] + 1)
    return widths


def measure_widths(mask: np.ndarray, landmarks) -> Optional[BodyWidths]:
    """
    mask: float or bool array (H, W), person = high values.
    landmarks: sequence indexable by MediaPipe pose indices, normalised x/y.
    Returns None when the torso is not fully visible or too small to measure.
    """
    if mask is None:
        return None
    h, w = mask.shape[:2]
    try:
        ls, rs = landmarks[LEFT_SHOULDER], landmarks[RIGHT_SHOULDER]
        lh, rh = landmarks[LEFT_HIP], landmarks[RIGHT_HIP]
    except (IndexError, TypeError):
        return None
    if not all(_visible(p, 0.5) for p in (ls, rs, lh, rh)):
        return None

    binary = (mask > MASK_THRESHOLD).astype(np.uint8)
    ys = (ls.y + rs.y) / 2 * h
    yh = (lh.y + rh.y) / 2 * h
    torso = yh - ys
    if torso < MIN_TORSO_PX or ys < 0 or yh >= h:
        return None
    xs = (ls.x + rs.x) / 2 * w
    xh = (lh.x + rh.x) / 2 * w
    shoulder_px = float(np.linalg.norm(_px(ls, w, h) - _px(rs, w, h)))
    if shoulder_px < 10:
        return None

    def x_at(y):  # torso midline, interpolated between shoulder and hip midpoints
        t = (y - ys) / torso
        return xs + t * (xh - xs)

    search = int(0.25 * shoulder_px)
    raw = binary.astype(bool)

    # Do the arms merge with the torso? Check the silhouette run at mid-torso and at the
    # hips: if an elbow or wrist landmark lies inside that run, the arm is touching the body.
    merged = False
    for check_y in (int(ys + 0.5 * torso), int(yh)):
        edges = _run_edges(raw[check_y], x_at(check_y), search) if 0 <= check_y < h else None
        if edges is None:
            continue
        for e in (LEFT_ELBOW, RIGHT_ELBOW, LEFT_WRIST, RIGHT_WRIST):
            try:
                lm = landmarks[e]
            except (IndexError, TypeError):
                continue
            if _visible(lm) and edges[0] - 2 <= lm.x * w <= edges[1] + 2:
                merged = True
    work = remove_arms(binary, landmarks, w, h, shoulder_px).astype(bool) if merged else raw

    sh_rows = _band_widths(work, ys + SHOULDER_BAND[0] * torso, ys + SHOULDER_BAND[1] * torso, x_at, search)
    wa_rows = _band_widths(work, ys + WAIST_BAND[0] * torso, ys + WAIST_BAND[1] * torso, x_at, search)
    hi_rows = _band_widths(work, yh + HIP_BAND[0] * torso, yh + HIP_BAND[1] * torso, x_at, search)
    if not (sh_rows and wa_rows and hi_rows):
        return None

    shoulder = float(np.percentile(sh_rows, 90))
    waist = float(np.percentile(wa_rows, 20))
    hip = float(np.percentile(hi_rows, 90))

    # Plausibility guard: legs spread apart, other people next to you, or a bad mask give
    # impossible proportions. Refuse to measure rather than classify nonsense.
    if not (PLAUSIBLE_SHOULDER_HIP[0] <= shoulder / hip <= PLAUSIBLE_SHOULDER_HIP[1]):
        return None
    if waist > 1.15 * max(shoulder, hip):
        return None
    return BodyWidths(
        shoulder=shoulder / w, waist=waist / w, hip=hip / w,
        rows=(int(ys + 0.32 * torso), int(ys + 0.63 * torso), int(yh + 0.05 * torso)),
    )
