import pytest

pytest.importorskip("mediapipe")

from cv_vto.body_shape import BodyRatios, BodyShapeEstimator
from cv_vto.style_recommender import BODY_SHAPE_STYLE_MAP, recommend_styles

VALID = {"hourglass", "rectangle", "inverted_triangle", "pear"}


def _ratios(s, w, h):
    return BodyRatios(shoulder_width=s, hip_width=h, waist_width=w, shoulder_to_hip=s / h)


def test_classify_returns_valid_shape():
    assert BodyShapeEstimator.classify(_ratios(1.0, 0.7, 1.0)) in VALID


def test_wide_shoulders_not_pear_and_wide_hips_not_inverted():
    assert BodyShapeEstimator.classify(_ratios(1.5, 1.0, 1.0)) != "pear"
    assert BodyShapeEstimator.classify(_ratios(1.0, 1.0, 1.5)) != "inverted_triangle"


def test_every_shape_has_styles():
    for shape in VALID:
        assert shape in BODY_SHAPE_STYLE_MAP
        assert len(recommend_styles(shape)) > 0
