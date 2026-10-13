"""
Compare every demand model on the same held-out weeks, one week ahead.

    python -m demand_forecasting.evaluate                  # last 12 weeks, all models (Prophet takes ~2 min)
    python -m demand_forecasting.evaluate --weeks 8 --skip-prophet

For each of the last N weeks and every SKU, each model predicts that week using only the weeks before it:
    naive last week, naive 4-week average          -> the baselines any real model must beat
    LightGBM, XGBoost                              -> trained once on weeks before the test window
    Prophet                                        -> refit on the past before every forecast (slow but fair)
Writes data/forecast_evaluation.json, which the dashboard's "How it works" tab displays.
"""
import argparse
import json
import logging
import warnings

import numpy as np
import pandas as pd

from demand_forecasting.features import build_feature_frame
from demand_forecasting.train_lightgbm import FEATURE_COLS, TARGET_COL, load_data, mape
from demand_forecasting.train_lightgbm import new_model as new_lgbm
from demand_forecasting.train_xgboost import new_model as new_xgb

OUT_PATH = "data/forecast_evaluation.json"


def scores(y, p):
    y, p = np.asarray(y, float), np.asarray(p, float)
    return {"mae": float(np.mean(np.abs(y - p))), "mape": mape(y, p),
            "wape": float(np.abs(y - p).sum() / max(y.sum(), 1.0))}


def prophet_predictions(raw: pd.DataFrame, test: pd.DataFrame):
    from prophet import Prophet
    logging.getLogger("cmdstanpy").setLevel(logging.CRITICAL)
    logging.getLogger("prophet").setLevel(logging.CRITICAL)
    preds = []
    for _, row in test.iterrows():
        hist = raw[(raw["sku"] == row["sku"]) & (raw["date"] < row["date"])][["date", "units_sold"]]
        hist = hist.rename(columns={"date": "ds", "units_sold": "y"})
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            m = Prophet(weekly_seasonality=False, yearly_seasonality=True).fit(hist)
            preds.append(max(0.0, float(m.predict(pd.DataFrame({"ds": [row["date"]]}))["yhat"].iloc[0])))
    return np.array(preds)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--weeks", type=int, default=12)
    ap.add_argument("--skip-prophet", action="store_true")
    args = ap.parse_args()

    raw = load_data()
    feats = build_feature_frame(raw)
    cutoff = np.sort(feats["date"].unique())[-args.weeks]
    train_df, test_df = feats[feats["date"] < cutoff], feats[feats["date"] >= cutoff].reset_index(drop=True)
    y = test_df[TARGET_COL].to_numpy()

    results = {
        "Naive: same as last week": scores(y, test_df["units_sold_lag_1"]),
        "Naive: 4-week average": scores(y, test_df["units_sold_rollmean_4"]),
        "LightGBM": scores(y, new_lgbm().fit(train_df[FEATURE_COLS], train_df[TARGET_COL]).predict(test_df[FEATURE_COLS])),
        "XGBoost": scores(y, np.maximum(new_xgb().fit(train_df[FEATURE_COLS], train_df[TARGET_COL]).predict(test_df[FEATURE_COLS]), 0)),
    }
    if not args.skip_prophet:
        print("Fitting Prophet once per SKU per week (this takes a couple of minutes)...")
        results["Prophet"] = scores(y, prophet_predictions(raw, test_df))

    print(f"\nLast {args.weeks} weeks, {test_df['sku'].nunique()} SKUs, {len(test_df)} forecasts, one week ahead")
    print(f"{'model':28s} {'MAE':>8s} {'MAPE':>8s} {'WAPE':>8s}")
    for name, r in sorted(results.items(), key=lambda kv: kv[1]["mae"]):
        print(f"{name:28s} {r['mae']:8.2f} {r['mape']:8.1%} {r['wape']:8.1%}")
    best = min(results, key=lambda k: results[k]["mae"])
    print(f"\nLowest error: {best}")
    with open(OUT_PATH, "w") as fh:
        json.dump({"weeks": args.weeks, "skus": int(test_df["sku"].nunique()), "forecasts": int(len(test_df)),
                   "horizon": "1 week ahead", "best": best, "models": results}, fh, indent=2)
    print(f"Saved {OUT_PATH}")


if __name__ == "__main__":
    main()
