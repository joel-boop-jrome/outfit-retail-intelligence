"""
Two-sided Streamlit UI.
  - Customer tab: live camera try-on, body-shape detection, product recommendations.
  - Retailer tab: insight cards, product gallery, next-step advice, trends and a pricing assistant
    (see frontend/retail_page.py).

  - How it works tab: architecture, code map, results and viva notes (frontend/about_page.py).

Run with:
    python -m streamlit run frontend/app.py
"""
import os
import sys

import streamlit as st

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(ROOT)

from cv_vto.body_shape import size_fit_note, size_with_number
from cv_vto.style_recommender import BODY_SHAPE_STYLE_MAP, recommend_styles
from frontend import about_page, api_client, retail_page, retail_style, style
from frontend.catalog import product_card, parse_recommendation

GARMENT_DIR = os.path.join(ROOT, "assets", "garments")

st.set_page_config(page_title="Outfit & Retail Intelligence", page_icon="🧵", layout="wide")
style.inject()
retail_style.inject()

st.markdown('<div class="brand">Outfit &amp; Retail Intelligence</div>', unsafe_allow_html=True)

customer_tab, retailer_tab, about_tab = st.tabs(["For shoppers", "For retailers", "How it works"])


# ----------------------------------------------------------------------------- shoppers
def render_card(card: dict):
    st.markdown(
        f'<div class="tag">{card["svg"]}'
        f'<div class="t-name">{card["name"]}</div>'
        f'<div class="t-row"><span class="t-color"><span class="t-dot" style="background:{card["color_hex"]}"></span>'
        f'{card["color_name"]}</span><span class="t-price">₹{card["price"]:,}</span></div>'
        f'<div class="t-why">{card["reason"]}</div></div>',
        unsafe_allow_html=True,
    )


def set_garment(filename: str):
    st.session_state["garment_choice"] = filename
    api_client.log_event("tryon", st.session_state.get("shape"), st.session_state.get("tone"), filename)
    st.toast("Shirt selected. Scroll up to the camera to see it on you.")


