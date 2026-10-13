"""
The Retailers page: insights first, statistics second.

Sections (top to bottom): welcome header, retail snapshot, product gallery,
"What should you do next?", trends and demand, pricing assistant, and a
collapsed "Product deep-dive" section that keeps the original
step-by-step charts and tables.

All numbers come from data/weekly_sales.csv, the LightGBM forecast and the
price-elasticity / price-rule modules. Nothing is made up.
"""
import html
import io
import json
import os
from dataclasses import replace

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components

from demand_forecasting.predict import forecast_next_week
from dynamic_pricing.elasticity import estimate_all
from dynamic_pricing.price_optimizer import recommend_price
from frontend import api_client, insights as ix
from frontend.explain import (GLOSSARY, elasticity_sentence, fit_label, price_effect_sentence, revenue_outlook,
                              sensitivity_word, stock_position, suggestion_phrase, sureness, verdict)
from frontend.retail_art import hero_art, icon, mini_thumb, product_visual, sparkline

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH = os.path.join(ROOT, "data", "weekly_sales.csv")
MODEL_PATH = os.path.join(ROOT, "data", "lightgbm_demand_model.pkl")
METRICS_PATH = os.path.join(ROOT, "data", "lightgbm_metrics.json")

CHARCOAL, OLIVE, CLAY, SAND = "#2A2A26", "#5F6B3A", "#B5694A", "#CDB98F"
TREND_COLOR = {"rising": "#3F7D4E", "steady": "#7C7767", "slowing": "#B7791F"}
GALLERY_FILTERS = ["All products", "Best sellers", "Needs attention", "Rising", "Slowing"]
PAGE_SIZE = 8


# ----------------------------------------------------------------------------- data (cached)
@st.cache_data(show_spinner=False)
def load_sales(stamp: float) -> pd.DataFrame:
    """The sales file after cleaning (duplicates merged, gaps filled, bad values fixed)."""
    from demand_forecasting.clean_data import clean_sales
    return clean_sales(pd.read_csv(DATA_PATH))[0]


@st.cache_data(show_spinner=False)
def all_elasticities(df: pd.DataFrame):
    return estimate_all(df)


@st.cache_data(show_spinner=False)
def all_forecasts(df: pd.DataFrame, model_stamp: float):
    """sku -> (expected units next week, came_from_model). Falls back to the 4-week average."""
    out = {}
    for sku, d in df.groupby("sku"):
        d = d.sort_values("date")
        try:
            out[sku] = (forecast_next_week(sku, float(d.iloc[-1]["price"]), 0), True)
        except Exception:
            out[sku] = (float(d["units_sold"].tail(4).mean()), False)
    return out


# ----------------------------------------------------------------------------- small helpers
def esc(x) -> str:
    return html.escape(str(x), quote=True)


def money(x: float) -> str:
    return f"₹{x:,.0f}"


def section(anchor: str, title: str, sub: str = "", extra: str = ""):
    st.markdown(f'<div id="{anchor}" class="rt-anchor"></div><div class="rt-sec"><h2>{title}</h2>'
                f"{f'<p>{sub}</p>' if sub else ''}{extra}</div>", unsafe_allow_html=True)


def pill(label: str, tone: str) -> str:
    return f'<span class="rt-pill {tone}">{esc(label)}</span>'


def minis(sigs) -> str:
    return '<div class="rt-minis">' + "".join(mini_thumb(s.category, s.sku) for s in sigs[:3]) + "</div>"


def open_product(sku: str, target: str):
    st.session_state["rt_focus"] = sku
    st.session_state["rt_price_sku"] = sku
    st.session_state["rt_scroll"] = "rt-pricing" if target == "pricing" else "rt-spot"


def open_category(cat: str):
    st.session_state["rt_cat"] = cat
    st.session_state["rt_filter"] = GALLERY_FILTERS[0]
    st.session_state["rt_scroll"] = "rt-gallery"


def close_spotlight():
    st.session_state.pop("rt_focus", None)


def chart_layout(fig, height=300):
    fig.update_layout(height=height, margin=dict(l=0, r=0, t=10, b=0), plot_bgcolor="rgba(0,0,0,0)",
                      paper_bgcolor="rgba(0,0,0,0)", font=dict(family="DM Sans", color=CHARCOAL),
                      legend=dict(orientation="h", y=1.12, x=0))
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(gridcolor="rgba(42,42,38,.1)")
    return fig


