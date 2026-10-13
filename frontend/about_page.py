"""
"How it works" tab: explains the project, shows where each part of the abstract lives in the code,
and presents the real evidence (read from the JSON files the scripts write). Text lives in
frontend/viva_content.py so the app and VIVA_GUIDE.md never disagree.
"""
import html
import os

import pandas as pd
import streamlit as st

from frontend import viva_content as vc
from frontend.retail_art import icon

OLIVE, CLAY = "#5F6B3A", "#B5694A"

CSS = """
<style>
div[data-baseweb="tab-panel"]:has(.ab-root) .ab-flow{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin:8px 0 4px}
div[data-baseweb="tab-panel"]:has(.ab-root) .ab-box{background:#FFFDF8;border:1px solid #E4DCC8;border-radius:14px;padding:12px 14px;font-size:.88rem;line-height:1.35}
div[data-baseweb="tab-panel"]:has(.ab-root) .ab-box b{display:block;font-family:Fraunces,Georgia,serif;font-size:1rem;margin-bottom:2px;color:#2A2A26}
div[data-baseweb="tab-panel"]:has(.ab-root) .ab-box.s{border-left:4px solid #5F6B3A}
div[data-baseweb="tab-panel"]:has(.ab-root) .ab-box.r{border-left:4px solid #B5694A}
div[data-baseweb="tab-panel"]:has(.ab-root) .ab-box.d{border-left:4px solid #CDB98F}
div[data-baseweb="tab-panel"]:has(.ab-root) .ab-lane{font-size:.78rem;letter-spacing:.08em;text-transform:uppercase;color:#7C7767;margin:14px 0 2px}
div[data-baseweb="tab-panel"]:has(.ab-root) .ab-status{font-size:.85rem;color:#4A4A42}
</style>
"""


def esc(x):
    return html.escape(str(x))


def box(title, text, tone):
    return f'<div class="ab-box {tone}"><b>{esc(title)}</b>{esc(text)}</div>'


def architecture():
    st.markdown('<div class="ab-lane">Shopper side</div><div class="ab-flow">'
                + box("1. Camera", "Browser webcam frames via streamlit-webrtc", "s")
                + box("2. Pose + silhouette", "MediaPipe: 33 joints and a body mask", "s")
                + box("3. Body shape", "Widths at chest, waist, hip -> 4 shapes", "s")
                + box("4. Try-on", "Affine warp of a shirt PNG onto shoulders and hips", "s")
                + box("5. Style picks", "Rule table: shape and colour tone -> products", "s")
                + '</div><div class="ab-lane">Shared layer</div><div class="ab-flow">'
                + box("Database", "SQLite or PostgreSQL: products, stock, sales, shopper events", "d")
                + box("Backend services", "backend/services.py, exposed by FastAPI", "d")
                + '</div><div class="ab-lane">Retailer side</div><div class="ab-flow">'
                + box("1. Sales data", "Weekly units by product, cleaned first", "r")
                + box("2. Forecast", "LightGBM on lags, rolling means, calendar, price", "r")
                + box("3. Elasticity", "Log-log regression per product", "r")
                + box("4. Pricing rule", "Demand vs stock, damped by elasticity", "r")
                + box("5. Console", "Insights, stock alerts, pricing assistant, shopper interest", "r")
                + "</div>", unsafe_allow_html=True)
    st.caption("Shopper actions (shape read, picks viewed, shirt tried) are written to the database and shown to the retailer as shopper interest.")


