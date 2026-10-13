"""
Plain-language explanations of the project, written for the viva.

One source, two outputs: the "How it works" tab in the app reads these lists, and
    python -m frontend.viva_content
writes the same text to VIVA_GUIDE.md so it can be printed or shared.
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# --------------------------------------------------------------------------- abstract -> where it lives
# (objective in the abstract, where in the code, how to see it, honest status)
OBJECTIVES = [
    ("1. Classify body shape from MediaPipe keypoints",
     "cv_vto/body_shape.py, cv_vto/silhouette.py",
     "For shoppers tab: press START, stand 120 cm away, 'Read my T-shirt size'.",
     "Classifier built and unit-tested (four shapes from silhouette widths), also available as an API for a photo. "
     "The live camera now reports T-shirt size only (team decision); shape is chosen in a dropdown. Accuracy on real people is NOT measured."),
    ("2. 2D virtual try-on: scale, rotate, align a garment",
     "cv_vto/garment_overlay.py, frontend/webcam.py",
     "For shoppers tab: pick a 'Shirt on camera'.",
     "Built for shirts (affine warp from 3 keypoints). Other garment types are not built."),
    ("3. Style recommendation from body shape and colour tone",
     "cv_vto/style_recommender.py, frontend/catalog.py",
     "For shoppers tab: 'Show outfit picks'.",
     "Built as a rule table (expert rules), not a learned model."),
    ("4. Demand forecasting and price elasticity, with markdowns",
     "demand_forecasting/, dynamic_pricing/",
     "For retailers tab: trends, pricing assistant, Product deep-dive.",
     "Built and evaluated against baselines. Data is SYNTHETIC; real-data check pending."),
    ("5. One web dashboard: customer store + retailer console",
     "frontend/app.py, backend/main.py, backend/services.py",
     "Run the app; the retailer tab shows 'Shopper interest' from the shopper tab.",
     "Built. Streamlit UI + FastAPI + SQLite/PostgreSQL. Shopper events feed the retailer page."),
    ("Outcome: 25+ FPS on CPU",
     "cv_vto/benchmark_fps.py",
     "python -m cv_vto.benchmark_fps",
     "Measured on a cloud test machine at 33-38 FPS. Re-measure on your own laptop and quote that number."),
    ("Outcome: trained dynamic pricing balancing stockouts vs markdowns",
     "dynamic_pricing/price_optimizer.py, dynamic_pricing/backtest.py",
     "python -m dynamic_pricing.backtest",
     "Rule-based, not a learned optimiser. Simulation shows more revenue and less leftover stock "
     "when stock is excessive; it does not reduce stockouts when stock is short."),
]

# --------------------------------------------------------------------------- module explanations
# (title, in one line, how it works, key files, one thing to show)
MODULES = [
    ("T-shirt size from the camera (and the body-shape classifier)",
     "Finds your joints, measures your outline, and decides which of four shapes you are.",
     ["MediaPipe Pose finds 33 body joints and also returns a 'silhouette mask' (a picture of where the person is).",
      "MediaPipe has no waist joint, so the waist is measured from the silhouette: the width of the body at three heights "
      "(chest, waist, hips), the way a tailor would.",
      "Chest = widest row 25-40% of the way from shoulders to hips. Waist = narrowest row 55-72% of the way. "
      "Hips = widest row around the hip joints.",
      "If arms hang against the body they merge with the torso, so the elbow/wrist joints are used to paint the arms out first.",
      "Rule: shoulders wider than hips by 7% -> inverted triangle; hips wider -> pear; about equal and waist at most 80% of the "
      "narrower of the two -> hourglass; otherwise rectangle.",
      "Guards: if the torso is hidden or the proportions are impossible (legs spread, two people), it says 'not clear' instead of guessing.",
      "Where to stand: a circle marks where the head goes. The size is calibrated for about 120 cm from the camera. The app checks that the torso "
      "looks the right size (38-52% of the picture height; a Calibrate button sets this for your own camera). Measurements are collected only while the circle is green.",
      "Steadiness: the median of the last 40 shoulder widths gives the size (odd frames are ignored), a result appears after 25 good frames "
      "(progress bar), and the shown size changes only if a new one wins 12 updates in a row.",
      "Size: shoulder-joint distance (fraction of the frame width) is mapped to S / M / L / XL / XXL, then to the team's chest chart "
      "(S 32 in, M 36, L 40, XL 44, XXL 48). The thresholds are rough and not yet checked against tape measurements."],
     "cv_vto/body_shape.py (classifier), cv_vto/silhouette.py (measuring), cv_vto/stance.py (stand-here guide and steady reading)",
     "Stand with arms a little away from your sides. The label on the video says what was measured."),
    ("Virtual try-on",
     "Pins a shirt picture onto your shoulders and hips and follows you.",
     ["The shirt image has three reference points: left shoulder, right shoulder, hem centre.",
      "The live frame has three matching points: your two shoulder joints and the middle of your hips.",
      "An affine transform (scale + rotate + shift + shear, found by cv2.getAffineTransform) maps the first three points onto the second three.",
      "The warped shirt is alpha-blended: pixel = shirt x alpha + camera x (1 - alpha), where alpha is the PNG's transparency.",
      "Exponential smoothing (0.6 old + 0.4 new) of the target points stops jitter. If the joints are not visible the shirt is hidden."],
     "cv_vto/garment_overlay.py, frontend/webcam.py",
     "Move closer and further: the shirt scales; tilt your shoulders: it rotates."),
    ("Style and colour recommendation",
     "Looks up which cuts suit each body shape and which colours suit each tone.",
     ["A table maps each body shape to four styles (for example pear -> boat-neck top, structured blazer).",
      "A second table maps warm / cool / neutral tone to a colour palette.",
      "frontend/catalog.py turns each pick into a product card (picture, colour, price, reason). Names and prices are sample placeholders."],
     "cv_vto/style_recommender.py, frontend/catalog.py, frontend/explain.py",
     "Change the body shape and tone, press 'Show outfit picks'."),
    ("Demand forecasting",
     "Predicts next week's units for each product from its recent weeks.",
     ["Data: one row per product per week: date, sku, category, price, promo_flag, units_sold (data/weekly_sales.csv).",
      "Cleaning (clean_data.py): fixes duplicates, missing weeks, negative units, bad prices, extreme spikes, and reports what it fixed.",
      "Features (features.py): units sold 1, 2, 4 and 8 weeks ago; average of the last 4 and 8 weeks; week of year, month, quarter; price; promo flag.",
      "Model: LightGBM, a collection of decision trees added one after another, each correcting the last one's mistakes (gradient boosting).",
      "Honest test: train on the past, test on the last 20 weeks, one week ahead. Compared with two simple rules (same as last week; 4-week average).",
      "evaluate.py also compares XGBoost and Prophet over the last 12 weeks. On this data XGBoost is best, LightGBM close, Prophet worst.",
      "The model that is served is refit on all data so it knows the latest weeks."],
     "demand_forecasting/ (clean_data, features, train_lightgbm, train_xgboost, train_prophet, evaluate, predict)",
     "Retailers tab -> Product deep-dive -> '2. What do we expect next week?'."),
    ("Price elasticity",
     "Measures how much sales fall when price rises, for each product.",
     ["Elasticity = % change in units for a 1% change in price. -1.5 means a 10% price rise loses about 15% of sales.",
      "Estimated per product with a log-log regression: log(units) = a + b x log(price) + c x promo. b is the elasticity.",
      "R squared says how much of the sales movement price explains. Median here is about 0.59.",
      "A few products (SKU 002, 004, 020) come out positive. That cannot be true for a normal product (prices and promotions were mixed up in the history), "
      "so the app flags them as unreliable and does not steer prices with them."],
     "dynamic_pricing/elasticity.py",
     "Product deep-dive -> '3. Do shoppers care about the price?'."),
    ("Dynamic pricing rule",
     "Suggests a markup or markdown from demand versus stock, softened for price-sensitive products.",
     ["Ratio = forecast demand / stock on hand.",
      "Ratio above 1.2 (demand beats stock): raise price, by half the gap, at most 15%.",
      "Ratio below 0.7 (stock piling up): lower price, by half the gap, at most 30%.",
      "In between: leave the price alone.",
      "The change is multiplied by 1 / |elasticity| (capped at 1) so very price-sensitive products move less.",
      "No stock, or an unreliable (positive) elasticity: price unchanged.",
      "It is a transparent rule rather than a learned optimiser, on purpose: every suggestion can be explained in one sentence."],
     "dynamic_pricing/price_optimizer.py, dynamic_pricing/backtest.py",
     "Retailers tab -> Pricing assistant."),
    ("Retail insights (the Retailers page)",
     "Turns the numbers into plain advice: best sellers, stock to watch, what to do next.",
     ["Trend: forecast vs the average of recent weeks. +8% or more is 'rising'; -8% or less is 'slowing'.",
      "Stock state uses demand / stock: above 1.2 is 'running short', 2.0 or more is 'urgent' (under half a week of stock), below 0.7 is 'excess'. Same thresholds as the pricing rule.",
      "Stock levels are not in the sales file, so stock alerts only appear after the retailer adds stock (CSV upload, saved in the database).",
      "Recommendations are ranked and capped so the page is never a wall of alerts.",
      "'Shopper interest' counts what shoppers did in the try-on store (body shapes read, picks viewed, shirts tried)."],
     "frontend/insights.py (logic, no screen code), frontend/retail_page.py (screen)",
     "Retailers tab, top to bottom."),
    ("Backend and database",
     "One set of services behind a REST API, with a database for stock and shopper events.",
     ["FastAPI exposes: /body-shape/classify, /body-shape/from-image, /styles, /events, /events/summary, /products, /stock, "
      "/demand/forecast, /demand/forecast-all, /pricing/recommend.",
      "backend/services.py holds the real logic. main.py is a thin layer on top.",
      "frontend/api_client.py uses the API if it is running, and calls the same services directly if not. The page footer says which.",
      "SQLite by default. Set DATABASE_URL to a PostgreSQL address to switch (the abstract lists both).",
      "Tables: products (with stock), sales_records, engagement_events."],
     "backend/main.py, backend/services.py, backend/database.py, frontend/api_client.py",
     "Open http://127.0.0.1:8000/docs while the API is running and try an endpoint."),
]

# --------------------------------------------------------------------------- demo script
DEMO_STEPS = [
    ("Start", "Open the app. Say: two sides, a shopper store and a retailer console, one data pipeline underneath."),
    ("Shopper: camera", "Press START, stand back with arms slightly away from the body. Show the outline and the label. Press 'Read my body shape'."),
    ("Shopper: try-on", "Pick a shirt. Move closer, tilt your shoulders. Explain the 3-point affine transform."),
    ("Shopper: picks", "Press 'Show outfit picks'. Press 'Try this shirt on' on one card."),
    ("Retailer: snapshot", "Switch to the retailer tab. Read the snapshot cards aloud. Note 'Shopper interest' now shows what you just did."),
    ("Retailer: stock", "Upload the stock CSV. Alerts switch on. Reload the page: the stock is still there (database)."),
    ("Retailer: pricing", "Open the Pricing assistant for one product. Change the stock number and watch the advice change."),
    ("Evidence", "Open 'How it works' -> Results. Show the forecast comparison table and the pricing simulation. Say what is not proven."),
]

# --------------------------------------------------------------------------- likely questions
QA = [
    ("Why LightGBM and not deep learning?",
     "Weekly sales per product is a small tabular dataset (about 2,000 rows). Gradient-boosted trees usually beat neural networks "
     "on small tabular data, train in seconds on a laptop and are easier to explain. We also tried XGBoost and Prophet."),
    ("Is your forecast accurate? How do you know?",
     "On the last 20 weeks, which the model did not train on, LightGBM is off by about 11 units a week (about 14%). Using last week's number "
     "would be off by 19 and the 4-week average by 17. So it beats simple rules by roughly 40%. Caveat: the data is synthetic."),
    ("What does MAE / MAPE / WAPE mean?",
     "MAE is the average size of the miss in units. MAPE is the average miss as a percentage of the real number (weeks with 0 units use 1 as the "
     "denominator). WAPE is total absolute miss divided by total units, so big sellers count more."),
    ("Why did XGBoost beat LightGBM?",
     "By a small margin (10.0 vs 10.5 units) on 240 forecasts. That gap is within noise, so we say they are about equal and both far better than the baselines. "
     "We keep LightGBM because the abstract names it and it is already integrated."),
    ("Why did Prophet do badly?",
     "Prophet is built for long single series with clear trend and yearly seasonality. Here each product has two years of weekly points and its pattern "
     "depends on price and promotions, which Prophet was not given. Lag features capture recent behaviour better."),
    ("Is the data real?",
     "No. data/weekly_sales.csv is generated (demand_forecasting/generate_sample_data.py) so the pipeline could be built before real data. "
     "import_dataset.py converts a real sales export into the same format, so the pipeline can be rerun on it. We should say this openly."),
    ("How does body-shape detection work without a waist joint?",
     "MediaPipe also gives a silhouette mask. We measure the body's width at chest, waist and hip heights from the mask, then compare them with simple rules."),
    ("How far should the person stand, and why did the result used to flicker?",
     "About 120 cm (4 ft) from the camera. A camera cannot measure metres, so we check how big the torso looks, and a calibrate button sets that for any camera. "
     "Flicker came from using single noisy frames near a size boundary. Now we take the median of 40 good frames and only change the shown size after 12 consecutive updates agree."),
    ("How accurate is the body-shape classifier?",
     "We have not measured it on real people yet. The measurement code is tested on drawn silhouettes with known widths. "
     "The evaluation script and photo folder are ready (data/validation); with 20+ labelled volunteers it gives accuracy and a confusion matrix."),
    ("Can it work in real time? What is the frame rate?",
     "Yes. cv_vto/benchmark_fps.py times pose + silhouette + classification + overlay per frame. On our test machine it ran 33-38 FPS with the silhouette on "
     "and about 39 without. Quote the figure from your own laptop. Browser video transport adds some delay on top."),
    ("What is price elasticity? Why log-log?",
     "It is the % change in sales per 1% change in price. In a log-log regression the slope on log price is exactly that number, and it makes the model "
     "multiplicative, which suits sales."),
    ("Some elasticities are positive. Isn't that wrong?",
     "Yes, for normal goods. In the history, high prices coincided with high-demand seasons, so the regression picks that up. We mark those products unreliable "
     "and the pricing rule leaves their price unchanged."),
    ("Is the pricing optimal?",
     "No. It is a rule, not an optimiser. The simulation back-test (17 products, 12 weeks) shows what it does: with excess stock revenue rises about 9% and leftover "
     "stock falls by more than half; with short stock revenue rises about 5% but stockout weeks do not improve, because the rule only changes price, not supply."),
    ("How does the back-test work, and what are its limits?",
     "It replays the last 12 weeks, lets the rule set prices from the forecast and stock, and assumes demand moves by (new price / old price) to the power of elasticity. "
     "Stock arrivals are assumed (80% or 150% of demand) because no real inventory data exists. So it is a simulation, not proof from a shop."),
    ("Where do the 'intent signals' come from?",
     "The shopper tab logs three events to the database: a body-shape read, outfit picks viewed, a shirt tried on. The retailer tab summarises them. "
     "They are not tied to SKUs yet because the shopper catalogue is sample data."),
    ("Why both Streamlit and FastAPI?",
     "Streamlit is the quick interface. FastAPI is the reusable service layer (any other app or phone client can call it). The dashboard works with or without the API server."),
    ("What would you do next with more time?",
     "Test the classifier on 20+ real volunteers and tune thresholds; run the pipeline on a real retail dataset; add more garment types and real product photos; "
     "feed shopper events into the demand model; replace the pricing rule with an optimiser that sets price and reorder together."),
    ("What are the limitations?", "See the limitations list. Say them before you are asked."),
]

LIMITATIONS = [
    "The sales data is synthetic. Forecast accuracy and the pricing simulation say how the pipeline behaves, not how a real shop would do.",
    "Body-shape accuracy on real people has not been measured. It needs a labelled photo set from volunteers.",
    "The silhouette method works best with a plain background, good light, fitted clothing and arms slightly away from the body. Loose clothes hide the waist.",
    "Only shirts can be tried on, using a flat 2D warp. It does not model fabric, depth or sleeves.",
    "Stock is not in the sales data. Stock-based advice appears only after stock is entered; the pricing back-test assumes stock arrivals.",
    "The pricing rule is not an optimiser and does not fix shortages.",
    "Shopper events are not linked to product SKUs, because the shopper catalogue is sample data.",
    "The 25+ FPS target is the processing speed on one machine; browser streaming adds delay.",
]

COMMANDS = [
    ("Run the app", "python -m streamlit run frontend/app.py --server.fileWatcherType none"),
    ("Run the API (optional)", "python -m uvicorn backend.main:app --reload"),
    ("Run every test", "python -m pytest -q"),
    ("Retrain the demand model", "python -m demand_forecasting.train_lightgbm"),
    ("Compare forecasting models", "python -m demand_forecasting.evaluate"),
    ("Pricing back-test", "python -m dynamic_pricing.backtest"),
    ("Measure frames per second", "python -m cv_vto.benchmark_fps --image path\\to\\photo.jpg"),
    ("Score body shapes on labelled photos", "python -m cv_vto.evaluate_shapes"),
    ("Use a real sales export", "python -m demand_forecasting.import_dataset --help"),
]

FILE_MAP = [
    ("cv_vto/", "Computer vision: body shape, silhouette, garment overlay, style rules, FPS and accuracy scripts"),
    ("demand_forecasting/", "Data cleaning, features, LightGBM / XGBoost / Prophet, evaluation, prediction"),
    ("dynamic_pricing/", "Elasticity, pricing rule, back-test simulation"),
    ("backend/", "FastAPI routes, services, database models"),
    ("frontend/", "Streamlit app, retailer page, insights logic, API client, this guide"),
    ("tests/", "Automated tests (python -m pytest -q)"),
    ("data/", "Sales CSV, trained model, metrics JSON files, validation photos"),
    ("assets/", "Shirt PNGs for the try-on, optional product photos"),
]


# --------------------------------------------------------------------------- results (read from JSON files)
def load_json(name):
    path = os.path.join(ROOT, "data", name)
    try:
        with open(path) as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


def to_markdown() -> str:
    out = ["# Viva guide: Virtual Outfit Recommendation and Dynamic Retail Intelligence", "",
           "Generated from `frontend/viva_content.py`, the same text as the app's **How it works** tab.", ""]
    out += ["## 1. The project in one paragraph", "",
            "A web app with two sides. Shoppers use their camera: the system finds their body shape, lets them try shirts on live and suggests outfits. "
            "Retailers get a console: it forecasts next week's demand per product, measures price sensitivity, and suggests when to raise or lower a price. "
            "Both sides share one backend and database, and what shoppers do is shown to the retailer as shopper-interest signals.", ""]
    out += ["## 2. Abstract versus what was built", "", "| Abstract item | Where | How to see it | Honest status |", "|---|---|---|---|"]
    out += [f"| {a} | `{b}` | {c} | {d} |" for a, b, c, d in OBJECTIVES]
    out += ["", "## 3. Architecture", "", "```",
            "Webcam -> MediaPipe Pose (+silhouette) -> Body shape -> Style & colour picks -> Product cards",
            "                         |                                      |",
            "                         +-> Garment overlay (try-on)           +-> shopper events -> database",
            "                                                                         |",
            "Sales CSV -> Cleaning -> Features -> LightGBM forecast -> Pricing rule <-+-> Retailer console",
            "                    \\-> Elasticity (log-log OLS) --------^                    (Streamlit + FastAPI)",
            "```", ""]
    out += ["## 4. Module by module", ""]
    for title, line, how, files, show in MODULES:
        out += [f"### {title}", "", f"**In one line:** {line}", ""]
        out += [f"- {h}" for h in how]
        out += ["", f"**Files:** {files}", "", f"**Show it:** {show}", ""]
    ev = load_json("forecast_evaluation.json")
    lg = load_json("lightgbm_metrics.json")
    bt = load_json("pricing_backtest.json")
    fp = load_json("fps_benchmark.json")
    out += ["## 5. Results to quote", ""]
    if lg:
        out += [f"**LightGBM, last {lg['holdout_weeks']} weeks, one week ahead:** MAE {lg['mae']:.1f} units, MAPE {lg['mape']:.1%}. "
                f"Same as last week: MAE {lg['baseline_last_week']['mae']:.1f}. 4-week average: MAE {lg['baseline_4week_average']['mae']:.1f}.", ""]
    if ev:
        out += [f"**Model comparison ({ev['weeks']} weeks, {ev['skus']} products, {ev['forecasts']} forecasts):**", "",
                "| Model | MAE | MAPE | WAPE |", "|---|---|---|---|"]
        out += [f"| {n} | {m['mae']:.1f} | {m['mape']:.1%} | {m['wape']:.1%} |" for n, m in ev["models"].items()]
        out += [""]
    if bt:
        out += [f"**Pricing simulation ({bt['skus_simulated']} products, {bt['weeks']} weeks):**", "",
                "| Supply | Policy | Revenue | Units | Stockout weeks | Left over |", "|---|---|---|---|---|---|"]
        for name, sc in bt["scenarios"].items():
            for pol in ("static", "dynamic"):
                r = sc[pol]
                out.append(f"| {name} ({sc['arrivals_vs_demand']:.0%} of demand) | {'keep price' if pol == 'static' else 'dynamic'} | "
                           f"{r['revenue']:,.0f} | {r['units']:,.0f} | {r['stockout_weeks']:.0f} | {r['left_over']:,.0f} |")
        out += [""]
    if fp:
        out += [f"**Speed:** {fp['fps']} FPS ({fp['ms_per_frame']} ms/frame), silhouette {'on' if fp['segmentation'] else 'off'}, "
                f"{fp['machine']}, {fp['date']}.", ""]
    out += ["## 6. Limitations (say these first)", ""] + [f"- {x}" for x in LIMITATIONS] + [""]
    out += ["## 7. Demo script (5 minutes)", ""] + [f"{i}. **{a}.** {b}" for i, (a, b) in enumerate(DEMO_STEPS, 1)] + [""]
    out += ["## 8. Likely questions and answers", ""]
    for q, a in QA:
        out += [f"**Q. {q}**", "", f"A. {a}", ""]
    out += ["## 9. Commands", "", "```"] + [f"# {a}\n{b}" for a, b in COMMANDS] + ["```", ""]
    out += ["## 10. Where things are", ""] + [f"- `{a}` {b}" for a, b in FILE_MAP] + [""]
    return "\n".join(out)


if __name__ == "__main__":
    path = os.path.join(ROOT, "VIVA_GUIDE.md")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(to_markdown())
    print(f"Wrote {path}")
