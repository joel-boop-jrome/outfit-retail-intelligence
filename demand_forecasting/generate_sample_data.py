"""
Generates a synthetic weekly sales dataset so Member 2 (and everyone
downstream) can build/test the pipeline before real retail data is
available. Replace with a real dataset loader once you have one
(e.g. Kaggle "Store Item Demand" or your own retailer's export).

Usage:
    python -m demand_forecasting.generate_sample_data
"""
import numpy as np
import pandas as pd

RNG = np.random.default_rng(42)

PRODUCTS = [f"SKU_{i:03d}" for i in range(1, 21)]
CATEGORIES = ["tops", "bottoms", "dresses", "outerwear", "accessories"]


def generate(n_weeks: int = 104, out_path: str = "data/weekly_sales.csv") -> pd.DataFrame:
    rows = []
    start = pd.Timestamp("2024-01-01")
    dates = [start + pd.Timedelta(weeks=i) for i in range(n_weeks)]

    for sku in PRODUCTS:
        category = RNG.choice(CATEGORIES)
        base_price = round(RNG.uniform(15, 120), 2)
        base_demand = RNG.uniform(20, 200)
        seasonality_amp = RNG.uniform(0.1, 0.4)
        trend = RNG.uniform(-0.05, 0.1)
        # True (negative) price elasticity baked into the simulation, so
        # that dynamic_pricing/elasticity.py has a real signal to recover
        # -- typical apparel elasticities are roughly -0.5 to -2.5.
        true_elasticity = RNG.uniform(-2.5, -0.5)

        # Independent price wandering (not tied to promo) so price has
        # variation the regression can actually use -- if price only ever
        # moves because of promo_flag, price and promo are collinear and
        # elasticity can't be identified.
        price_multiplier = 1 + np.cumsum(RNG.normal(0, 0.02, size=n_weeks))
        price_multiplier = np.clip(price_multiplier, 0.7, 1.3)

        for week_idx, date in enumerate(dates):
            seasonal = 1 + seasonality_amp * np.sin(2 * np.pi * week_idx / 52)
            trend_factor = 1 + trend * (week_idx / n_weeks)
            promo = RNG.choice([0, 1], p=[0.85, 0.15])
            price = base_price * price_multiplier[week_idx] * (0.8 if promo else 1.0)
            price = max(price, 1.0)
            noise = RNG.normal(1, 0.1)

            price_effect = (price / base_price) ** true_elasticity
            demand = max(
                0,
                base_demand * seasonal * trend_factor * price_effect
                * (1 + 0.3 * promo) * noise,
            )

            rows.append({
                "date": date,
                "sku": sku,
                "category": category,
                "price": round(price, 2),
                "promo_flag": promo,
                "units_sold": int(round(demand)),
            })

    df = pd.DataFrame(rows)
    import os
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    df.to_csv(out_path, index=False)
    print(f"Wrote {len(df)} rows to {out_path}")
    return df


if __name__ == "__main__":
    generate()
