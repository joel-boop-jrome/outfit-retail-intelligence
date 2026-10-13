"""
Feature engineering for demand forecasting: lag features, rolling
statistics, and calendar/seasonality features.
"""
import pandas as pd


def add_calendar_features(df: pd.DataFrame, date_col: str = "date") -> pd.DataFrame:
    df = df.copy()
    df[date_col] = pd.to_datetime(df[date_col])
    df["week_of_year"] = df[date_col].dt.isocalendar().week.astype(int)
    df["month"] = df[date_col].dt.month
    df["quarter"] = df[date_col].dt.quarter
    return df


def add_lag_features(df: pd.DataFrame, group_col: str = "sku",
                      target_col: str = "units_sold",
                      lags=(1, 2, 4, 8)) -> pd.DataFrame:
    df = df.sort_values([group_col, "date"]).copy()
    for lag in lags:
        df[f"{target_col}_lag_{lag}"] = df.groupby(group_col)[target_col].shift(lag)
    return df


def add_rolling_features(df: pd.DataFrame, group_col: str = "sku",
                          target_col: str = "units_sold",
                          windows=(4, 8)) -> pd.DataFrame:
    df = df.sort_values([group_col, "date"]).copy()
    for w in windows:
        df[f"{target_col}_rollmean_{w}"] = (
            df.groupby(group_col)[target_col]
            .shift(1)
            .rolling(w)
            .mean()
            .reset_index(level=0, drop=True)
        )
    return df


def build_feature_frame(df: pd.DataFrame) -> pd.DataFrame:
    df = add_calendar_features(df)
    df = add_lag_features(df)
    df = add_rolling_features(df)
    df = df.dropna().reset_index(drop=True)
    return df
