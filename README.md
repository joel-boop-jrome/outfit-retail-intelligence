# Virtual Outfit Recommendation and Dynamic Retail Intelligence

Skeleton codebase for the SRM M.Sc. Applied Data Science mini project
(Semester III). Matches the abstract's four-member task division so
each of you can build inside your own folder without stepping on each
other's code.

## Project structure

```
outfit_retail_intelligence/
├── cv_vto/                 # Member 1: pose extraction, body shape, garment overlay
│   ├── body_shape.py
│   ├── garment_overlay.py
│   └── style_recommender.py
├── demand_forecasting/      # Member 2: data, features, LightGBM/Prophet
│   ├── generate_sample_data.py
│   ├── features.py
│   ├── train_lightgbm.py
│   └── train_prophet.py
├── dynamic_pricing/         # Member 3: elasticity + price rules
│   ├── elasticity.py
│   └── price_optimizer.py
├── backend/                 # Member 4: FastAPI + SQLite
│   ├── database.py
│   ├── schemas.py
│   └── main.py
├── frontend/                 # Member 4: Streamlit two-sided UI
│   └── app.py
├── data/                     # generated/trained artifacts (gitignored except sample scripts)
├── notebooks/                 # exploratory analysis / report figures
└── requirements.txt
```

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Some notes on install:
- `mediapipe` and `opencv-python` need a real webcam-capable machine to
  run the interactive demos; they still import fine on a headless
  server for unit tests.
- `prophet` can be slow to install the first time (it pulls in
  `cmdstanpy`). If it fails on your machine, `pip install prophet
  --no-cache-dir` usually fixes stale wheel issues.

## Quickstart: run each module end to end

```bash
# 1. Generate synthetic sales data (stand-in until you have a real dataset)
python -m demand_forecasting.generate_sample_data

# 2. Train the demand forecasting model
python -m demand_forecasting.train_lightgbm

# 3. Check price elasticity per SKU
python -m dynamic_pricing.elasticity

# 4. Test body-shape classification + style recommendation logic
python -m cv_vto.style_recommender

# 5. Run the FastAPI backend
uvicorn backend.main:app --reload
# then open http://127.0.0.1:8000/docs for the interactive API explorer

# 6. Run the Streamlit dashboard (separate terminal)
streamlit run frontend/app.py

# 7. Try the live webcam body-shape demo (needs a webcam)
python -m cv_vto.body_shape

# 8. Try the live webcam garment overlay demo (needs a webcam + a transparent PNG garment)
python -m cv_vto.garment_overlay assets/garments/tshirt_01.png
```

## Team task map (from the abstract)

| Member | Module | Where to work |
|---|---|---|
| 1 | CV & Virtual Try-On | `cv_vto/` |
| 2 | Demand Forecasting | `demand_forecasting/` |
| 3 | Dynamic Pricing | `dynamic_pricing/` |
| 4 | Backend & Dashboard | `backend/`, `frontend/` |

## What's already stubbed vs. what you still need to build

**Already working (skeleton level):**
- MediaPipe pose extraction + rule-based body shape classification (4 classes)
- OpenCV affine-warp garment overlay with alpha blending
- Style recommendation lookup table (body shape + color tone)
- Synthetic weekly sales data generator (20 SKUs, 2 years, promo/seasonality/trend)
- Feature engineering: lags, rolling means, calendar features
- LightGBM demand forecasting training script with train/test MAE + MAPE
- Prophet per-SKU forecasting baseline
- Log-log OLS price elasticity estimation per SKU
- Rule-based markdown/markup price recommender that reacts to stock velocity + elasticity
- FastAPI backend with `/body-shape/classify` and `/pricing/recommend` endpoints, SQLite models
- Streamlit two-tab dashboard (customer style recommender + retailer analytics)

**You still need to:**
1. Replace the waist-width heuristic in `cv_vto/body_shape.py` with something
   more accurate (e.g. selfie segmentation contour width) if your evaluator
   wants a stronger CV justification -- currently it's a documented
   simplification since MediaPipe Pose has no waist landmark.
2. Get real garment PNGs with transparent backgrounds and tune the
   `src_points` in `garment_overlay.py` to match each garment's actual
   shoulder-seam pixel positions.
