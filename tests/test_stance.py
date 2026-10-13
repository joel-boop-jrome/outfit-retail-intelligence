import random
from types import SimpleNamespace as NS

from cv_vto.stance import DEFAULT_TORSO_RANGE, SizeStabilizer, check_placement, torso_range_from


def _lm(torso=0.45, cx=0.5, vis=0.9, nose_y=0.15):
    pts = {i: NS(x=cx, y=0.5, visibility=vis) for i in range(33)}
    top = 0.5 - torso / 2
    pts[0] = NS(x=cx, y=nose_y, visibility=1.0)
    pts[11] = NS(x=cx - 0.1, y=top, visibility=vis); pts[12] = NS(x=cx + 0.1, y=top, visibility=vis)
    pts[23] = NS(x=cx - 0.08, y=top + torso, visibility=vis); pts[24] = NS(x=cx + 0.08, y=top + torso, visibility=vis)
    return pts


def test_good_position():
    assert check_placement(_lm()).ok


def test_distance_and_side_messages():
    assert "closer" in check_placement(_lm(torso=0.25)).message
    assert "step back" in check_placement(_lm(torso=0.6)).message
    assert "right" in check_placement(_lm(cx=0.3)).message
    assert "left" in check_placement(_lm(cx=0.7)).message
    assert "hips" in check_placement(_lm() | {23: NS(x=.4, y=.7, visibility=.1), 24: NS(x=.6, y=.7, visibility=.1)}).message


def test_calibration_moves_the_target():
    lo, hi = torso_range_from(0.30)
    assert lo < 0.30 < hi and (lo, hi) != DEFAULT_TORSO_RANGE
    assert check_placement(_lm(torso=0.30), (lo, hi)).ok
    assert not check_placement(_lm(torso=0.45), (lo, hi)).ok


def _size(w):
    return "S" if w < 0.18 else "M" if w < 0.22 else "L" if w < 0.26 else "XL"


def test_size_on_a_boundary_does_not_flicker():
    random.seed(1)
    m = SizeStabilizer(_size)
    shown = []
    for _ in range(300):
        s = m.update(random.gauss(0.22, 0.006), True).size      # right on the M/L boundary
        if s:
            shown.append(s)
    assert sum(a != b for a, b in zip(shown, shown[1:])) <= 2   # raw per-frame sizes would flip ~100 times


def test_needs_samples_and_clears_when_lost():
    m = SizeStabilizer(_size)
    for _ in range(10):
        assert m.update(0.20, True).size is None
    for _ in range(30):
        r = m.update(0.20, True)
    assert r.size == "M" and r.locked
    for _ in range(50):
        r = m.update(None, False)
    assert r.size is None


def test_real_change_is_accepted_after_a_while():
    m = SizeStabilizer(_size)
    for _ in range(40):
        m.update(0.20, True)
    for _ in range(80):
        r = m.update(0.28, True)
    assert r.size == "XL"


def test_size_has_a_number():
    from cv_vto.body_shape import size_fit_note, size_with_number
    assert size_with_number("L") == "L (chest 40 in, 100-105 cm)"
    assert size_with_number("XXL") == "XXL (chest 48 in, 120-125 cm)"
    assert size_fit_note("S") == "Slim frames, fitted style"
