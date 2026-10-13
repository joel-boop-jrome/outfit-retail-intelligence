"""
FastAPI backend: one REST surface over the vision, forecasting, pricing and data modules.
All real work lives in backend/services.py; these routes only validate input and map errors.

Run with:
    python -m uvicorn backend.main:app --reload
Interactive docs: http://127.0.0.1:8000/docs
"""
from typing import List, Optional

from fastapi import FastAPI, HTTPException

from backend import services
from backend.database import init_db
from backend.schemas import (
    BatchForecastResponse, BodyShapeRequest, BodyShapeResponse,
    DemandForecastRequest, DemandForecastResponse, EngagementSummary, EventIn,
    ImageShapeRequest, ImageShapeResponse, PriceRecommendationRequest,
    PriceRecommendationResponse, ProductOut, StockUpdate, StyleResponse,
)
from demand_forecasting.predict import ForecastError, forecast_next_week

app = FastAPI(
    title="Virtual Outfit Recommendation & Retail Intelligence API",
    version="0.2.0",
)


@app.on_event("startup")
def on_startup():
    init_db()


@app.get("/health")
def health():
    return {"status": "ok"}


# ---- shopper side -----------------------------------------------------------------
@app.post("/body-shape/classify", response_model=BodyShapeResponse)
def classify_body_shape(payload: BodyShapeRequest):
    """Classify from three widths already measured by a client."""
    shape = services.classify_ratios(payload.shoulder_width, payload.hip_width, payload.waist_width)
    return BodyShapeResponse(body_shape=shape, recommended_styles=services.styles_for(shape))


@app.post("/body-shape/from-image", response_model=ImageShapeResponse)
def body_shape_from_image(payload: ImageShapeRequest):
    """Full pipeline on one photo: pose + silhouette widths + classifier + style picks."""
    try:
        result = services.classify_image_b64(payload.image_base64)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        raise HTTPException(status_code=400, detail="The image could not be decoded.")
    shape = result.get("body_shape")
    result["recommended_styles"] = services.styles_for(shape) if shape else []
    return ImageShapeResponse(**result)


@app.get("/styles", response_model=StyleResponse)
def styles(body_shape: str, color_tone: Optional[str] = None):
    picks = services.styles_for(body_shape, color_tone)
    if not picks:
        raise HTTPException(status_code=404, detail=f"Unknown body shape: {body_shape}")
    return StyleResponse(body_shape=body_shape, color_tone=color_tone, recommended_styles=picks)


@app.post("/events", status_code=201)
def add_event(payload: EventIn):
    """Record a shopper action (intent signal) from the try-on store."""
    try:
        return {"id": services.log_event(payload.kind, payload.body_shape, payload.color_tone, payload.item)}
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


# ---- retailer side ----------------------------------------------------------------
@app.get("/products", response_model=List[ProductOut])
def products():
    return services.list_products()


@app.put("/stock")
def update_stock(payload: StockUpdate):
    """Save stock numbers the retailer entered, so they survive a page reload."""
    return {"updated": services.set_stock(payload.levels)}


@app.delete("/stock")
def clear_stock():
    services.clear_stock()
    return {"cleared": True}


@app.get("/events/summary", response_model=EngagementSummary)
def events_summary():
    return services.engagement_summary()


@app.post("/pricing/recommend", response_model=PriceRecommendationResponse)
def price_recommendation(payload: PriceRecommendationRequest):
    rec = services.price_recommendation(payload.sku, payload.current_price, payload.forecasted_demand,
                                        payload.current_stock, payload.elasticity)
    return PriceRecommendationResponse(**rec.__dict__)


@app.post("/demand/forecast", response_model=DemandForecastResponse)
def demand_forecast(payload: DemandForecastRequest):
    """Next-week unit forecast for a SKU at a given price / promo setting."""
    try:
        units = forecast_next_week(payload.sku, payload.price, payload.promo_flag)
    except ForecastError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return DemandForecastResponse(sku=payload.sku, forecasted_units=round(units, 1))


@app.get("/demand/forecast-all", response_model=BatchForecastResponse)
def demand_forecast_all():
    try:
        return BatchForecastResponse(forecasts=services.forecast_all())
    except ForecastError as e:
        raise HTTPException(status_code=404, detail=str(e))
