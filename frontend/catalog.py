"""
Sample product catalog + flat-illustration previews for the style recommender.

The recommender (cv_vto.style_recommender) returns style tags such as
"wrap_dress (mustard)". This module turns each tag into a product card:
a name, a price, a one-line reason, and an inline-SVG preview drawn in the
recommended colour. Names, prices and illustrations are placeholders --
swap `PRODUCTS` for rows from a real catalogue / image URLs later.
"""
import re
from typing import Dict, Optional, Tuple

COLORS: Dict[str, Tuple[str, str]] = {
    # key: (hex, display name)
    "mustard": ("#D6A026", "Mustard"),
    "olive": ("#6B7A3A", "Olive"),
    "terracotta": ("#C4623E", "Terracotta"),
    "cream": ("#EEE4CD", "Cream"),
    "navy": ("#1F3864", "Navy"),
    "emerald": ("#2E8B6A", "Emerald"),
    "lavender": ("#A99BD1", "Lavender"),
    "slate_grey": ("#6B7787", "Slate grey"),
    "black": ("#1C1C1E", "Black"),
    "white": ("#F4F4F1", "White"),
    "beige": ("#D9C7A7", "Beige"),
    "charcoal": ("#3A3D42", "Charcoal"),
}

# style tag -> (display name, silhouette, price in INR, why it suits the body shape)
PRODUCTS: Dict[str, Tuple[str, str, int, str]] = {
    "wrap_dress": ("Wrap dress", "dress", 2799, "The wrap cinches the waist and balances shoulders and hips."),
    "fitted_blazer": ("Fitted blazer", "blazer", 3499, "Tailored through the waist to keep your natural curve."),
    "high_waisted_jeans": ("High-waisted jeans", "jeans", 1999, "A high rise sits at the narrowest point and lengthens the leg."),
    "belted_coat": ("Belted coat", "coat", 4999, "The belt marks the waist even under a heavy layer."),
    "peplum_top": ("Peplum top", "peplum", 1299, "The flared hem adds shape at the waist."),
    "layered_outfit": ("Layered set", "layered", 2499, "Layers add depth and the look of a defined waist."),
    "structured_jacket": ("Structured jacket", "jacket", 3299, "Structured shoulders give a clean, shaped line."),
    "a_line_skirt": ("A-line skirt", "skirt", 1499, "Flares out from the waist to balance shoulders and hips."),
    "wide_leg_pants": ("Wide-leg pants", "wide", 2199, "Adds volume below the waist to balance broad shoulders."),
    "v_neck_top": ("V-neck top", "vneck", 999, "The V draws the eye down and softens the shoulder line."),
    "dark_top_light_bottom": ("Dark top with light skirt", "combo_dark_top", 2899, "A dark top over a lighter bottom moves attention downward."),
    "boat_neck_top": ("Boat-neck top", "boat", 1099, "A wide neckline broadens the shoulders to balance the hips."),
    "statement_shoulder": ("Statement-shoulder top", "statement", 1799, "Shoulder detail adds width on top to balance the hips."),
    "dark_bottom_light_top": ("Light top with dark pants", "combo_dark_bottom", 2699, "Light on top draws the eye up; a dark bottom slims the hips."),
    "structured_blazer": ("Structured blazer", "longblazer", 3799, "Sharp shoulders and a longer line balance the hips."),
}

# colours for which the webcam try-on has a placeholder T-shirt PNG
TRYON_FILES = {c: f"tshirt_{c}.png" for c in ("navy", "mustard", "olive", "terracotta", "cream")}
TRYON_KINDS = {"vneck", "boat", "peplum", "statement", "layered"}

_REC_RE = re.compile(r"^(?P<style>[a-z_]+?)(?: \((?P<color>[a-z_]+)\))?$")


def parse_recommendation(text: str) -> Tuple[str, Optional[str]]:
    """'wrap_dress (mustard)' -> ('wrap_dress', 'mustard')."""
    m = _REC_RE.match(text.strip())
    if not m:
        return text, None
    return m.group("style"), m.group("color")


def shade(hex_color: str, amount: int) -> str:
    """Lighten (+) or darken (-) a #RRGGBB colour."""
    h = hex_color.lstrip("#")
    r, g, b = (max(0, min(255, int(h[i:i + 2], 16) + amount)) for i in (0, 2, 4))
    return f"#{r:02X}{g:02X}{b:02X}"