3. Swap the synthetic dataset for a real one (e.g. a Kaggle retail sales
   dataset) once you pick a data source -- keep the same column names
   (`date, sku, category, price, promo_flag, units_sold`) and everything
   downstream keeps working.
4. Add a `/demand/forecast` FastAPI endpoint that loads
   `data/lightgbm_demand_model.pkl` and serves predictions (there's a
   `TODO` marker for this in `backend/main.py`).
5. Wire the Streamlit "Customer" tab to `streamlit-webrtc` (or a similar
   library) so webcam try-on runs inside the browser instead of a
   separate OpenCV window -- needed for the "unified web dashboard" goal
   in the abstract.
6. Add tests (a `tests/` folder with `pytest`) for the classification
   thresholds and elasticity estimation once you have real data to
   validate against.
7. Write up the report: problem statement, literature review, system
   architecture diagram (the abstract already has an ASCII version you
   can turn into a proper figure), results/evaluation, and screenshots
   of the working dashboard.

## Suggested timeline (adjust to your semester deadlines)

1. **Week 1-2:** Environment setup, synthetic/real data collected, each
   member's skeleton running locally.
2. **Week 3-4:** Body shape classification tuned + tested on real people;
   LightGBM/Prophet trained and compared on real data; elasticity model
   validated.
3. **Week 5-6:** Garment overlay working smoothly in real time; pricing
   rules tuned; FastAPI endpoints completed and connected to Streamlit.
4. **Week 7:** Integration testing across all four modules end to end.
5. **Week 8:** Report writing, results/evaluation section, demo
   recording, final polish.

## Architecture (from the abstract)

```
[Webcam Feed] -> [MediaPipe Keypoint Extraction] -> [Body Shape Classification]
                                                            |
                                                            v
[Streamlit UI] <- [OpenCV Garment Overlay] <- [Style & Color Recommendation]
      |
      +-> [Intent Signals & Sales Data] -> [LightGBM Demand Forecast] -> [Price Optimization]
```

## Retailers page (insight-first)

`frontend/retail_page.py` builds the "For retailers" tab. Logic lives in `frontend/insights.py` (no Streamlit), drawings in `frontend/retail_art.py`, styling in `frontend/retail_style.py`.

- **Stock alerts** need stock levels, because `weekly_sales.csv` has no inventory column. Upload a CSV with columns `sku,stock` in the "Add your stock levels" box (a blank template can be downloaded there).
- **Product names**: products are shown with readable names built from their outfit type (e.g. "Olive Utility Jacket", see `frontend/product_names.py`); the code (SKU_002) stays as small text. Add a `product_name` column to `data/weekly_sales.csv` to use your own names instead.
- **Product photos**: put `SKU_001.jpg` (or .png/.webp) in `assets/products/`. Without a photo the page draws a category sketch.

## Viva preparation and what changed after the abstract audit

- Open the **How it works** tab in the app, or read `VIVA_GUIDE.md` (regenerate with `python -m frontend.viva_content`).
- **Body shape**: measured from the person's silhouette (`cv_vto/silhouette.py`). Put labelled photos in `data/validation/` and run `python -m cv_vto.evaluate_shapes` for accuracy.
- **Speed**: `python -m cv_vto.benchmark_fps --image your_photo.jpg` on your own laptop (writes `data/fps_benchmark.json`).
- **Forecasting**: cleaned data, honest time-based test, LightGBM vs XGBoost vs Prophet:
  `python -m demand_forecasting.train_lightgbm` then `python -m demand_forecasting.evaluate`.
  A real sales export can be converted with `python -m demand_forecasting.import_dataset --help`.
- **Pricing**: `python -m dynamic_pricing.backtest` replays the last 12 weeks (a simulation; stock arrivals are assumed).
- **Backend**: stock levels and shopper events are stored in a database (`data/retail.db`). For PostgreSQL set `DATABASE_URL`
  (for example `postgresql+psycopg2://user:pass@localhost:5432/retail`) and `python -m pip install psycopg2-binary`.
  Start the API with `python -m uvicorn backend.main:app --reload`; the dashboard uses it when it is running and falls back to the same code in-process when it is not.
