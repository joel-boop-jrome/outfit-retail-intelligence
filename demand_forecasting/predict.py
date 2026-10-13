"""
Serves next-week demand forecasts from the trained LightGBM model.

The model uses lag/rolling features, so a forecast for a SKU is built from
that SKU's recent history in data/weekly_sales.csv plus the price and
promo flag the caller wants to test.
"""
import os
from functools import lru_cache

import joblib
import pandas as pd

from demand_forecasting.train_lightgbm import DATA_PATH, FEATURE_COLS, MODEL_PATH

MIN_HISTORY_WEEKS = 8  # needs lag_8 and rollmean_8


class ForecastError(Exception):
    """Raised when a forecast cannot be produced (missing model/data/SKU)."""


@lru_cache(maxsize=1)
def _load_model(path: str = MODEL_PATH):
    if not os.path.exists(path):
        raise ForecastError(
            f"{path} not found. Run `python -m demand_forecasting.train_lightgbm` first."
        )
    return joblib.load(path)


@lru_cache(maxsize=4)
def _cached_history(path: str, mtime: float) -> pd.DataFrame:
    from demand_forecasting.clean_data import clean_sales
    return clean_sales(pd.read_csv(path))[0]


def _load_history(path: str = DATA_PATH) -> pd.DataFrame:
    if not os.path.exists(path):
        raise ForecastError(
            f"{path} not found. Run `python -m demand_forecasting.generate_sample_data` first."
        )
    return _cached_history(path, os.path.getmtime(path))


def build_next_week_features(history: pd.DataFrame, price: float, promo_flag: int) -> pd.DataFrame:
    """One-row feature frame for the week after the last observed week."""
    history = history.sort_values("date")
    if len(history) < MIN_HISTORY_WEEKS:
        raise ForecastError(f"Need at least {MIN_HISTORY_WEEKS} weeks of history.")
    units = history["units_sold"].to_numpy()
    next_date = history["date"].iloc[-1] + pd.Timedelta(weeks=1)
    row = {
        "price": float(price),
        "promo_flag": int(promo_flag),
        "week_of_year": int(next_date.isocalendar().week),
        "month": int(next_date.month),
        "quarter": int(next_date.quarter),
        "units_sold_lag_1": units[-1],
        "units_sold_lag_2": units[-2],
        "units_sold_lag_4": units[-4],
        "units_sold_lag_8": units[-8],
        "units_sold_rollmean_4": units[-4:].mean(),
        "units_sold_rollmean_8": units[-8:].mean(),
    }
    return pd.DataFrame([row])[FEATURE_COLS]


def forecast_next_week(sku: str, price: float, promo_flag: int = 0) -> float:
    model = _load_model()
    history = _load_history()
    sku_hist = history[history["sku"] == sku]
    if sku_hist.empty:
        raise ForecastError(f"Unknown SKU: {sku}")
    features = build_next_week_features(sku_hist, price, promo_flag)
    return max(0.0, float(model.predict(features)[0]))
