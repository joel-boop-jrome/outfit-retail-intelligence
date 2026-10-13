"""
Service layer: the real work behind every API endpoint.

The FastAPI routes in main.py are thin wrappers around these functions, and the Streamlit
dashboard can call the same functions directly when the API server is not running (see
frontend/api_client.py). One implementation, two ways to reach it.
"""
import base64
from collections import Counter
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.database import EngagementEvent, Product, SalesRecord, SessionLocal, init_db
from cv_vto.style_recommender import recommend_styles
from demand_forecasting.predict import ForecastError, forecast_next_week
from dynamic_pricing.price_optimizer import recommend_price

SALES_CSV = "data/weekly_sales.csv"
EVENT_KINDS = ("shape_read", "size_read", "picks_viewed", "tryon")


# ----------------------------------------------------------------------------- database helpers
def _session(db: Optional[Session]):
    """(session, should_close). Lets service functions work with or without an injected session."""
    if db is not None:
        return db, False
    init_db()
    return SessionLocal(), True


def seed_from_csv(db: Optional[Session] = None, path: str = SALES_CSV) -> Dict[str, int]:
    """Copy the cleaned weekly sales into the database (once) and create one Product row per SKU."""
    from demand_forecasting.clean_data import clean_sales
    db, close = _session(db)
    try:
        if db.query(func.count(SalesRecord.id)).scalar():
            return {"sales_records": db.query(func.count(SalesRecord.id)).scalar(),
                    "products": db.query(func.count(Product.id)).scalar(), "seeded": 0}
        df, _ = clean_sales(pd.read_csv(path))
        db.bulk_insert_mappings(SalesRecord, [
            {"sku": r.sku, "date": r.date.to_pydatetime(), "price": float(r.price),
             "promo_flag": int(r.promo_flag), "units_sold": int(round(r.units_sold))}
            for r in df.itertuples()])
        for sku, d in df.sort_values("date").groupby("sku"):
            db.add(Product(sku=sku, category=str(d.iloc[-1]["category"]), current_price=float(d.iloc[-1]["price"]),
                           current_stock=None))
        db.commit()
        return {"sales_records": len(df), "products": df["sku"].nunique(), "seeded": len(df)}
    finally:
        if close:
            db.close()


# ----------------------------------------------------------------------------- products and stock
def list_products(db: Optional[Session] = None) -> List[dict]:
    db, close = _session(db)
    try:
        seed_from_csv(db)
        return [{"sku": p.sku, "category": p.category, "current_price": p.current_price,
                 "current_stock": p.current_stock}
                for p in db.query(Product).order_by(Product.sku).all()]
    finally:
        if close:
            db.close()


def get_stock_map(db: Optional[Session] = None) -> Dict[str, float]:
    """sku -> stock, only for products where the retailer has entered a number."""
    return {p["sku"]: p["current_stock"] for p in list_products(db) if p["current_stock"] is not None}


def set_stock(levels: Dict[str, float], db: Optional[Session] = None) -> int:
    """Save stock numbers. Unknown SKUs are ignored. Returns how many products were updated."""
    db, close = _session(db)
    try:
        seed_from_csv(db)
        n = 0
        for sku, qty in levels.items():
            p = db.query(Product).filter(Product.sku == sku).one_or_none()
            if p is not None and qty is not None and qty >= 0:
                p.current_stock = float(qty)
                n += 1
        db.commit()
        return n
    finally:
        if close:
            db.close()


def clear_stock(db: Optional[Session] = None) -> None:
    db, close = _session(db)
    try:
        db.query(Product).update({Product.current_stock: None})
        db.commit()
    finally:
        if close:
            db.close()


# ----------------------------------------------------------------------------- engagement ("intent signals")
def log_event(kind: str, body_shape: Optional[str] = None, color_tone: Optional[str] = None,
              item: Optional[str] = None, db: Optional[Session] = None) -> int:
    if kind not in EVENT_KINDS:
        raise ValueError(f"kind must be one of {EVENT_KINDS}")
    db, close = _session(db)
    try:
        ev = EngagementEvent(kind=kind, body_shape=body_shape, color_tone=color_tone, item=item)
        db.add(ev)
        db.commit()
        return ev.id
    finally:
        if close:
            db.close()