# ----------------------------------------------------------------------------- page
def render():
    st.markdown('<div class="rt-root"></div>', unsafe_allow_html=True)

    if not os.path.exists(DATA_PATH):
        header(None, None, False)
        st.markdown('<div class="rt-empty"><b>No sales data yet.</b><br>Run '
                    "<code>python -m demand_forecasting.generate_sample_data</code> and reload this page.</div>",
                    unsafe_allow_html=True)
        return

    with st.spinner("Reading your sales and preparing forecasts..."):
        df_all = load_sales(os.path.getmtime(DATA_PATH))
        model_stamp = os.path.getmtime(MODEL_PATH) if os.path.exists(MODEL_PATH) else 0.0
        elasticities = all_elasticities(df_all)
        forecasts = all_forecasts(df_all, model_stamp)

    model_ok = any(used for _, used in forecasts.values())
    header(df_all, model_stamp, model_ok)
    glossary()

    # ---- controls: category, look-back window, optional stock
    cats = sorted(df_all["category"].unique())
    c1, c2 = st.columns([1, 1], gap="large")
    with c1:
        cat = st.selectbox("Category", ["all"] + cats, key="rt_cat",
                           format_func=lambda c: "All categories" if c == "all" else ix.pretty_category(c))
    with c2:
        window = st.select_slider("Look back over", options=[4, 8, 12], value=4, key="retailer_stock_rt_window",
                                  format_func=lambda w: f"Last {w} weeks",
                                  help="How many recent weeks of real sales to compare against.")

    st.markdown('<div id="rt-stock" class="rt-anchor"></div>', unsafe_allow_html=True)
    stock_map = stock_controls(df_all)

    df = df_all if cat == "all" else df_all[df_all["category"] == cat]
    signals = ix.build_signals(df, forecasts, elasticities, stock_map, window)
    cat_trends = ix.category_trends(df, signals)
    sig_by_sku = {s.sku: s for s in signals}

    if not model_ok:
        st.markdown('<div class="rt-note warn">The demand model has not been trained yet, so next-week numbers use each '
                    "product's recent average. Run <code>python -m demand_forecasting.train_lightgbm</code> for model forecasts.</div>",
                    unsafe_allow_html=True)

    snapshot(signals, cat_trends, bool(stock_map), window)
    gallery(signals, window)
    recommendations(signals, cat_trends)
    trends(cat_trends, signals)
    pricing_assistant(signals, stock_map)

    shopper_interest(df_all)

    section("rt-advanced", "Product deep-dive", "Pick one product and see the story behind the advice, step by step, in plain words.")
    with st.expander("Open the product deep-dive"):
        advanced(df_all, elasticities, forecasts, model_ok, stock_map)

    st.caption(f"Data connection: {api_client.mode()}.")

    scroll_to = st.session_state.pop("rt_scroll", None)
    if scroll_to:
        components.html(
            "<script>setTimeout(function(){var e=window.parent.document.getElementById('%s');"
            "if(e){e.scrollIntoView({behavior:'smooth',block:'start'});}},400);</script>" % scroll_to, height=0)


# ----------------------------------------------------------------------------- A. header
def header(df, model_stamp, model_ok):
    chips = ""
    if df is not None:
        last = df["date"].max()
        chips = (f'<span class="rt-chip">Sales through {last:%d %b %Y}</span>'
                 f'<span class="rt-chip">Forecast for the week of {last + pd.Timedelta(weeks=1):%d %b}</span>'
                 f'<span class="rt-chip">{"Demand model on" if model_ok else "Using recent averages"}</span>')
    st.markdown(
        '<div class="rt-hero"><div>'
        '<p class="rt-eyebrow">Retail intelligence</p>'
        "<h1>Your retail, <em>made smarter.</em></h1>"
        '<p class="rt-sub">Understand your products, discover trends, and make better retail decisions. '
        "Start with the snapshot, then see what to do next.</p>"
        f'<div class="rt-chips">{chips}</div></div>'
        f'<div class="rt-hero-art">{hero_art()}</div></div>', unsafe_allow_html=True)


# ----------------------------------------------------------------------------- stock input
def stock_controls(df_all: pd.DataFrame) -> dict:
    """
    Optional stock levels. The sales file has no inventory, so stock insights wait for this.
    Numbers are saved in the database (through the backend), so they are still there after a reload.
    """
    skus = sorted(df_all["sku"].unique())
    saved = {k: v for k, v in api_client.get_stock_map().items() if k in skus}
    with st.expander("Add your stock levels (optional)" + (f"  -  {len(saved)} saved" if saved else "")):
        st.write("Your sales file does not say how many units you hold, so stock alerts stay off until you add them. "
                 "Upload a small CSV with the **sku** (product code) and **stock** columns. The product name column in the template is only there to help you fill it in. It is saved, so you only do this once.")
        from frontend.product_names import friendly_names
        _nm = friendly_names(df_all.drop_duplicates("sku")[["sku", "category"]].itertuples(index=False, name=None))
        template = pd.DataFrame({"sku": skus, "product": [_nm.get(k, k) for k in skus], "stock": ""}).to_csv(index=False)
        st.download_button("Download a blank template", template, file_name="stock_template.csv", mime="text/csv", key="retailer_stock_blank_template_download")
        up = st.file_uploader("Your stock file", type=["csv"], key="rt_stock_file", label_visibility="collapsed")
        if up is not None:
            try:
                stock, problems = ix.parse_stock_csv(pd.read_csv(io.BytesIO(up.getvalue())), skus)
            except Exception:
                st.error("That file could not be read as a CSV. Please check it and try again.")
                return saved
            for p in problems:
                st.warning(p)
            if stock:
                key = (up.name, up.size)
                if st.session_state.get("rt_stock_saved") != key:       # save once per uploaded file
                    api_client.save_stock(stock)
                    st.session_state["rt_stock_saved"] = key
                st.success(f"Stock levels saved for {len(stock)} products. Stock alerts are now on.")
                return {**saved, **stock}
        if saved:
            st.caption(f"Using the {len(saved)} stock levels you saved earlier.")
            if st.button("Forget my saved stock", key="rt_stock_clear"):
                api_client.clear_stock()
                st.session_state.pop("rt_stock_saved", None)
                st.rerun()
        return saved


