"""
Member 3 module: rule-based dynamic price adjustment.

Combines: (a) forecasted demand vs. current stock ("stock velocity"),
and (b) estimated price elasticity, to recommend a markdown or markup.

This is intentionally simple/interpretable (good for a report) -- swap
in a constrained optimizer (e.g. scipy.optimize) later if you want to
maximize projected revenue subject to a min/max price band.
"""
from dataclasses import dataclass


@dataclass
class PriceRecommendation:
    sku: str
    current_price: float
    recommended_price: float
    pct_change: float
    reason: str


def recommend_price(
    sku: str,
    current_price: float,
    forecasted_demand: float,
    current_stock: float,
    elasticity: float,
    max_markdown: float = 0.30,
    max_markup: float = 0.15,
) -> PriceRecommendation:
    """
    stock_velocity_ratio > 1  -> demand exceeds stock -> raise price
    stock_velocity_ratio < 1  -> stock outpacing demand -> markdown
    The magnitude of the adjustment is damped by elasticity: more elastic
    (very negative) products get smaller price moves since demand reacts
    strongly to price.
    """
    if current_stock <= 0:
        return PriceRecommendation(
            sku, current_price, current_price, 0.0,
            "no stock on hand -- price unchanged",
        )

    if elasticity >= 0:
        # Sales rose with price in the history (promotions/seasons are mixed into the data),
        # so the sensitivity estimate cannot be trusted to steer a price move.
        return PriceRecommendation(
            sku, current_price, current_price, 0.0,
            "price sensitivity estimate is unreliable (sales rose with price) -- price unchanged",
        )

    velocity_ratio = forecasted_demand / current_stock
    elasticity_damping = min(1.0, 1.0 / max(abs(elasticity), 0.5))

    if velocity_ratio > 1.2:
        raw_change = min(max_markup, (velocity_ratio - 1) * 0.5) * elasticity_damping
        new_price = current_price * (1 + raw_change)
        reason = f"demand ({forecasted_demand:.0f}) exceeds stock ({current_stock:.0f}) -- markup"
    elif velocity_ratio < 0.7:
        raw_change = min(max_markdown, (1 - velocity_ratio) * 0.5) * elasticity_damping
        new_price = current_price * (1 - raw_change)
        reason = f"stock ({current_stock:.0f}) outpacing demand ({forecasted_demand:.0f}) -- markdown"
    else:
        new_price = current_price
        reason = "stock and demand roughly balanced -- no change"

    pct_change = (new_price - current_price) / current_price
    return PriceRecommendation(sku, current_price, round(new_price, 2), round(pct_change, 4), reason)


if __name__ == "__main__":
    rec = recommend_price(
        sku="SKU_001", current_price=49.99, forecasted_demand=180,
        current_stock=100, elasticity=-1.4,
    )
    print(rec)
