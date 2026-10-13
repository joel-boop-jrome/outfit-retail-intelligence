"""
Member 3 module: Price Elasticity of Demand (PED).

Estimates elasticity per SKU using a log-log OLS regression:
    log(units_sold) = beta_0 + beta_1 * log(price) + controls
so that beta_1 is (approximately) the price elasticity of demand.

Usage:
    python -m dynamic_pricing.elasticity
"""
import os
from dataclasses import dataclass
from typing import Dict

import numpy as np
import pandas as pd

DATA_PATH = "data/weekly_sales.csv"


@dataclass
class ElasticityResult:
    sku: str
    elasticity: float
    r_squared: float
    n_obs: int

    def interpretation(self) -> str:
        if self.elasticity <= -1:
            return "elastic (demand highly sensitive to price)"
        elif -1 < self.elasticity < 0:
            return "inelastic (demand mildly sensitive to price)"
        else:
            return "unexpected sign -- inspect data quality"


def estimate_elasticity_for_sku(df: pd.DataFrame, sku: str) -> ElasticityResult:
    sku_df = df[df["sku"] == sku].copy()
    sku_df = sku_df[(sku_df["price"] > 0) & (sku_df["units_sold"] > 0)]
    if len(sku_df) < 10:
        raise ValueError(f"Not enough observations for sku={sku} (need >= 10)")

    sku_df["log_price"] = np.log(sku_df["price"])
    sku_df["log_units"] = np.log(sku_df["units_sold"])

    # Ordinary least squares with numpy (same result as statsmodels.OLS, without that heavy dependency)
    X = np.column_stack([np.ones(len(sku_df)), sku_df["log_price"], sku_df["promo_flag"]])
    y = sku_df["log_units"].to_numpy()
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ beta
    ss_tot = float(((y - y.mean()) ** 2).sum())
    r_squared = 1.0 - float((resid ** 2).sum()) / ss_tot if ss_tot > 0 else 0.0

    return ElasticityResult(
        sku=sku,
        elasticity=float(beta[1]),
        r_squared=r_squared,
        n_obs=len(sku_df),
    )


def estimate_all(df: pd.DataFrame) -> Dict[str, ElasticityResult]:
    results = {}
    for sku in df["sku"].unique():
        try:
            results[sku] = estimate_elasticity_for_sku(df, sku)
        except ValueError:
            continue
    return results


if __name__ == "__main__":
    if not os.path.exists(DATA_PATH):
        raise SystemExit(
            f"{DATA_PATH} not found. Run "
            "`python -m demand_forecasting.generate_sample_data` first."
        )
    data = pd.read_csv(DATA_PATH)
    all_results = estimate_all(data)
    for sku, res in list(all_results.items())[:5]:
        print(f"{sku}: elasticity={res.elasticity:.2f} "
              f"({res.interpretation()}), R^2={res.r_squared:.2f}, n={res.n_obs}")
