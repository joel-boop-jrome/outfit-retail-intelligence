"""
Friendly product names.

The sales file only has codes like SKU_001. Retailers think in products, so when no real
`product_name` column exists we build a readable name from the outfit type:
    colour word (from the product's thumbnail colour) + a style word for its category
    e.g. SKU_002 -> "Olive Utility Jacket".

Names are deterministic (same code, same name every run) and unique within the data.
Plug in real names any time by adding a `product_name` column to the sales CSV.
"""
from typing import Dict, Iterable

from frontend.retail_art import PALETTE, sku_color

COLOR_WORDS = {
    "#6B7A3A": "Olive", "#B5694A": "Terracotta", "#CDB98F": "Sand", "#46525A": "Slate",
    "#8F7E66": "Taupe", "#80946F": "Sage", "#A7605A": "Clay", "#D9C9A3": "Cream",
}

STYLES = {
    "tops": ["Classic Tee", "Crew Neck Tee", "Everyday Polo", "Relaxed Henley", "Linen Shirt", "Boxy Tee"],
    "outerwear": ["Utility Jacket", "Bomber Jacket", "Quilted Jacket", "Field Coat", "Denim Jacket",
                  "Windbreaker", "Overshirt Jacket", "Trench Coat"],
    "bottoms": ["Straight Jeans", "Slim Chinos", "Tapered Trousers", "Relaxed Jeans", "Cargo Pants",
                "Pleated Trousers", "Jogger Pants", "Wide-Leg Pants"],
    "dresses": ["Wrap Dress", "Midi Dress", "Shirt Dress", "Slip Dress"],
    "accessories": ["Canvas Tote", "Weekender Bag", "Leather Belt", "Knit Scarf"],
}
FALLBACK = {"tops": "Top", "outerwear": "Jacket", "bottoms": "Pants", "dresses": "Dress", "accessories": "Accessory"}


def friendly_names(items: Iterable[tuple]) -> Dict[str, str]:
    """items: (sku, category) pairs -> {sku: friendly name}. Unique, stable, sorted by code."""
    out: Dict[str, str] = {}
    used = set()
    seen_per_cat: Dict[str, int] = {}
    for sku, cat in sorted(set((str(s), str(c)) for s, c in items)):
        key = cat.lower()
        i = seen_per_cat.get(key, 0)
        seen_per_cat[key] = i + 1
        styles = STYLES.get(key)
        if styles:
            style = styles[i % len(styles)]
        else:
            style = f"{key.replace('_', ' ').title()} Piece"
        name = f"{COLOR_WORDS.get(sku_color(sku), 'Classic')} {style}"
        n = 2
        base = name
        while name in used:               # only if there are more products than styles
            name = f"{base} {n}"
            n += 1
        used.add(name)
        out[sku] = name
    return out
