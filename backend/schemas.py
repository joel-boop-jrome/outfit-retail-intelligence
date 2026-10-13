"""Pydantic request/response models for the FastAPI backend."""
from datetime import date
from typing import Dict, List, Optional

from pydantic import BaseModel


class BodyShapeRequest(BaseModel):
    shoulder_width: float
    hip_width: float
    waist_width: float


class BodyShapeResponse(BaseModel):
    body_shape: str
    recommended_styles: list[str]


class ImageShapeRequest(BaseModel):
    image_base64: str           # a JPEG/PNG photo, optionally as a data: URL


class ImageShapeResponse(BaseModel):
    body_shape: Optional[str] = None
    message: str
    tshirt_size: Optional[str] = None
    ratios: Optional[Dict[str, float]] = None
    recommended_styles: List[str] = []


class StyleResponse(BaseModel):
    body_shape: str
    color_tone: Optional[str] = None
    recommended_styles: List[str]


class ProductOut(BaseModel):
    sku: str
    category: Optional[str] = None
    current_price: Optional[float] = None
    current_stock: Optional[float] = None


class StockUpdate(BaseModel):
    levels: Dict[str, float]


class EventIn(BaseModel):
    kind: str                   # size_read | picks_viewed | tryon (shape_read still accepted)
    body_shape: Optional[str] = None
    color_tone: Optional[str] = None
    item: Optional[str] = None


class EngagementSummary(BaseModel):
    total_events: int
    shape_reads: int
    size_reads: int = 0
    top_sizes: List[List] = []
    picks_viewed: int
    tryons: int
    top_shapes: List[List]
    top_tryons: List[List]


class BatchForecastResponse(BaseModel):
    forecasts: Dict[str, float]


class DemandForecastRequest(BaseModel):
    sku: str
    price: float
    promo_flag: int = 0


class DemandForecastResponse(BaseModel):
    sku: str
    forecasted_units: float


class PriceRecommendationRequest(BaseModel):
    sku: str
    current_price: float
    forecasted_demand: float
    current_stock: float
    elasticity: float


class PriceRecommendationResponse(BaseModel):
    sku: str
    current_price: float
    recommended_price: float
    pct_change: float
    reason: str
