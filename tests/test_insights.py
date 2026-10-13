import pandas as pd
import pytest

from frontend import insights as ix


class _El:
    def __init__(self, e, r2=0.6):
        self.elasticity, self.r_squared = e, r2


def make_df():
    weeks = pd.date_range("2025-01-06", periods=12, freq="W-MON")
    rows = []
    for sku, cat, base in [("A", "tops", 100), ("B", "tops", 50), ("C", "bottoms", 80), ("D", "bottoms", 20)]:
        for i, d in enumerate(weeks):
            rows.append(dict(date=d, sku=sku, category=cat, price=50.0, promo_flag=0, units_sold=base))
    return pd.DataFrame(rows)


FORECASTS = {"A": (130.0, True), "B": (50.0, True), "C": (60.0, True), "D": (20.0, True)}
ELAST = {"A": _El(-0.6), "B": _El(-1.4), "C": _El(-1.5), "D": _El(0.3)}


def signals(stock=None):
    return ix.build_signals(make_df(), FORECASTS, ELAST, stock, window=4)


def by(sigs):
    return {s.sku: s for s in sigs}


def test_trend_labels():
    s = by(signals())
    assert s["A"].trend == "rising" and s["B"].trend == "steady" and s["C"].trend == "slowing"


def test_best_sellers_are_top_three_by_units():
    assert {s.sku for s in ix.best_sellers(signals())} == {"A", "C", "B"}


def test_no_stock_means_no_stock_alerts():
    sigs = signals()
    assert ix.stock_watch(sigs) == []
    assert all(s.stock_state is None for s in sigs)
    assert not any(r.kind in ("restock", "overstock") for r in ix.build_recommendations(sigs, ix.category_trends(make_df(), sigs)))


def test_stock_states_and_restock_recommendation():
    sigs = signals({"A": 40, "B": 50, "C": 200})
    s = by(sigs)
    assert s["A"].stock_state == "urgent"          # 130 vs 40
    assert s["B"].stock_state == "ok"
    assert s["C"].stock_state == "excess"          # 60 vs 200
    assert [x.sku for x in ix.stock_watch(sigs)] == ["A"]
    kinds = [r.kind for r in ix.build_recommendations(sigs, ix.category_trends(make_df(), sigs))]
    assert "restock" in kinds and "overstock" in kinds


def test_price_ideas_do_not_invent_prices_without_stock():
    s = by(signals())
    assert ix.price_idea(s["C"])["kind"] == "review" and ix.price_idea(s["C"])["suggested"] is None
    assert ix.price_idea(s["A"])["kind"] == "room"
    assert ix.price_idea(s["D"]) is None            # positive elasticity: unreliable


def test_price_idea_with_stock_uses_price_rule():
    s = by(signals({"A": 40}))
    idea = ix.price_idea(s["A"])
    assert idea["kind"] == "raise" and idea["suggested"] > s["A"].price


def test_describe_always_has_cta_and_tone():
    for s in signals({"A": 40}):
        info = ix.describe(s)
        assert info["cta"] and info["tone"] in {"good", "watch", "urgent", "neutral"}


def test_category_trends_and_recommendations_limit():
    sigs = signals()
    cats = ix.category_trends(make_df(), sigs)
    assert {c["category"] for c in cats} == {"tops", "bottoms"}
    assert len(ix.build_recommendations(sigs, cats, limit=2)) <= 2


def test_parse_stock_csv():
    stock, problems = ix.parse_stock_csv(pd.DataFrame({"SKU": ["A", "B", "Z", "C"], "Stock": [10, "x", 5, 7]}), ["A", "B", "C"])
    assert stock == {"A": 10.0, "C": 7.0}
    assert len(problems) == 2
    assert ix.parse_stock_csv(pd.DataFrame({"a": [1]}), ["A"])[0] == {}


def test_retailer_page_renders_without_error():
    """Runs only the retailer page (the shopper tab's webcam widget needs a real browser)."""
    from streamlit.testing.v1 import AppTest

    def page():
        import sys
        sys.path.insert(0, ".")
        from frontend import retail_page, retail_style
        retail_style.inject()
        retail_page.render()

    at = AppTest.from_function(page, default_timeout=60).run()
    assert not at.exception, [e.value for e in at.exception]
    assert any("made smarter" in m.value for m in at.markdown)
    # pressing a product button opens the spotlight without errors
    at.button(key="cta_SKU_001").click().run()
    assert not at.exception, [e.value for e in at.exception]
    assert at.session_state["rt_focus"] == "SKU_001"


def test_friendly_names_unique_and_typed():
    import pandas as pd
    from frontend.product_names import friendly_names
    df = pd.read_csv("data/weekly_sales.csv").drop_duplicates("sku")
    names = friendly_names(df[["sku", "category"]].itertuples(index=False, name=None))
    assert len(names) == df["sku"].nunique() == len(set(names.values()))
    assert not any(n.startswith("SKU") for n in names.values())
    cat = dict(zip(df["sku"], df["category"]))
    assert any(w in names[[k for k, c in cat.items() if c == "dresses"][0]] for w in ("Dress",))
    assert names == friendly_names(df[["sku", "category"]].itertuples(index=False, name=None))
