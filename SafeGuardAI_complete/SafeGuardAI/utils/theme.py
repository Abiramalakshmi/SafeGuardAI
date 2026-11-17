"""
utils_ui/theme.py
Injects the full Material 3 Light CSS into Streamlit.
Called once from app.py before any page renders.
"""
import streamlit as st


def inject_theme():
    st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,400;0,9..40,500;0,9..40,600;1,9..40,300&family=DM+Mono:wght@400;500&family=Syne:wght@700;800&display=swap');

/* ── Design tokens (Material 3 Light) ── */
:root {
  --pri: #1a73e8;    --pri-c: #d3e3fd;
  --sec: #34a853;    --sec-c: #d5f5e3;
  --err: #ea4335;    --err-c: #fce8e6;
  --wrn: #e37400;    --wrn-c: #fef9c3;
  --pur: #7c3aed;    --pur-c: #ede9fe;
  --sur: #ffffff;    --sur-v: #f8f9fa;
  --sur-ct: #f1f3f4; --sur-cth: #e8eaed;
  --out: #dadce0;    --out-v: #e8eaed;
  --on-sur: #202124; --on-surv: #5f6368; --on-surm: #9aa0a6;
  --sh1: 0 1px 2px rgba(60,64,67,.3), 0 1px 3px 1px rgba(60,64,67,.15);
  --sh2: 0 1px 2px rgba(60,64,67,.3), 0 2px 6px 2px rgba(60,64,67,.15);
  --sh3: 0 4px 8px 3px rgba(60,64,67,.15), 0 1px 3px rgba(60,64,67,.3);
  --font:   'DM Sans', sans-serif;
  --font-d: 'Syne', sans-serif;
  --font-m: 'DM Mono', monospace;
  --r: 12px; --r-sm: 8px; --r-lg: 16px; --r-xl: 24px; --r-f: 9999px;
}

/* ── Global reset ── */
html, body, [class*="css"] {
  background: var(--sur-v) !important;
  color: var(--on-sur) !important;
  font-family: var(--font) !important;
}
.stApp { background: var(--sur-v) !important; }
.main .block-container {
  background: transparent !important;
  padding: 24px 32px 64px !important;
  max-width: 1440px !important;
}

/* ── Sidebar ── */
[data-testid="stSidebar"] {
  background: var(--sur) !important;
  border-right: 1px solid var(--out-v) !important;
}
[data-testid="stSidebar"] * { color: var(--on-surv) !important; }
[data-testid="stSidebarContent"] { padding: 0 !important; }