def results():
    lg, ev, bt, fp = (vc.load_json(n) for n in
                      ("lightgbm_metrics.json", "forecast_evaluation.json", "pricing_backtest.json", "fps_benchmark.json"))

    st.markdown("#### Demand forecasting")
    if lg and lg.get("baseline_last_week"):
        a, b, c = st.columns(3)
        a.metric("LightGBM average miss", f"{lg['mae']:.1f} units", help=f"About {lg['mape']:.1%} of weekly sales")
        b.metric("Same as last week", f"{lg['baseline_last_week']['mae']:.1f} units")
        c.metric("4-week average", f"{lg['baseline_4week_average']['mae']:.1f} units")
        st.caption(f"Tested on the last {lg['holdout_weeks']} weeks (from {lg['cutoff_date']}) that the model was not trained on, one week ahead. Lower is better.")
    else:
        st.info("Run `python -m demand_forecasting.train_lightgbm` to fill this in.")
    if ev:
        rows = [{"Model": n, "Average miss (units)": round(m["mae"], 1), "MAPE": f"{m['mape']:.1%}", "WAPE": f"{m['wape']:.1%}"}
                for n, m in sorted(ev["models"].items(), key=lambda kv: kv[1]["mae"])]
        st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
        st.caption(f"{ev['forecasts']} forecasts ({ev['skus']} products x {ev['weeks']} weeks, {ev['horizon']}). Best: {ev['best']}. "
                   "Prophet is refit weekly per product. The synthetic data is the main caveat.")
    else:
        st.info("Run `python -m demand_forecasting.evaluate` to compare LightGBM, XGBoost and Prophet.")

    st.markdown("#### Dynamic pricing (simulation)")
    if bt:
        rows = []
        for name, sc in bt["scenarios"].items():
            for pol, label in (("static", "Keep price"), ("dynamic", "Dynamic rule")):
                r = sc[pol]
                rows.append({"Stock supply": f"{name.title()} ({sc['arrivals_vs_demand']:.0%} of demand)", "Policy": label,
                             "Revenue": f"{r['revenue']:,.0f}", "Units sold": f"{r['units']:,.0f}",
                             "Stockout weeks": f"{r['stockout_weeks']:.0f}", "Left over": f"{r['left_over']:,.0f}"})
        st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
        st.caption(f"{bt['skus_simulated']} products over the last {bt['weeks']} weeks. Stock arrivals are assumed because there is no real inventory data. "
                   f"{len(bt['skus_excluded_unreliable_elasticity'])} products with an unreliable (positive) elasticity were left out. "
                   "Read: the rule helps revenue and clears excess stock, but it cannot fix shortages by price alone.")
    else:
        st.info("Run `python -m dynamic_pricing.backtest` to fill this in.")

    st.markdown("#### Speed and body-shape accuracy")
    c1, c2 = st.columns(2)
    with c1:
        if fp:
            st.metric("Frames per second", f"{fp['fps']}", help="The abstract's target is 25 or more")
            st.caption(f"{fp['ms_per_frame']} ms per frame, silhouette {'on' if fp['segmentation'] else 'off'}, from {fp['source']}. "
                       f"Machine: {fp['machine']} ({fp['date']}). Run `python -m cv_vto.benchmark_fps` on your own laptop.")
        else:
            st.info("Run `python -m cv_vto.benchmark_fps --image your_photo.jpg`.")
    with c2:
        labels = os.path.join(vc.ROOT, "data", "validation", "labels.csv")
        if os.path.exists(labels):
            try:
                n = len(pd.read_csv(labels))
            except Exception:
                n = 0
            st.metric("Labelled photos", n)
        else:
            st.metric("Labelled photos", 0)
        st.caption("Body-shape accuracy is not measured until there are labelled photos. It needs photos of real volunteers with agreed labels. See data/validation/README.md.")


def render():
    st.markdown('<div class="ab-root"></div>' + CSS, unsafe_allow_html=True)
    st.markdown("## How this project works")
    st.write("A guide to the code and the screens: what each part does, where it lives, what was measured, and what is still not proven.")

    t1, t2, t3, t4, t5 = st.tabs(["Overview", "Parts explained", "Results", "Demo and questions", "Limits"])

    with t1:
        st.markdown("#### Architecture")
        architecture()
        st.markdown("#### The abstract, item by item")
        rows = [{"Abstract item": a, "Where in the code": b, "See it": c, "Status": d} for a, b, c, d in vc.OBJECTIVES]
        st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
        st.markdown("#### Where things are")
        for a, b in vc.FILE_MAP:
            st.markdown(f"- `{a}` {b}")

    with t2:
        st.write("Open a part to see how it works in plain words, which files hold it, and what to show.")
        for title, line, how, files, show in vc.MODULES:
            with st.expander(f"{title}  -  {line}"):
                for h in how:
                    st.markdown(f"- {h}")
                st.markdown(f"**Files:** `{files}`")
                st.markdown(f"**Show it:** {show}")

    with t3:
        results()

    with t4:
        st.markdown("#### Five-minute demo")
        for i, (a, b) in enumerate(vc.DEMO_STEPS, 1):
            st.markdown(f"**{i}. {a}.** {b}")
        st.markdown("#### Likely questions")
        for q, a in vc.QA:
            with st.expander(q):
                st.write(a)
        st.markdown("#### Commands")
        st.code("\n".join(f"# {a}\n{b}" for a, b in vc.COMMANDS), language="bash")

    with t5:
        st.write("Say these before you are asked. It shows you understand the work.")
        for x in vc.LIMITATIONS:
            st.markdown(f"- {x}")