def engagement_summary(db: Optional[Session] = None, top: int = 5) -> dict:
    db, close = _session(db)
    try:
        events = db.query(EngagementEvent).all()
        by_kind = Counter(e.kind for e in events)
        shapes = Counter(e.body_shape for e in events if e.body_shape and e.kind in ("shape_read", "picks_viewed"))
        tryons = Counter(e.item for e in events if e.kind == "tryon" and e.item)
        sizes = Counter(e.item for e in events if e.kind == "size_read" and e.item)
        return {
            "total_events": len(events),
            "shape_reads": by_kind.get("shape_read", 0),
            "size_reads": by_kind.get("size_read", 0),
            "top_sizes": sizes.most_common(top),
            "picks_viewed": by_kind.get("picks_viewed", 0),
            "tryons": by_kind.get("tryon", 0),
            "top_shapes": shapes.most_common(top),
            "top_tryons": tryons.most_common(top),
        }
    finally:
        if close:
            db.close()


# ----------------------------------------------------------------------------- styles, forecasts, pricing
def styles_for(body_shape: str, color_tone: Optional[str] = None) -> List[str]:
    return recommend_styles(body_shape, color_tone=color_tone)


def forecast_all(prices: Optional[Dict[str, float]] = None) -> Dict[str, float]:
    """Next-week forecast for every SKU in the sales file (SKUs that cannot be forecast are left out)."""
    from demand_forecasting.predict import _load_history
    history = _load_history()
    out = {}
    for sku, d in history.groupby("sku"):
        price = (prices or {}).get(sku, float(d.sort_values("date").iloc[-1]["price"]))
        try:
            out[sku] = round(forecast_next_week(sku, price, 0), 1)
        except ForecastError:
            continue
    return out


def price_recommendation(sku, current_price, forecasted_demand, current_stock, elasticity):
    return recommend_price(sku=sku, current_price=current_price, forecasted_demand=forecasted_demand,
                           current_stock=current_stock, elasticity=elasticity)


# ----------------------------------------------------------------------------- body shape
def classify_ratios(shoulder_width: float, hip_width: float, waist_width: float) -> str:
    from cv_vto.body_shape import BodyRatios, BodyShapeEstimator
    ratios = BodyRatios(shoulder_width=shoulder_width, hip_width=hip_width, waist_width=waist_width,
                        shoulder_to_hip=shoulder_width / hip_width if hip_width else 0.0)
    return BodyShapeEstimator.classify(ratios)


def classify_image_bytes(data: bytes) -> dict:
    """
    Run the full vision pipeline on one photo: MediaPipe Pose + silhouette widths + classifier.
    Returns {"body_shape": str|None, "message": str, "ratios": dict|None}.
    """
    import cv2
    from cv_vto.body_shape import BodyShapeEstimator, estimate_tshirt_size
    frame = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
    if frame is None:
        raise ValueError("The file is not a readable image.")
    with BodyShapeEstimator(static_image_mode=True, model_complexity=1) as est:
        shape, ratios = est.classify_from_frame(frame)
    if ratios is None:
        return {"body_shape": None, "message": "No body found. Stand back so your head to hips are in view.", "ratios": None}
    if shape is None:
        return {"body_shape": None, "ratios": ratios.as_dict(),
                "message": "Your body was found but the outline was not clear enough to measure the waist. "
                           "Try plain lighting, a plain background, and arms slightly away from your sides."}
    return {"body_shape": shape, "ratios": ratios.as_dict(), "message": "ok",
            "tshirt_size": estimate_tshirt_size(ratios.size_width)}


def classify_image_b64(image_b64: str) -> dict:
    if "," in image_b64[:60]:               # accept "data:image/jpeg;base64,...."
        image_b64 = image_b64.split(",", 1)[1]
    return classify_image_bytes(base64.b64decode(image_b64))
