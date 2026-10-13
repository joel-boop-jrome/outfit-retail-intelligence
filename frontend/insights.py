"""
Plain-English retail insights for the Retailers page (no Streamlit dependency).

Everything here is derived from three things the project already has:
  - the weekly sales history (data/weekly_sales.csv),
  - the LightGBM next-week forecast (demand_forecasting.predict),
  - the price elasticity and rule-based price suggestion (dynamic_pricing).

Nothing is invented. Stock-related insights are only produced when the retailer
supplies stock levels, because the sales file has no inventory column.
"""
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import pandas as pd

from dynamic_pricing.price_optimizer import recommend_price
from frontend.product_names import friendly_names

RISING_AT = 0.08        # forecast at least 8% above the recent average
SLOWING_AT = -0.08      # forecast at least 8% below the recent average
SHORT_AT = 1.2          # demand > 1.2 x stock (same threshold the price rule uses)
URGENT_AT = 2.0         # demand > 2 x stock: less than half a week of stock
OVERSTOCK_AT = 0.7      # demand < 0.7 x stock (same threshold the price rule uses)
TOP_SELLERS = 3


@dataclass
class ProductSignal:
    sku: str
    name: str
    category: str
    price: float
    window: int
    recent_avg: float          # average weekly units over the window (actual sales)
    units_window: float        # total units over the window (actual sales)
    forecast: float            # model estimate for next week
    used_model: bool
    trend_pct: float           # forecast vs recent average
    elasticity: Optional[float] = None
    r_squared: Optional[float] = None
    stock: Optional[float] = None
    best_seller: bool = False

    @property
    def trend(self) -> str:
        if self.trend_pct >= RISING_AT:
            return "rising"
        if self.trend_pct <= SLOWING_AT:
            return "slowing"
        return "steady"

    @property
    def velocity(self) -> Optional[float]:
        """Forecast demand divided by stock; None when stock is unknown or zero."""
        if self.stock is None or self.stock <= 0:
            return None
        return self.forecast / self.stock

    @property
    def stock_state(self) -> Optional[str]:
        v = self.velocity
        if self.stock is not None and self.stock <= 0 and self.forecast > 0:
            return "urgent"
        if v is None:
            return None
        if v >= URGENT_AT:
            return "urgent"
        if v > SHORT_AT:
            return "short"
        if v < OVERSTOCK_AT:
            return "excess"
        return "ok"

    @property
    def price_is_reliable(self) -> bool:
        return self.elasticity is not None and self.elasticity < 0

    @property
    def days_of_stock(self) -> Optional[float]:
        if self.stock is None or self.forecast <= 0:
            return None
        return self.stock / self.forecast * 7


@dataclass
class Recommendation:
    kind: str                  # restock | overstock | slowing | feature | category
    tone: str                  # urgent | watch | good
    title: str
    happening: str
    why: str
    action: str
    cta: str
    target: str                # spotlight | pricing | gallery
    sku: Optional[str] = None
    category: Optional[str] = None


# --------------------------------------------------------------------- building signals
def pretty_category(cat: str) -> str:
    return str(cat).replace("_", " ").title()


def build_signals(
    df: pd.DataFrame,
    forecasts: Dict[str, Tuple[float, bool]],
    elasticities: dict,
    stock: Optional[Dict[str, float]] = None,
    window: int = 4,
) -> List[ProductSignal]:
    """One ProductSignal per SKU in df. `forecasts` maps sku -> (units, came_from_model)."""
    stock = stock or {}
    has_names = "product_name" in df.columns
    made_up = friendly_names(df.drop_duplicates("sku")[["sku", "category"]].itertuples(index=False, name=None))
    out: List[ProductSignal] = []
    for sku, d in df.groupby("sku", sort=True):
        d = d.sort_values("date")
        recent = d.tail(window)
        recent_avg = float(recent["units_sold"].mean())
        fc, used_model = forecasts[sku]
        res = elasticities.get(sku)
        name = str(d["product_name"].iloc[-1]) if has_names and pd.notna(d["product_name"].iloc[-1]) else made_up.get(sku, sku)
        out.append(ProductSignal(
            sku=sku, name=name, category=str(d["category"].iloc[-1]),
            price=float(d["price"].iloc[-1]), window=window,
            recent_avg=recent_avg, units_window=float(recent["units_sold"].sum()),
            forecast=float(fc), used_model=used_model,
            trend_pct=(fc / recent_avg - 1) if recent_avg > 0 else 0.0,
            elasticity=res.elasticity if res else None,
            r_squared=res.r_squared if res else None,
            stock=float(stock[sku]) if sku in stock else None,
        ))
    ranked = sorted(out, key=lambda s: s.units_window, reverse=True)
    for s in ranked[:TOP_SELLERS]:
        s.best_seller = True
    return out


def best_sellers(signals: List[ProductSignal]) -> List[ProductSignal]:
    return sorted((s for s in signals if s.best_seller), key=lambda s: s.units_window, reverse=True)