def _poly(points, fill, stroke, extra=""):
    pts = " ".join(f"{x},{y}" for x, y in points)
    return f'<polygon points="{pts}" fill="{fill}" stroke="{stroke}" stroke-width="1.5" stroke-linejoin="round" {extra}/>'


def _top(c, neck="round", flare=False, puffs=False):
    d = shade(c, -40)
    out = []
    if flare:
        out.append(_poly([(46, 176), (154, 176), (178, 218), (22, 218)], shade(c, 12), d))
    out.append(_poly([(78, 24), (122, 24), (156, 38), (190, 80), (166, 96), (152, 72),
                      (152, 190), (48, 190), (48, 72), (34, 96), (10, 80), (44, 38)], c, d))
    if puffs:
        out.append(f'<circle cx="46" cy="44" r="17" fill="{shade(c, 14)}" stroke="{d}" stroke-width="1.5"/>')
        out.append(f'<circle cx="154" cy="44" r="17" fill="{shade(c, 14)}" stroke="{d}" stroke-width="1.5"/>')
    if neck == "v":
        out.append('<polygon points="78,24 122,24 100,70" fill="#FFFFFF" stroke="%s" stroke-width="1.5"/>' % d)
    elif neck == "boat":
        out.append('<ellipse cx="100" cy="23" rx="36" ry="9" fill="#FFFFFF" stroke="%s" stroke-width="1.5"/>' % d)
    else:
        out.append('<ellipse cx="100" cy="24" rx="19" ry="11" fill="#FFFFFF" stroke="%s" stroke-width="1.5"/>' % d)
    return "".join(out)


def _jacket(c, hem=200, long=False):
    d = shade(c, -40)
    out = [
        _poly([(52, 30), (30, 40), (22, 172), (44, 174), (54, 92)], c, d),
        _poly([(148, 30), (170, 40), (178, 172), (156, 174), (146, 92)], c, d),
        _poly([(50, 30), (150, 30), (154, hem), (46, hem)], shade(c, 8), d),
        _poly([(84, 30), (100, 94), (116, 30)], shade(c, 30), d),
        _poly([(84, 30), (66, 40), (86, 78), (100, 94)], shade(c, -14), d),
        _poly([(116, 30), (134, 40), (114, 78), (100, 94)], shade(c, -14), d),
        f'<circle cx="100" cy="122" r="3.5" fill="{d}"/>',
        f'<circle cx="100" cy="150" r="3.5" fill="{d}"/>',
    ]
    if long:
        out.append(f'<rect x="114" y="150" width="22" height="3" fill="{d}"/>')
    return "".join(out)


def _coat(c):
    d = shade(c, -40)
    return "".join([
        _poly([(52, 28), (28, 40), (18, 190), (42, 192), (54, 96)], c, d),
        _poly([(148, 28), (172, 40), (182, 190), (158, 192), (146, 96)], c, d),
        _poly([(50, 28), (150, 28), (170, 232), (30, 232)], shade(c, 8), d),
        _poly([(84, 28), (100, 100), (116, 28)], shade(c, 30), d),
        _poly([(84, 28), (62, 40), (88, 84), (100, 100)], shade(c, -14), d),
        _poly([(116, 28), (138, 40), (112, 84), (100, 100)], shade(c, -14), d),
        f'<rect x="46" y="118" width="108" height="11" fill="{shade(c, -28)}" stroke="{d}" stroke-width="1.5"/>',
        f'<rect x="92" y="115" width="16" height="17" rx="2" fill="{shade(c, 40)}" stroke="{d}" stroke-width="1.5"/>',
    ])


def _dress(c):
    d = shade(c, -40)
    return "".join([
        _poly([(74, 16), (126, 16), (140, 92), (178, 228), (22, 228), (60, 92)], c, d),
        f'<line x1="74" y1="16" x2="124" y2="112" stroke="{d}" stroke-width="2"/>',
        f'<rect x="58" y="92" width="84" height="11" fill="{shade(c, -28)}" stroke="{d}" stroke-width="1.5"/>',
        f'<circle cx="124" cy="98" r="7" fill="{shade(c, 40)}" stroke="{d}" stroke-width="1.5"/>',
        '<polygon points="84,16 116,16 100,44" fill="#FFFFFF" stroke="%s" stroke-width="1.5"/>' % d,
    ])


