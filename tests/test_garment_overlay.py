from types import SimpleNamespace

import numpy as np
import pytest

cv2 = pytest.importorskip("cv2")
pytest.importorskip("mediapipe")
from PIL import Image

from cv_vto.garment_overlay import GarmentOverlay


def _landmarks(visibility=1.0):
    pts = {11: (0.35, 0.3), 12: (0.65, 0.3), 23: (0.4, 0.7), 24: (0.6, 0.7)}
    lm = [SimpleNamespace(x=0.5, y=0.5, visibility=1.0) for _ in range(33)]
    for i, (x, y) in pts.items():
        lm[i] = SimpleNamespace(x=x, y=y, visibility=visibility)
    return lm


@pytest.fixture
def garment_path(tmp_path):
    p = tmp_path / "g.png"
    Image.new("RGBA", (200, 200), (255, 0, 0, 255)).save(p)
    return str(p)


def test_overlay_paints_torso(garment_path):
    frame = np.zeros((400, 400, 3), np.uint8)
    out = GarmentOverlay(garment_path, smoothing=0).apply(frame, _landmarks())
    assert out[200, 200].sum() > 0          # centre of the torso now coloured
    assert out[5, 5].sum() == 0             # far corner untouched


def test_low_visibility_skips_overlay(garment_path):
    frame = np.zeros((400, 400, 3), np.uint8)
    out = GarmentOverlay(garment_path).apply(frame, _landmarks(visibility=0.1))
    assert out.sum() == 0


def test_rejects_png_without_alpha(tmp_path):
    p = tmp_path / "rgb.png"
    Image.new("RGB", (50, 50), (1, 2, 3)).save(p)
    with pytest.raises(ValueError):
        GarmentOverlay(str(p))