def snapshot_card(icon_name, title, pill_html, text, thumbs_html, link, href):
    return (f'<div class="rt-snap-card"><div class="rt-snap-top"><span class="rt-ico">{icon(icon_name)}</span>{pill_html}</div>'
            f"<h3>{title}</h3><p>{text}</p>{thumbs_html}"
            f'<a class="rt-more" href="{href}">{link} {icon("arrow", 16)}</a></div>')


def snapshot(signals, cats, has_stock, window):
    section("rt-snapshot", "Your retail snapshot", "Four things worth knowing today.")
    cards = []

    top = ix.best_sellers(signals)
    if top:
        cards.append(snapshot_card(
            "star", "Best sellers", pill("Going well", "good"),
            f"<b>{esc(top[0].name)}</b> leads your sales over the last {window} weeks"
            + (f", with {len(top) - 1} more close behind." if len(top) > 1 else "."),
            minis(top), "See the products", "#rt-gallery"))

    if not has_stock:
        cards.append(snapshot_card(
            "box", "Stock watch", pill("Needs your stock", "neutral"),
            "Add your stock levels to see which products may run short next week.",
            "", "Add stock levels", "#rt-stock"))
    else:
        flagged = ix.stock_watch(signals)
        if flagged:
            urgent = flagged[0].stock_state == "urgent"
            cards.append(snapshot_card(
                "box", "Stock watch", pill(f"{len(flagged)} need attention", "urgent" if urgent else "watch"),
                f"<b>{esc(flagged[0].name)}</b> is the most urgent. It may sell out before you can restock.",
                minis(flagged), "See what to do", "#rt-recs"))
        else:
            cards.append(snapshot_card(
                "box", "Stock watch", pill("All covered", "good"),
                "Your stock looks enough for next week's expected demand.", "", "See what to do", "#rt-recs"))

    up_cats = [c for c in cats if c["trend"] == "rising"]
    rising_products = ix.rising(signals)
    if up_cats:
        c = up_cats[0]
        cards.append(snapshot_card(
            "trend", "Emerging trends", pill("Rising", "good"),
            f"<b>{esc(c['label'])}</b> is heading up. Shoppers are expected to buy more of it next week.",
            minis(rising_products), "See the trends", "#rt-trends"))
    else:
        cards.append(snapshot_card(
            "trend", "Emerging trends", pill("Steady", "neutral"),
            "No category stands out right now. Demand looks stable.", minis(rising_products), "See the trends", "#rt-trends"))

    opps = ix.pricing_opportunities(signals)
    if opps:
        cards.append(snapshot_card(
            "tag", "Pricing opportunities", pill(f"{len(opps)} to review", "watch"),
            f"<b>{esc(opps[0][0].name)}</b> is a good place to start. Its price or promotion is worth a second look.",
            minis([s for s, _ in opps]), "Open the pricing assistant", "#rt-pricing"))
    else:
        cards.append(snapshot_card(
            "tag", "Pricing opportunities", pill("Nothing urgent", "neutral"),
            "No clear pricing opportunities at the moment.", "", "Open the pricing assistant", "#rt-pricing"))

    st.markdown('<div class="rt-snap">' + "".join(cards) + "</div>", unsafe_allow_html=True)


# ----------------------------------------------------------------------------- C. gallery
def product_card_html(s, info):
    return (f'<div class="rt-card">{product_visual(s.category, s.sku, s.name)}<div class="rt-body">'
            f'<div class="rt-tags"><span class="rt-cat">{esc(ix.pretty_category(s.category))}</span>'
            f'{pill(info["label"], info["tone"])}</div>'
            f'<div class="rt-name">{esc(s.name)}</div><div class="rt-text">{esc(info["text"])}</div>'
            f'<div class="rt-meta">Code {esc(s.sku)} · expected next week: about {s.forecast:,.0f} units (estimate)</div></div></div>')


