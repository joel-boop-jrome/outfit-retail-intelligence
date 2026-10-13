"""Silhouette measurement and the 4-class body-shape classifier, tested on drawn bodies."""
from types import SimpleNamespace

import numpy as np
import pytest

cv2 = pytest.importorskip("cv2")
pytest.importorskip("mediapipe")

from cv_vto.body_shape import BodyRatios, BodyShapeEstimator
from cv_vto.silhouette import measure_widths

W, H = 640, 960


def lm_list(shoulder_half, hip_half, cx=320, ys=250, yh=560, arm_out=None):
    """33 fake landmarks; only shoulders, elbows, wrists, hips matter."""
    pts = [SimpleNamespace(x=0.5, y=0.5, visibility=1.0) for _ in range(33)]

    def put(i, x, y):
        pts[i] = SimpleNamespace(x=x / W, y=y / H, visibility=1.0)

    put(11, cx - shoulder_half, ys); put(12, cx + shoulder_half, ys)
    put(23, cx - hip_half, yh); put(24, cx + hip_half, yh)
    ax = arm_out if arm_out is not None else max(shoulder_half, hip_half) + 55   # A-pose: arm axis clearly away from the body
    put(13, cx - ax, (ys + yh) / 2); put(14, cx + ax, (ys + yh) / 2)
    put(15, cx - ax, yh + 40); put(16, cx + ax, yh + 40)
    return pts


def body_mask(shoulder, waist, hip, cx=320, ys=250, yh=560, arms=False, arm_w=36):
    """Silhouette polygon: half-widths at shoulder, waist (63% down), hip rows; optional hanging arms."""
    m = np.zeros((H, W), np.uint8)
    yw = int(ys + 0.63 * (yh - ys))
    yc = int(ys + 0.42 * (yh - ys))   # chest stays as wide as the shoulders down to here
    poly = [(cx - shoulder, ys - 10), (cx + shoulder, ys - 10), (cx + shoulder, yc), (cx + waist, yw),
            (cx + hip, yh + 20), (cx + hip, yh + 120), (cx - hip, yh + 120), (cx - hip, yh + 20),
            (cx - waist, yw), (cx - shoulder, yc)]
    cv2.fillPoly(m, [np.array(poly, np.int32)], 1)
    if arms:  # arms hang right beside the body, touching the torso edge
        for sgn in (-1, 1):
            edge = cx + sgn * max(shoulder, hip)
            inner, outer = edge - sgn * 25, edge + sgn * arm_w   # arms overlap the body edge a little, as real hanging arms do
            cv2.rectangle(m, (int(min(inner, outer)), ys), (int(max(inner, outer)), yh + 60), 1, -1)
    return m.astype(np.float32)


CASES = {
    #  shoulder, waist, hip half-widths -> expected shape
    "hourglass": (100, 66, 100),
    "rectangle": (100, 95, 100),
    "inverted_triangle": (125, 100, 95),
    "pear": (90, 78, 120),
}


@pytest.mark.parametrize("name", CASES)
def test_all_four_shapes_are_reachable_from_silhouettes(name):
    s, w, h = CASES[name]
    est = BodyShapeEstimator.__new__(BodyShapeEstimator)
    ratios = est.compute_ratios(lm_list(s, h), body_mask(s, w, h))
    assert ratios.waist_measured
    assert BodyShapeEstimator.classify(ratios) == name


def test_measured_widths_are_close_to_the_drawn_widths():
    bw = measure_widths(body_mask(100, 66, 100), lm_list(100, 100))
    assert bw.shoulder * W == pytest.approx(200, rel=0.08)
    assert bw.waist * W == pytest.approx(132, rel=0.12)
    assert bw.hip * W == pytest.approx(200, rel=0.12)


def test_hanging_arms_do_not_inflate_waist_and_hip():
    no_arms = measure_widths(body_mask(100, 66, 100), lm_list(100, 100))
    # arms hug the body: elbows sit inside the merged silhouette, arm pixels touch the torso
    with_arms = measure_widths(body_mask(100, 66, 100, arms=True), lm_list(100, 100, arm_out=118))
    assert with_arms.waist == pytest.approx(no_arms.waist, rel=0.15)
    assert with_arms.hip == pytest.approx(no_arms.hip, rel=0.15)


def test_returns_none_when_torso_not_visible():
    lms = lm_list(100, 100)
    lms[23].visibility = 0.1
    assert measure_widths(body_mask(100, 66, 100), lms) is None
    assert measure_widths(None, lm_list(100, 100)) is None


def test_without_a_mask_the_waist_is_flagged_as_estimated_and_never_hourglass():
    est = BodyShapeEstimator.__new__(BodyShapeEstimator)
    r = est.compute_ratios(lm_list(100, 100), None)
    assert r.waist_measured is False
    assert BodyShapeEstimator.classify(r) == "rectangle"


def test_old_failure_is_fixed_rectangle_reachable_in_a_sweep():
    seen = set()
    for s in np.linspace(0.1, 0.4, 31):
        for h in np.linspace(0.1, 0.4, 31):
            for waist_frac in (0.65, 0.95):
                seen.add(BodyShapeEstimator.classify(BodyRatios(shoulder_width=s, hip_width=h, waist_width=min(s, h) * waist_frac, shoulder_to_hip=s / h)))
    assert seen == {"hourglass", "rectangle", "inverted_triangle", "pear"}
