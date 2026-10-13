"""
Small drawings for the Retailers page: category sketches, icons, sparklines, header art.

Product pictures: if a file named after the SKU exists in assets/products
(for example assets/products/SKU_001.jpg), the page shows that photo. Otherwise it
draws a soft sketch for the product's category. Sketches are placeholders, not photos.
"""
import base64
import os
from typing import List, Optional

from frontend.catalog import _dress, _group, _jacket, _pants, _top, shade

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PRODUCT_DIR = os.path.join(ROOT, "assets", "products")

# muted, earthy shades used to tell sketches apart (decoration only, not data)
PALETTE = ["#6B7A3A", "#B5694A", "#CDB98F", "#46525A", "#8F7E66", "#80946F", "#A7605A", "#D9C9A3"]


def sku_color(sku: str) -> str:
    return PALETTE[sum(ord(c) for c in sku) % len(PALETTE)]


def _tote(c: str) -> str:
    d = shade(c, -40)
    return "".join([
        f'<path d="M70 92 C70 28 130 28 130 92" fill="none" stroke="{d}" stroke-width="7" stroke-linecap="round"/>',
        f'<polygon points="42,88 158,88 170,214 30,214" fill="{c}" stroke="{d}" stroke-width="1.5" stroke-linejoin="round"/>',
        f'<polygon points="42,88 158,88 160,112 40,112" fill="{shade(c, 14)}" stroke="{d}" stroke-width="1.5" stroke-linejoin="round"/>',
        f'<circle cx="100" cy="150" r="9" fill="{shade(c, 40)}" stroke="{d}" stroke-width="1.5"/>',
    ])


def _shape(category: str, c: str) -> str:
    cat = category.lower()
    if cat in ("dress", "dresses"):
        return _dress(c)
    if cat in ("outerwear", "jackets", "coats"):
        return _jacket(c, hem=200)
    if cat in ("bottoms", "pants", "trousers", "jeans"):
        return _pants(c, jeans=True)
    if cat in ("accessories", "bags"):
        return _tote(c)
    return _top(c, neck="v")


def category_svg(category: str, sku: str) -> str:
    c = sku_color(sku)
    return (f'<svg viewBox="0 0 200 240" xmlns="http://www.w3.org/2000/svg" role="img" '
            f'aria-label="{category} sketch">{_shape(category, c)}</svg>')


def _photo_uri(sku: str) -> Optional[str]:
    for ext, mime in (("jpg", "jpeg"), ("jpeg", "jpeg"), ("png", "png"), ("webp", "webp")):
        path = os.path.join(PRODUCT_DIR, f"{sku}.{ext}")
        if os.path.isfile(path):
            with open(path, "rb") as fh:
                return f"data:image/{mime};base64,{base64.b64encode(fh.read()).decode()}"
    return None


def product_visual(category: str, sku: str, name: str = "") -> str:
    """HTML for the picture area of a card: a photo if one exists, else the category sketch."""
    uri = _photo_uri(sku)
    inner = (f'<img src="{uri}" alt="{name or sku}" loading="lazy"/>' if uri else category_svg(category, sku))
    return f'<div class="rt-thumb">{inner}</div>'


def mini_thumb(category: str, sku: str) -> str:
    uri = _photo_uri(sku)
    inner = f'<img src="{uri}" alt=""/>' if uri else category_svg(category, sku)
    return f'<span class="rt-mini" title="{sku}">{inner}</span>'


# --------------------------------------------------------------------- icons (24px, stroke)
_ICON = {
    "star": '<path d="M12 3.5l2.6 5.3 5.9.9-4.3 4.1 1 5.8L12 16.9 6.8 19.6l1-5.8L3.5 9.7l5.9-.9z"/>',
    "box": '<path d="M3.5 7.5L12 3l8.5 4.5v9L12 21l-8.5-4.5z"/><path d="M3.5 7.5L12 12l8.5-4.5M12 12v9"/>',
    "trend": '<path d="M3.5 17l6-6 4 4 7-8"/><path d="M15 7h5.5v5.5"/>',
    "tag": '<path d="M3.5 12.2V4.5h7.7l9.3 9.3-7.7 7.7z"/><circle cx="8" cy="9" r="1.4"/>',
    "check": '<path d="M5 12.5l4.5 4.5L19 7.5"/>',
    "arrow": '<path d="M5 12h14M13 6l6 6-6 6"/>',
}


def icon(name: str, size: int = 22) -> str:
    return (f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
            f'stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{_ICON[name]}</svg>')


# --------------------------------------------------------------------- sparkline
def sparkline(history: List[float], forecast: Optional[float] = None, color: str = "#5F6B3A",
              width: int = 220, height: int = 56) -> str:
    """Actual weekly values as a line, then a dotted step to the model's estimate."""
    if len(history) < 2:
        return ""
    vals = list(history) + ([forecast] if forecast is not None else [])
    lo, hi = min(vals), max(vals)
    span = (hi - lo) or 1.0
    pad = 6
    n = len(vals)

    def xy(i, v):
        return pad + i * (width - 2 * pad) / (n - 1), height - pad - (v - lo) / span * (height - 2 * pad)

    pts = [xy(i, v) for i, v in enumerate(history)]
    line = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    area = f"{pts[0][0]:.1f},{height - pad} {line} {pts[-1][0]:.1f},{height - pad}"
    out = [f'<svg viewBox="0 0 {width} {height}" class="rt-spark" role="img" aria-label="Weekly sales trend" '
           f'preserveAspectRatio="none">',
           f'<polygon points="{area}" fill="{color}" opacity=".10"/>',
           f'<polyline points="{line}" fill="none" stroke="{color}" stroke-width="2" stroke-linejoin="round" '
           f'stroke-linecap="round"/>']
    if forecast is not None:
        (x1, y1), (x2, y2) = pts[-1], xy(n - 1, forecast)
        out.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{color}" '
                   f'stroke-width="2" stroke-dasharray="3 3"/>')
        out.append(f'<circle cx="{x2:.1f}" cy="{y2:.1f}" r="4" fill="#FFFDF8" stroke="{color}" stroke-width="2"/>')
    out.append("</svg>")
    return "".join(out)


# --------------------------------------------------------------------- header art
def hero_art() -> str:
    """A small editorial still life: three garments on soft arches."""
    olive, terracotta, sand = "#6B7A3A", "#B5694A", "#CDB98F"
    return (
        '<svg viewBox="0 0 420 300" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Illustration of a dress, jacket and tote">'
        '<path d="M20 300V150a80 80 0 0 1 160 0v150z" fill="#E6DECB"/>'
        '<path d="M150 300V110a90 90 0 0 1 180 0v190z" fill="#D9CFB6"/>'
        '<path d="M300 300V170a60 60 0 0 1 120 0v130z" fill="#EDE6D5"/>'
        + _group(_dress(terracotta), 24, 52, 0.95)
        + _group(_jacket(olive, hem=200), 150, 30, 1.02)
        + _group(_tote(sand), 296, 118, 0.62)
        + "</svg>"
    )
