"""
Database setup.

By default a local SQLite file (data/retail.db) is used, so nothing needs installing.
To use PostgreSQL (the abstract's second option) set the environment variable before
starting the API or the dashboard:

    set DATABASE_URL=postgresql+psycopg2://user:password@localhost:5432/retail     (Windows)
    export DATABASE_URL=postgresql+psycopg2://user:password@localhost:5432/retail  (Mac/Linux)
    python -m pip install psycopg2-binary

Tables
    products           one row per SKU: category, latest price, stock the retailer entered
    sales_records      the weekly sales history (copied from data/weekly_sales.csv)
    engagement_events  "Intent signals": what shoppers did in the try-on store
                       (read their body shape, viewed picks, tried a shirt on)
"""
import os
from datetime import datetime

from sqlalchemy import Column, DateTime, Float, Integer, String, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./data/retail.db")

_kwargs = {"connect_args": {"check_same_thread": False}} if DATABASE_URL.startswith("sqlite") else {"pool_pre_ping": True}
engine = create_engine(DATABASE_URL, **_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    sku = Column(String, unique=True, index=True, nullable=False)
    category = Column(String)
    current_price = Column(Float)
    current_stock = Column(Float)          # NULL until the retailer enters it


class SalesRecord(Base):
    __tablename__ = "sales_records"

    id = Column(Integer, primary_key=True, index=True)
    sku = Column(String, index=True, nullable=False)
    date = Column(DateTime, nullable=False)
    price = Column(Float)
    promo_flag = Column(Integer)
    units_sold = Column(Integer)


class EngagementEvent(Base):
    __tablename__ = "engagement_events"

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    kind = Column(String, index=True, nullable=False)   # shape_read | picks_viewed | tryon
    body_shape = Column(String)
    color_tone = Column(String)
    item = Column(String)                                # garment file or style id


def init_db():
    os.makedirs("data", exist_ok=True)
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