with customer_tab:
    st.markdown(
        '<div class="hero"><h1>Find what suits you, and price what sells.</h1>'
        "<p>Stand in front of the camera to get your T-shirt size, try shirts on live, and get outfit picks. "
        "Switch to the retailer view to see how your store is doing and what to do next.</p></div>",
        unsafe_allow_html=True,
    )
    try:
        from streamlit_webrtc import webrtc_streamer, RTCConfiguration
        from frontend.webcam import BodyShapeProcessor
        webcam_ok, webcam_err = True, None
    except Exception as e:  # package missing, mediapipe blocked, etc.
        webcam_ok, webcam_err = False, e

    garments = sorted(f for f in os.listdir(GARMENT_DIR) if f.lower().endswith(".png")) \
        if os.path.isdir(GARMENT_DIR) else []

    cam_col, ctl_col = st.columns([3, 2], gap="large")

    with cam_col:
        st.subheader("Try it on")
        if webcam_ok:
            ctx = webrtc_streamer(
                key="body-shape",
                video_processor_factory=BodyShapeProcessor,
                media_stream_constraints={"video": True, "audio": False},
                rtc_configuration=RTCConfiguration(
                    {"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]}),
                async_processing=True,
            )
            st.caption("Press START and allow the camera. Stand about 120 cm (4 ft) from the camera, head inside the circle, "
                       "shoulders and hips in view. The circle turns green when you are in place; hold still until the bar fills.")
        else:
            ctx = None
            st.markdown(
                f'<div class="note">The in-browser camera could not load ({webcam_err}). '
                "Run <code>python -m pip install streamlit-webrtc==0.47.9</code>, or use the desktop window: "
                "<code>python -m cv_vto.garment_overlay assets/garments/tshirt_navy.png</code></div>",
                unsafe_allow_html=True,
            )

    with ctl_col:
        st.subheader("Your size")
        proc = ctx.video_processor if (ctx is not None and ctx.video_processor) else None
        if proc is not None and st.session_state.get("torso_target"):
            proc.torso_target = st.session_state["torso_target"]

        if ctx is not None and st.button("Read my T-shirt size", type="primary"):
            _, detected_size = proc.read() if proc else (None, None)
            if detected_size:
                st.session_state["size"] = detected_size
                api_client.log_event("size_read", item=detected_size)
            else:
                st.warning("Not measured yet. Stand about 120 cm (4 ft) from the camera with your head in the circle, "
                           "and hold still until the bar fills and the size appears on the video. Then press this again.")
        if st.session_state.get("size"):
            size = st.session_state["size"]
            st.markdown(f'<div class="note"><b>Your estimated T-shirt size: {size_with_number(size)}</b><br>'
                        f'{size_fit_note(size)}. An estimate from your shoulder width at about 120 cm. '
                        "Check the brand's size chart before buying.</div>", unsafe_allow_html=True)
        if ctx is not None:
            with st.expander("Is the distance right? Calibrate for your camera"):
                st.write("Every camera sees a different amount. Stand exactly **120 cm (4 ft)** from the camera, head in the circle, "
                         "shoulders and hips in view, then press the button. The app remembers how big you look at that distance.")
                if st.button("I am standing 120 cm away: calibrate"):
                    got = proc.calibrate() if proc else None
                    if got:
                        st.session_state["torso_target"] = got
                        st.success("Calibrated. The circle turns green when you are at about this distance.")
                    else:
                        st.warning("No body found. Stand in view, wait a second and press it again.")
                if st.session_state.get("torso_target"):
                    st.caption("Calibration is on for this session.")

        st.subheader("Your look")
        choice = st.selectbox("Shirt on camera", ["None"] + garments, key="garment_choice",
                              format_func=lambda f: f if f == "None" else f[:-4].replace("_", " ").title())
        show_skel = st.checkbox("Show body outline", value=False)
        if proc is not None:
            proc.garment_path = None if choice == "None" else os.path.join(GARMENT_DIR, choice)
            proc.show_skeleton = show_skel

        shapes = list(BODY_SHAPE_STYLE_MAP.keys())
        shape = st.selectbox("Body shape (for outfit picks)", shapes, key="shape",
                             format_func=lambda s: s.replace("_", " ").title(),
                             help="Choose the shape closest to yours. It selects which styles are suggested.")
        tone = st.selectbox("Colour tone", ["warm", "cool", "neutral"], key="tone",
                            format_func=str.title)
        if st.button("Show outfit picks"):
            st.session_state["picks"] = (shape, tone)
            api_client.log_event("picks_viewed", shape, tone)

    picks = st.session_state.get("picks")
    if picks:
        p_shape, p_tone = picks
        st.subheader(f"Picks for a {p_shape.replace('_', ' ')} shape in {p_tone} tones")
        recs = [parse_recommendation(r) for r in api_client.styles_for(p_shape, p_tone)]
        cols = st.columns(4, gap="medium")
        for col, (style_id, color_key) in zip(cols, recs):
            card = product_card(style_id, color_key)
            with col:
                render_card(card)
                if card["tryon_file"] and card["tryon_file"] in garments and ctx is not None:
                    st.button("Try this shirt on", key=f"try_{style_id}_{color_key}",
                              on_click=set_garment, args=(card["tryon_file"],))
        st.caption("Names, prices and pictures are sample placeholders. Connect a real catalogue to show your own products.")
    else:
        st.markdown('<div class="note">Choose your body shape and colour tone, then press '
                    '<b>Show outfit picks</b> to see products that suit you.</div>', unsafe_allow_html=True)


# ----------------------------------------------------------------------------- retailers
with retailer_tab:
    retail_page.render()


# ----------------------------------------------------------------------------- guide
with about_tab:
    about_page.render()
