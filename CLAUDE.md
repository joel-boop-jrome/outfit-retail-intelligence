# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

Skeleton codebase for an SRM M.Sc. Applied Data Science mini project. It has four independent modules matching a four-member task division: CV/virtual try-on, demand forecasting, dynamic pricing, and a FastAPI+Streamlit backend/frontend. Modules communicate through well-known file paths (`data/weekly_sales.csv`, `data/lightgbm_demand_model.pkl`) and a small FastAPI surface rather than shared in-process state, so each module can be developed and tested in isolation.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Notes:
- `mediapipe` and `opencv-python` need a real webcam to run the interactive demos, but import fine headlessly for other code paths.
- `prophet` can be slow to install (pulls in `cmdstanpy`); `pip install prophet --no-cache-dir` fixes stale-wheel failures.
- `lightgbm` on macOS requires the OpenMP runtime (`libomp`, e.g. via Homebrew: `brew install libomp`) or it fails at import time with a `dlopen`/`libomp.dylib` error.

## Common commands

```bash
# Generate synthetic weekly sales data (data/weekly_sales.csv) -- run this first,
# most other modules read from this file
python -m demand_forecasting.generate_sample_data

# Train LightGBM demand model -> writes data/lightgbm_demand_model.pkl
python -m demand_forecasting.train_lightgbm

# Train Prophet per-SKU baseline
python -m demand_forecasting.train_prophet

# Log-log OLS price elasticity per SKU (reads data/weekly_sales.csv)
python -m dynamic_pricing.elasticity

# Body-shape classification + style recommendation logic (no webcam needed)
python -m cv_vto.style_recommender

# FastAPI backend (creates data/retail.db via SQLAlchemy on startup)
uvicorn backend.main:app --reload
# interactive API docs at http://127.0.0.1:8000/docs

# Streamlit two-tab dashboard (run backend separately if needed)
streamlit run frontend/app.py

# Live webcam demos (need a physical webcam)
python -m cv_vto.body_shape
python -m cv_vto.garment_overlay assets/garments/tshirt_01.png
```

Run the tests with `python -m pytest -q`.

## Architecture

```
[Webcam Feed] -> [MediaPipe Keypoint Extraction] -> [Body Shape Classification]
                                                            |
                                                            v
[Streamlit UI] <- [OpenCV Garment Overlay] <- [Style & Color Recommendation]
      |
      +-> [Intent Signals & Sales Data] -> [LightGBM Demand Forecast] -> [Price Optimization]
```

### Module boundaries and data flow

- **`cv_vto/`** — `body_shape.py` runs MediaPipe Pose on a frame and classifies into one of 4 shapes (`hourglass`, `rectangle`, `inverted_triangle`, `pear`) using shoulder/waist/hip landmark ratios. Waist width has no MediaPipe landmark, so it's approximated as the midpoint of shoulder/hip width (`BodyShapeEstimator._estimate_waist`) — a documented simplification, not a bug. `style_recommender.py` maps `(body_shape, color_tone)` to outfit suggestions via a lookup table (`BODY_SHAPE_STYLE_MAP`) and has no CV dependency, so it's the fastest module to iterate on without a webcam. `garment_overlay.py` does OpenCV affine-warp + alpha blending of a transparent garment PNG onto the live frame; garment `src_points` need tuning per garment image.
- **`demand_forecasting/`** — `generate_sample_data.py` is the canonical source of the `date, sku, category, price, promo_flag, units_sold` schema that every downstream module expects; swapping in a real dataset just means matching these column names. `features.py` builds lag/rolling/calendar features per SKU (`build_feature_frame`) and is shared by both training scripts. `train_lightgbm.py` and `train_prophet.py` are independent baselines — LightGBM needs `features.py`, Prophet works off raw per-SKU series.
- **`dynamic_pricing/`** — `elasticity.py` fits log-log OLS elasticity per SKU from `weekly_sales.csv` (`estimate_all`); `price_optimizer.py` (`recommend_price`) consumes an elasticity estimate + forecasted demand + current stock to produce a markdown/markup recommendation reacting to stock velocity. These are decoupled: elasticity is a statistical fit over historical data, pricing is a rules engine over its output plus live demand/stock signals.
- **`backend/`** — `database.py` defines the SQLAlchemy models (`Product`, `SalesRecord`) against SQLite (`data/retail.db`, created on startup via `init_db()`); swap `DATABASE_URL` for Postgres in production. `main.py` wires `cv_vto` and `dynamic_pricing` behind `/body-shape/classify` and `/pricing/recommend`. There is a known gap: no `/demand/forecast` endpoint yet to serve predictions from `data/lightgbm_demand_model.pkl` (marked with a `TODO` in `main.py`).
- **`frontend/`** — `app.py` is a two-tab Streamlit app. The "Customer" tab currently calls `cv_vto` functions directly rather than the FastAPI backend, and webcam try-on runs as a separate OpenCV window (not embedded in the browser) since Streamlit can't stream a raw OpenCV window — embedding would need `streamlit-webrtc`. The "Retailer" tab reads `data/weekly_sales.csv` directly and calls `dynamic_pricing.elasticity`/`price_optimizer` in-process (not through the backend API).

### Current state

- `backend/services.py` holds the logic behind every API route; `frontend/api_client.py` calls the API when it is up and the services directly otherwise.
- Tests live in `tests/` (`python -m pytest -q`). Body shape is measured from the MediaPipe segmentation mask (`cv_vto/silhouette.py`).
- Sales data is synthetic; body-shape accuracy on real people is not yet measured. See `VIVA_GUIDE.md` for limitations.
