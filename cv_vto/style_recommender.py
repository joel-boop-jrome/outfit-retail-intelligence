"""
Member 1 module: Personalized style recommendation.

Maps a classified body shape (+ optional color tone) to a shortlist of
complementary apparel style tags. This is a rule-based lookup table --
swap in a learned model later if you collect enough labeled preference
data.
"""
from typing import List, Optional

BODY_SHAPE_STYLE_MAP = {
    "hourglass": [
        "wrap_dress", "fitted_blazer", "high_waisted_jeans", "belted_coat",
    ],
    "rectangle": [
        "peplum_top", "layered_outfit", "structured_jacket", "a_line_skirt",
    ],
    "inverted_triangle": [
        "wide_leg_pants", "a_line_skirt", "v_neck_top", "dark_top_light_bottom",
    ],
    "pear": [
        "boat_neck_top", "statement_shoulder", "dark_bottom_light_top", "structured_blazer",
    ],
}

# Very small color-tone -> palette lookup as a starting point.
COLOR_TONE_PALETTE = {
    "warm": ["mustard", "olive", "terracotta", "cream"],
    "cool": ["navy", "emerald", "lavender", "slate_grey"],
    "neutral": ["black", "white", "beige", "charcoal"],
}


def recommend_styles(body_shape: str, color_tone: Optional[str] = None) -> List[str]:
    styles = BODY_SHAPE_STYLE_MAP.get(body_shape, [])
    if not styles:
        return []
    if color_tone and color_tone in COLOR_TONE_PALETTE:
        palette = COLOR_TONE_PALETTE[color_tone]
        return [f"{style} ({palette[i % len(palette)]})" for i, style in enumerate(styles)]
    return styles


if __name__ == "__main__":
    for shape in BODY_SHAPE_STYLE_MAP:
        print(shape, "->", recommend_styles(shape, color_tone="warm"))