def spotlight(s):
    info = ix.describe(s)
    idea = ix.price_idea(s)
    if s.stock is None:
        stock_line = "Add your stock levels above to see if it may run short."
    else:
        d = s.days_of_stock
        stock_line = f"You hold {s.stock:,.0f} units" + (f", roughly {d:.0f} days at the expected pace." if d is not None else ".")
    price_line = {
        "raise": "The price rule would nudge the price up, because demand is higher than your stock.",
        "lower": "The price rule would nudge the price down, because you hold more than you are likely to sell.",
        "review": "Sales look slower and shoppers react to price here, so a promotion may be worth testing.",
        "room": "Demand is rising and shoppers are not very price-sensitive, so there may be room to raise the price.",
    }.get(idea["kind"] if idea else "", "No price change is suggested right now.")
    if not s.price_is_reliable:
        price_line = "Price advice is unreliable here: in the past, sales rose when the price rose."
    facts = [("Current price", money(s.price)),
             (f"Sold, last {s.window} weeks", f"{s.units_window:,.0f} units"),
             ("Expected next week", f"~{s.forecast:,.0f} units"),
             ("Your stock", f"{s.stock:,.0f} units" if s.stock is not None else "Not added")]
    st.markdown(
        f'<div class="rt-spot">{product_visual(s.category, s.sku, s.name)}<div>'
        f'<div class="rt-tags"><span class="rt-cat">{esc(ix.pretty_category(s.category))}</span>{pill(info["label"], info["tone"])}</div>'
        f"<h3>{esc(s.name)}</h3><div class=\"rt-meta\">Product code {esc(s.sku)}</div>"
        f'<div class="rt-text">{esc(info["text"])}<br>{esc(stock_line)}<br>{esc(price_line)}</div>'
        '<div class="rt-facts">' + "".join(f'<div class="rt-fact"><small>{a}</small><span>{b}</span></div>' for a, b in facts)
        + "</div></div></div>", unsafe_allow_html=True)


def sales_chart(sku_df, forecast, height=240):
    recent = sku_df.tail(26)
    next_date = sku_df["date"].iloc[-1] + pd.Timedelta(weeks=1)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=recent["date"], y=recent["units_sold"], mode="lines", name="Actual sales",
                             line=dict(color=CHARCOAL, width=2)))
    fig.add_trace(go.Scatter(x=[recent["date"].iloc[-1], next_date], y=[recent["units_sold"].iloc[-1], forecast],
                             mode="lines+markers", name="Model estimate", line=dict(color=OLIVE, dash="dot"),
                             marker=dict(size=[0, 11])))
    fig.update_yaxes(title_text="Units per week")
    return chart_layout(fig, height)


def gallery(signals, window):
    section("rt-gallery", "How your products are doing",
            "Each card says what is happening and why it matters. Open one to see more.",
            '<div class="rt-legend"><span><b>Actual</b> = what customers bought</span>'
            "<span><b>Estimate</b> = what the model expects next week</span></div>")

    st.markdown('<div id="rt-spot" class="rt-anchor"></div>', unsafe_allow_html=True)
    focus = st.session_state.get("rt_focus")
    by_sku = {s.sku: s for s in signals}
    if focus in by_sku:
        spotlight(by_sku[focus])
        df = load_sales(os.path.getmtime(DATA_PATH))
        sku_df = df[df["sku"] == focus].sort_values("date")
        st.plotly_chart(sales_chart(sku_df, by_sku[focus].forecast), use_container_width=True)
        st.button("Close this product", key="rt_close", on_click=close_spotlight)

    choice = st.radio("Show", GALLERY_FILTERS, horizontal=True, key="rt_filter", label_visibility="collapsed")
    infos = {s.sku: ix.describe(s) for s in signals}
    pick = {
        "All products": lambda s: True,
        "Best sellers": lambda s: s.best_seller,
        "Needs attention": lambda s: infos[s.sku]["tone"] in ("watch", "urgent"),
        "Rising": lambda s: s.trend == "rising",
        "Slowing": lambda s: s.trend == "slowing",
    }[choice]
    shown = sorted((s for s in signals if pick(s)), key=lambda s: s.units_window, reverse=True)
    if not shown:
        st.markdown('<div class="rt-empty"><b>Nothing here right now.</b><br>No products match this view. '
                    "Try another filter or category.</div>", unsafe_allow_html=True)
        return

    limit = st.session_state.get("rt_show", PAGE_SIZE)
    for row_start in range(0, min(limit, len(shown)), 4):
        cols = st.columns(4, gap="medium")
        for col, s in zip(cols, shown[row_start:min(row_start + 4, limit)]):
            info = infos[s.sku]
            with col:
                st.markdown(product_card_html(s, info), unsafe_allow_html=True)
                st.button(info["cta"], key=f"cta_{s.sku}", on_click=open_product, args=(s.sku, info["target"]))
    if len(shown) > limit:
        st.button(f"Show more products ({len(shown) - limit} more)", key="rt_more",
                  on_click=lambda: st.session_state.update(rt_show=limit + PAGE_SIZE))
    elif limit > PAGE_SIZE:
        st.button("Show fewer", key="rt_less", on_click=lambda: st.session_state.update(rt_show=PAGE_SIZE))


