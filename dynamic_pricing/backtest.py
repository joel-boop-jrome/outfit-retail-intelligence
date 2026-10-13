"""
Back-test the rule-based price optimiser against "keep the price" on held-out weeks.

    python -m dynamic_pricing.backtest

What is simulated (no real inventory data exists, so this is a SIMULATION, not proof from a real shop):
  * Last 12 weeks of every SKU whose price elasticity (estimated only from earlier weeks) is negative.
  * Demand at the price that was actually charged is the real units sold that week. If a policy charges a
    different price P instead of p, demand becomes  actual_units * (P / p) ** elasticity.
  * Each week new stock arrives and unsold stock carries over. Two supply situations, same for both policies:
        lean   : arrivals = 80% of that week's real demand  -> shortages likely  (stockout risk)
        excess : arrivals = 150% of that week's real demand -> stock piles up    (markdown pressure)
  * "static" keeps the actual price. "dynamic" asks recommend_price() every week using the LightGBM forecast
    (trained only on earlier weeks) and the stock on hand.
Reported per scenario: revenue, units sold, weeks with unmet demand (stockouts) and units left at the end.
Writes data/pricing_backtest.json for the dashboard's "How it works" tab.
"""
import json

import numpy as np
import pandas as pd

from demand_forecasting.features import build_feature_frame
from demand_forecasting.train_lightgbm import FEATURE_COLS, TARGET_COL, load_data, new_model
from dynamic_pricing.elasticity import estimate_all
from dynamic_pricing.price_optimizer import recommend_price

OUT_PATH = "data/pricing_backtest.json"
SCENARIOS = {"lean": 0.8, "excess": 1.5}


def simulate_sku(rows: pd.DataFrame, elasticity: float, supply_factor: float, dynamic: bool) -> dict:
    """rows: one SKU's test weeks with columns price, units_sold, forecast (one row per week, in order)."""
    stock, revenue, sold_total, stockout_weeks = 0.0, 0.0, 0.0, 0
    for r in rows.itertuples():
        stock += supply_factor * r.units_sold                       # this week's arrivals
        price = r.price
        if dynamic:
            price = recommend_price(r.sku, r.price, r.forecast, stock, elasticity).recommended_price
        demand = r.units_sold * (price / r.price) ** elasticity
        sold = min(demand, stock)
        stockout_weeks += int(demand > stock + 1e-9)
        stock -= sold
        revenue += sold * price
        sold_total += sold
    return {"revenue": revenue, "units": sold_total, "stockout_weeks": stockout_weeks, "left_over": stock}


def run(weeks: int = 12) -> dict:
    raw = load_data()
    feats = build_feature_frame(raw)
    cutoff = np.sort(feats["date"].unique())[-weeks]
    model = new_model().fit(feats[feats["date"] < cutoff][FEATURE_COLS], feats[feats["date"] < cutoff][TARGET_COL])
    test = feats[feats["date"] >= cutoff].copy()
    test["forecast"] = np.maximum(model.predict(test[FEATURE_COLS]), 0)

    elast = estimate_all(raw[raw["date"] < cutoff])
    usable = sorted(s for s, r in elast.items() if r.elasticity < 0)
    excluded = sorted(set(test["sku"]) - set(usable))

    result = {"weeks": weeks, "skus_simulated": len(usable), "skus_excluded_unreliable_elasticity": excluded,
              "scenarios": {}}
    for name, factor in SCENARIOS.items():
        agg = {"static": pd.Series(dtype=float), "dynamic": pd.Series(dtype=float)}
        for policy in agg:
            tot = pd.DataFrame([simulate_sku(test[test["sku"] == s].sort_values("date"), elast[s].elasticity,
                                             factor, policy == "dynamic") for s in usable]).sum()
            agg[policy] = tot
        result["scenarios"][name] = {
            "arrivals_vs_demand": factor,
            **{p: {k: float(v) for k, v in agg[p].items()} for p in agg},
        }
    return result


def main():
    res = run()
    print(f"Pricing back-test: last {res['weeks']} weeks, {res['skus_simulated']} SKUs "
          f"(left out, unreliable elasticity: {', '.join(res['skus_excluded_unreliable_elasticity']) or 'none'})")
    for name, sc in res["scenarios"].items():
        print(f"\nSupply '{name}' (arrivals = {sc['arrivals_vs_demand']:.0%} of demand)")
        print(f"  {'':8s} {'revenue':>12s} {'units sold':>11s} {'stockout wks':>13s} {'left over':>10s}")
        for p in ("static", "dynamic"):
            r = sc[p]
            print(f"  {p:8s} {r['revenue']:12,.0f} {r['units']:11,.0f} {r['stockout_weeks']:13.0f} {r['left_over']:10,.0f}")
    with open(OUT_PATH, "w") as fh:
        json.dump(res, fh, indent=2)
    print(f"\nSaved {OUT_PATH}. This is a simulation using estimated elasticities, not real-shop evidence.")


if __name__ == "__main__":
    main()
