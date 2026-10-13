from cv_vto.smoothing import ShapeSmoother


def test_majority_vote_ignores_single_noisy_frame():
    s = ShapeSmoother(window=5)
    for label in ["pear", "pear", "rectangle", "pear", "pear"]:
        out = s.update(label)
    assert out == "pear"


def test_none_frames_keep_label_briefly_then_clear():
    s = ShapeSmoother(window=5, patience=3)
    s.update("pear")
    assert s.update(None) == "pear"
    s.update(None)
    assert s.update(None) is None


def test_empty_starts_none():
    assert ShapeSmoother().current is None
