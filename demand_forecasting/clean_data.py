"""
Data cleaning for the weekly sales table (Member 2: "data cleaning").

Real retail exports are messy. Before features are built, `clean_sales` checks the
columns and repairs the problems below, and returns a short report so every fix is visible:

    - missing required columns          -> error (the pipeline cannot guess these)
    - unparseable dates / missing SKU   -> rows dropped
    - duplicate (sku, week) rows        -> sales summed, price averaged
    - negative or missing units         -> treated as missing
    - price <= 0 or missing             -> filled from the SKU's neighbouring weeks
    - missing weeks inside a SKU's run  -> inserted; units interpolated, promo set to 0
    - extreme spikes                    -> a week over 3x the rolling median is capped at 3x (counted in the report)

    python -m demand_forecasting.clean_data            # clean data/weekly_sales.csv and print the report
"""
import os
from typing import Dict, Tuple

import numpy as np
import pandas as pd

REQUIRED = ["date", "sku", "category", "price", "promo_flag", "units_sold"]
DATA_PATH = "data/weekly_sales.csv"


def clean_sales(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, int]]:
    missing = [c for c in REQUIRED if c not in df.columns]
    if missing:
        raise ValueError(f"Sales data is missing required column(s): {', '.join(missing)}")

    report: Dict[str, int] = {"rows_in": len(df)}
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    bad = df["date"].isna() | df["sku"].isna()
    report["dropped_bad_date_or_sku"] = int(bad.sum())
    df = df[~bad]

    for col in ("price", "promo_flag", "units_sold"):
        df[col] = pd.to_numeric(df[col], errors="coerce")
    report["negative_units_set_missing"] = int((df["units_sold"] < 0).sum())
    df.loc[df["units_sold"] < 0, "units_sold"] = np.nan
    report["bad_price_set_missing"] = int(((df["price"] <= 0) | df["price"].isna()).sum())
    df.loc[df["price"] <= 0, "price"] = np.nan
    df["category"] = df["category"].fillna("unknown")
    df["promo_flag"] = df["promo_flag"].fillna(0).clip(0, 1).round().astype(int)

    dup = df.duplicated(["sku", "date"], keep=False)
    report["duplicate_rows_merged"] = int(df.duplicated(["sku", "date"]).sum())
    if dup.any():
        agg = {"category": "first", "price": "mean", "promo_flag": "max", "units_sold": "sum"}
        df = df.groupby(["sku", "date"], as_index=False).agg(agg)

    pieces, filled_weeks, capped = [], 0, 0
    for sku, d in df.groupby("sku"):
        d = d.sort_values("date").set_index("date")
        full = pd.date_range(d.index.min(), d.index.max(), freq="7D")
        filled_weeks += len(full) - len(d)
        d = d.reindex(full)
        d["sku"] = sku
        d["category"] = d["category"].ffill().bfill()
        d["promo_flag"] = d["promo_flag"].fillna(0).astype(int)
        d["price"] = d["price"].interpolate(limit_direction="both")
        d["units_sold"] = d["units_sold"].interpolate(limit_direction="both")
        # a week more than 3x its own neighbourhood (9-week rolling median) is almost surely a data error
        cap = 3 * d["units_sold"].rolling(9, center=True, min_periods=3).median()
        spikes = d["units_sold"] > cap
        capped += int(spikes.sum())
        d["units_sold"] = d["units_sold"].where(~spikes, cap).round().astype(int)
        pieces.append(d.rename_axis("date").reset_index())
    out = pd.concat(pieces, ignore_index=True)[REQUIRED].sort_values(["sku", "date"]).reset_index(drop=True)
    report.update({"missing_weeks_inserted": int(filled_weeks), "spikes_capped": capped, "rows_out": len(out)})
    return out, report


def load_clean_sales(path: str = DATA_PATH) -> pd.DataFrame:
    return clean_sales(pd.read_csv(path))[0]


if __name__ == "__main__":
    if not os.path.exists(DATA_PATH):
        raise SystemExit(f"{DATA_PATH} not found. Run `python -m demand_forecasting.generate_sample_data` first.")
    cleaned, rep = clean_sales(pd.read_csv(DATA_PATH))
    print("Cleaning report:")
    for k, v in rep.items():
        print(f"  {k:28s} {v}")
