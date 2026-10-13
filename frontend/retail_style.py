"""Styles for the Retailers page: warm ivory, charcoal and olive. Scoped to the retailer tab."""
import streamlit as st

P = 'div[data-baseweb="tab-panel"]:has(.rt-root)'   # the retailer tab panel only

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,400;0,9..144,600;1,9..144,400;1,9..144,500&display=swap');

__P__{
  --ivory:#FAF7F0; --card:#FFFDF8; --sand:#EFE8DA; --line:#E2D9C6; --ink:#2A2A26; --muted:#655F54;
  --olive:#5F6B3A; --olive-dk:#48522B; --olive-soft:#E8ECD6;
  --good:#2F6B3F; --good-bg:#E2F0E4; --watch:#8A5A0B; --watch-bg:#FBEFD2; --urgent:#A33A2B; --urgent-bg:#F8E1DB;
  --serif:'Fraunces',Georgia,'Times New Roman',serif;
  background:var(--ivory); color:var(--ink); border:1px solid var(--line); border-radius:28px;
  padding:34px 36px 44px; margin-top:10px; box-shadow:0 18px 50px -28px rgba(60,50,30,.35);
}
__P__ .rt-root{ display:none; }
__P__ h1, __P__ h2, __P__ h3, __P__ h4{ font-family:var(--serif); color:var(--ink); letter-spacing:-.01em; font-weight:500; }
__P__ p, __P__ li, __P__ label, __P__ span{ color:inherit; }
__P__ .rt-anchor{ scroll-margin-top:24px; height:0; }