def stock_watch(signals: List[ProductSignal]) -> List[ProductSignal]:
    """Products that may run short, most urgent first. Empty if stock is unknown."""
    flagged = [s for s in signals if s.stock_state in ("urgent", "short")]
    return sorted(flagged, key=lambda s: (s.velocity if s.velocity is not None else 99), reverse=True)


def rising(signals: List[ProductSignal]) -> List[ProductSignal]:
    return sorted((s for s in signals if s.trend == "rising"), key=lambda s: s.trend_pct, reverse=True)


def slowing(signals: List[ProductSignal]) -> List[ProductSignal]:
    return sorted((s for s in signals if s.trend == "slowing"), key=lambda s: s.trend_pct)


def price_idea(s: ProductSignal) -> Optional[dict]:
    """
    A reason to look at this product's price, or None.
    With stock: uses the project's price rule. Without stock: uses the forecast
    trend and price sensitivity only, and never names a new price.
    """
    if not s.price_is_reliable:
        return None
    if s.stock is not None and s.stock > 0:
        rec = recommend_price(s.sku, s.price, s.forecast, s.stock, s.elasticity)
        if rec.pct_change > 0:
            return {"kind": "raise", "suggested": rec.recommended_price, "pct": rec.pct_change}
        if rec.pct_change < 0:
            return {"kind": "lower", "suggested": rec.recommended_price, "pct": rec.pct_change}
        return None
    if s.trend == "slowing" and s.elasticity <= -1:
        return {"kind": "review", "suggested": None, "pct": None}
    if s.trend == "rising" and s.elasticity > -1:
        return {"kind": "room", "suggested": None, "pct": None}
    return None


def pricing_opportunities(signals: List[ProductSignal]) -> List[Tuple[ProductSignal, dict]]:
    found = [(s, i) for s in signals if (i := price_idea(s))]
    return sorted(found, key=lambda t: abs(t[1]["pct"] or 0) + abs(t[0].trend_pct), reverse=True)


# --------------------------------------------------------------------- words for one product
def describe(s: ProductSignal) -> dict:
    """Status label, colour tone, one-line story and the call-to-action for a product card."""
    idea = price_idea(s)
    st_state = s.stock_state
    if st_state == "urgent":
        return dict(label="Stock watch", tone="urgent", cta="Review stock", target="spotlight",
                    text="Stock levels need attention. It could sell out within days.")
    if st_state == "short":
        return dict(label="Stock watch", tone="watch", cta="Review stock", target="spotlight",
                    text="Stock levels need attention before next week.")
    if s.best_seller and s.trend != "slowing":
        return dict(label="Best seller", tone="good", cta="View insights", target="spotlight",
                    text="A customer favourite." + (" Demand looks set to grow." if s.trend == "rising" else ""))
    if s.trend == "slowing":
        return dict(label="Slowing", tone="watch", cta="Explore pricing" if idea else "View insights",
                    target="pricing" if idea else "spotlight",
                    text="Sales may be slowing. Consider reviewing its price or promotion.")
    if s.trend == "rising":
        return dict(label="Rising", tone="good", cta="View insights", target="spotlight",
                    text="Demand may be picking up.")
    if st_state == "excess":
        return dict(label="Overstocked", tone="watch", cta="Explore pricing" if idea else "View insights",
                    target="pricing" if idea else "spotlight",
                    text="More stock than shoppers are likely to buy next week.")
    return dict(label="Steady", tone="neutral", cta="View insights", target="spotlight",
                text="Demand appears stable. Nothing needs changing right now.")


def trend_phrase(trend: str) -> str:
    return {"rising": "Likely to gain popularity", "steady": "Demand appears stable",
            "slowing": "Sales may be slowing"}[trend]


# --------------------------------------------------------------------- categories
def category_trends(df: pd.DataFrame, signals: List[ProductSignal], weeks: int = 26) -> List[dict]:
    """Per-category weekly totals (actual) plus the expected next-week total (model estimate)."""
    out = []
    by_cat: Dict[str, List[ProductSignal]] = {}
    for s in signals:
        by_cat.setdefault(s.category, []).append(s)
    for cat, sigs in by_cat.items():
        skus = {s.sku for s in sigs}
        weekly = (df[df["sku"].isin(skus)].groupby("date")["units_sold"].sum().sort_index())
        recent_avg = sum(s.recent_avg for s in sigs)
        fc = sum(s.forecast for s in sigs)
        pct = (fc / recent_avg - 1) if recent_avg > 0 else 0.0
        trend = "rising" if pct >= RISING_AT else "slowing" if pct <= SLOWING_AT else "steady"
        out.append({"category": cat, "label": pretty_category(cat), "history": weekly.tail(weeks).tolist(),
                    "forecast": fc, "recent_avg": recent_avg, "pct": pct, "trend": trend, "n": len(sigs)})
    return sorted(out, key=lambda c: c["pct"], reverse=True)


