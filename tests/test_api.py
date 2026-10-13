import pytest

pytest.importorskip("mediapipe")
pytest.importorskip("lightgbm")
from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def test_health():
    assert client.get("/health").json() == {"status": "ok"}


def test_body_shape_endpoint():
    r = client.post("/body-shape/classify",
                    json={"shoulder_width": 1.0, "hip_width": 1.0, "waist_width": 0.7})
    assert r.status_code == 200
    assert r.json()["body_shape"] in {"hourglass", "rectangle", "inverted_triangle", "pear"}


def test_pricing_endpoint():
    r = client.post("/pricing/recommend", json={
        "sku": "S", "current_price": 100, "forecasted_demand": 200,
        "current_stock": 100, "elasticity": -0.5})
    assert r.status_code == 200
    assert r.json()["recommended_price"] > 100


@pytest.fixture(scope="module")
def trained():
    import os
    from demand_forecasting.generate_sample_data import generate as gen
    from demand_forecasting.train_lightgbm import train
    if not os.path.exists("data/weekly_sales.csv"):
        gen()
    train()


def test_demand_forecast_endpoint(trained):
    r = client.post("/demand/forecast", json={"sku": "SKU_001", "price": 50, "promo_flag": 0})
    assert r.status_code == 200
    assert r.json()["forecasted_units"] >= 0


def test_demand_forecast_unknown_sku(trained):
    r = client.post("/demand/forecast", json={"sku": "NOPE", "price": 50})
    assert r.status_code == 404
