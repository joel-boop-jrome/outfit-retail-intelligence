"""Generates simple transparent T-shirt PNGs for the try-on demo.

Run from the project root:  python assets/make_placeholder_garments.py
Replace these with real garment photos (transparent background) when you have them;
the shoulder seams should sit near 20% / 80% of the image width at ~12% of its height
(see GarmentOverlay.src_points).
"""
import os

from PIL import Image, ImageDraw

SIZE = 600
COLORS = {
    "tshirt_navy": (31, 56, 100),
    "tshirt_mustard": (214, 160, 38),
    "tshirt_olive": (107, 122, 58),
    "tshirt_terracotta": (196, 98, 62),
    "tshirt_cream": (238, 228, 205),
}


def shirt(color):
    s = SIZE
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    pts = [
        (0.38, 0.06), (0.62, 0.06),            # neck edge (top)
        (0.80, 0.12), (0.97, 0.32),            # right shoulder -> sleeve tip
        (0.85, 0.40), (0.76, 0.30),            # sleeve underside -> armpit
        (0.76, 0.95), (0.24, 0.95),            # right hem -> left hem
        (0.24, 0.30), (0.15, 0.40),            # left armpit -> sleeve underside
        (0.03, 0.32), (0.20, 0.12),            # left sleeve tip -> left shoulder
    ]
    d.polygon([(x * s, y * s) for x, y in pts], fill=color + (235,))
    d.ellipse([0.40 * s, 0.01 * s, 0.60 * s, 0.14 * s], fill=(0, 0, 0, 0))  # neckline
    shade = tuple(max(0, c - 35) for c in color) + (235,)
    d.line([(0.24 * s, 0.93 * s), (0.76 * s, 0.93 * s)], fill=shade, width=8)
    return img


if __name__ == "__main__":
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "garments")
    os.makedirs(out, exist_ok=True)
    for name, color in COLORS.items():
        shirt(color).save(os.path.join(out, f"{name}.png"))
        print("wrote", name)