# ----------------------------------------------------------------------------- D. recommendations
def recommendations(signals, cats):
    section("rt-recs", "What should you do next?",
            "Plain-English suggestions drawn from your sales history and the model's forecast.")
    recs = ix.build_recommendations(signals, cats)
    if not recs:
        st.markdown('<div class="rt-empty"><b>Nothing needs your attention.</b><br>Demand looks steady across your '
                    "products. Check back after the next week of sales.</div>", unsafe_allow_html=True)
        return
    names = {"urgent": "Act soon", "watch": "Worth a look", "good": "Opportunity"}
    for i in range(0, len(recs), 2):
        cols = st.columns(2, gap="medium")
        for col, r in zip(cols, recs[i:i + 2]):
            with col:
                st.markdown(
                    f'<div class="rt-reco {r.tone}"><h3><span>{esc(r.title)}</span>{pill(names[r.tone], r.tone)}</h3>'
                    f'<div class="rt-row"><b>What is happening</b><span>{esc(r.happening)}</span></div>'
                    f'<div class="rt-row"><b>Why it matters</b><span>{esc(r.why)}</span></div>'
                    f'<div class="rt-row do"><b>What you could do</b><span>{esc(r.action)}</span></div></div>',
                    unsafe_allow_html=True)
                if r.sku:
                    st.button(r.cta, key=f"rec_{r.kind}_{r.sku}", on_click=open_product, args=(r.sku, r.target))
                else:
                    st.button(r.cta, key=f"rec_{r.kind}_{r.category}", on_click=open_category, args=(r.category,))
    st.caption("Suggestions are model estimates based on past sales. They are a starting point for your own judgement.")


# ----------------------------------------------------------------------------- E. trends
def trends(cats, signals):
    section("rt-trends", "Trends and demand", "Where shoppers are heading, category by category.")
    if not cats:
        st.markdown('<div class="rt-empty"><b>No trend data yet.</b></div>', unsafe_allow_html=True)
        return
    cards = []
    for c in cats:
        tone = {"rising": "good", "steady": "neutral", "slowing": "watch"}[c["trend"]]
        sentence = {
            "rising": f"Shoppers are expected to buy about {abs(c['pct']):.0%} more than in recent weeks.",
            "steady": "Sales are expected to stay close to recent weeks.",
            "slowing": f"Shoppers are expected to buy about {abs(c['pct']):.0%} less than in recent weeks.",
        }[c["trend"]]
        cards.append(
            f'<div class="rt-trend"><div class="rt-tags"><h3>{esc(c["label"])}</h3>{pill(ix.trend_phrase(c["trend"]), tone)}</div>'
            f'{sparkline(c["history"], c["forecast"], TREND_COLOR[c["trend"]])}'
            f'<div class="rt-text">{sentence}</div></div>')
    st.markdown('<div class="rt-trends">' + "".join(cards) + "</div>", unsafe_allow_html=True)
    st.caption("The line is actual weekly sales. The dotted step and open circle are the model's estimate for next week.")

    def box(title, sigs, empty):
        if not sigs:
            return f'<div class="rt-watchbox"><h4>{title}</h4><div class="rt-text">{empty}</div></div>'
        rows = "".join(
            f'<div class="rt-li">{mini_thumb(s.category, s.sku)}<div>{esc(s.name)}<small>{esc(ix.pretty_category(s.category))}'
            f" · about {abs(s.trend_pct):.0%} {'above' if s.trend_pct > 0 else 'below'} recent weeks</small></div></div>"
            for s in sigs[:3])
        return f'<div class="rt-watchbox"><h4>{title}</h4>{rows}</div>'

    st.markdown('<div class="rt-watch">'
                + box("Likely to gain popularity", ix.rising(signals), "No product stands out right now.")
                + box("Sales may be slowing", ix.slowing(signals), "No product stands out right now.") + "</div>",
                unsafe_allow_html=True)


