"""Plain-language helpers for the retailer page (no Streamlit dependency)."""
from typing import Optional


def elasticity_sentence(e: float) -> str:
    if e >= 0:
        return ("The history shows sales rising when the price rose. That usually means promotions "
                "or seasons are mixed into the data, so treat the price advice for this product with caution.")
    pct = abs(e) * 10
    if e > -1:
        return (f"Shoppers barely react to price here: a 10% price rise would lose roughly {pct:.0f}% of sales, "
                "so there is room to raise prices when stock is short.")
    return (f"Shoppers react strongly to price here: a 10% price rise would lose roughly {pct:.0f}% of sales, "
            "so price changes should stay small.")


def fit_label(r_squared: float) -> str:
    if r_squared < 0.3:
        return "weak"
    if r_squared < 0.6:
        return "moderate"
    return "strong"


def verdict(current_price: float, recommended_price: float, pct_change: float) -> str:
    if abs(pct_change) < 1e-9:
        return f"Keep the price at ₹{current_price:,.0f}"
    word = "Raise" if pct_change > 0 else "Lower"
    return f"{word} the price {abs(pct_change):.0%}: ₹{current_price:,.0f} to ₹{recommended_price:,.0f}"


def revenue_outlook(price: float, forecast: float, stock: float,
                    recommended_price: float, elasticity: float) -> Optional[dict]:
    """
    Expected next-week revenue at the current vs the recommended price.
    Units sold can never exceed stock. Returns None when the elasticity has
    an unexpected (non-negative) sign, because the estimate wouldn't be reliable.
    """
    if elasticity >= 0 or price <= 0:
        return None
    units_now = min(forecast, stock)
    ratio = recommended_price / price
    units_new = min(forecast * (ratio ** elasticity), stock)
    return {
        "units_now": units_now, "units_new": units_new,
        "revenue_now": units_now * price, "revenue_new": units_new * recommended_price,
    }


def stock_position(forecast: float, stock: float) -> str:
    if stock <= 0:
        return "You have no stock on hand, so there is nothing to price."
    weeks = stock / forecast if forecast > 0 else float("inf")
    if forecast > stock * 1.2:
        return f"Demand ({forecast:,.0f} units) is higher than your stock ({stock:,.0f}). You would sell out, so a higher price protects margin."
    if forecast < stock * 0.7:
        return f"You hold {weeks:.1f} weeks of stock against {forecast:,.0f} units of weekly demand. A lower price helps clear it."
    return f"Stock ({stock:,.0f}) and demand ({forecast:,.0f}) are roughly in balance, so no change is needed."


def sensitivity_word(e: float) -> str:
    """How much shoppers react to price, in one word."""
    if e >= 0:
        return "Unclear"
    if e > -0.7:
        return "Low"
    if e > -1.3:
        return "Medium"
    return "High"


def price_effect_sentence(e: float) -> str:
    """What a 10% price change would do, in plain words."""
    if e >= 0:
        return "We cannot tell how shoppers react to price for this product, because past sales rose and fell with promotions and seasons."
    x = abs(e) * 10
    return (f"If you raised the price by 10%, you would likely sell about {x:.0f}% fewer units. "
            f"If you lowered it by 10%, you might sell about {x:.0f}% more.")


def sureness(r_squared: float, weeks: int) -> str:
    """How much to trust the price-sensitivity guess, in words."""
    if r_squared < 0.3:
        return f"Not very sure. Price explains only a little of the ups and downs in sales (based on {weeks} weeks)."
    if r_squared < 0.6:
        return f"Fairly sure. Price explains some of the ups and downs in sales (based on {weeks} weeks)."
    return f"Quite sure. Price explains much of the ups and downs in sales (based on {weeks} weeks)."


def suggestion_phrase(pct_change: float) -> str:
    if abs(pct_change) < 1e-9:
        return "Keep the price"
    return f"{'Raise' if pct_change > 0 else 'Lower'} price {abs(pct_change):.0%}"


GLOSSARY = [
    ("Units", "How many items were sold (not rupees)."),
    ("Actual vs estimate", "Actual is what customers really bought. An estimate is what the computer expects next week, based on past weeks."),
    ("Forecast", "The estimate of how many units a product will sell next week."),
    ("Rising / slowing", "Rising: we expect next week to beat the recent weekly average by about 8% or more. Slowing: about 8% or more below it."),
    ("Best seller", "One of the products that sold the most units in the weeks you are looking back over."),
    ("Stock", "How many units you hold right now. Your sales file does not include this, so you add it yourself."),
    ("Running short", "You expect to sell more next week than you hold, so you may run out."),
    ("Excess stock", "You hold much more than you expect to sell soon (more than about 1.4 weeks of sales)."),
    ("Promotion week", "A week when the product was on offer. These weeks often sell more, which can hide the true effect of price."),
    ("Price sensitivity", "How much sales drop when the price goes up. High: shoppers walk away quickly. Low: they keep buying. "
                          "(Statisticians call this price elasticity.)"),
    ("How sure we are", "Whether the price-sensitivity guess is built on a clear pattern in past sales or only a faint one."),
    ("Suggested price", "A starting point from a simple rule: raise when demand beats stock, lower when stock piles up, and move less for price-sensitive products. "
                        "It is advice to think about, not an order."),
    ("Typical miss", "On weeks the computer had not seen, how far its estimate was from what really sold, on average."),
]
