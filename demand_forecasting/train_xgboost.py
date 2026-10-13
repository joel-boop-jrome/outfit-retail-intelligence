"""
XGBoost version of the demand model, trained on the same features and the same time split as
LightGBM so the two can be compared fairly (the abstract names "LightGBM/XGBoost").

    python -m demand_forecasting.train_xgboost
"""
import numpy as np
import xgboost as xgb
from sklearn.metrics import mean_absolute_error

from demand_forecasting.features import build_feature_frame
from demand_forecasting.train_lightgbm import FEATURE_COLS, TARGET_COL, load_data, mape, time_split


def new_model():
    return xgb.XGBRegressor(n_estimators=300, learning_rate=0.05, max_depth=5, subsample=0.9,
                            colsample_bytree=0.9, random_state=42, n_jobs=2)


def train():
    features = build_feature_frame(load_data())
    train_df, test_df, cutoff = time_split(features)
    model = new_model().fit(train_df[FEATURE_COLS], train_df[TARGET_COL])
    preds = np.maximum(model.predict(test_df[FEATURE_COLS]), 0)
    y = test_df[TARGET_COL].to_numpy()
    out = {"mae": float(mean_absolute_error(y, preds)), "mape": mape(y, preds)}
    print(f"XGBoost, last weeks from {cutoff.date()}: MAE {out['mae']:.2f} | MAPE {out['mape']:.1%}")
    return model, out


if __name__ == "__main__":
    train()
