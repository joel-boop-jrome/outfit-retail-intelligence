"""Look and feel for the dashboard: pattern-paper background, stitched hang tags."""
import streamlit as st

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,500;12..96,700&family=DM+Sans:wght@400;500;700&display=swap');
:root{
  --ink:#1B2559; --paper:#F2F4F9; --chalk:#FFFFFF; --coral:#F2546B; --sky:#DDE5F7; --muted:#5A6592;
  --stitch:rgba(27,37,89,.38);
}
html, body, [class*="css"], .stApp{ font-family:'DM Sans',system-ui,sans-serif; color:var(--ink); }
.stApp{
  background-color:var(--paper);
  background-image:
    linear-gradient(rgba(27,37,89,.045) 1px, transparent 1px),
    linear-gradient(90deg, rgba(27,37,89,.045) 1px, transparent 1px);
  background-size:28px 28px;
}
.block-container{ padding-top:2.2rem; max-width:1180px; }
h1,h2,h3,h4{ font-family:'Bricolage Grotesque','DM Sans',sans-serif; letter-spacing:-.01em; color:var(--ink); }
h2{ font-size:1.65rem; margin-top:.4rem; }
h3{ font-size:1.25rem; }
p, li{ line-height:1.55; }
header[data-testid="stHeader"]{ background:transparent; }

.brand{ font-family:'Bricolage Grotesque','DM Sans',sans-serif; font-weight:700; font-size:1.05rem; letter-spacing:.02em; margin:0 0 10px 4px; }

/* hero */
.hero{ background:var(--ink); color:#fff; border-radius:20px; padding:30px 34px 28px; margin-bottom:22px;
  background-image:radial-gradient(circle at 92% 18%, rgba(242,84,107,.55), transparent 42%),
                   linear-gradient(rgba(255,255,255,.06) 1px, transparent 1px),
                   linear-gradient(90deg, rgba(255,255,255,.06) 1px, transparent 1px);
  background-size:auto, 28px 28px, 28px 28px; }
.hero h1{ color:#fff; font-size:2.35rem; line-height:1.08; margin:0 0 10px; font-weight:700; max-width:760px; }
.hero p{ color:#C9D2F0; font-size:1.05rem; margin:0; max-width:640px; }

/* tabs as pills */
.stTabs [data-baseweb="tab-list"]{ gap:8px; border-bottom:none; }
.stTabs [data-baseweb="tab"]{ background:var(--chalk); border-radius:999px; padding:8px 20px; height:auto;
  border:1.5px solid rgba(27,37,89,.15); color:var(--ink); font-weight:500; }
.stTabs [aria-selected="true"]{ background:var(--ink); color:#fff; border-color:var(--ink); }
.stTabs [data-baseweb="tab-highlight"], .stTabs [data-baseweb="tab-border"]{ display:none; }

/* hang-tag product card */
.tag{ background:var(--chalk); border:2px dashed var(--stitch); border-radius:16px; padding:22px 16px 14px;
  position:relative; margin-top:16px; height:100%; }
.tag::before{ content:""; position:absolute; top:-10px; left:50%; width:16px; height:16px; margin-left:-8px;
  border-radius:50%; background:var(--paper); border:2px dashed var(--stitch); }
.tag svg{ width:100%; height:190px; display:block; margin:2px 0 8px; }
.tag .t-name{ font-family:'Bricolage Grotesque',sans-serif; font-weight:700; font-size:1.08rem; line-height:1.2; }
.tag .t-row{ display:flex; justify-content:space-between; align-items:center; margin:6px 0 8px; }
.tag .t-color{ display:flex; align-items:center; gap:7px; color:var(--muted); font-size:.9rem; }
.tag .t-dot{ width:14px; height:14px; border-radius:50%; border:1.5px solid rgba(27,37,89,.3); display:inline-block; }
.tag .t-price{ font-weight:700; font-size:1.05rem; }
.tag .t-why{ color:var(--muted); font-size:.88rem; line-height:1.45; }

/* panels and step cards */
.panel{ background:var(--chalk); border-radius:16px; padding:18px 20px; border:1.5px solid rgba(27,37,89,.1); }
.steps{ display:grid; grid-template-columns:repeat(4,1fr); gap:12px; margin:8px 0 18px; }
.step{ background:var(--chalk); border-radius:14px; padding:14px 16px; border:1.5px solid rgba(27,37,89,.1); }
.step b{ font-family:'Bricolage Grotesque',sans-serif; font-size:1.05rem; display:block; margin-bottom:4px; }
.step span{ color:var(--muted); font-size:.9rem; line-height:1.45; display:block; }
.step i{ font-style:normal; display:inline-flex; width:26px; height:26px; border-radius:50%; background:var(--ink); color:#fff;
  align-items:center; justify-content:center; font-weight:700; font-size:.85rem; margin-bottom:8px; }
@media (max-width:820px){ .steps{ grid-template-columns:1fr 1fr; } .hero h1{ font-size:1.8rem; } }

.verdict{ border-radius:18px; padding:22px 26px; margin:6px 0 14px; color:#fff; }
.verdict.up{ background:var(--ink); } .verdict.down{ background:var(--coral); } .verdict.hold{ background:#3A4A8C; }
.verdict h3{ color:#fff; margin:0 0 6px; font-size:1.6rem; }
.verdict p{ margin:0; color:rgba(255,255,255,.88); }
.note{ background:var(--sky); border-radius:12px; padding:12px 16px; color:var(--ink); font-size:.95rem; margin:6px 0 12px; }

/* streamlit widgets */
div[data-testid="stMetric"]{ background:var(--chalk); border-radius:14px; padding:12px 16px; border:1.5px solid rgba(27,37,89,.1); }
div[data-testid="stMetricLabel"] p{ color:var(--muted); }
.stButton > button{ border-radius:999px; border:1.5px solid var(--ink); color:var(--ink); background:var(--chalk); font-weight:500; }
.stButton > button:hover{ background:var(--ink); color:#fff; border-color:var(--ink); }
.stButton > button:focus:not(:active){ color:var(--ink); border-color:var(--ink); }
.stButton > button:hover:focus:not(:active){ color:#fff; }
.stButton > button[kind="primary"]:focus:not(:active){ color:#fff; border-color:var(--coral); }
.stCaptionContainer{ margin-top:10px; }
.stButton > button:focus-visible{ outline:3px solid var(--coral); outline-offset:2px; }
.stButton > button[kind="primary"]{ background:var(--coral); border-color:var(--coral); color:#fff; }
@media (prefers-reduced-motion:no-preference){ .stButton > button{ transition:background .15s, color .15s; } }
</style>
"""


def inject():
    st.markdown(CSS, unsafe_allow_html=True)