# ----------------------------------------------------------------------------- F. pricing assistant
def pricing_assistant(signals, stock_map):
    section("rt-pricing", "Pricing assistant",
            "Compare today's price with the model's suggestion, and see the reason behind it.")
    usable = [s for s in signals if s.elasticity is not None]
    if not usable:
        st.markdown('<div class="rt-empty"><b>Not enough sales history to suggest prices.</b><br>'
                    "Each product needs at least 10 weeks of sales.</div>", unsafe_allow_html=True)
        return
    by_sku = {s.sku: s for s in usable}
    options = [s.sku for s in usable]
    opps = ix.pricing_opportunities(usable)
    if st.session_state.get("rt_price_sku") not in by_sku:
        st.session_state["rt_price_sku"] = opps[0][0].sku if opps else options[0]

    c1, c2 = st.columns([3, 2], gap="large")
    with c1:
        sku = st.selectbox("Choose a product", options, key="rt_price_sku",
                           format_func=lambda k: f"{by_sku[k].name}  ({k})")
    s = by_sku[sku]
    known = stock_map.get(sku)
    with c2:
        stock = st.number_input("Units you have in stock", min_value=0, value=int(known) if known is not None else 100,
                                step=10, key=f"rt_pstock_{sku}",
                                help="Taken from your stock file if you added one. Otherwise 100 is only an example, so enter your own number.")
    if known is None:
        st.caption("No stock file for this product, so 100 units is just an example. Change it to see how the advice moves.")

    rec = recommend_price(sku=sku, current_price=s.price, forecasted_demand=s.forecast,
                          current_stock=float(stock), elasticity=s.elasticity)
    change = rec.recommended_price - s.price
    low_conf = (not s.price_is_reliable) or (s.r_squared is not None and s.r_squared < 0.3)
    badge = pill("Low confidence", "watch") if low_conf else pill("Model estimate", "est")
    if rec.pct_change == 0:
        why = stock_position(s.forecast, float(stock))
        change_txt = "No change suggested"
    else:
        why = stock_position(s.forecast, float(stock))
        change_txt = f"{'Up' if change > 0 else 'Down'} {abs(rec.pct_change):.0%} ({'+' if change > 0 else '-'}{money(abs(change))})"
    st.markdown(
        '<div class="rt-prices">'
        f'<div class="rt-pbox"><small>Current price {pill("Actual", "neutral")}</small><div class="rt-big">{money(s.price)}</div>'
        f"<p>What you charge now.</p></div>"
        f'<div class="rt-pbox sug"><small>Suggested price {badge}</small><div class="rt-big">{money(rec.recommended_price)}</div>'
        f"<p>{change_txt}</p></div>"
        f'<div class="rt-pbox"><small>The reason</small><p style="margin-top:10px">{esc(why)}<br><br>{esc(elasticity_sentence(s.elasticity))}</p></div>'
        "</div>", unsafe_allow_html=True)

    if rec.pct_change == 0 and known is None and ix.price_idea(s):
        st.markdown('<div class="rt-note">This product was flagged from its sales trend. The price rule also needs your stock, so '
                    "enter your own number above to see a suggested price.</div>", unsafe_allow_html=True)
    if not s.price_is_reliable:
        st.markdown('<div class="rt-note warn">For this product, sales rose when the price rose in the past. That usually means '
                    "promotions or seasons are mixed into the data, so treat the suggestion as a rough guide only.</div>",
                    unsafe_allow_html=True)
    st.markdown('<div class="rt-note"><b>Model estimates, not results.</b> The suggested price is based on past sales and your stock. '
                "A price change does not guarantee more sales or more revenue, so use it alongside your own judgement.</div>",
                unsafe_allow_html=True)

    with st.expander("How was this estimated?"):
        st.write(f"Price sensitivity here is **{fit_label(s.r_squared or 0)}** in how well it explains past sales "
                 f"(based on this product's full sales history). The rule moves the price at most 15% up or 30% down, and moves it "
                 "less for products whose sales react strongly to price.")
        out = revenue_outlook(s.price, s.forecast, float(stock), rec.recommended_price, s.elasticity)
        if out and rec.pct_change != 0:
            delta = out["revenue_new"] - out["revenue_now"]
            m1, m2 = st.columns(2)
            m1.metric("Estimated revenue, keep price", money(out["revenue_now"]))
            m2.metric("Estimated revenue, suggested price", money(out["revenue_new"]), f"{delta:+,.0f}")
            st.caption("Estimates only. Units are capped at your stock, and the model's price-sensitivity figure is used to guess how many "
                       "customers a price change would cost you.")
        else:
            st.caption("A revenue estimate is not shown because no price change is suggested, or the price-sensitivity figure is unreliable.")


# ----------------------------------------------------------------------------- F2. shopper interest
def shopper_interest(df_all):
    """What shoppers did in the try-on store (the abstract's 'intent signals'), from the events log."""
    ev = api_client.engagement_summary()
    section("rt-interest", "Shopper interest",
            "What shoppers did in the try-on store. This is a live log from the shopper tab, so it starts empty.")
    if not ev["total_events"]:
        st.markdown('<div class="rt-empty">No shopper activity yet. Open the <b>For shoppers</b> tab, measure your T-shirt size, '
                    "view some picks or try a shirt on, then come back.</div>", unsafe_allow_html=True)
        return
    m1, m2, m3 = st.columns(3)
    m1.metric("T-shirt sizes read", ev.get("size_reads", 0))
    m2.metric("Outfit picks viewed", ev["picks_viewed"])
    m3.metric("Shirts tried on", ev["tryons"])
    c1, c2 = st.columns(2, gap="large")
    with c1:
        if ev.get("top_sizes"):
            st.markdown("**T-shirt sizes shoppers measured**")
            fig = px.bar(pd.DataFrame(ev["top_sizes"], columns=["Size", "Shoppers"]), x="Shoppers", y="Size", orientation="h")
            fig.update_traces(marker_color=OLIVE)
            fig.update_xaxes(dtick=1)
            st.plotly_chart(chart_layout(fig, 220), use_container_width=True)
    with c2:
        window = st.select_slider("Look back over", options=[4, 8, 12], value=4, key="shopper_interest_rt_window",
                                  format_func=lambda w: f"Last {w} weeks",
                                  help="How many recent weeks of real sales to compare against.")

    st.markdown('<div id="rt-stock" class="rt-anchor"></div>', unsafe_allow_html=True)
    stock_map = stock_controls(df_all)

    df = df_all if cat == "all" else df_all[df_all["category"] == cat]
    signals = ix.build_signals(df, forecasts, elasticities, stock_map, window)
    cat_trends = ix.category_trends(df, signals)
    sig_by_sku = {s.sku: s for s in signals}

    if not model_ok:
        st.markdown('<div class="rt-note warn">The demand model has not been trained yet, so next-week numbers use each '
                    "product's recent average. Run <code>python -m demand_forecasting.train_lightgbm</code> for model forecasts.</div>",
                    unsafe_allow_html=True)

    snapshot(signals, cat_trends, bool(stock_map), window)
    gallery(signals, window)
    recommendations(signals, cat_trends)
    trends(cat_trends, signals)
    pricing_assistant(signals, stock_map)

    shopper_interest(df_all)

    section("rt-advanced", "Product deep-dive", "Pick one product and see the story behind the advice, step by step, in plain words.")
    with st.expander("Open the product deep-dive"):
        advanced(df_all, elasticities, forecasts, model_ok, stock_map)

    st.caption(f"Data connection: {api_client.mode()}.")

    scroll_to = st.session_state.pop("rt_scroll", None)
    if scroll_to:
        components.html(
            "<script>setTimeout(function(){var e=window.parent.document.getElementById('%s');"
            "if(e){e.scrollIntoView({behavior:'smooth',block:'start'});}},400);</script>" % scroll_to, height=0)


