"""
Trains a LightGBM regressor to forecast weekly units_sold per SKU.

Testing is by TIME: the last 20 weeks of every SKU are held out. (An earlier version split by row
order, which put whole SKUs in the test set and measured accuracy on products the model had never seen.)

Usage:
    python -m demand_forecasting.generate_sample_data   # if data missing
    python -m demand_forecasting.train_lightgbm
"""
import json
import os

import joblib
import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error

from demand_forecasting.clean_data import clean_sales
from demand_forecasting.features import build_feature_frame

DATA_PATH = "data/weekly_sales.csv"
MODEL_PATH = "data/lightgbm_demand_model.pkl"
METRICS_PATH = "data/lightgbm_metrics.json"

FEATURE_COLS = [
    "price", "promo_flag", "week_of_year", "month", "quarter",
    "units_sold_lag_1", "units_sold_lag_2", "units_sold_lag_4", "units_sold_lag_8",
    "units_sold_rollmean_4", "units_sold_rollmean_8",
]
CATEGORICAL_COLS = []  # add 'category', 'sku' as category dtype if using them directly
TARGET_COL = "units_sold"


HOLDOUT_WEEKS = 20  # the most recent weeks of EVERY SKU are held out for testing


def load_data() -> pd.DataFrame:
    if not os.path.exists(DATA_PATH):
        raise FileNotFoundError(
            f"{DATA_PATH} not found. Run "
            "`python -m demand_forecasting.generate_sample_data` first, "
            "or replace with your real dataset."
        )
    cleaned, report = clean_sales(pd.read_csv(DATA_PATH))
    print("Data cleaning:", {k: v for k, v in report.items() if v})
    return cleaned


def mape(y, p) -> float:
    """Mean absolute percentage error; weeks with 0 units use a denominator of 1."""
    y, p = np.asarray(y, dtype=float), np.asarray(p, dtype=float)
    return float(np.mean(np.abs(y - p) / np.maximum(y, 1.0)))


def time_split(features: pd.DataFrame, holdout_weeks: int = HOLDOUT_WEEKS):
    """Train on everything before the cutoff date, test on the weeks after it (all SKUs)."""
    cutoff = np.sort(features["date"].unique())[-holdout_weeks]
    return features[features["date"] < cutoff], features[features["date"] >= cutoff], pd.Timestamp(cutoff)


def new_model():
    return lgb.LGBMRegressor(n_estimators=300, learning_rate=0.05, num_leaves=31, random_state=42, verbose=-1)


def train():
    raw = load_data()
    features = build_feature_frame(raw)
    train_df, test_df, cutoff = time_split(features)

    # 1) honest test: fit on the past, predict the held-out recent weeks of products it has seen
    model = new_model().fit(train_df[FEATURE_COLS], train_df[TARGET_COL])
    preds = model.predict(test_df[FEATURE_COLS])
    y = test_df[TARGET_COL].to_numpy()
    mae = float(mean_absolute_error(y, preds))
    metrics = {
        "split": "time",
        "holdout_weeks": HOLDOUT_WEEKS,
        "cutoff_date": str(cutoff.date()),
        "mae": mae,
        "mape": mape(y, preds),
        "n_train": int(len(train_df)),
        "n_test": int(len(test_df)),
        "baseline_last_week": {"mae": float(mean_absolute_error(y, test_df["units_sold_lag_1"])),
                               "mape": mape(y, test_df["units_sold_lag_1"])},
        "baseline_4week_average": {"mae": float(mean_absolute_error(y, test_df["units_sold_rollmean_4"])),
                                   "mape": mape(y, test_df["units_sold_rollmean_4"])},
    }
    print(f"Last {HOLDOUT_WEEKS} weeks (from {cutoff.date()}), one week ahead:  "
          f"MAE {mae:.2f} | MAPE {metrics['mape']:.1%}")
    print(f"  naive 'same as last week':   MAE {metrics['baseline_last_week']['mae']:.2f} | "
          f"MAPE {metrics['baseline_last_week']['mape']:.1%}")
    print(f"  naive '4-week average':      MAE {metrics['baseline_4week_average']['mae']:.2f} | "
          f"MAPE {metrics['baseline_4week_average']['mape']:.1%}")

    # 2) the model that is actually served is refit on all data, so it also knows the latest weeks
    final = new_model().fit(features[FEATURE_COLS], features[TARGET_COL])
    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    joblib.dump(final, MODEL_PATH)
    with open(METRICS_PATH, "w") as f:
        json.dump(metrics, f, indent=2)
    print(f"Model saved to {MODEL_PATH}")
    return final, metrics


if __name__ == "__main__":
    train()
