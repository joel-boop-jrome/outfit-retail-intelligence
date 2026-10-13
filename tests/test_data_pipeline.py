"""Cleaning, dataset import, time split and the pricing back-test simulator."""
import numpy as np
import pandas as pd
import pytest

from demand_forecasting.clean_data import clean_sales
from demand_forecasting.import_dataset import to_weekly


def _frame(n=12):
    return pd.DataFrame({
        "date": pd.date_range("2024-01-01", periods=n, freq="7D"), "sku": "A", "category": "tops",
        "price": 100.0, "promo_flag": 0, "units_sold": [50] * n})


def test_missing_column_is_an_error():
    with pytest.raises(ValueError, match="units_sold"):
        clean_sales(_frame().drop(columns=["units_sold"]))


def test_duplicates_gaps_and_bad_values_are_repaired():
    df = _frame()
    df = pd.concat([df, df.iloc[[3]]])                  # duplicate week
    df = df.drop(index=df.index[6]) if False else df[df["date"] != df["date"].iloc[6]]   # a missing week
    df.loc[df.index[2], "units_sold"] = -5              # negative units
    df.loc[df.index[4], "price"] = 0                    # bad price
    clean, report = clean_sales(df)
    assert report["duplicate_rows_merged"] == 1
    assert report["negative_units_set_missing"] == 1
    assert report["bad_price_set_missing"] == 1
    assert len(clean) == 12                              # gap inserted
    assert clean["units_sold"].notna().all() and (clean["price"] > 0).all()


def test_a_real_spike_is_capped():
    df = _frame(20)
    df.loc[10, "units_sold"] = 5000
    clean, _ = clean_sales(df)
    assert clean["units_sold"].max() <= 3 * 50 + 1


def test_clean_sales_leaves_good_data_unchanged():
    df = _frame()
    clean, _ = clean_sales(df)
    assert len(clean) == len(df) and clean["units_sold"].tolist() == df["units_sold"].tolist()


def test_import_dataset_turns_daily_rows_into_weeks():
    raw = pd.DataFrame({"when": pd.date_range("2024-01-01", periods=14),
                        "item": "X", "qty": 2, "cost": 10.0})
    weekly = to_weekly(raw, "when", "item", "qty", price_col="cost")
    assert list(weekly.columns) == ["date", "sku", "category", "price", "promo_flag", "units_sold"]
    assert weekly["units_sold"].tolist() == [14, 14]


def test_time_split_trains_on_the_past_and_tests_on_the_future():
    pytest.importorskip("lightgbm")
    from demand_forecasting.train_lightgbm import time_split
    feats = pd.DataFrame({"date": np.tile(pd.date_range("2024-01-01", periods=30, freq="7D"), 3),
                          "sku": np.repeat(list("ABC"), 30)})
    train, test, cutoff = time_split(feats, holdout_weeks=5)
    assert train["date"].max() < cutoff <= test["date"].min()
    assert test["date"].nunique() == 5
    assert set(test["sku"]) == set("ABC")                # every product appears in the test weeks


def test_backtest_simulation_respects_stock():
    from dynamic_pricing.backtest import simulate_sku
    rows = pd.DataFrame({"sku": "A", "price": [100.0] * 4, "units_sold": [10] * 4, "forecast": [10.0] * 4})
    lean = simulate_sku(rows, -1.0, 0.5, dynamic=False)
    assert lean["units"] == pytest.approx(20)            # only half of demand was ever in stock
    assert lean["stockout_weeks"] == 4
    plenty = simulate_sku(rows, -1.0, 2.0, dynamic=False)
    assert plenty["units"] == pytest.approx(40) and plenty["stockout_weeks"] == 0
    assert plenty["left_over"] == pytest.approx(40)
