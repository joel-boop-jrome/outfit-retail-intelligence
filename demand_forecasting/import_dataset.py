"""
Turn any retail sales export (daily or weekly rows) into the weekly table the project uses.

    python -m demand_forecasting.import_dataset --input train.csv \
        --date-col date --sku-col item --units-col sales --price-col price \
        [--category-col family] [--promo-col onpromotion] [--top 30] [--out data/weekly_sales.csv]

Rows are grouped by SKU and week (weeks start Monday): units are summed, price averaged, promo = 1 if any
day was on promotion. Missing price -> a constant 1.0 (price elasticity is then meaningless and flagged).
After importing, run `python -m demand_forecasting.train_lightgbm` again.
"""
import argparse

import pandas as pd


def to_weekly(df: pd.DataFrame, date_col, sku_col, units_col, price_col=None, category_col=None,
              promo_col=None, top=None) -> pd.DataFrame:
    d = pd.DataFrame({
        "date": pd.to_datetime(df[date_col], errors="coerce"),
        "sku": df[sku_col].astype(str),
        "units_sold": pd.to_numeric(df[units_col], errors="coerce"),
        "price": pd.to_numeric(df[price_col], errors="coerce") if price_col else 1.0,
        "category": df[category_col].astype(str) if category_col else "all",
        "promo_flag": (pd.to_numeric(df[promo_col], errors="coerce").fillna(0) > 0).astype(int) if promo_col else 0,
    }).dropna(subset=["date", "units_sold"])
    d["date"] = d["date"].dt.to_period("W-SUN").dt.start_time
    if top:
        keep = d.groupby("sku")["units_sold"].sum().nlargest(top).index
        d = d[d["sku"].isin(keep)]
    weekly = d.groupby(["sku", "date"], as_index=False).agg(
        category=("category", "first"), price=("price", "mean"),
        promo_flag=("promo_flag", "max"), units_sold=("units_sold", "sum"))
    weekly["units_sold"] = weekly["units_sold"].clip(lower=0).round().astype(int)
    weekly["price"] = weekly["price"].round(2)
    return weekly[["date", "sku", "category", "price", "promo_flag", "units_sold"]].sort_values(["sku", "date"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--date-col", required=True)
    ap.add_argument("--sku-col", required=True)
    ap.add_argument("--units-col", required=True)
    ap.add_argument("--price-col")
    ap.add_argument("--category-col")
    ap.add_argument("--promo-col")
    ap.add_argument("--top", type=int, help="keep only the N best-selling SKUs")
    ap.add_argument("--out", default="data/weekly_sales.csv")
    a = ap.parse_args()
    weekly = to_weekly(pd.read_csv(a.input), a.date_col, a.sku_col, a.units_col, a.price_col,
                       a.category_col, a.promo_col, a.top)
    weekly.to_csv(a.out, index=False)
    print(f"Wrote {len(weekly)} weekly rows for {weekly['sku'].nunique()} SKUs to {a.out}")
    if not a.price_col:
        print("Warning: no price column given, so price is constant and elasticity cannot be estimated.")


if __name__ == "__main__":
    main()