# ----------------------------------------------------------------------------- G. advanced analytics
def glossary():
    with st.expander("New to these words? What things on this page mean"):
        for term, text in GLOSSARY:
            st.markdown(f"**{term}.** {text}")


def advanced(df, elasticities, forecasts, model_ok, stock_map):
    st.markdown("Pick one product. We walk you through it in four simple questions, with pictures and plain words. "
                "Stuck on a word? Open *What things on this page mean* near the top of the page.")
    skus = sorted(df["sku"].unique())
    sig_all = {s.sku: s for s in ix.build_signals(df, forecasts, elasticities, stock_map, 4)}

    def label(k):
        sg = sig_all.get(k)
        return f"{sg.name}  ({k})" if sg else k
    sku = st.selectbox("Product", skus, key="adv_sku", format_func=label)
    sku_df = df[df["sku"] == sku].sort_values("date")
    latest = sku_df.iloc[-1]
    price_now = float(latest["price"])
    forecast, used_model = forecasts[sku]
    sg = sig_all.get(sku)
    recent_avg = float(sku_df["units_sold"].tail(4).mean())

    if sg is not None:
        info = ix.describe(sg)
        st.markdown(f'<div class="rt-note"><b>In short:</b> {esc(info["text"])} You usually sell about {recent_avg:,.0f} units a week '
                    f"and we expect about {forecast:,.0f} next week.</div>", unsafe_allow_html=True)

    st.subheader("1. How have sales been going?")
    st.write("Each point is one week. A line going up means more units sold that week.")
    fig = px.line(sku_df, x="date", y="units_sold", labels={"units_sold": "Units sold in the week", "date": ""})
    fig.update_traces(line_color=CHARCOAL)
    promo = sku_df[sku_df["promo_flag"] == 1]
    if len(promo):
        fig.add_trace(go.Scatter(x=promo["date"], y=promo["units_sold"], mode="markers", name="Week with a promotion",
                                 marker=dict(color=CLAY, size=7)))
    st.plotly_chart(chart_layout(fig), use_container_width=True)
    st.caption("Orange dots are weeks when the product was on promotion. Notice how often they sit above the line.")
    m1, m2, m3 = st.columns(3)
    m1.metric("Usual week lately", f"{recent_avg:,.0f} units", help="The average of the last 4 weeks.")
    m2.metric("Price now", money(price_now))
    m3.metric("Weeks on promotion", f"{sku_df['promo_flag'].mean():.0%}", help="Share of all weeks in this history when the product was on promotion.")

    st.subheader("2. What do we expect next week?")
    st.plotly_chart(sales_chart(sku_df, forecast, 260), use_container_width=True)
    st.caption("The solid line is what really sold. The dotted step and open circle are the computer's estimate for next week.")
    f1, f2 = st.columns([1, 2])
    f1.metric("Expected next week", f"about {forecast:,.0f} units")
    if used_model and os.path.exists(METRICS_PATH):
        with open(METRICS_PATH) as fh:
            mt = json.load(fh)
        if mt.get("split") == "time" and mt.get("baseline_4week_average"):
            base = mt["baseline_4week_average"]
            f2.markdown(f'<div class="rt-note"><b>How much to trust this?</b> We tested the computer on the last {mt["holdout_weeks"]} weeks, '
                        f'pretending not to know them. It was usually within about <b>{mt["mae"]:.0f} units</b> of what really sold. '
                        f'Just guessing "same as the last 4 weeks" would have missed by about {base["mae"]:.0f}. '
                        "So the estimate is useful, but it is still an estimate.</div>", unsafe_allow_html=True)
        else:
            f2.markdown('<div class="rt-note">The estimate comes from a computer model that learned from every product\'s weekly sales.</div>',
                        unsafe_allow_html=True)
    elif used_model:
        f2.markdown('<div class="rt-note">The estimate comes from a computer model that learned from every product\'s weekly sales.</div>',
                    unsafe_allow_html=True)
    else:
        f2.markdown('<div class="rt-note">The model is not set up yet, so this uses the average of the last 4 weeks.</div>',
                    unsafe_allow_html=True)

    st.subheader("3. Do shoppers care about the price?")
    res = elasticities.get(sku)
    if not res:
        st.warning("There are not enough weeks of sales to tell how shoppers react to price for this product.")
    else:
        e1, e2 = st.columns([2, 3], gap="large")
        with e1:
            word = sensitivity_word(res.elasticity)
            st.metric("Price sensitivity", word, help="High: shoppers walk away quickly when the price rises. Low: they keep buying.")
            st.write(price_effect_sentence(res.elasticity))
            st.caption(sureness(res.r_squared, res.n_obs))
            st.caption(f"Technical numbers, for the report: price elasticity {res.elasticity:.2f}, R-squared {res.r_squared:.2f}, "
                       f"{res.n_obs} weeks. Elasticity is the % change in units for a 1% price change; R-squared is the share "
                       "of the ups and downs in sales that price explains.")
        with e2:
            sc = px.scatter(sku_df.assign(Week=sku_df["promo_flag"].map({0: "Normal week", 1: "Promotion week"})),
                            x="price", y="units_sold", color="Week",
                            color_discrete_map={"Normal week": CHARCOAL, "Promotion week": CLAY},
                            labels={"price": "Price that week (₹)", "units_sold": "Units sold"})
            sc.update_layout(legend_title_text="")
            st.plotly_chart(chart_layout(sc, 260), use_container_width=True)
            st.caption("Each dot is one week. If the dots slope down to the right, higher prices meant fewer sales.")

        st.subheader("4. So what should you do?")
        default_stock = stock_map.get(sku, 100.0)
        stock = st.number_input("How many units do you have in stock?", min_value=0.0, value=float(default_stock), step=10.0, key="adv_stock",
                                help="Try different numbers. More stock than you can sell pushes the advice toward a lower price; less pushes it higher.")
        if sku not in stock_map:
            st.caption("You have not added stock for this product, so 100 is just an example. Change it to your real number.")
        rec = recommend_price(sku=sku, current_price=price_now, forecasted_demand=forecast,
                              current_stock=stock, elasticity=res.elasticity)
        st.markdown(f'<div class="rt-note"><b>{verdict(rec.current_price, rec.recommended_price, rec.pct_change)}.</b> '
                    f"{esc(stock_position(forecast, stock))}</div>", unsafe_allow_html=True)
        out = revenue_outlook(price_now, forecast, stock, rec.recommended_price, res.elasticity)
        if out and rec.pct_change != 0:
            r1, r2 = st.columns([2, 3], gap="large")
            with r1:
                delta = out["revenue_new"] - out["revenue_now"]
                st.metric("Estimated money from this product next week", money(out["revenue_new"]), f"{delta:+,.0f} compared with keeping the price")
                st.caption("An estimate, not a promise. You cannot sell more than you have in stock.")
            with r2:
                bar = go.Figure(go.Bar(x=["Keep current price", "Use suggested price"],
                                       y=[out["revenue_now"], out["revenue_new"]], marker_color=[SAND, OLIVE],
                                       text=[money(out["revenue_now"]), money(out["revenue_new"])], textposition="outside"))
                bar.update_yaxes(visible=False)
                st.plotly_chart(chart_layout(bar, 240), use_container_width=True)

    st.subheader("All products at a glance")
    st.write("One line per product, with the plain-words advice. Click a column title to sort.")
    cover = st.slider("For products without a stock number, assume you hold this many weeks of sales", 0.3, 3.0, 1.0, 0.1,
                      help="Only used when you have not added stock. 1.0 means you hold about one week of sales, so no price change is pushed. It is a guess, not your real stock.")
    rows = []
    for k in skus:
        d = df[df["sku"] == k].sort_values("date")
        r = elasticities.get(k)
        if r is None:
            continue
        fc, _ = forecasts[k]
        p = float(d.iloc[-1]["price"])
        have = stock_map.get(k)
        rc = recommend_price(k, p, fc, have if have is not None else fc * cover, r.elasticity)
        sg_k = sig_all.get(k)
        rows.append({"Product": sg_k.name if sg_k else k, "Code": k, "Type": ix.pretty_category(d.iloc[-1]["category"]), "Price now (₹)": round(p),
                     "Expected next week (units)": round(fc), "Price sensitivity": sensitivity_word(r.elasticity),
                     "Stock": "Yours" if have is not None else "Guessed",
                     "Suggestion": suggestion_phrase(rc.pct_change), "Suggested price (₹)": round(rc.recommended_price)})
    table = pd.DataFrame(rows)
    st.dataframe(table, use_container_width=True, hide_index=True)
    st.caption("Raise: you expect to sell more than you hold. Lower: you hold much more than you expect to sell. Keep: they are close, "
               "or the price signal is not reliable. Rows marked Guessed use the assumption above, not your real stock.")
