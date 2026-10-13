"""
Trains a Prophet model per-SKU for weekly demand forecasting -- useful
as a baseline / comparison against LightGBM, and gives clean seasonality
decomposition plots for the report.

Usage:
    python -m demand_forecasting.train_prophet --sku SKU_001
"""
import argparse
import os

import pandas as pd
from prophet import Prophet

DATA_PATH = "data/weekly_sales.csv"


def train_for_sku(sku: str, periods: int = 12):
    if not os.path.exists(DATA_PATH):
        raise FileNotFoundError(
            f"{DATA_PATH} not found. Run "
            "`python -m demand_forecasting.generate_sample_data` first."
        )
    df = pd.read_csv(DATA_PATH, parse_dates=["date"])
    sku_df = df[df["sku"] == sku][["date", "units_sold"]].rename(
        columns={"date": "ds", "units_sold": "y"}
    )
    if sku_df.empty:
        raise ValueError(f"No rows found for sku={sku}")

    model = Prophet(weekly_seasonality=False, yearly_seasonality=True)
    model.fit(sku_df)

    future = model.make_future_dataframe(periods=periods, freq="W")
    forecast = model.predict(future)
    print(forecast[["ds", "yhat", "yhat_lower", "yhat_upper"]].tail(periods))
    return model, forecast


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--sku", default="SKU_001")
    parser.add_argument("--periods", type=int, default=12)
    args = parser.parse_args()
    train_for_sku(args.sku, args.periods)