# --------------------------------------------------------------------- recommendations
def build_recommendations(signals: List[ProductSignal], cats: List[dict], limit: int = 6) -> List[Recommendation]:
    recs: List[Tuple[float, Recommendation]] = []
    w = signals[0].window if signals else 4

    for s in signals:
        if s.stock_state in ("urgent", "short"):
            days = s.days_of_stock
            urgent = s.stock_state == "urgent"
            recs.append((0 if urgent else 1, s.velocity or 99, Recommendation(
                "restock", "urgent" if urgent else "watch", f"{s.name}: restock soon",
                f"Shoppers are expected to buy about {s.forecast:,.0f} units next week. "
                f"You have {s.stock:,.0f} in stock" + (f", roughly {days:.0f} days' worth." if days is not None else "."),
                "You could sell out and miss sales you would otherwise have made.",
                "Consider replenishing this product before stock runs low.",
                "Review stock", "spotlight", sku=s.sku)))
        elif s.stock_state == "excess":
            weeks = s.stock / s.forecast if s.forecast > 0 else float("inf")
            recs.append((3, 1 / max(s.velocity or 0.01, 0.01), Recommendation(
                "overstock", "watch", f"{s.name}: more stock than demand",
                f"You hold about {weeks:.1f} weeks of stock, but only {s.forecast:,.0f} units are expected to sell next week.",
                "Slow-moving stock ties up money and often needs discounting later.",
                "Consider a gentle price reduction, or feature it in a promotion.",
                "Explore pricing" if s.price_is_reliable else "View insights",
                "pricing" if s.price_is_reliable else "spotlight", sku=s.sku)))

    for s in slowing(signals):
        if s.stock_state in ("urgent", "short"):
            continue  # restocking matters more than discounting something that may sell out
        sensitive = s.price_is_reliable and s.elasticity <= -1
        why = ("Shoppers react to price on this product, so a promotion may bring sales back."
               if sensitive else "Sales are slower than they have been, so it is worth checking what is holding it back.")
        recs.append((2, -s.trend_pct, Recommendation(
            "slowing", "watch", f"{s.name}: sales are slowing",
            f"The model expects about {s.forecast:,.0f} units next week, down from a recent average of {s.recent_avg:,.0f}.",
            why, "Review this product's pricing or promotion.",
            "Explore pricing" if s.price_is_reliable else "View insights",
            "pricing" if s.price_is_reliable else "spotlight", sku=s.sku)))

    for s in best_sellers(signals):
        if s.trend == "slowing" or s.stock_state in ("urgent", "short"):
            continue
        recs.append((4, s.units_window, Recommendation(
            "feature", "good", f"{s.name}: a proven favourite",
            f"It is one of your top sellers, with {s.units_window:,.0f} units over the last {w} weeks.",
            "Popular styles are the safest ones to put in front of shoppers.",
            "Consider featuring this popular style in your next promotion.",
            "View insights", "spotlight", sku=s.sku)))

    for c in cats:
        if c["trend"] == "rising":
            recs.append((5, c["pct"], Recommendation(
                "category", "good", f"{c['label']}: demand is climbing",
                f"The model expects {c['label'].lower()} sales to be about {c['pct']:.0%} higher next week than the recent average.",
                "Rising demand is easier to serve when stock and displays are ready.",
                "Demand may increase in this category. Check your stock for these products.",
                "See these products", "gallery", category=c["category"])))

    recs.sort(key=lambda t: (t[0], -t[1]))
    picked: List[Recommendation] = []
    per_kind: Dict[str, int] = {}
    for _, _, r in recs:
        if per_kind.get(r.kind, 0) >= 2:
            continue
        per_kind[r.kind] = per_kind.get(r.kind, 0) + 1
        picked.append(r)
        if len(picked) == limit:
            break
    return picked


# --------------------------------------------------------------------- stock file
def parse_stock_csv(df: pd.DataFrame, known_skus) -> Tuple[Dict[str, float], List[str]]:
    """
    Turn an uploaded table (columns sku, stock) into {sku: units}.
    Returns (stock, problems). Rows that cannot be used are skipped and reported.
    """
    problems: List[str] = []
    cols = {c.strip().lower(): c for c in df.columns}
    if "sku" not in cols or "stock" not in cols:
        return {}, ["The file needs two columns named sku and stock."]
    known = set(known_skus)
    stock: Dict[str, float] = {}
    unknown = []
    for _, row in df.iterrows():
        sku = str(row[cols["sku"]]).strip()
        val = pd.to_numeric(row[cols["stock"]], errors="coerce")
        if pd.isna(val) or val < 0:
            if str(row[cols["stock"]]).strip() not in ("", "nan"):
                problems.append(f"{sku}: '{row[cols['stock']]}' is not a valid stock number, so it was skipped.")
            continue
        if sku not in known:
            unknown.append(sku)
            continue
        stock[sku] = float(val)
    if unknown:
        problems.append(f"{len(unknown)} SKU(s) were not found in the sales data and were ignored: "
                        + ", ".join(unknown[:5]) + ("..." if len(unknown) > 5 else ""))
    if not stock and not problems:
        problems.append("No stock numbers were found in the file.")
    return stock, problems
