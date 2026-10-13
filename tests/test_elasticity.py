import numpy as np
import pandas as pd
import pytest

from dynamic_pricing.elasticity import estimate_elasticity_for_sku


def _synthetic(true_elasticity, n=120, seed=0):
    rng = np.random.default_rng(seed)
    price = rng.uniform(20, 80, n)
    units = 1000 * price ** true_elasticity * np.exp(rng.normal(0, 0.05, n))
    return pd.DataFrame({"sku": "A", "price": price, "units_sold": units, "promo_flag": rng.integers(0, 2, n)})


def test_recovers_known_elasticity():
    res = estimate_elasticity_for_sku(_synthetic(-1.5), "A")
    assert res.elasticity == pytest.approx(-1.5, abs=0.15)
    assert res.r_squared > 0.9


def test_too_few_observations_raises():
    df = _synthetic(-1.0, n=5)
    with pytest.raises(ValueError):
        estimate_elasticity_for_sku(df, "A")