/* ------------------------------------------------------------ welcome header */
__P__ .rt-hero{ display:grid; grid-template-columns:1.1fr .9fr; gap:28px; align-items:center;
  background:linear-gradient(135deg,#F3ECDC 0%,#EBE2CC 100%); border-radius:24px; padding:34px 38px; margin-bottom:26px;
  border:1px solid var(--line); }
__P__ .rt-eyebrow{ font-size:.78rem; letter-spacing:.16em; text-transform:uppercase; color:var(--olive-dk); font-weight:700; margin:0 0 12px; }
__P__ .rt-hero h1{ font-size:clamp(2.1rem,4.4vw,3.3rem); line-height:1.04; margin:0 0 14px; padding:0; }
__P__ .rt-hero h1 em{ color:var(--olive); font-style:italic; font-weight:400; }
__P__ .rt-hero p.rt-sub{ font-size:1.08rem; line-height:1.55; color:var(--muted); max-width:30em; margin:0 0 18px; }
__P__ .rt-chips{ display:flex; flex-wrap:wrap; gap:8px; }
__P__ .rt-chip{ background:rgba(255,253,248,.8); border:1px solid var(--line); border-radius:999px; padding:6px 14px; font-size:.85rem; color:var(--muted); }
__P__ .rt-hero-art svg{ width:100%; height:auto; display:block; max-height:290px; }

/* ------------------------------------------------------------ section headings */
__P__ .rt-sec{ margin:40px 0 16px; }
__P__ .rt-sec h2{ font-size:clamp(1.55rem,2.6vw,2rem); margin:0 0 4px; padding:0; }
__P__ .rt-sec p{ color:var(--muted); margin:0; font-size:1rem; }
__P__ .rt-legend{ display:flex; flex-wrap:wrap; gap:14px; font-size:.84rem; color:var(--muted); margin:6px 0 0; }
__P__ .rt-legend b{ color:var(--ink); }

/* ------------------------------------------------------------ pills */
__P__ .rt-pill{ white-space:nowrap; display:inline-flex; align-items:center; gap:6px; border-radius:999px; padding:4px 11px; font-size:.78rem; font-weight:700; letter-spacing:.01em; }
__P__ .rt-pill::before{ content:""; width:7px; height:7px; border-radius:50%; background:currentColor; }
__P__ .rt-pill.good{ background:var(--good-bg); color:var(--good); }
__P__ .rt-pill.watch{ background:var(--watch-bg); color:var(--watch); }
__P__ .rt-pill.urgent{ background:var(--urgent-bg); color:var(--urgent); }
__P__ .rt-pill.neutral{ background:var(--sand); color:var(--muted); }
__P__ .rt-pill.est{ background:var(--olive-soft); color:var(--olive-dk); }
__P__ .rt-pill.est::before{ display:none; }

/* ------------------------------------------------------------ snapshot cards */
__P__ .rt-snap{ display:grid; grid-template-columns:repeat(4,1fr); gap:16px; }
__P__ .rt-snap-card{ background:var(--card); border:1px solid var(--line); border-radius:20px; padding:20px 20px 16px;
  display:flex; flex-direction:column; gap:10px; text-decoration:none; color:var(--ink); min-height:236px; }
__P__ .rt-snap-top{ display:flex; justify-content:space-between; align-items:center; }
__P__ .rt-ico{ width:42px; height:42px; border-radius:12px; background:var(--olive-soft); color:var(--olive-dk);
  display:inline-flex; align-items:center; justify-content:center; }
__P__ .rt-snap-card h3{ font-size:1.18rem; margin:4px 0 0; padding:0; }
__P__ .rt-snap-card p{ margin:0; color:var(--muted); font-size:.95rem; line-height:1.5; }
__P__ .rt-minis{ display:flex; padding-top:4px; }
__P__ .rt-mini{ width:38px; height:38px; border-radius:50%; background:var(--sand); border:2px solid var(--card); margin-right:-8px;
  display:inline-flex; align-items:center; justify-content:center; overflow:hidden; }
__P__ .rt-mini svg, __P__ .rt-mini img{ width:100%; height:100%; object-fit:cover; padding:5px; box-sizing:border-box; }
__P__ .rt-mini img{ padding:0; }
__P__ .rt-more{ display:inline-flex; align-items:center; gap:6px; color:var(--olive-dk); font-weight:700; font-size:.88rem; text-decoration:none; margin-top:auto; padding-top:8px; }
__P__ .rt-more:hover{ text-decoration:underline; }

/* ------------------------------------------------------------ product cards */
__P__ .rt-card{ min-height:410px; background:var(--card); border:1px solid var(--line); border-radius:20px; overflow:hidden; height:100%;
  display:flex; flex-direction:column; }
__P__ .rt-thumb{ background:radial-gradient(circle at 50% 38%,#F7F1E3 0%,#EADFC8 100%); height:170px; display:flex; align-items:center; justify-content:center; }
__P__ .rt-thumb svg{ height:148px; width:auto; display:block; filter:drop-shadow(0 8px 10px rgba(70,55,30,.16)); }
__P__ .rt-thumb img{ width:100%; height:100%; object-fit:cover; }
__P__ .rt-body{ padding:14px 16px 16px; display:flex; flex-direction:column; gap:8px; flex:1; }
__P__ .rt-tags{ display:flex; justify-content:space-between; align-items:center; gap:8px; flex-wrap:wrap; }
__P__ .rt-cat{ font-size:.76rem; letter-spacing:.1em; text-transform:uppercase; color:var(--muted); font-weight:700; }
__P__ .rt-name{ font-family:var(--serif); font-size:1.15rem; line-height:1.2; font-weight:500; }
__P__ .rt-text{ color:var(--muted); font-size:.93rem; line-height:1.45; }
__P__ .rt-meta{ margin-top:auto; padding-top:8px; border-top:1px dashed var(--line); font-size:.84rem; color:var(--muted); }

/* ------------------------------------------------------------ recommendations */
__P__ .rt-reco{ margin-bottom:8px; background:var(--card); border:1px solid var(--line); border-left:5px solid var(--olive); border-radius:18px; padding:18px 20px; height:100%; }
__P__ .rt-reco.urgent{ border-left-color:var(--urgent); } __P__ .rt-reco.watch{ border-left-color:#C48A1A; } __P__ .rt-reco.good{ border-left-color:var(--good); }
__P__ .rt-reco h3{ font-size:1.12rem; margin:0 0 10px; padding:0; display:flex; justify-content:space-between; gap:10px; align-items:flex-start; }
__P__ .rt-row{ display:grid; grid-template-columns:128px 1fr; gap:10px; padding:7px 0; border-top:1px solid var(--line); font-size:.94rem; line-height:1.45; }
__P__ .rt-row:first-of-type{ border-top:none; }
__P__ .rt-row b{ font-size:.74rem; letter-spacing:.09em; text-transform:uppercase; color:var(--muted); padding-top:2px; }
__P__ .rt-row.do span{ font-weight:600; color:var(--olive-dk); }

/* ------------------------------------------------------------ trends */
__P__ .rt-trends{ display:grid; grid-template-columns:repeat(auto-fit,minmax(150px,1fr)); gap:16px; }
__P__ .rt-trend{ background:var(--card); border:1px solid var(--line); border-radius:20px; padding:18px; display:flex; flex-direction:column; gap:8px; }
__P__ .rt-trend .rt-tags{ flex-direction:column; align-items:flex-start; gap:6px; }
__P__ .rt-trend .rt-pill{ white-space:normal; }
__P__ .rt-trend h3{ font-size:1.15rem; margin:0; padding:0; }
__P__ .rt-spark{ width:100%; height:56px; display:block; }
__P__ .rt-trend .rt-text{ font-size:.9rem; }
__P__ .rt-watch{ display:grid; grid-template-columns:1fr 1fr; gap:16px; margin-top:16px; }
__P__ .rt-watchbox{ background:var(--card); border:1px solid var(--line); border-radius:18px; padding:16px 18px; }
__P__ .rt-watchbox h4{ font-size:1.02rem; margin:0 0 10px; padding:0; }
__P__ .rt-li{ display:flex; align-items:center; gap:12px; padding:6px 0; font-size:.94rem; }
__P__ .rt-li .rt-mini{ margin:0; flex:none; }
__P__ .rt-li small{ color:var(--muted); display:block; font-size:.82rem; }

/* ------------------------------------------------------------ pricing assistant */
__P__ .rt-prices{ display:grid; grid-template-columns:1fr 1fr 1.4fr; gap:16px; margin:10px 0 12px; }
__P__ .rt-pbox{ background:var(--card); border:1px solid var(--line); border-radius:20px; padding:20px 22px; }
__P__ .rt-pbox.sug{ background:var(--olive-soft); border-color:#CBD3A8; }
__P__ .rt-pbox small{ display:flex; flex-wrap:wrap; justify-content:space-between; align-items:center; gap:8px; color:var(--muted); font-size:.8rem; letter-spacing:.08em; text-transform:uppercase; font-weight:700; }
__P__ .rt-big{ font-family:var(--serif); font-size:2.1rem; line-height:1.15; margin:8px 0 2px; }
__P__ .rt-pbox p{ margin:6px 0 0; color:var(--muted); font-size:.94rem; line-height:1.5; }
__P__ .rt-note{ background:var(--sand); border-radius:14px; padding:12px 16px; font-size:.92rem; line-height:1.5; margin:8px 0; color:var(--ink); }
__P__ .rt-note.warn{ background:var(--watch-bg); color:#5E3C05; }
__P__ .rt-empty{ border:1.5px dashed #CFC4AA; border-radius:18px; padding:22px 24px; background:rgba(255,253,248,.6); color:var(--muted); }
__P__ .rt-empty b{ color:var(--ink); }

/* ------------------------------------------------------------ spotlight */
__P__ .rt-spot{ display:grid; grid-template-columns:200px 1fr; gap:22px; background:var(--card); border:1px solid var(--line); border-radius:22px; padding:20px; margin:14px 0; }
__P__ .rt-spot .rt-thumb{ border-radius:16px; height:210px; }
__P__ .rt-spot h3{ font-size:1.5rem; margin:4px 0 8px; padding:0; }
__P__ .rt-facts{ display:grid; grid-template-columns:repeat(auto-fit,minmax(150px,1fr)); gap:10px; margin-top:12px; }
__P__ .rt-fact{ background:var(--ivory); border:1px solid var(--line); border-radius:14px; padding:10px 12px; }
__P__ .rt-fact small{ display:block; color:var(--muted); font-size:.76rem; letter-spacing:.07em; text-transform:uppercase; font-weight:700; }
__P__ .rt-fact span{ font-family:var(--serif); font-size:1.15rem; }

/* ------------------------------------------------------------ Streamlit widgets inside the tab */
__P__ div[data-testid="stSlider"] [data-baseweb="slider"] div[role="slider"]{ background:var(--olive); box-shadow:none; }
__P__ div[data-testid="stSlider"] [data-testid="stThumbValue"]{ color:var(--olive-dk); font-family:inherit; font-weight:700; }
__P__ div[data-testid="stSlider"] [data-baseweb="slider"] > div > div{ background:linear-gradient(to right,var(--olive) 0%,var(--olive) 0%,var(--line) 0%); }
__P__ div[data-testid="stTickBar"] div, __P__ div[data-testid="stTickBarMin"], __P__ div[data-testid="stTickBarMax"]{ color:var(--muted); font-family:inherit; background:transparent; }
__P__ .stButton > button, __P__ .stDownloadButton > button{ border-radius:999px; border:1.5px solid var(--ink); background:var(--card); color:var(--ink); font-weight:600; padding:.35rem 1.1rem; }
__P__ .stButton > button:hover, __P__ .stDownloadButton > button:hover{ background:var(--ink); color:#fff; border-color:var(--ink); }
__P__ .stButton > button:focus:not(:active), __P__ .stDownloadButton > button:focus:not(:active){ color:var(--ink); border-color:var(--ink); }
__P__ .stButton > button:hover:focus:not(:active){ color:#fff; }
__P__ .stButton > button[kind="primary"]{ background:var(--olive); border-color:var(--olive); color:#fff; }
__P__ .stButton > button[kind="primary"]:hover{ background:var(--olive-dk); border-color:var(--olive-dk); }
__P__ .stButton > button:focus-visible{ outline:3px solid var(--olive); outline-offset:2px; }
__P__ div[data-baseweb="select"] > div, __P__ div[data-baseweb="input"] > div, __P__ div[data-baseweb="base-input"]{ border-radius:12px; background:var(--card); border-color:var(--line); }
__P__ div[data-testid="stExpander"]{ background:var(--card); border:1px solid var(--line); border-radius:18px; }
__P__ div[data-testid="stExpander"] summary p{ font-family:var(--serif); font-size:1.12rem; }
__P__ div[data-testid="stMetric"]{ background:var(--card); border:1px solid var(--line); border-radius:14px; padding:12px 16px; }
__P__ div[data-testid="stMetricLabel"] p{ color:var(--muted); }
__P__ div[data-testid="stFileUploaderDropzone"]{ background:var(--card); border:1.5px dashed #CFC4AA; border-radius:14px; }
__P__ .stCaptionContainer, __P__ [data-testid="stCaptionContainer"]{ color:var(--muted); }
__P__ div[role="radiogroup"]{ flex-direction:row; flex-wrap:wrap; gap:8px; }
__P__ div[role="radiogroup"] > label{ background:var(--card); border:1.5px solid var(--line); border-radius:999px; padding:6px 16px; margin:0; cursor:pointer; }
__P__ div[role="radiogroup"] > label > div:first-child{ display:none; }
__P__ div[role="radiogroup"] > label p{ color:var(--ink); }
__P__ div[data-baseweb="select"] div{ color:var(--ink); }
__P__ div[role="radiogroup"] > label:hover{ border-color:var(--olive); }
__P__ div[role="radiogroup"] > label:has(input:checked){ background:var(--olive); border-color:var(--olive); }
__P__ div[role="radiogroup"] > label:has(input:checked) p, __P__ div[role="radiogroup"] > label:has(input:checked) div{ color:#fff; }
__P__ div[role="radiogroup"] > label:has(input:focus-visible){ outline:3px solid var(--olive); outline-offset:2px; }

@media (prefers-reduced-motion:no-preference){
  __P__ .rt-snap-card, __P__ .rt-card, __P__ .rt-trend{ transition:transform .18s ease, box-shadow .18s ease, border-color .18s ease; }
  __P__ .rt-snap-card:hover, __P__ .rt-card:hover, __P__ .rt-trend:hover{ transform:translateY(-3px); box-shadow:0 14px 28px -18px rgba(60,50,30,.45); border-color:#D3C8AE; }
  __P__ .stButton > button{ transition:background .15s, color .15s; }
}
@media (max-width:1000px){
  __P__ .rt-snap{ grid-template-columns:1fr 1fr; }
  __P__ .rt-prices{ grid-template-columns:1fr 1fr; } __P__ .rt-prices .rt-pbox:last-child{ grid-column:1 / -1; }
}
@media (max-width:760px){
  __P__{ padding:20px 14px 30px; border-radius:20px; }
  __P__ .rt-hero{ grid-template-columns:1fr; padding:24px 20px; } __P__ .rt-hero-art{ order:-1; max-width:280px; margin:0 auto; }
  __P__ .rt-watch{ grid-template-columns:1fr; }
  __P__ .rt-spot{ grid-template-columns:1fr; } __P__ .rt-spot .rt-thumb{ height:170px; }
  __P__ .rt-row{ grid-template-columns:1fr; gap:2px; }
}
@media (max-width:560px){
  __P__ .rt-snap, __P__ .rt-prices{ grid-template-columns:1fr; }
}
</style>
""".replace("__P__", P)


def inject():
    st.markdown(CSS, unsafe_allow_html=True)