def _pants(c, wide=False, jeans=False):
    d = shade(c, -40)
    if wide:
        l_leg = [(58, 34), (100, 34), (98, 230), (26, 230)]
        r_leg = [(100, 34), (142, 34), (174, 230), (102, 230)]
    else:
        l_leg = [(60, 34), (100, 34), (95, 230), (58, 230)]
        r_leg = [(100, 34), (140, 34), (142, 230), (105, 230)]
    out = [_poly(l_leg, c, d), _poly(r_leg, c, d),
           f'<rect x="58" y="22" width="84" height="13" fill="{shade(c, -20)}" stroke="{d}" stroke-width="1.5"/>']
    if jeans:
        out.append(f'<path d="M64 40 q10 22 26 12" fill="none" stroke="{shade(c, 50)}" stroke-width="1.5" stroke-dasharray="3 2"/>')
        out.append(f'<path d="M136 40 q-10 22 -26 12" fill="none" stroke="{shade(c, 50)}" stroke-width="1.5" stroke-dasharray="3 2"/>')
        out.append(f'<circle cx="100" cy="44" r="3" fill="{shade(c, 50)}"/>')
    return "".join(out)


def _skirt(c):
    d = shade(c, -40)
    return "".join([
        _poly([(68, 34), (132, 34), (178, 204), (22, 204)], c, d),
        f'<rect x="66" y="22" width="68" height="13" fill="{shade(c, -20)}" stroke="{d}" stroke-width="1.5"/>',
        f'<line x1="90" y1="36" x2="70" y2="202" stroke="{d}" stroke-width="1" opacity=".45"/>',
        f'<line x1="110" y1="36" x2="130" y2="202" stroke="{d}" stroke-width="1" opacity=".45"/>',
    ])


def _layered(c):
    d = shade(c, -40)
    cardi = shade(c, -26)
    return "".join([
        _top(c),
        _poly([(52, 30), (30, 40), (22, 172), (44, 174), (54, 92)], cardi, d),
        _poly([(148, 30), (170, 40), (178, 172), (156, 174), (146, 92)], cardi, d),
        _poly([(48, 32), (86, 32), (80, 204), (46, 204)], cardi, d),
        _poly([(152, 32), (114, 32), (120, 204), (154, 204)], cardi, d),
    ])


def _group(svg, tx, ty, s):
    return f'<g transform="translate({tx},{ty}) scale({s})">{svg}</g>'


def _silhouette(kind: str, c: str, color_key: str) -> str:
    if kind == "dress":
        return _dress(c)
    if kind == "blazer":
        return _jacket(c, hem=200)
    if kind == "jacket":
        return _jacket(c, hem=172)
    if kind == "longblazer":
        return _jacket(c, hem=228, long=True)
    if kind == "coat":
        return _coat(c)
    if kind == "jeans":
        return _pants(c, jeans=True)
    if kind == "wide":
        return _pants(c, wide=True)
    if kind == "skirt":
        return _skirt(c)
    if kind == "vneck":
        return _top(c, neck="v")
    if kind == "boat":
        return _top(c, neck="boat")
    if kind == "peplum":
        return _top(c, flare=True)
    if kind == "statement":
        return _top(c, puffs=True)
    if kind == "layered":
        return _layered(c)
    if kind == "combo_dark_top":
        return _group(_skirt(c), 36, 104, 0.64) + _group(_top(COLORS["charcoal"][0]), 36, 0, 0.64)
    if kind == "combo_dark_bottom":
        return _group(_pants(COLORS["charcoal"][0], wide=True), 36, 100, 0.66) + _group(_top(c), 36, 0, 0.64)
    return _top(c)


def preview_svg(style: str, color_key: Optional[str]) -> str:
    name, kind, _, _ = PRODUCTS[style]
    hex_color, color_name = COLORS.get(color_key or "", ("#8A94B8", "Default"))
    label = f"{color_name} {name.lower()}"
    return (f'<svg viewBox="0 0 200 240" xmlns="http://www.w3.org/2000/svg" role="img" '
            f'aria-label="{label}">{_silhouette(kind, hex_color, color_key or "")}</svg>')


def product_card(style: str, color_key: Optional[str]) -> dict:
    """Everything the UI needs to draw one product card."""
    if style not in PRODUCTS:
        raise KeyError(style)
    name, kind, price, reason = PRODUCTS[style]
    hex_color, color_name = COLORS.get(color_key or "", ("#8A94B8", "Classic"))
    tryon = TRYON_FILES.get(color_key) if kind in TRYON_KINDS else None
    return {
        "style": style, "name": name, "kind": kind, "price": price, "reason": reason,
        "color_key": color_key, "color_hex": hex_color, "color_name": color_name,
        "svg": preview_svg(style, color_key), "tryon_file": tryon,
    }