/* ── Buttons ── */
.stButton > button {
  background: var(--sur) !important;
  border: 1px solid var(--out) !important;
  color: var(--on-sur) !important;
  font-family: var(--font) !important;
  font-size: 14px !important;
  font-weight: 500 !important;
  border-radius: var(--r-f) !important;
  padding: 8px 20px !important;
  transition: all .2s cubic-bezier(.2,0,0,1) !important;
  letter-spacing: .01em !important;
}
.stButton > button:hover {
  background: var(--pri-c) !important;
  border-color: var(--pri) !important;
  color: var(--pri) !important;
  box-shadow: var(--sh1) !important;
}
.btn-filled > button {
  background: var(--pri) !important;
  border-color: var(--pri) !important;
  color: #fff !important;
  font-weight: 600 !important;
  box-shadow: var(--sh1) !important;
}
.btn-filled > button:hover { background: #1557b0 !important; box-shadow: var(--sh2) !important; }
.btn-tonal > button  { background: var(--pri-c) !important; border-color: transparent !important; color: var(--pri) !important; font-weight: 600 !important; }
.btn-danger > button { background: var(--err-c) !important; border-color: transparent !important; color: var(--err) !important; }
.btn-record > button { background: var(--err) !important; border-color: var(--err) !important; color: #fff !important; font-weight: 700 !important; font-size: 14px !important; }
.btn-warn > button   { background: var(--wrn-c) !important; border-color: var(--wrn) !important; color: var(--wrn) !important; font-weight: 600 !important; }

/* ── File uploader ── */
[data-testid="stFileUploader"] {
  background: var(--sur) !important;
  border: 1.5px dashed var(--out) !important;
  border-radius: var(--r-lg) !important;
  transition: border-color .2s !important;
}
[data-testid="stFileUploader"]:hover { border-color: var(--pri) !important; }

/* ── Progress bar ── */
.stProgress > div > div { background: linear-gradient(90deg, var(--pri), #4285f4) !important; border-radius: var(--r-f) !important; }
.stProgress > div       { background: var(--sur-ct) !important; border-radius: var(--r-f) !important; }

/* ── Expander ── */
[data-testid="stExpander"] {
  background: var(--sur) !important;
  border: 1px solid var(--out-v) !important;
  border-radius: var(--r-lg) !important;
}
[data-testid="stExpander"]:hover { box-shadow: var(--sh1) !important; }
[data-testid="stExpander"] summary { font-size: 14px !important; font-weight: 500 !important; }

/* ── Form inputs ── */
.stTextInput input,
.stDateInput > div > div > input {
  background: var(--sur) !important;
  border: 1.5px solid var(--out) !important;
  color: var(--on-sur) !important;
  border-radius: var(--r-sm) !important;
  font-family: var(--font) !important;
  font-size: 14px !important;
  transition: border-color .2s !important;
}
.stTextInput input:focus { border-color: var(--pri) !important; box-shadow: 0 0 0 3px rgba(26,115,232,.12) !important; }
.stSelectbox > div > div {
  background: var(--sur) !important;
  border: 1.5px solid var(--out) !important;
  border-radius: var(--r-sm) !important;
  color: var(--on-sur) !important;
}

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] {
  background: var(--sur-ct) !important;
  border-radius: var(--r-f) !important;
  padding: 4px !important;
  gap: 2px !important;
  border: none !important;
}
.stTabs [data-baseweb="tab"] {
  background: transparent !important;
  border-radius: var(--r-f) !important;
  color: var(--on-surv) !important;
  font-weight: 500 !important;
  font-size: 14px !important;
  padding: 8px 24px !important;
  font-family: var(--font) !important;
}
.stTabs [aria-selected="true"] {
  background: var(--sur) !important;
  color: var(--pri) !important;
  box-shadow: var(--sh1) !important;
}

/* ── DataFrames / Tables — FIX: force dark text ── */
[data-testid="stDataFrame"],
[data-testid="stDataFrame"] *,
[data-testid="stDataFrame"] td,
[data-testid="stDataFrame"] th,
[data-testid="stDataFrame"] div,
[data-testid="stDataFrame"] span,
.stDataFrame * {
  color: var(--on-sur) !important;
}
[data-testid="stDataFrame"] {
  background: var(--sur) !important;
  border-radius: var(--r-lg) !important;
  border: 1px solid var(--out-v) !important;
  overflow: hidden !important;
}
[data-testid="stDataFrame"] th {
  background: var(--sur-ct) !important;
  color: var(--on-surv) !important;
  font-weight: 600 !important;
  font-size: 11px !important;
  letter-spacing: .06em !important;
  text-transform: uppercase !important;
}
table { border-collapse: collapse !important; width: 100% !important; }
thead th {
  background: var(--sur-ct) !important;
  color: var(--on-surv) !important;
  font-weight: 600 !important;
  font-size: 11px !important;
  letter-spacing: .06em !important;
  text-transform: uppercase !important;
  padding: 10px 14px !important;
}
tbody td {
  color: var(--on-sur) !important;
  padding: 9px 14px !important;
  border-bottom: 1px solid var(--out-v) !important;
  font-size: 13px !important;
}
tbody tr:hover td { background: var(--sur-v) !important; }

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-thumb { background: var(--out); border-radius: var(--r-f); }
::-webkit-scrollbar-track { background: var(--sur-v); }

/* ── Typography ── */
hr { border-color: var(--out-v) !important; margin: 20px 0 !important; }
h1 { font-family: var(--font-d) !important; font-size: 26px !important; font-weight: 800 !important; color: var(--on-sur) !important; letter-spacing: -.3px; }
h2, h3 { font-family: var(--font) !important; font-weight: 600 !important; color: var(--on-sur) !important; }

/* ══════════════════════════════════════════════════════════
   CUSTOM COMPONENT CLASSES
   ══════════════════════════════════════════════════════════ */

/* Card */
.sg-card {
  background: var(--sur);
  border: 1px solid var(--out-v);
  border-radius: var(--r-lg);
  padding: 20px 24px;
  transition: box-shadow .2s;
}
.sg-card:hover { box-shadow: var(--sh1); }
.sg-card-el    { box-shadow: var(--sh1) !important; border: none !important; }

/* Stat chip */
.sg-chip {
  background: var(--sur);
  border: 1px solid var(--out-v);
  border-radius: var(--r-lg);
  padding: 16px 20px;
  position: relative;
  overflow: hidden;
  transition: box-shadow .2s;
}
.sg-chip:hover { box-shadow: var(--sh2); }
.sg-chip::after {
  content: '';
  position: absolute;
  bottom: 0; left: 0; right: 0;
  height: 3px;
  border-radius: 0 0 var(--r-lg) var(--r-lg);
}
.chip-blue::after   { background: var(--pri); }
.chip-green::after  { background: var(--sec); }
.chip-red::after    { background: var(--err); }
.chip-amber::after  { background: var(--wrn); }
.chip-purple::after { background: var(--pur); }
.sg-chip-label { font-size: 11px; font-weight: 600; color: var(--on-surm); letter-spacing: .8px; text-transform: uppercase; margin-bottom: 8px; }
.sg-chip-value { font-family: var(--font-d); font-size: 2rem; font-weight: 800; line-height: 1; color: var(--on-sur); }
.sg-chip-sub   { font-size: 12px; color: var(--on-surm); margin-top: 4px; }

/* Section header */
.sg-sec {
  font-size: 11px; font-weight: 600; color: var(--on-surm);
  letter-spacing: 1px; text-transform: uppercase;
  margin-bottom: 12px;
  display: flex; align-items: center; gap: 8px;
}
.sg-sec-line { flex: 1; height: 1px; background: var(--out-v); }

/* Badges */
.sg-badge {
  display: inline-flex; align-items: center; gap: 5px;
  padding: 4px 12px; border-radius: var(--r-f);
  font-size: 12px; font-weight: 600;
  font-family: var(--font); letter-spacing: .02em;
}
.sg-badge-red    { background: var(--err-c); color: var(--err); }
.sg-badge-amber  { background: var(--wrn-c); color: #92400e; }
.sg-badge-green  { background: var(--sec-c); color: #14532d; }
.sg-badge-blue   { background: var(--pri-c); color: var(--pri); }
.sg-badge-purple { background: var(--pur-c); color: var(--pur); }

/* Linear progress */
.sg-prog-wrap  { margin: 4px 0 12px; }
.sg-prog-track { background: var(--sur-cth); border-radius: var(--r-f); height: 6px; overflow: hidden; }
.sg-prog-fill  { height: 100%; border-radius: var(--r-f); transition: width .5s cubic-bezier(.4,0,.2,1); }

/* Score row */
.sg-score-row { display: flex; justify-content: space-between; align-items: center; padding: 10px 0; border-bottom: 1px solid var(--out-v); }
.sg-score-row:last-child { border-bottom: none; }
.sg-score-label { font-size: 13px; color: var(--on-surv); font-weight: 400; }
.sg-score-value { font-family: var(--font-m); font-size: 13px; font-weight: 600; }

/* Transcript box */
.sg-transcript {
  background: var(--sur-v);
  border: 1px solid var(--out-v);
  border-radius: var(--r);
  padding: 14px 16px;
  font-family: var(--font);
  font-size: 13px;
  color: var(--on-surv);
  line-height: 1.7;
  min-height: 56px;
  white-space: pre-wrap;
}

/* Phrase tag */
.sg-phrase-tag {
  display: inline-block;
  background: var(--err-c); color: var(--err);
  border-radius: var(--r-f);
  padding: 3px 10px; font-size: 12px; font-weight: 500;
  margin: 3px 3px 3px 0;
}

/* Video container */
.sg-video-wrap {
  background: #000; border-radius: var(--r-lg);
  overflow: hidden; margin: 8px 0 12px;
  box-shadow: var(--sh1);
}
.sg-video-wrap video { width: 100%; max-height: 360px; display: block; }

/* Empty state */
.sg-await {
  background: var(--sur);
  border: 1.5px dashed var(--out);
  border-radius: var(--r-lg);
  padding: 48px 24px;
  text-align: center;
  transition: border-color .2s;
}
.sg-await:hover { border-color: var(--pri); }

/* Incident row */
.sg-incident {
  background: var(--sur);
  border: 1px solid var(--out-v);
  border-radius: var(--r-lg);
  padding: 14px 20px; margin-bottom: 8px;
  transition: box-shadow .2s, border-color .2s;
}
.sg-incident:hover { box-shadow: var(--sh1); border-color: var(--pri); }

/* Status dots */
.sg-dot-g { display: inline-block; width: 8px; height: 8px; border-radius: 50%; background: #34a853; box-shadow: 0 0 5px #34a85388; margin-right: 6px; }
.sg-dot-r { display: inline-block; width: 8px; height: 8px; border-radius: 50%; background: #ea4335; box-shadow: 0 0 5px #ea433588; margin-right: 6px; }
.sg-dot-a { display: inline-block; width: 8px; height: 8px; border-radius: 50%; background: #fbbc04; box-shadow: 0 0 5px #fbbc0488; margin-right: 6px; }

/* Record pulse animation */
.rec-pulse {
  display: inline-block; width: 9px; height: 9px;
  border-radius: 50%; background: var(--err);
  animation: rp 1.2s ease-in-out infinite; margin-right: 7px;
}
@keyframes rp { 0%,100%{opacity:1;transform:scale(1)} 50%{opacity:.3;transform:scale(.7)} }

/* Sidebar nav buttons */
.sg-nav > button {
  text-align: left !important;
  justify-content: flex-start !important;
  border-radius: var(--r-f) !important;
  font-size: 14px !important;
}

/* Login card */
.sg-login-card {
  max-width: 420px;
  margin: 80px auto 0;
  background: var(--sur);
  border: 1px solid var(--out-v);
  border-radius: var(--r-xl);
  padding: 40px 36px;
  box-shadow: var(--sh3);
}

/* Result banner */
.sg-banner {
  border-radius: var(--r-lg);
  padding: 16px 24px; margin-bottom: 20px;
  display: flex; align-items: center; gap: 12px;
  font-family: var(--font-d); font-size: 16px; font-weight: 800;
}
.sg-banner-unsafe { background: var(--err-c); color: var(--err); border: 1px solid #f5c6c2; border-left: 4px solid var(--err); }
.sg-banner-review { background: var(--wrn-c); color: #92400e;   border: 1px solid #fde68a; border-left: 4px solid var(--wrn); }
.sg-banner-safe   { background: var(--sec-c); color: #14532d;   border: 1px solid #a7f3d0; border-left: 4px solid var(--sec); }
</style>
""", unsafe_allow_html=True)
