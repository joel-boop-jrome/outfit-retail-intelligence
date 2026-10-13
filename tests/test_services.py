"""Service layer + new API endpoints, on a throw-away database."""
import importlib

import pytest

pytest.importorskip("lightgbm")
pytest.importorskip("mediapipe")


@pytest.fixture()
def svc(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path/'t.db'}")
    import backend.database as database
    importlib.reload(database)
    import backend.services as services
    importlib.reload(services)
    database.init_db()
    return services


def test_seed_creates_products_once(svc):
    first = svc.seed_from_csv()
    again = svc.seed_from_csv()
    assert first["products"] >= 1 and again["seeded"] == 0
    assert all(p["current_stock"] is None for p in svc.list_products())


def test_stock_round_trip_and_clear(svc):
    sku = svc.list_products()[0]["sku"]
    assert svc.set_stock({sku: 42, "NOPE": 5}) == 1
    assert svc.get_stock_map() == {sku: 42.0}
    svc.clear_stock()
    assert svc.get_stock_map() == {}


def test_events_are_counted(svc):
    svc.log_event("size_read", item="L")
    svc.log_event("tryon", "pear", "warm", "tshirt_navy.png")
    svc.log_event("tryon", None, None, "tshirt_navy.png")
    s = svc.engagement_summary()
    assert (s["size_reads"], s["tryons"], s["total_events"]) == (1, 2, 3)
    assert s["top_sizes"][0] == ("L", 1)
    assert s["top_tryons"][0] == ("tshirt_navy.png", 2)
    with pytest.raises(ValueError):
        svc.log_event("bogus")


def test_new_endpoints(svc):
    from fastapi.testclient import TestClient
    import backend.main as main
    importlib.reload(main)
    c = TestClient(main.app)
    assert c.get("/styles", params={"body_shape": "pear"}).status_code == 200
    assert c.get("/styles", params={"body_shape": "alien"}).status_code == 404
    assert c.post("/events", json={"kind": "tryon", "item": "x.png"}).status_code == 201
    assert c.post("/events", json={"kind": "nope"}).status_code == 422
    assert c.get("/events/summary").json()["tryons"] == 1
    skus = [p["sku"] for p in c.get("/products").json()]
    assert c.put("/stock", json={"levels": {skus[0]: 10}}).json()["updated"] == 1
    assert c.post("/body-shape/from-image", json={"image_base64": "not-an-image"}).status_code == 400
    bad = c.post("/body-shape/from-image", json={"image_base64": "aGVsbG8="})
    assert bad.status_code == 400


def test_image_with_no_person(svc):
    import cv2, numpy as np
    blank = np.full((240, 320, 3), 200, np.uint8)
    ok, buf = cv2.imencode(".jpg", blank)
    r = svc.classify_image_bytes(buf.tobytes())
    assert r["body_shape"] is None and "No body" in r["message"]
