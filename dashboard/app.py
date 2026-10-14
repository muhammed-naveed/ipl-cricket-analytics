# ============================================================
# IPL BATTER INTELLIGENCE  ·  dashboard/app.py
# ============================================================

# ============================================================
# 1. IMPORTS
# ============================================================
import base64
import html as htmllib
import math
import re
import sqlite3
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components
from plotly.subplots import make_subplots

try:
    from scipy.stats import ttest_ind
    SCIPY_OK = True
except Exception:
    SCIPY_OK = False


# ============================================================
# 2. PAGE CONFIGURATION
# ============================================================
st.set_page_config(
    page_title="IPL Batter Intelligence",
    page_icon="🏏",
    layout="wide",
    initial_sidebar_state="expanded",
)

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "data" / "raw" / "ipl.db"

PHASES = ["Powerplay", "Middle", "Death"]
HANDS = ["Left hand Bat", "Right hand Bat"]
ENTRY_ORDER = ["1", "2", "3", "4", "5+"]
PHASE_METRICS = ["Strike rate", "Run share", "Dot-ball %"]

CYAN = "#22D3EE"
VIOLET = "#8B5CF6"
PINK = "#F0ABFC"
AMBER = "#FBBF24"
MUTED = "#7F97B0"
GRID = "rgba(148,163,184,.10)"
HAND_COLORS = {"Left hand Bat": "#A78BFA", "Right hand Bat": "#22D3EE", "Unknown": "#64748B"}
PALETTE = ["#22D3EE", "#8B5CF6", "#F0ABFC", "#34D399", "#FBBF24", "#60A5FA",
           "#FB7185", "#A3E635", "#F97316", "#2DD4BF", "#C084FC", "#38BDF8"]
NEON_SCALE = [[0, "#0B1B31"], [0.35, "#3B1E8A"], [0.7, "#8B5CF6"], [1, "#22D3EE"]]


# ============================================================
# 3. CSS
# ============================================================
CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

:root { --cyan:#22D3EE; --violet:#8B5CF6; --navy:#061225; --ink:#E5EEF8; --muted:#7F97B0; }

html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

#MainMenu, footer, [data-testid="stToolbar"], [data-testid="stDecoration"],
[data-testid="stStatusWidget"] { display: none !important; visibility: hidden; }
/* ==========================================================
   BACKGROUND  (safest possible method)

   The whole scene (stadium photo, dark navy overlay, light sweep, particles)
   is painted as the BACKGROUND of .stApp itself. There are no extra
   full-screen elements and no pseudo-element layers, so nothing can ever sit
   on top of the dashboard or intercept a click. Streamlit's own wrappers are
   transparent so the scene shows through, and no z-index is set on any
   Streamlit content.
   ========================================================== */
.stApp {
    color: var(--ink);
    overflow-x: hidden;
    background-color: #020817;
    background-image:
        radial-gradient(circle at 20% 30%, rgba(34,211,238,.70) 0 1.5px, transparent 3px),
        radial-gradient(circle at 70% 60%, rgba(139,92,246,.65) 0 1.5px, transparent 3px),
        linear-gradient(105deg, transparent 42%, rgba(34,211,238,.09) 50%, transparent 58%),
        linear-gradient(105deg, transparent 44%, rgba(139,92,246,.08) 50%, transparent 56%),
        radial-gradient(ellipse at 50% 45%, rgba(2,8,23,0) 10%, rgba(2,8,23,.30) 60%, rgba(2,8,23,.70) 100%),
        linear-gradient(180deg, rgba(2,8,23,.93) 0%, rgba(5,14,30,.66) 30%, rgba(5,14,30,.58) 58%, rgba(2,8,23,.95) 100%),
        url("__BG_URL__"),
        radial-gradient(ellipse at 50% 5%, rgba(255,255,255,.28) 0, transparent 22%),
        linear-gradient(180deg, #071426 0%, #0B2236 60%, #020817 100%);
    background-repeat: repeat, repeat, no-repeat, no-repeat, no-repeat, no-repeat, no-repeat, no-repeat, no-repeat;
    background-attachment: fixed;
    background-size: 460px 520px, 610px 570px, 250% 100%, 320% 100%, 100% 100%, 100% 100%, 112% auto, 100% 100%, 100% 100%;
    background-position: 0 0, 0 0, 150% 0, 150% 0, 0 0, 0 0, 50% 40%, 0 0, 0 0;
    animation: sceneDrift 40s ease-in-out infinite alternate;
}

/* slow cinematic zoom + horizontal camera drift, light sweep and particles in one cheap animation */
@keyframes sceneDrift {
    0% {
        background-size: 460px 520px, 610px 570px, 250% 100%, 320% 100%, 100% 100%, 100% 100%, 108% auto, 100% 100%, 100% 100%;
        background-position: 0 0, 0 0, 150% 0, 150% 0, 0 0, 0 0, 40% 40%, 0 0, 0 0;
    }
    100% {
        background-size: 460px 520px, 610px 570px, 250% 100%, 320% 100%, 100% 100%, 100% 100%, 122% auto, 100% 100%, 100% 100%;
        background-position: 0 -520px, 0 -570px, -50% 0, -50% 0, 0 0, 0 0, 60% 40%, 0 0, 0 0;
    }
}

[data-testid="stAppViewContainer"],
[data-testid="stMain"],
[data-testid="stMainBlockContainer"],
[data-testid="stBottom"],
[data-testid="stBottom"] > div,
.main {
    background: transparent !important;
}
header[data-testid="stHeader"] { background: transparent !important; }

.block-container { max-width: 1520px; padding-top: 1.4rem; padding-bottom: 3rem; }

@media (prefers-reduced-motion: reduce) {
    .stApp, .hero-banner::after { animation: none !important; }
    [class*="st-key-mod_"], .kpi { transition: none !important; }
    [class*="st-key-mod_"]:hover, .kpi:hover { transform: none !important; }
}

/* ---------- sidebar ---------- */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, rgba(7,20,38,.94) 0%, rgba(10,24,48,.92) 60%, rgba(11,27,56,.92) 100%) !important;
    border-right: 1px solid rgba(34,211,238,.18);
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
}
[data-testid="stSidebar"] * { color: #DDE8F5; }
.brand { display:flex; align-items:center; gap:11px; margin: 4px 0 18px; }
.brand-mark {
    width: 38px; height: 38px; border-radius: 11px; display:flex; align-items:center; justify-content:center;
    background: linear-gradient(135deg, #22D3EE, #8B5CF6); box-shadow: 0 0 22px rgba(34,211,238,.35); font-size: 20px;
}
.brand-name { font-weight: 800; font-size: 15px; letter-spacing: .4px; color:#F8FAFC; line-height: 1.1; }
.brand-sub { font-size: 10px; letter-spacing: 1.6px; color: var(--cyan); font-weight: 700; text-transform: uppercase; }
.live-badge {
    border: 1px solid rgba(52,211,153,.30); background: rgba(52,211,153,.07); border-radius: 12px;
    padding: 11px 13px; margin-bottom: 14px;
}
.live-badge.bad { border-color: rgba(251,113,133,.35); background: rgba(251,113,133,.08); }
.live-top { font-size: 11px; font-weight: 800; letter-spacing: 1.4px; color: #6EE7B7; display:flex; align-items:center; gap:8px; }
.live-badge.bad .live-top { color: #FDA4AF; }
.live-dot { width:8px; height:8px; border-radius:50%; background:#34D399; box-shadow:0 0 0 0 rgba(52,211,153,.7); animation: pulse 2s infinite; display:inline-block; }
.live-badge.bad .live-dot { background:#FB7185; animation: none; }
.live-sub { font-size: 12px; color:#A7F3D0; margin-top: 4px; }
@keyframes pulse { 0% { box-shadow: 0 0 0 0 rgba(52,211,153,.55);} 70% { box-shadow: 0 0 0 8px rgba(52,211,153,0);} 100% { box-shadow: 0 0 0 0 rgba(52,211,153,0);} }
.side-label { font-size: 10px; font-weight: 800; letter-spacing: 1.6px; color: var(--muted); text-transform: uppercase; margin: 16px 0 8px; }
.side-row { display:flex; justify-content:space-between; font-size: 12px; padding: 5px 0; border-bottom: 1px solid rgba(148,163,184,.08); color:#AFC1D4; }
.side-row b { color:#F1F5F9; font-weight: 700; }
.side-note { font-size: 11px; line-height: 1.5; color: var(--muted); }

/* ---------- hero banner ---------- */
.hero-banner {
    position: relative; overflow: hidden; border-radius: 22px; padding: 28px 32px; margin-bottom: 18px;
    border: 1px solid rgba(34,211,238,.20);
    background: linear-gradient(135deg, rgba(14,116,144,.20), rgba(79,70,229,.15)), rgba(7,20,38,.80);
    box-shadow: 0 20px 60px rgba(0,0,0,.28), inset 0 1px 0 rgba(255,255,255,.04);
    backdrop-filter: blur(14px);
}
.hero-banner::after {
    content:""; position:absolute; top:0; left:-40%; width:40%; height:2px;
    background: linear-gradient(90deg, transparent, #22D3EE, #8B5CF6, transparent);
    animation: sweep 6s linear infinite;
}
@keyframes sweep { from { left:-40%; } to { left:100%; } }
.eyebrow { color: var(--cyan); font-size: 11px; font-weight: 800; letter-spacing: 2.4px; text-transform: uppercase; }
.hero-banner h1 { margin: 6px 0 8px; font-size: 38px; line-height: 1.05; color:#F8FAFC; font-weight: 800; letter-spacing: .5px; padding: 0; }
.hero-sub { color:#A9BBCF; font-size: 15px; max-width: 760px; margin: 0; }
.reader {
    display: inline-block; margin-top: 16px; border-left: 3px solid var(--cyan); padding: 10px 16px;
    background: rgba(34,211,238,.07); border-radius: 0 12px 12px 0; color:#E2EEF9; font-size: 14px;
}
.reader b { color: var(--cyan); letter-spacing: 1px; font-size: 11px; text-transform: uppercase; margin-right: 6px; }
.scale-strip { display:grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-top: 20px; }
.scale-item { border:1px solid rgba(148,163,184,.16); border-radius: 14px; padding: 12px 16px; background: rgba(6,18,37,.55); }
.scale-k { font-size: 10px; font-weight: 800; letter-spacing: 1.5px; text-transform: uppercase; color: var(--muted); }
.scale-v { font-size: 24px; font-weight: 800; color:#F8FAFC; margin-top: 3px; }
.scale-tag { font-size: 10px; letter-spacing: 1.6px; color: var(--violet); font-weight: 800; text-transform: uppercase; margin-top: 18px; }

/* ---------- glass modules ---------- */
[class*="st-key-mod_"], [class*="st-key-bar_"] {
    border: 1px solid rgba(34,211,238,.16); border-radius: 20px; padding: 18px 20px 14px;
    background: linear-gradient(160deg, rgba(15,32,56,.78), rgba(8,22,42,.78));
    box-shadow: 0 14px 40px rgba(0,0,0,.20), inset 0 1px 0 rgba(255,255,255,.035);
    backdrop-filter: blur(12px); transition: border-color .25s ease, box-shadow .25s ease, transform .25s ease;
}
[class*="st-key-mod_"]:hover { border-color: rgba(34,211,238,.42); box-shadow: 0 18px 46px rgba(0,0,0,.28), 0 0 26px rgba(34,211,238,.08); transform: translateY(-1px); }
[class*="st-key-bar_"] { border-color: rgba(139,92,246,.28); padding-bottom: 8px; }

.mod-kicker { display:flex; align-items:center; gap: 8px; font-size: 10.5px; font-weight: 800; letter-spacing: 1.8px; text-transform: uppercase; color: var(--cyan); }
.mod-kicker svg { width: 14px; height: 14px; }
.mod-title { font-size: 19px; font-weight: 800; color:#F8FAFC; line-height: 1.25; margin: 5px 0 3px; }
.mod-sub { font-size: 12px; color: var(--muted); margin-bottom: 8px; line-height: 1.45; }
.bar-title { font-size: 10.5px; font-weight: 800; letter-spacing: 1.8px; text-transform: uppercase; color: #C4B5FD; margin-bottom: 4px; }

/* ---------- KPI ---------- */
.kpi {
    position: relative; overflow: hidden; border-radius: 18px; padding: 18px 20px; min-height: 136px; margin: 4px 0 10px;
    border: 1px solid rgba(100,116,139,.25);
    background: linear-gradient(150deg, rgba(17,36,62,.92), rgba(8,22,42,.92));
    box-shadow: 0 14px 34px rgba(0,0,0,.18); transition: transform .25s ease, border-color .25s ease;
}
.kpi::before { content:""; position:absolute; left:0; right:0; top:0; height:2px; background: linear-gradient(90deg, transparent, var(--accent), transparent); }
.kpi::after { content:""; position:absolute; right:-40px; top:-40px; width:130px; height:130px; border-radius:50%; background: radial-gradient(circle, var(--accent), transparent 70%); opacity:.13; }
.kpi:hover { transform: translateY(-2px); border-color: var(--accent); }
.kpi-top { display:flex; align-items:center; gap:9px; }
.kpi-icon { color: var(--accent); display:flex; }
.kpi-icon svg { width: 18px; height: 18px; }
.kpi-label { font-size: 11px; font-weight: 800; letter-spacing: 1.5px; text-transform: uppercase; color: #8EA5BD; }
.kpi-value { font-size: 31px; font-weight: 800; color:#F8FAFC; margin-top: 10px; line-height: 1.1; }
.kpi-note { font-size: 12px; color: #7F97B0; margin-top: 6px; line-height: 1.4; }

/* ---------- insight / chips ---------- */
.insight {
    border: 1px solid rgba(139,92,246,.30); border-radius: 14px; padding: 13px 16px; margin: 6px 0 4px;
    background: linear-gradient(135deg, rgba(139,92,246,.10), rgba(34,211,238,.05));
}
.insight-title { color: #C4B5FD; font-weight: 800; font-size: 10.5px; text-transform: uppercase; letter-spacing: 1.6px; }
.insight-text { color: #E5EEF8; font-size: 13px; line-height: 1.55; margin-top: 5px; }
.chip { display:inline-block; margin: 8px 8px 0 0; padding: 4px 11px; border-radius: 999px; font-size: 11px; color:#BFD0E3;
        border: 1px solid rgba(34,211,238,.28); background: rgba(34,211,238,.07); }
.chip b { color:#F8FAFC; margin-left: 4px; }
.empty {
    border: 1px dashed rgba(148,163,184,.30); border-radius: 14px; padding: 26px; text-align:center;
    color:#9FB2C8; font-size: 14px; background: rgba(15,32,56,.45); margin: 8px 0;
}
.footer-strip {
    margin-top: 26px; padding: 14px 20px; border-radius: 16px; border: 1px solid rgba(148,163,184,.15);
    background: rgba(7,20,38,.70); color:#8EA5BD; font-size: 12px; display:flex; flex-wrap:wrap; gap: 8px 26px; align-items:center;
}
.footer-strip b { color:#E2E8F0; }
.footer-tag { color: var(--cyan); font-weight: 800; letter-spacing: 1.6px; font-size: 10.5px; text-transform: uppercase; }

/* ---------- widgets ---------- */
[data-testid="stWidgetLabel"] p {
    font-size: 10px !important; font-weight: 800 !important; letter-spacing: 1.2px; text-transform: uppercase; color: var(--muted) !important;
}
div[data-baseweb="select"] > div, div[data-baseweb="input"] > div, [data-testid="stNumberInput"] div[data-baseweb="input"] {
    background: rgba(8,22,42,.75) !important; border-color: rgba(100,116,139,.32) !important; border-radius: 10px !important; min-height: 38px;
}
div[data-baseweb="select"] > div:hover, div[data-baseweb="input"] > div:hover { border-color: rgba(34,211,238,.55) !important; }
div[data-baseweb="tag"] { background: rgba(139,92,246,.30) !important; border-radius: 8px; }
[data-testid="stSlider"] [role="slider"] { background: var(--cyan) !important; box-shadow: 0 0 10px rgba(34,211,238,.7); }
.stButton > button { border-radius: 10px; font-weight: 700; border: 1px solid rgba(34,211,238,.35); background: rgba(34,211,238,.08); color:#E2F7FC; }
.stButton > button:hover { border-color: var(--cyan); box-shadow: 0 0 14px rgba(34,211,238,.3); }

/* ---------- tabs ---------- */
div[data-baseweb="tab-list"] {
    gap: 8px; padding: 6px; border-radius: 16px; background: rgba(7,20,38,.80); border: 1px solid rgba(148,163,184,.14); margin-bottom: 14px;
}
button[data-baseweb="tab"] { border-radius: 11px; padding: 10px 22px; height: auto; }
button[data-baseweb="tab"] p { font-weight: 800; letter-spacing: 1.6px; font-size: 12.5px; color:#8EA5BD; }
button[data-baseweb="tab"][aria-selected="true"] { background: linear-gradient(135deg, rgba(34,211,238,.18), rgba(139,92,246,.22)); box-shadow: 0 0 22px rgba(34,211,238,.28); }
button[data-baseweb="tab"][aria-selected="true"] p { color:#F8FAFC; }
div[data-baseweb="tab-highlight"] { background: var(--cyan) !important; height: 3px; box-shadow: 0 0 14px var(--cyan); border-radius: 3px; }
div[data-baseweb="tab-border"] { background: transparent !important; }

@media (max-width: 1000px) {
    .hero-banner h1 { font-size: 27px; }
    .scale-strip { grid-template-columns: 1fr; }
    .hero-banner { padding: 20px; }
}

/* ==========================================================
   MISSION-CONTROL LAYER  (ticker, HUD, per-chart themes, cursor)
   ========================================================== */
/* --- live ticker --- */
.ticker { position:relative; overflow:hidden; border-radius:14px; margin: 0 0 16px; padding: 9px 0;
    border:1px solid rgba(34,211,238,.22); background: linear-gradient(90deg, rgba(34,211,238,.10), rgba(139,92,246,.10)), rgba(5,14,30,.82); }
.ticker-tag { position:absolute; left:0; top:0; bottom:0; z-index:2; display:flex; align-items:center; padding:0 16px;
    font-size:10.5px; font-weight:800; letter-spacing:2px; color:#061225; background: linear-gradient(135deg,#22D3EE,#8B5CF6);
    clip-path: polygon(0 0, 100% 0, calc(100% - 14px) 100%, 0 100%); }
.ticker-track { display:inline-flex; gap:38px; padding-left:170px; white-space:nowrap; animation: tick 46s linear infinite; }
.ticker:hover .ticker-track { animation-play-state: paused; }
.tk { font-size:12.5px; color:#BFD0E3; } .tk b { color:#F8FAFC; } .tk i { color:#22D3EE; font-style:normal; font-weight:800; margin-right:6px; }
@keyframes tick { from { transform: translateX(0); } to { transform: translateX(-50%); } }

/* --- hero HUD scoreboard --- */
.hud { display:grid; grid-template-columns: 1fr 190px 1fr; gap:14px; margin: 6px 0 12px; align-items:stretch; }
.hud-side { position:relative; border-radius:16px; padding:14px 18px; border:1px solid var(--c); background: linear-gradient(160deg, rgba(8,22,42,.85), rgba(8,22,42,.55));
    box-shadow: 0 0 28px color-mix(in srgb, var(--c) 18%, transparent), inset 0 0 30px color-mix(in srgb, var(--c) 8%, transparent); overflow:hidden; }
.hud-side::before { content:""; position:absolute; inset:0; background: repeating-linear-gradient(0deg, transparent 0 3px, rgba(255,255,255,.025) 3px 4px); pointer-events:none; }
.hud-name { font-size:10.5px; font-weight:800; letter-spacing:2px; text-transform:uppercase; color:var(--c); }
.hud-big { font-size:34px; font-weight:800; color:#F8FAFC; line-height:1.1; margin-top:4px; text-shadow: 0 0 18px var(--c); }
.hud-big small { font-size:12px; color:#7F97B0; font-weight:700; letter-spacing:1px; margin-left:6px; }
.hud-row { display:flex; gap:16px; margin-top:8px; font-size:12px; color:#9FB2C8; } .hud-row b { color:#F1F5F9; }
.hud-core { display:flex; flex-direction:column; align-items:center; justify-content:center; text-align:center; border-radius:16px;
    border:1px dashed rgba(148,163,184,.30); background: radial-gradient(circle at 50% 50%, rgba(34,211,238,.10), transparent 70%); padding:10px; }
.hud-core .k { font-size:9.5px; letter-spacing:1.8px; font-weight:800; color:#7F97B0; text-transform:uppercase; }
.hud-core .v { font-size:28px; font-weight:800; color:#FBBF24; text-shadow:0 0 16px rgba(251,191,36,.55); }
.hud-core .m { font-size:11px; color:#BFD0E3; }
@media (max-width:1000px){ .hud { grid-template-columns:1fr; } }

/* --- shared module furniture --- */
[class*="st-key-mod_"] { position:relative; --mx:50%; --my:50%; }
[class*="st-key-mod_"]::after { content:""; position:absolute; inset:0; border-radius:inherit; pointer-events:none;
    background: radial-gradient(420px circle at var(--mx) var(--my), rgba(34,211,238,.10), transparent 60%); opacity:0; transition: opacity .3s; }
[class*="st-key-mod_"]:hover::after { opacity:1; }
[class*="st-key-mod_"]::before { content:""; position:absolute; pointer-events:none; }

/* HERO : HUD corner brackets + scanning beam */
.st-key-mod_hero { border-color: rgba(34,211,238,.45) !important; box-shadow: 0 0 50px rgba(34,211,238,.12), inset 0 0 60px rgba(139,92,246,.07) !important; }
.st-key-mod_hero::before { inset:8px; border-radius:14px; border:1px solid transparent;
    background:
      linear-gradient(#22D3EE,#22D3EE) top left / 26px 2px no-repeat, linear-gradient(#22D3EE,#22D3EE) top left / 2px 26px no-repeat,
      linear-gradient(#8B5CF6,#8B5CF6) top right / 26px 2px no-repeat, linear-gradient(#8B5CF6,#8B5CF6) top right / 2px 26px no-repeat,
      linear-gradient(#8B5CF6,#8B5CF6) bottom left / 26px 2px no-repeat, linear-gradient(#8B5CF6,#8B5CF6) bottom left / 2px 26px no-repeat,
      linear-gradient(#22D3EE,#22D3EE) bottom right / 26px 2px no-repeat, linear-gradient(#22D3EE,#22D3EE) bottom right / 2px 26px no-repeat; }
/* hero chart-type selector rendered as neon pills */
.st-key-mod_hero [data-testid="stRadio"] > div[role="radiogroup"] { gap:8px; flex-wrap:wrap; }
.st-key-mod_hero [data-testid="stRadio"] label { border:1px solid rgba(34,211,238,.30); border-radius:999px; padding:5px 14px; background:rgba(8,22,42,.7);
    transition: all .2s ease; cursor:pointer; }
.st-key-mod_hero [data-testid="stRadio"] label:hover { border-color:#22D3EE; box-shadow:0 0 14px rgba(34,211,238,.35); }
.st-key-mod_hero [data-testid="stRadio"] label:has(input:checked) { background: linear-gradient(135deg, rgba(34,211,238,.28), rgba(139,92,246,.32)); border-color:#22D3EE; box-shadow:0 0 18px rgba(34,211,238,.45); }
.st-key-mod_hero [data-testid="stRadio"] label > div:first-child { display:none; }
.st-key-mod_hero [data-testid="stRadio"] label p { font-size:12px; font-weight:700; letter-spacing:.6px; color:#E2EEF9; }

/* HEATMAP : amber thermal grid */
.st-key-mod_heat { border-color: rgba(251,191,36,.30) !important; background-image: linear-gradient(160deg, rgba(40,24,40,.70), rgba(8,22,42,.80)), repeating-linear-gradient(0deg, transparent 0 22px, rgba(251,191,36,.05) 22px 23px), repeating-linear-gradient(90deg, transparent 0 22px, rgba(251,191,36,.05) 22px 23px) !important; }
.st-key-mod_heat .mod-kicker { color:#FBBF24; }
.st-key-mod_heat::before { top:0; left:0; right:0; height:3px; background: linear-gradient(90deg,#8B5CF6,#F0ABFC,#FBBF24,#F97316); border-radius:20px 20px 0 0; }

/* LOLLIPOP : vertical launch rail */
.st-key-mod_lolli { border-left: 4px solid #F0ABFC !important; }
.st-key-mod_lolli .mod-kicker { color:#F0ABFC; }
.st-key-mod_lolli::before { left:-4px; top:18px; width:4px; height:46px; background:#fff; box-shadow:0 0 16px #F0ABFC; animation: rail 3.2s ease-in-out infinite alternate; }
@keyframes rail { from { top:18px; } to { top: calc(100% - 64px); } }

/* SCATTER : radar-lock crosshair dots */
.st-key-mod_scatter { border-color: rgba(52,211,153,.32) !important; background-image: linear-gradient(160deg, rgba(8,34,38,.75), rgba(8,22,42,.80)), radial-gradient(rgba(52,211,153,.14) 1px, transparent 1.6px) !important; background-size: auto, 22px 22px !important; }
.st-key-mod_scatter .mod-kicker { color:#34D399; }
.st-key-mod_scatter::before { right:16px; top:16px; width:34px; height:34px; border:1.5px solid #34D399; border-radius:50%; box-shadow:0 0 14px rgba(52,211,153,.5), inset 0 0 8px rgba(52,211,153,.4);
    background: linear-gradient(#34D399,#34D399) center/1.5px 100% no-repeat, linear-gradient(#34D399,#34D399) center/100% 1.5px no-repeat; animation: lock 4s linear infinite; }
@keyframes lock { to { transform: rotate(360deg); } }

/* TREEMAP : diagonal armour plating */
.st-key-mod_tree { border-color: rgba(96,165,250,.34) !important; background-image: linear-gradient(160deg, rgba(10,24,56,.78), rgba(8,22,42,.80)), repeating-linear-gradient(45deg, transparent 0 14px, rgba(96,165,250,.05) 14px 16px) !important; clip-path: polygon(0 0, calc(100% - 26px) 0, 100% 26px, 100% 100%, 26px 100%, 0 calc(100% - 26px)); }
.st-key-mod_tree .mod-kicker { color:#60A5FA; }

/* TIMELINE : heartbeat baseline */
.st-key-mod_timeline { border-color: rgba(34,211,238,.34) !important; }
.st-key-mod_timeline::before { left:0; right:0; bottom:0; height:3px; background: linear-gradient(90deg, transparent, #22D3EE, #8B5CF6, transparent); background-size:200% 100%; animation: flow 3.5s linear infinite; border-radius:0 0 20px 20px; }
@keyframes flow { from { background-position:200% 0; } to { background-position:-200% 0; } }

/* RADAR : concentric sonar rings */
.st-key-mod_radar { border-color: rgba(167,139,250,.38) !important; background-image: linear-gradient(160deg, rgba(24,18,56,.78), rgba(8,22,42,.80)), repeating-radial-gradient(circle at 50% 62%, transparent 0 34px, rgba(167,139,250,.07) 34px 35px) !important; }
.st-key-mod_radar .mod-kicker { color:#C4B5FD; }

/* OPPONENTS : chevron stripe header */
.st-key-mod_opp { border-color: rgba(251,113,133,.34) !important; }
.st-key-mod_opp .mod-kicker { color:#FB7185; }
.st-key-mod_opp::before { top:0; left:0; right:0; height:6px; border-radius:20px 20px 0 0; background: repeating-linear-gradient(115deg, #FB7185 0 10px, transparent 10px 20px); opacity:.65; }

/* VENUES : stadium-light glow top-right */
.st-key-mod_venue { border-color: rgba(163,230,53,.30) !important; background-image: radial-gradient(circle at 100% 0%, rgba(163,230,53,.14), transparent 45%), linear-gradient(160deg, rgba(15,32,56,.78), rgba(8,22,42,.78)) !important; }
.st-key-mod_venue .mod-kicker { color:#A3E635; }

/* DISMISSALS : danger dashed frame */
.st-key-mod_dismiss { border:1.5px dashed rgba(249,115,22,.55) !important; }
.st-key-mod_dismiss .mod-kicker { color:#F97316; }
.st-key-mod_dismiss::before { right:18px; top:16px; width:10px; height:10px; border-radius:50%; background:#F97316; box-shadow:0 0 0 0 rgba(249,115,22,.7); animation: alarm 1.6s infinite; }
@keyframes alarm { 70% { box-shadow:0 0 0 12px rgba(249,115,22,0);} 100% { box-shadow:0 0 0 0 rgba(249,115,22,0);} }

/* --- custom cursor --- */
#fx-dot, #fx-ring { position:fixed; left:0; top:0; pointer-events:none; z-index:2147483647; border-radius:50%; will-change:transform; }
#fx-dot { width:7px; height:7px; background:#22D3EE; box-shadow:0 0 12px #22D3EE, 0 0 24px #8B5CF6; margin:-3.5px 0 0 -3.5px; }
#fx-ring { width:38px; height:38px; margin:-19px 0 0 -19px; border:1.5px solid rgba(34,211,238,.65);
    background: conic-gradient(from 0deg, transparent 0 70%, rgba(139,92,246,.55) 100%); -webkit-mask: radial-gradient(circle, transparent 15px, #000 16px); mask: radial-gradient(circle, transparent 15px, #000 16px);
    transition: width .2s, height .2s, margin .2s, border-color .2s; }
#fx-ring.act { width:58px; height:58px; margin:-29px 0 0 -29px; border-color:#F0ABFC; }
#fx-trail { position:fixed; inset:0; pointer-events:none; z-index:2147483646; }
@media (hover:none) { #fx-dot, #fx-ring, #fx-trail { display:none; } }
@media (prefers-reduced-motion: reduce) { .ticker-track, .st-key-mod_lolli::before, .st-key-mod_scatter::before, .st-key-mod_timeline::before { animation:none !important; } }
</style>
"""
REMOTE_BG_URL = "https://www.smargengroup.com/assets/hero-stadium-BHqKFcI7.jpg"


@st.cache_resource(show_spinner=False)
def background_url():
    """Optional local photo: put it at assets/stadium.jpg (or .png/.webp) next to app.py.
    Otherwise the remote stadium image is used; CSS gradients cover the case where it cannot load."""
    try:
        base = Path(__file__).resolve().parent / "assets"
        for name, mime in (("stadium.jpg", "image/jpeg"), ("stadium.jpeg", "image/jpeg"),
                           ("stadium.png", "image/png"), ("stadium.webp", "image/webp")):
            p = base / name
            if p.exists() and p.stat().st_size < 6_000_000:
                return f"data:{mime};base64," + base64.b64encode(p.read_bytes()).decode("ascii")
    except Exception:
        pass
    return REMOTE_BG_URL


st.markdown(CSS.replace("__BG_URL__", background_url()), unsafe_allow_html=True)


CURSOR_JS = """
<script>
(function () {
  const w = window.parent, d = w.document;
  if (w.__fxInit) return; w.__fxInit = true;
  if (w.matchMedia('(hover: none)').matches) return;
  const mk = (tag, id) => { const e = d.createElement(tag); e.id = id; d.body.appendChild(e); return e; };
  const dot = mk('div', 'fx-dot'), ring = mk('div', 'fx-ring'), cv = mk('canvas', 'fx-trail');
  const ctx = cv.getContext('2d');
  const fit = () => { cv.width = w.innerWidth; cv.height = w.innerHeight; };
  fit(); w.addEventListener('resize', fit);
  let mx = -100, my = -100, rx = -100, ry = -100, pts = [], ang = 0;
  d.addEventListener('mousemove', e => {
    mx = e.clientX; my = e.clientY;
    pts.push({x: mx, y: my, a: 1});
    if (pts.length > 26) pts.shift();
    const m = e.target.closest && e.target.closest('[class*="st-key-mod_"]');
    if (m) { const r = m.getBoundingClientRect(); m.style.setProperty('--mx', (e.clientX - r.left) + 'px'); m.style.setProperty('--my', (e.clientY - r.top) + 'px'); }
    const hot = e.target.closest && e.target.closest('button, a, input, label, [role="tab"], [data-baseweb="select"], [role="slider"]');
    ring.classList.toggle('act', !!hot);
  }, {passive: true});
  d.addEventListener('mousedown', () => { ring.style.transform += ' scale(.8)'; });
  (function loop() {
    rx += (mx - rx) * 0.18; ry += (my - ry) * 0.18; ang += 4;
    dot.style.transform = 'translate(' + mx + 'px,' + my + 'px)';
    ring.style.transform = 'translate(' + rx + 'px,' + ry + 'px) rotate(' + ang + 'deg)';
    ctx.clearRect(0, 0, cv.width, cv.height);
    for (let i = 0; i < pts.length; i++) {
      const p = pts[i]; p.a *= 0.92;
      ctx.beginPath(); ctx.arc(p.x, p.y, 1 + 3 * (i / pts.length), 0, 6.283);
      ctx.fillStyle = (i % 2 ? 'rgba(34,211,238,' : 'rgba(139,92,246,') + (p.a * 0.55) + ')'; ctx.fill();
    }
    w.requestAnimationFrame(loop);
  })();
})();
</script>
"""
components.html(CURSOR_JS, height=0)


# ============================================================
# 4. DATABASE CONNECTION
# ============================================================
ICONS = {
    "users": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="9" cy="8" r="3.2"/><path d="M3 20c0-3.3 2.7-6 6-6s6 2.7 6 6"/><circle cx="17" cy="9" r="2.4"/><path d="M16 14.2c3 .2 5 2.3 5 5.8"/></svg>',
    "bolt": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M13 2 4 14h7l-1 8 9-12h-7z"/></svg>',
    "target": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="4.5"/><circle cx="12" cy="12" r="1"/></svg>',
    "chart": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M4 20V10M10 20V4M16 20v-7M22 20H2"/></svg>',
    "shield": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3 4 6v6c0 4.5 3.2 8 8 9 4.8-1 8-4.5 8-9V6z"/></svg>',
    "db": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><ellipse cx="12" cy="5" rx="8" ry="3"/><path d="M4 5v6c0 1.7 3.6 3 8 3s8-1.3 8-3V5M4 11v6c0 1.7 3.6 3 8 3s8-1.3 8-3v-6"/></svg>',
    "grid": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/></svg>',
    "pin": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M12 21s7-6.2 7-11.5A7 7 0 0 0 5 9.5C5 14.8 12 21 12 21z"/><circle cx="12" cy="9.5" r="2.5"/></svg>',
    "pulse": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M3 12h4l3-8 4 16 3-8h4"/></svg>',
}


def esc(x):
    return htmllib.escape(str(x), quote=True)


def html(s):
    """Render single-line HTML (collapsing whitespace avoids markdown code-block parsing)."""
    st.markdown(re.sub(r"\s+", " ", s).strip(), unsafe_allow_html=True)


def sidebar_badge(ok, line2):
    cls = "live-badge" if ok else "live-badge bad"
    label = "LIVE DATABASE" if ok else "DATABASE OFFLINE"
    st.sidebar.markdown(
        re.sub(r"\s+", " ", f"""
        <div class="brand"><div class="brand-mark">🏏</div>
        <div><div class="brand-name">IPL INTELLIGENCE</div><div class="brand-sub">Batter analytics</div></div></div>
        <div class="{cls}"><div class="live-top"><span class="live-dot"></span>{label}</div>
        <div class="live-sub">{esc(line2)}</div></div>
        """).strip(),
        unsafe_allow_html=True,
    )


def error_screen(title, body_html):
    html(f"""
    <div class="hero-banner" style="border-color: rgba(251,113,133,.35);">
        <div class="eyebrow" style="color:#FDA4AF;">● Connection problem</div>
        <h1>{esc(title)}</h1>
        {body_html}
    </div>
    """)
    st.stop()


@st.cache_resource(show_spinner=False)
def get_connection(path_string):
    return sqlite3.connect(path_string, check_same_thread=False)


def table_exists(conn, name):
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type IN ('table','view') AND name = ?", (name,)
    ).fetchone()
    return row is not None


def table_columns(conn, name):
    try:
        return [r[1] for r in conn.execute(f'PRAGMA table_info("{name}")').fetchall()]
    except Exception:
        return []


if not DB_PATH.exists():
    sidebar_badge(False, "ipl.db not found")
    error_screen(
        "DATABASE CONNECTION ERROR",
        f"""<p class="hero-sub">The dashboard connects automatically on start-up, but no file exists at the expected path.</p>
        <div class="reader"><b>Expected</b> <code>{esc(str(DB_PATH))}</code></div>""",
    )

try:
    CONN = get_connection(str(DB_PATH))
    REQUIRED_COLS = [
        "season_id", "match_id", "innings", "batter", "non_striker", "bowling_team", "over_number",
        "ball_number", "batter_runs", "is_wicket", "player_out", "wicket_kind", "phase", "is_legal",
        "batsman_type",
    ]
    if not table_exists(CONN, "v_ball"):
        raise ValueError("The database has no 'v_ball' view/table.")
    missing_cols = [c for c in REQUIRED_COLS if c not in table_columns(CONN, "v_ball")]
    if missing_cols:
        raise ValueError("v_ball is missing columns: " + ", ".join(missing_cols))
    HAS_PLAYERS = table_exists(CONN, "players") and {"player_name", "bat_style"}.issubset(
        set(table_columns(CONN, "players"))
    )
    HAS_MATCHES = table_exists(CONN, "matches") and {"match_id", "venue"}.issubset(
        set(table_columns(CONN, "matches"))
    )
except Exception as exc:
    sidebar_badge(False, "ipl.db could not be read")
    error_screen(
        "DATABASE CONNECTION ERROR",
        f"""<p class="hero-sub">{esc(exc)}</p>
        <div class="reader"><b>Expected</b> <code>{esc(str(DB_PATH))}</code></div>""",
    )

DB_MTIME = DB_PATH.stat().st_mtime


# ============================================================
# 5. HELPER FUNCTIONS
# ============================================================
def sdiv(a, b):
    try:
        if b is None or pd.isna(b) or b <= 0 or pd.isna(a):
            return np.nan
        return float(a) / float(b)
    except Exception:
        return np.nan


def ratio(a, b, scale=1.0):
    """Series ratio; NaN where the denominator is zero."""
    return (a * scale) / b.where(b > 0)


def fnum(x, d=0):
    try:
        if x is None or pd.isna(x):
            return "—"
        return f"{x:,.{d}f}"
    except Exception:
        return "—"


def fmt_metric(v, metric):
    if v is None or pd.isna(v):
        return "—"
    return f"{v:.1f}" if metric == "Strike rate" else f"{v:.1f}%"


def norm_hand(v):
    s = str(v).lower() if v is not None and not pd.isna(v) else ""
    if "left" in s:
        return "Left hand Bat"
    if "right" in s:
        return "Right hand Bat"
    return "Unknown"


def norm_phase(v):
    s = str(v).lower()
    if "power" in s:
        return "Powerplay"
    if "middle" in s:
        return "Middle"
    if "death" in s:
        return "Death"
    return str(v)


def short_venue(v):
    name = str(v).split(",")[0].strip()
    return name if len(name) <= 28 else name[:26] + "…"


def short_hand(h):
    return str(h).replace(" Bat", "").replace(" hand", "-hand")


def filter_season(df, season):
    if season in ("All", None):
        return df
    return df[df["season"] == season]


def style_fig(fig, height=360, legend=True):
    fig.update_layout(
        height=height,
        margin=dict(l=8, r=8, t=14, b=8),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, sans-serif", color="#BFD0E3", size=12),
        showlegend=legend,
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color="#AFC1D4"), orientation="h",
                    yanchor="bottom", y=1.02, xanchor="right", x=1),
        hoverlabel=dict(bgcolor="#0B1B31", bordercolor=CYAN, font=dict(color="#F8FAFC", family="Inter, sans-serif")),
    )
    fig.update_xaxes(gridcolor=GRID, zeroline=False, linecolor=GRID, tickfont=dict(color=MUTED))
    fig.update_yaxes(gridcolor=GRID, zeroline=False, linecolor=GRID, tickfont=dict(color=MUTED))
    return fig


def show_chart(fig, key):
    cfg = {"displayModeBar": False}
    try:
        st.plotly_chart(fig, width="stretch", key=key, config=cfg, theme=None)
    except (TypeError, ValueError):
        st.plotly_chart(fig, use_container_width=True, key=key, config=cfg, theme=None)


def module(key):
    try:
        return st.container(key=f"mod_{key}")
    except TypeError:
        return st.container(border=True)


def bar_container(key):
    try:
        return st.container(key=f"bar_{key}")
    except TypeError:
        return st.container(border=True)


def head_html(icon, kicker, title, sub=""):
    return re.sub(
        r"\s+", " ",
        f"""<div class="mod-kicker">{ICONS.get(icon, '')}<span>{esc(kicker)}</span></div>
        <div class="mod-title">{esc(title)}</div><div class="mod-sub">{esc(sub)}</div>""",
    ).strip()


def render_head(ph, icon, kicker, title, sub=""):
    ph.markdown(head_html(icon, kicker, title, sub), unsafe_allow_html=True)


def empty_state(msg="No players match these filters. Try lowering the minimum sample size."):
    html(f'<div class="empty">{esc(msg)}</div>')


def kpi_card(icon, label, value, note, accent=CYAN):
    html(f"""
    <div class="kpi" style="--accent:{accent}">
        <div class="kpi-top"><span class="kpi-icon">{ICONS[icon]}</span><span class="kpi-label">{esc(label)}</span></div>
        <div class="kpi-value">{value}</div>
        <div class="kpi-note">{note}</div>
    </div>
    """)


def insight_card(title, text_html):
    html(f"""
    <div class="insight"><div class="insight-title">{esc(title)}</div>
    <div class="insight-text">{text_html}</div></div>
    """)


def chart_season(key, global_season):
    pick = st.selectbox("Season", ["As global"] + SEASONS, key=f"{key}_season")
    return global_season if pick == "As global" else pick


def chart_hands(key, global_hand):
    sel = st.multiselect("Batting hand", HANDS, default=HANDS, key=f"{key}_hands")
    if global_hand != "All":
        sel = [h for h in sel if h == global_hand]
    return sel


def pad_range(vals, pad=0.12):
    vals = [v for v in vals if v is not None and np.isfinite(v)]
    if not vals:
        return None
    lo, hi = min(vals), max(vals)
    span = (hi - lo) or max(abs(hi), 1.0) * 0.1
    return [lo - span * pad, hi + span * pad]


# ============================================================
# 6. CACHED DATA FUNCTIONS
# ============================================================
DISMISSAL_COND = (
    "is_wicket = 1 AND player_out = batter "
    "AND COALESCE(wicket_kind,'') NOT IN ('retired hurt','retired not out')"
)

INNINGS_SQL = f"""
SELECT
    CAST(season_id AS TEXT) AS season,
    match_id,
    innings,
    batter,
    MAX(bowling_team) AS opponent,
    SUM(batter_runs) AS runs,
    SUM(CASE WHEN is_legal = 1 THEN 1 ELSE 0 END) AS balls,
    SUM(CASE WHEN is_legal = 1 AND batter_runs = 0 THEN 1 ELSE 0 END) AS dots,
    SUM(CASE WHEN batter_runs = 4 THEN 1 ELSE 0 END) AS fours,
    SUM(CASE WHEN batter_runs = 6 THEN 1 ELSE 0 END) AS sixes,
    MAX(CASE WHEN {DISMISSAL_COND} THEN 1 ELSE 0 END) AS outs
FROM v_ball
WHERE batter IS NOT NULL
GROUP BY season_id, match_id, innings, batter
"""

PHASE_SQL = f"""
SELECT
    CAST(season_id AS TEXT) AS season,
    batter,
    phase,
    SUM(batter_runs) AS runs,
    SUM(CASE WHEN is_legal = 1 THEN 1 ELSE 0 END) AS balls,
    SUM(CASE WHEN is_legal = 1 AND batter_runs = 0 THEN 1 ELSE 0 END) AS dots,
    SUM(CASE WHEN {DISMISSAL_COND} THEN 1 ELSE 0 END) AS outs
FROM v_ball
WHERE batter IS NOT NULL
GROUP BY season_id, batter, phase
"""

DISMISSAL_SQL = f"""
SELECT CAST(season_id AS TEXT) AS season, batter, COALESCE(wicket_kind, 'unknown') AS kind, COUNT(*) AS n
FROM v_ball
WHERE {DISMISSAL_COND}
GROUP BY season_id, batter, kind
"""

ENTRY_ORDER_SQL = """
SELECT match_id, innings, batter AS player,
       MIN(over_number * 100 + COALESCE(ball_number, 0)) AS first_ball, 0 AS flag
FROM v_ball WHERE batter IS NOT NULL
GROUP BY match_id, innings, batter
UNION ALL
SELECT match_id, innings, non_striker AS player,
       MIN(over_number * 100 + COALESCE(ball_number, 0)) AS first_ball, 1 AS flag
FROM v_ball WHERE non_striker IS NOT NULL
GROUP BY match_id, innings, non_striker
"""

HAND_SQL_JOIN = """
SELECT b.batter AS batter, COALESCE(p.bat_style, b.batsman_type) AS batting_hand
FROM (SELECT batter, MAX(batsman_type) AS batsman_type FROM v_ball WHERE batter IS NOT NULL GROUP BY batter) b
LEFT JOIN players p ON LOWER(p.player_name) = LOWER(b.batter)
"""

HAND_SQL_FALLBACK = """
SELECT batter, MAX(batsman_type) AS batting_hand FROM v_ball WHERE batter IS NOT NULL GROUP BY batter
"""


@st.cache_resource(show_spinner="Reading ball-by-ball data from ipl.db …")
def load_data(path_string, mtime):
    conn = get_connection(path_string)

    def qry(sql):
        return pd.read_sql_query(sql, conn)

    inn = qry(INNINGS_SQL)
    num_cols = ["runs", "balls", "dots", "fours", "sixes", "outs"]
    inn[num_cols] = inn[num_cols].fillna(0).astype(float)
    inn["season"] = inn["season"].astype(str)
    inn["opponent"] = inn["opponent"].fillna("Unknown")

    # entry position (batters or non-strikers, by first appearance)
    order = qry(ENTRY_ORDER_SQL)
    order = order.sort_values(["match_id", "innings", "first_ball", "flag", "player"])
    order = order.drop_duplicates(["match_id", "innings", "player"], keep="first")
    order["entry_pos"] = order.groupby(["match_id", "innings"]).cumcount() + 1
    order["entry_group"] = np.where(order["entry_pos"] >= 5, "5+", order["entry_pos"].astype(str))
    inn = inn.merge(
        order[["match_id", "innings", "player", "entry_group"]],
        left_on=["match_id", "innings", "batter"],
        right_on=["match_id", "innings", "player"],
        how="left",
    ).drop(columns="player")
    inn["entry_group"] = inn["entry_group"].fillna("5+")

    # batting hand: COALESCE(p.bat_style, v.batsman_type)
    hand_df = qry(HAND_SQL_JOIN if HAS_PLAYERS else HAND_SQL_FALLBACK)
    hand_df["batting_hand"] = hand_df["batting_hand"].map(norm_hand)
    hand_df = hand_df.sort_values("batting_hand", key=lambda s: (s == "Unknown")).drop_duplicates("batter")
    hand_map = dict(zip(hand_df["batter"], hand_df["batting_hand"]))
    inn["batting_hand"] = inn["batter"].map(hand_map).fillna("Unknown")

    # venue
    latest_date = None
    if HAS_MATCHES:
        ven = qry("SELECT match_id, venue FROM matches")
        vmap = dict(zip(ven["match_id"], ven["venue"]))
        inn["venue"] = inn["match_id"].map(vmap).fillna("Unknown")
        try:
            latest_date = qry("SELECT MAX(match_date) AS d FROM matches")["d"].iloc[0]
        except Exception:
            latest_date = None
    else:
        inn["venue"] = "Unknown"

    phase = qry(PHASE_SQL)
    phase[["runs", "balls", "dots", "outs"]] = phase[["runs", "balls", "dots", "outs"]].fillna(0).astype(float)
    phase["season"] = phase["season"].astype(str)
    phase["phase"] = phase["phase"].map(norm_phase)
    phase = phase.groupby(["season", "batter", "phase"], as_index=False)[["runs", "balls", "dots", "outs"]].sum()
    phase["batting_hand"] = phase["batter"].map(hand_map).fillna("Unknown")

    dis = qry(DISMISSAL_SQL)
    dis["season"] = dis["season"].astype(str)

    scale = {
        "matches": int(inn["match_id"].nunique()),
        "balls": int(inn["balls"].sum()),
        "batters": int(inn["batter"].nunique()),
        "runs": int(inn["runs"].sum()),
    }
    top_batter = inn.groupby("batter")["runs"].sum().idxmax() if len(inn) else None

    return SimpleNamespace(
        inn=inn,
        phase=phase,
        dis=dis,
        hand_map=hand_map,
        seasons=sorted(inn["season"].unique().tolist()),
        batters=sorted(inn["batter"].dropna().unique().tolist()),
        scale=scale,
        latest_date=latest_date,
        top_batter=top_batter,
    )


def D():
    return load_data(str(DB_PATH), DB_MTIME)


@st.cache_data(show_spinner=False)
def batter_pool(season, hand, min_balls, min_runs):
    cols = ["batter", "batting_hand", "runs", "balls", "dots", "outs", "fours", "sixes",
            "innings", "sr", "avg", "dot_pct"]
    inn = filter_season(D().inn, season)
    if inn.empty:
        return pd.DataFrame(columns=cols)
    g = inn.groupby("batter", as_index=False).agg(
        runs=("runs", "sum"), balls=("balls", "sum"), dots=("dots", "sum"), outs=("outs", "sum"),
        fours=("fours", "sum"), sixes=("sixes", "sum"), innings=("match_id", "size"),
    )
    g["batting_hand"] = g["batter"].map(D().hand_map).fillna("Unknown")
    if hand != "All":
        g = g[g["batting_hand"] == hand]
    g = g[(g["balls"] >= min_balls) & (g["runs"] >= min_runs) & (g["balls"] > 0)].copy()
    if g.empty:
        return pd.DataFrame(columns=cols)
    g["sr"] = ratio(g["runs"], g["balls"], 100)
    g["avg"] = np.where(g["outs"] > 0, g["runs"] / g["outs"].replace(0, np.nan), g["runs"])
    g["dot_pct"] = ratio(g["dots"], g["balls"], 100)
    return g[cols].reset_index(drop=True)


@st.cache_data(show_spinner=False)
def hand_phase_table(season, hand, min_balls, min_runs):
    cols = ["batting_hand", "phase", "runs", "balls", "dots", "outs", "batters"]
    pool = batter_pool(season, hand, min_balls, min_runs)
    if pool.empty:
        return pd.DataFrame(columns=cols)
    ph = filter_season(D().phase, season)
    ph = ph[ph["batter"].isin(pool["batter"])]
    if ph.empty:
        return pd.DataFrame(columns=cols)
    out = ph.groupby(["batting_hand", "phase"], as_index=False).agg(
        runs=("runs", "sum"), balls=("balls", "sum"), dots=("dots", "sum"),
        outs=("outs", "sum"), batters=("batter", "nunique"),
    )
    return out[cols]


@st.cache_data(show_spinner=False)
def entry_stats(season, hand, min_balls, min_runs):
    cols = ["batting_hand", "entry_group", "runs", "balls", "sixes", "dots", "innings", "batters"]
    pool = batter_pool(season, hand, min_balls, min_runs)
    if pool.empty:
        return pd.DataFrame(columns=cols)
    inn = filter_season(D().inn, season)
    inn = inn[inn["batter"].isin(pool["batter"])]
    if inn.empty:
        return pd.DataFrame(columns=cols)
    out = inn.groupby(["batting_hand", "entry_group"], as_index=False).agg(
        runs=("runs", "sum"), balls=("balls", "sum"), sixes=("sixes", "sum"), dots=("dots", "sum"),
        innings=("match_id", "size"), batters=("batter", "nunique"),
    )
    return out[cols]


@st.cache_data(show_spinner=False)
def league_baseline(season):
    inn = filter_season(D().inn, season)
    runs, balls, outs, dots = (inn[c].sum() for c in ("runs", "balls", "outs", "dots"))
    return {
        "sr": sdiv(runs * 100, balls),
        "avg": sdiv(runs, outs),
        "dot": sdiv(dots * 100, balls),
    }


@st.cache_data(show_spinner=False)
def league_season_table():
    inn = D().inn
    bs = inn.groupby(["season", "batter"], as_index=False).agg(runs=("runs", "sum"), balls=("balls", "sum"))
    tot = bs.groupby("season").agg(total_runs=("runs", "sum"), total_balls=("balls", "sum"))
    qual = bs[bs["balls"] >= 50].groupby("season").agg(lg_runs=("runs", "mean"), lg_balls=("balls", "mean"))
    out = tot.join(qual, how="left").reset_index()
    out["lg_sr"] = out["total_runs"] * 100 / out["total_balls"].where(out["total_balls"] > 0)
    return out[["season", "lg_runs", "lg_balls", "lg_sr"]]


def phase_metric_values(df, metric, group=None):
    df = df.copy()
    if metric == "Strike rate":
        df["value"] = ratio(df["runs"], df["balls"], 100)
    elif metric == "Dot-ball %":
        df["value"] = ratio(df["dots"], df["balls"], 100)
    else:
        if group:
            tot = df.groupby(group)["runs"].transform("sum")
        else:
            tot = pd.Series(df["runs"].sum(), index=df.index)
        df["value"] = df["runs"] * 100 / tot.where(tot > 0)
    return df


def hand_test(pool):
    """Welch's t-test on per-batter strike rate: left vs right hand."""
    if pool is None or pool.empty:
        return None
    left = pool.loc[pool["batting_hand"] == HANDS[0], "sr"].dropna().astype(float)
    right = pool.loc[pool["batting_hand"] == HANDS[1], "sr"].dropna().astype(float)
    nl, nr = len(left), len(right)
    if nl < 2 or nr < 2:
        return None
    vl, vr = left.var(ddof=1), right.var(ddof=1)
    if SCIPY_OK:
        _, p = ttest_ind(left, right, equal_var=False)
    else:
        se = math.sqrt(vl / nl + vr / nr)
        t = (left.mean() - right.mean()) / se if se > 0 else 0.0
        p = math.erfc(abs(t) / math.sqrt(2))
    pooled = math.sqrt(((nl - 1) * vl + (nr - 1) * vr) / (nl + nr - 2))
    d = (left.mean() - right.mean()) / pooled if pooled > 0 else np.nan
    return {"left_sr": float(left.mean()), "right_sr": float(right.mean()),
            "p": float(p), "d": float(d), "n_left": nl, "n_right": nr}


def evidence_label(p):
    if p is None or pd.isna(p):
        return "not available"
    if p < 0.01:
        return "strong evidence of a difference"
    if p < 0.05:
        return "moderate evidence of a difference"
    if p < 0.10:
        return "weak evidence of a difference"
    return "little evidence of a difference"


def effect_label(d):
    if d is None or pd.isna(d):
        return "n/a"
    a = abs(d)
    if a < 0.2:
        return "negligible"
    if a < 0.5:
        return "small"
    if a < 0.8:
        return "medium"
    return "large"


# ============================================================
# 7. GLOBAL DATA + SIDEBAR
# ============================================================
DATA = D()
SEASONS = DATA.seasons
SCALE = DATA.scale

if not SCALE["batters"]:
    sidebar_badge(False, "v_ball contains no rows")
    error_screen("DATABASE CONNECTION ERROR", '<p class="hero-sub">The v_ball view returned no deliveries.</p>')

sidebar_badge(True, f"{DB_PATH.name} connected")
st.sidebar.markdown(
    re.sub(r"\s+", " ", f"""
    <div class="side-label">Dataset scale</div>
    <div class="side-row"><span>Matches</span><b>{SCALE['matches']:,}</b></div>
    <div class="side-row"><span>Legal balls</span><b>{SCALE['balls']:,}</b></div>
    <div class="side-row"><span>Batters</span><b>{SCALE['batters']:,}</b></div>
    <div class="side-row"><span>Seasons</span><b>{len(SEASONS)}</b></div>
    <div class="side-label">How to read</div>
    <div class="side-note">Strike rate = runs × 100 / legal balls.<br>Average = runs / dismissals (runs if never dismissed).<br>
    Phases: Powerplay, Middle, Death.<br>Chart filters tune one module; "As global" follows the filter bar. Extra minimums apply on top of the global ones.</div>
    """).strip(),
    unsafe_allow_html=True,
)
st.sidebar.markdown('<div class="side-label">Background</div>', unsafe_allow_html=True)
bg_mode = st.sidebar.radio("Stadium background", ["Animated", "Static", "Off"], horizontal=True,
                           key="bg_mode", label_visibility="collapsed")
if bg_mode == "Static":
    st.sidebar.markdown("<style>.stApp{animation:none !important;}</style>", unsafe_allow_html=True)
elif bg_mode == "Off":
    st.sidebar.markdown(
        "<style>.stApp{animation:none !important;background-image:none !important;background-color:#061225 !important;}</style>",
        unsafe_allow_html=True,
    )
if st.sidebar.button("↻ Reload data"):
    st.cache_data.clear()
    st.cache_resource.clear()
    st.rerun()


# ============================================================
# 8. OVERVIEW TAB  ·  BATTER UNIVERSE
# ============================================================
def render_universe_header():
    html(f"""
    <div class="hero-banner">
        <div class="eyebrow">IPL · Data analytics · Batter intelligence</div>
        <h1>BATTER UNIVERSE</h1>
        <p class="hero-sub">Find the scoring profiles, roles and batting patterns that stand out across the IPL.</p>
        <div class="reader"><b>Reader</b>For the batting coach, deciding which batter to pick and for which role.</div>
        <div class="scale-tag">Dataset scale · complete database, before any filter</div>
        <div class="scale-strip">
            <div class="scale-item"><div class="scale-k">Total matches</div><div class="scale-v">{SCALE['matches']:,}</div></div>
            <div class="scale-item"><div class="scale-k">Total legal balls</div><div class="scale-v">{SCALE['balls']:,}</div></div>
            <div class="scale-item"><div class="scale-k">Total batters</div><div class="scale-v">{SCALE['batters']:,}</div></div>
        </div>
    </div>
    """)


HERO_METRICS = {"Strike rate": "sr", "Batting average": "avg", "Runs": "runs"}
HERO_CHARTS = ["Dumbbell", "Bar Chart", "Race Bars", "Line Chart", "Area Chart", "Radar Chart",
               "Polar Bars", "Slope Chart", "Bubble Matrix"]
HAND_FILLS = {"Left hand Bat": "rgba(167,139,250,.22)", "Right hand Bat": "rgba(34,211,238,.20)"}
DONUT_SHADES = {"Left hand Bat": ["#C4B5FD", "#8B5CF6", "#6D28D9"], "Right hand Bat": ["#67E8F9", "#22D3EE", "#0E7490"]}


def hero_alt_figure(chart, metric, look):
    """Alternative hero views built from the SAME `look` table as the dumbbell (same SQL / data)."""
    key = HERO_METRICS[metric]
    dec = 0 if key == "runs" else 1
    cats = ["Overall"] + PHASES

    def val(c, h):
        return look.get((c, h), {}).get(key, np.nan)

    def extra(c, h):
        d = look.get((c, h), {})
        return [d.get("batters", np.nan), d.get("balls", np.nan)]

    def lab(v):
        return f"{v:,.{dec}f}" if np.isfinite(v) else ""

    fig = go.Figure()
    if chart == "Bar Chart":
        for hand in HANDS:
            ys = [val(c, hand) for c in cats]
            fig.add_trace(go.Bar(
                x=cats, y=ys, name=hand, marker=dict(color=HAND_COLORS[hand], line=dict(color="rgba(255,255,255,.18)", width=1)),
                text=[lab(v) for v in ys], textposition="outside", textfont=dict(size=11, color="#CBD5E1"),
                customdata=[extra(c, hand) for c in cats], cliponaxis=False,
                hovertemplate="<b>" + hand + "</b><br>%{x}: %{y:,.1f}<br>%{customdata[0]:,.0f} batters · "
                              "%{customdata[1]:,.0f} legal balls<extra></extra>",
            ))
        style_fig(fig, 430)
        fig.update_layout(barmode="group", bargap=0.28)
        fig.update_yaxes(title=metric, rangemode="tozero")
        fig.update_xaxes(showgrid=False)
    elif chart in ("Line Chart", "Area Chart"):
        for hand in HANDS:
            ys = [val(p, hand) for p in PHASES]
            fig.add_trace(go.Scatter(
                x=PHASES, y=ys, name=hand, mode="lines+markers+text",
                line=dict(color=HAND_COLORS[hand], width=3, shape="spline", smoothing=0.4),
                marker=dict(size=10, color=HAND_COLORS[hand], line=dict(color="#061225", width=2)),
                fill="tozeroy" if chart == "Area Chart" else None, fillcolor=HAND_FILLS[hand],
                text=[lab(v) for v in ys], textposition="top center", textfont=dict(size=11, color=HAND_COLORS[hand]),
                customdata=[extra(p, hand) for p in PHASES],
                hovertemplate="<b>" + hand + "</b><br>%{x}: %{y:,.1f}<br>%{customdata[0]:,.0f} batters · "
                              "%{customdata[1]:,.0f} legal balls<extra></extra>",
            ))
        style_fig(fig, 430)
        fig.update_yaxes(title=metric, rangemode="tozero")
        fig.update_xaxes(showgrid=False, type="category")
    elif chart == "Radar Chart":
        allv = []
        for hand in HANDS:
            rs = [val(p, hand) for p in PHASES]
            rs = [r if np.isfinite(r) else 0 for r in rs]
            allv += rs
            fig.add_trace(go.Scatterpolar(
                r=rs + rs[:1], theta=PHASES + PHASES[:1], name=hand, fill="toself", fillcolor=HAND_FILLS[hand],
                mode="lines+markers+text", line=dict(color=HAND_COLORS[hand], width=3), marker=dict(size=8),
                text=[lab(r) for r in rs] + [""], textfont=dict(size=11, color=HAND_COLORS[hand]),
                hovertemplate="<b>" + hand + "</b> · %{theta}<br>" + metric + ": %{r:,.1f}<extra></extra>",
            ))
        style_fig(fig, 430)
        fig.update_layout(polar=dict(
            bgcolor="rgba(0,0,0,0)",
            radialaxis=dict(range=[0, max(allv + [1]) * 1.2], gridcolor=GRID, linecolor=GRID, tickfont=dict(color=MUTED, size=10)),
            angularaxis=dict(gridcolor=GRID, linecolor=GRID, tickfont=dict(color="#CBD5E1", size=13)),
        ))
    elif chart == "Race Bars":
        for hand in HANDS:
            xs = [val(c, hand) for c in cats][::-1]
            fig.add_trace(go.Bar(
                y=cats[::-1], x=xs, name=hand, orientation="h",
                marker=dict(color=HAND_COLORS[hand], line=dict(color="rgba(255,255,255,.25)", width=1)),
                text=[lab(v) for v in xs], textposition="outside", textfont=dict(size=11, color="#CBD5E1"), cliponaxis=False,
                customdata=[extra(c, hand) for c in cats[::-1]],
                hovertemplate="<b>" + hand + "</b><br>%{y}: %{x:,.1f}<br>%{customdata[0]:,.0f} batters · "
                              "%{customdata[1]:,.0f} legal balls<extra></extra>",
            ))
        style_fig(fig, 430)
        fig.update_layout(barmode="group", bargap=0.30)
        fig.update_xaxes(title=metric, rangemode="tozero")
        fig.update_yaxes(showgrid=False)
    elif chart == "Polar Bars":
        for hand in HANDS:
            rs = [val(p, hand) for p in PHASES]
            fig.add_trace(go.Barpolar(
                r=[r if np.isfinite(r) else 0 for r in rs], theta=PHASES, name=hand,
                marker=dict(color=HAND_COLORS[hand], opacity=0.78, line=dict(color="#061225", width=2)),
                hovertemplate="<b>" + hand + "</b> · %{theta}<br>" + metric + ": %{r:,.1f}<extra></extra>",
            ))
        style_fig(fig, 430)
        fig.update_layout(polar=dict(
            bgcolor="rgba(0,0,0,0)", barmode="overlay",
            radialaxis=dict(gridcolor=GRID, linecolor=GRID, tickfont=dict(color=MUTED, size=10)),
            angularaxis=dict(gridcolor=GRID, linecolor=GRID, tickfont=dict(color="#CBD5E1", size=13)),
        ))
    elif chart == "Slope Chart":
        for i, c in enumerate(cats):
            lv, rv = val(c, HANDS[0]), val(c, HANDS[1])
            if not (np.isfinite(lv) and np.isfinite(rv)):
                continue
            col = PALETTE[i % len(PALETTE)]
            fig.add_trace(go.Scatter(
                x=["Left-hand", "Right-hand"], y=[lv, rv], name=c, mode="lines+markers+text",
                line=dict(color=col, width=4), marker=dict(size=13, color=col, line=dict(color="#061225", width=2)),
                text=[f"{c} · {lab(lv)}", f"{lab(rv)}"], textposition=["middle left", "middle right"],
                textfont=dict(size=11, color=col),
                hovertemplate="<b>" + c + "</b><br>%{x}: %{y:,.1f}<extra></extra>",
            ))
        style_fig(fig, 430)
        fig.update_xaxes(showgrid=False, type="category", range=[-0.6, 1.6])
        fig.update_yaxes(title=metric)
    elif chart == "Bubble Matrix":
        xs, ys, sz, cl, tx = [], [], [], [], []
        for hand in HANDS:
            for c in cats:
                v = val(c, hand)
                if np.isfinite(v):
                    xs.append(c); ys.append(short_hand(hand)); sz.append(v); cl.append(v); tx.append(lab(v))
        mx_ = max(sz + [1])
        fig.add_trace(go.Scatter(
            x=xs, y=ys, mode="markers+text", text=tx, textposition="middle center",
            textfont=dict(size=12, color="#F8FAFC"),
            marker=dict(size=[28 + 62 * (v / mx_) for v in sz], color=cl, colorscale=NEON_SCALE, opacity=0.92,
                        line=dict(color="rgba(255,255,255,.55)", width=1.5),
                        colorbar=dict(thickness=10, outlinewidth=0, tickfont=dict(color=MUTED))),
            hovertemplate="<b>%{y}</b> · %{x}<br>" + metric + ": %{text}<extra></extra>",
        ))
        style_fig(fig, 430, legend=False)
        fig.update_xaxes(type="category", categoryorder="array", categoryarray=cats, showgrid=False)
        fig.update_yaxes(showgrid=False)
    else:  # Donut Chart — only offered for the additive metric (Runs)
        labels, values, colors = [], [], []
        for hand in HANDS:
            for i, p in enumerate(PHASES):
                v = val(p, hand)
                if np.isfinite(v) and v > 0:
                    labels.append(f"{short_hand(hand)} · {p}")
                    values.append(v)
                    colors.append(DONUT_SHADES[hand][i])
        fig.add_trace(go.Pie(
            labels=labels, values=values, hole=0.62, sort=False,
            marker=dict(colors=colors, line=dict(color="#061225", width=3)),
            textinfo="label+percent", textfont=dict(color="#F8FAFC", size=12),
            hovertemplate="<b>%{label}</b><br>Runs: %{value:,.0f}<br>Share: %{percent}<extra></extra>",
        ))
        fig.add_annotation(text=f"<b>{sum(values):,.0f}</b><br><span style='font-size:11px;color:#7F97B0'>runs</span>",
                           x=0.5, y=0.5, xref="paper", yref="paper", showarrow=False,
                           font=dict(size=26, color="#F8FAFC"))
        style_fig(fig, 430, legend=False)
    return fig


def render_hero_insight(test):
    if test:
        p_txt = f"{test['p']:.4f}" if test["p"] >= 0.0001 else "< 0.0001"
        insight_card(
            "Statistical validation · Welch's t-test",
            f"Mean per-batter strike rate is {test['left_sr']:.1f} for left-handers versus {test['right_sr']:.1f} for right-handers. "
            f"The data show <b>{evidence_label(test['p'])}</b> (p = {p_txt}) with a <b>{effect_label(test['d'])}</b> effect size "
            f"(Cohen's d = {test['d']:.2f}). This describes an association in this batter pool only and does not show that "
            f"batting hand causes the difference."
            f'<br><span class="chip">p-value<b>{p_txt}</b></span><span class="chip">Cohen\'s d<b>{test["d"]:.2f}</b></span>'
            f'<span class="chip">Left n<b>{test["n_left"]}</b></span><span class="chip">Right n<b>{test["n_right"]}</b></span>',
        )
    else:
        insight_card("Statistical validation · Welch's t-test",
                     "At least two batters of each hand are needed for a valid test. Lower the minimum sample size.")



def render_hud(look, base):
    """Hero scoreboard: left-hand vs right-hand, with the SR gap in the middle."""
    def card(hand, color):
        o = look.get(("Overall", hand), {})
        sr_v, avg_v = o.get("sr", np.nan), o.get("avg", np.nan)
        return (f'<div class="hud-side" style="--c:{color}"><div class="hud-name">{esc(hand)}</div>'
                f'<div class="hud-big">{fnum(sr_v, 1)}<small>STRIKE RATE</small></div>'
                f'<div class="hud-row"><span>Avg <b>{fnum(avg_v, 1)}</b></span><span>Batters <b>{fnum(o.get("batters"))}</b></span>'
                f'<span>Balls <b>{fnum(o.get("balls"))}</b></span></div></div>')
    l = look.get(("Overall", HANDS[0]), {}).get("sr", np.nan)
    r = look.get(("Overall", HANDS[1]), {}).get("sr", np.nan)
    gap = (l - r) if np.isfinite(l) and np.isfinite(r) else np.nan
    sign = "+" if np.isfinite(gap) and gap >= 0 else ""
    core = (f'<div class="hud-core"><div class="k">SR gap · L − R</div><div class="v">{sign}{fnum(gap, 1)}</div>'
            f'<div class="m">IPL baseline {fnum(base["sr"], 1)}</div></div>')
    html(f'<div class="hud">{card(HANDS[0], HAND_COLORS[HANDS[0]])}{core}{card(HANDS[1], HAND_COLORS[HANDS[1]])}</div>')


def render_ticker():
    """Scrolling top-scorer strip — gives the dashboard its mission-control feel."""
    t = DATA.inn.groupby("batter").agg(runs=("runs", "sum"), balls=("balls", "sum"), sixes=("sixes", "sum"))
    t = t.sort_values("runs", ascending=False).head(12)
    items = "".join(
        f'<span class="tk"><i>#{i}</i><b>{esc(n)}</b> {int(r.runs):,} runs · SR {sdiv(r.runs * 100, r.balls):.1f} · {int(r.sixes)} sixes</span>'
        for i, (n, r) in enumerate(t.iterrows(), 1))
    html(f'<div class="ticker"><div class="ticker-tag">TOP SCORERS</div><div class="ticker-track">{items}{items}</div></div>')


def render_dumbbell(g):
    with module("hero"):
        head = st.empty()
        c1, c2, c4 = st.columns([1, 1, 1.3])
        with c1:
            season = chart_season("hero", g["season"])
        with c2:
            extra = st.number_input("Min legal balls", 0, 5000, 0, 25, key="hero_minballs",
                                    help="Applied on top of the global minimum.")
        # Metric is created first (it decides which chart types make sense) but sits in the 4th column.
        with c4:
            hero_metric = st.selectbox("Metric", list(HERO_METRICS.keys()), key="hero_metric",
                                       help="The Dumbbell always shows strike rate and average together.")
        chart_options = HERO_CHARTS + (["Donut Chart"] if hero_metric == "Runs" else [])
        hero_chart = st.radio("Hero Visualization — pick a chart type", chart_options, horizontal=True, key="hero_chart_pick")
        st.caption("This module always compares both hands, so the global batting-hand filter is not applied here.")

        min_balls = max(g["min_balls"], int(extra))
        min_runs = g["min_runs"]
        pool = batter_pool(season, "All", min_balls, min_runs)
        pool = pool[pool["batting_hand"].isin(HANDS)]
        if pool.empty or pool["batting_hand"].nunique() < 2:
            render_head(head, "bolt", "Hero insight · batting hand", "Not enough batters of both hands to compare")
            empty_state()
            return

        overall = pool.groupby("batting_hand").agg(
            runs=("runs", "sum"), balls=("balls", "sum"), outs=("outs", "sum"), batters=("batter", "nunique")
        )
        ptbl = hand_phase_table(season, "All", min_balls, min_runs)
        ptbl = ptbl[ptbl["batting_hand"].isin(HANDS) & ptbl["phase"].isin(PHASES)]

        look = {}
        for hand in HANDS:
            if hand in overall.index:
                o = overall.loc[hand]
                look[("Overall", hand)] = dict(runs=o["runs"], balls=o["balls"], outs=o["outs"], batters=o["batters"])
        for _, r in ptbl.iterrows():
            look[(r["phase"], r["batting_hand"])] = dict(runs=r["runs"], balls=r["balls"], outs=r["outs"], batters=r["batters"])
        for v in look.values():
            v["sr"] = sdiv(v["runs"] * 100, v["balls"])
            v["avg"] = sdiv(v["runs"], v["outs"])

        base = league_baseline(season)
        render_hud(look, base)

        if hero_chart != "Dumbbell":
            test_alt = hand_test(pool)
            alt_fig = hero_alt_figure(hero_chart, hero_metric, look)
            ov_l = look.get(("Overall", HANDS[0]), {})
            ov_r = look.get(("Overall", HANDS[1]), {})
            alt_title = f"{hero_metric} compared across batting hands and match phases"
            alt_sub = (f"{hero_chart} · {int(ov_l.get('batters', 0))} left-hand vs {int(ov_r.get('batters', 0))} right-hand batters · "
                       f"{fnum(ov_l.get('balls'))} vs {fnum(ov_r.get('balls'))} legal balls · "
                       f"minimum {min_balls} balls and {min_runs} runs")
            render_head(head, "bolt", "Hero insight · batting hand", alt_title, alt_sub)
            show_chart(alt_fig, "chart_hero_alt")
            render_hero_insight(test_alt)
            return

        cats = ["Overall"] + PHASES
        fig = make_subplots(rows=1, cols=2, subplot_titles=("STRIKE RATE", "BATTING AVERAGE"),
                            horizontal_spacing=0.10, shared_yaxes=True)
        fig.update_annotations(font=dict(color="#9FB2C8", size=11))

        all_x = {"sr": [], "avg": []}
        for col, metric, ref in ((1, "sr", base["sr"]), (2, "avg", base["avg"])):
            for cat in cats:
                lv = look.get((cat, HANDS[0]), {}).get(metric, np.nan)
                rv = look.get((cat, HANDS[1]), {}).get(metric, np.nan)
                if np.isfinite(lv) and np.isfinite(rv):
                    fig.add_trace(go.Scatter(x=[lv, rv], y=[cat, cat], mode="lines",
                                             line=dict(color="rgba(148,163,184,.45)", width=5),
                                             hoverinfo="skip", showlegend=False), row=1, col=col)
            for hand, pos in zip(HANDS, ("top center", "bottom center")):
                xs = [look.get((c, hand), {}).get(metric, np.nan) for c in cats]
                custom = [[look.get((c, hand), {}).get("batters", np.nan),
                           look.get((c, hand), {}).get("balls", np.nan)] for c in cats]
                all_x[metric] += [x for x in xs if np.isfinite(x)]
                fig.add_trace(go.Scatter(
                    x=xs, y=cats, mode="markers+text", name=hand, legendgroup=hand, showlegend=(col == 1),
                    marker=dict(size=17, color=HAND_COLORS[hand], line=dict(color="#061225", width=2)),
                    text=[f"{x:.1f}" if np.isfinite(x) else "" for x in xs], textposition=pos,
                    textfont=dict(size=11, color=HAND_COLORS[hand]), customdata=custom,
                    hovertemplate="<b>" + hand + "</b><br>%{y}: %{x:.1f}<br>%{customdata[0]:,.0f} batters · "
                                  "%{customdata[1]:,.0f} legal balls<extra></extra>",
                ), row=1, col=col)
            if np.isfinite(ref):
                all_x[metric].append(ref)
                fig.add_vline(x=ref, line_dash="dot", line_color=AMBER, row=1, col=col,
                              annotation_text=f"IPL baseline {ref:.1f}", annotation_position="bottom right",
                              annotation_font=dict(color=AMBER, size=10))
        style_fig(fig, 430)
        fig.update_yaxes(categoryorder="array", categoryarray=cats[::-1])
        for col, metric in ((1, "sr"), (2, "avg")):
            rng = pad_range(all_x[metric], 0.18)
            if rng:
                fig.update_xaxes(range=rng, row=1, col=col)

        test = hand_test(pool)
        ov_l = look.get(("Overall", HANDS[0]), {})
        ov_r = look.get(("Overall", HANDS[1]), {})
        gap = abs(ov_l.get("sr", np.nan) - ov_r.get("sr", np.nan))
        if test and np.isfinite(gap):
            who = "Left-handers" if ov_l["sr"] > ov_r["sr"] else "Right-handers"
            if test["p"] < 0.05:
                title = f"{who} score faster by {gap:.1f} SR points — a gap unlikely to be chance alone"
            else:
                title = f"Batting hand shifts scoring tempo by only {gap:.1f} SR points — the gap is not statistically clear"
        else:
            title = "Left- and right-handers compared on tempo, average and sample size"
        sub = (f"Which batting hand creates the stronger scoring profile? · {int(ov_l.get('batters', 0))} left-hand vs "
               f"{int(ov_r.get('batters', 0))} right-hand batters · {fnum(ov_l.get('balls'))} vs {fnum(ov_r.get('balls'))} legal balls · "
               f"minimum {min_balls} balls and {min_runs} runs")
        render_head(head, "bolt", "Hero insight · batting hand", title, sub)
        show_chart(fig, "chart_hero_dumbbell")
        render_hero_insight(test)


def render_heatmap(g):
    with module("heat"):
        head = st.empty()
        c1, c2, c3 = st.columns(3)
        with c1:
            season = chart_season("heat", g["season"])
        with c2:
            hands = chart_hands("heat", g["hand"])
        with c3:
            metric = st.selectbox("Metric", PHASE_METRICS, key="heat_metric")

        tbl = hand_phase_table(season, "All", g["min_balls"], g["min_runs"])
        if not tbl.empty:
            tbl = tbl[tbl["batting_hand"].isin(hands) & tbl["phase"].isin(PHASES)]
        if tbl.empty:
            render_head(head, "grid", "Phase heatmap", "No scoring pattern to show for these filters")
            empty_state()
            return

        vals = phase_metric_values(tbl, metric, group="batting_hand")
        rows = [h for h in HANDS if h in set(vals["batting_hand"])]

        def pv(col):
            return vals.pivot(index="batting_hand", columns="phase", values=col).reindex(index=rows, columns=PHASES)

        z = pv("value")
        text = z.map(lambda v: fmt_metric(v, metric))
        custom = np.dstack([pv("runs").values, pv("balls").values, pv("batters").values])
        fig = go.Figure(go.Heatmap(
            z=z.values, x=PHASES, y=[short_hand(r) if False else r for r in rows], text=text.values,
            texttemplate="%{text}", textfont=dict(size=17, color="#F8FAFC"), customdata=custom,
            colorscale=NEON_SCALE, xgap=5, ygap=5,
            colorbar=dict(thickness=10, outlinewidth=0, tickfont=dict(color=MUTED)),
            hovertemplate="<b>%{y}</b> · %{x}<br>" + metric + ": %{text}<br>Runs: %{customdata[0]:,.0f}<br>"
                          "Balls: %{customdata[1]:,.0f}<br>Batters: %{customdata[2]:,.0f}<extra></extra>",
        ))
        style_fig(fig, 330, legend=False)
        fig.update_xaxes(showgrid=False)
        fig.update_yaxes(showgrid=False, autorange="reversed")

        best = vals.dropna(subset=["value"])
        if best.empty:
            title = "Phase patterns are not available for these filters"
        else:
            b = best.loc[best["value"].idxmax()]
            if metric == "Strike rate":
                title = f"{b['phase']} overs create the strongest scoring tempo — {b['value']:.1f} SR for {b['batting_hand']}"
            elif metric == "Run share":
                title = f"{b['phase']} overs carry the biggest slice of runs — {b['value']:.1f}% for {b['batting_hand']}"
            else:
                title = f"{b['phase']} overs bring the heaviest dot-ball pressure — {b['value']:.1f}% for {b['batting_hand']}"
        n_b = int(tbl.groupby("batting_hand")["batters"].max().sum())
        sub = f"{metric} by batting hand and phase · {n_b} batters · {fnum(tbl['balls'].sum())} legal balls · minimum {g['min_balls']} balls"
        render_head(head, "grid", "Phase heatmap", title, sub)
        show_chart(fig, "chart_heatmap")


def render_lollipop(g):
    with module("lolli"):
        head = st.empty()
        c1, c2, c3 = st.columns(3)
        with c1:
            season = chart_season("lolli", g["season"])
        with c2:
            metric = st.selectbox("Metric", ["Runs", "Sixes", "Strike rate"], key="lolli_metric")
        with c3:
            extra = st.number_input("Min balls", 0, 5000, 0, 25, key="lolli_minballs",
                                    help="Applied on top of the global minimum.")
        min_balls = max(g["min_balls"], int(extra))
        es = entry_stats(season, g["hand"], min_balls, g["min_runs"])
        if es.empty:
            render_head(head, "pulse", "Batter role · entry position", "No entry-position pattern for these filters")
            empty_state()
            return

        grp = es.groupby("entry_group").agg(
            runs=("runs", "sum"), balls=("balls", "sum"), sixes=("sixes", "sum"),
            innings=("innings", "sum"), batters=("batters", "sum"),
        ).reindex(ENTRY_ORDER).fillna(0).reset_index()
        grp["sr"] = ratio(grp["runs"], grp["balls"], 100)
        col = {"Runs": "runs", "Sixes": "sixes", "Strike rate": "sr"}[metric]
        grp = grp.dropna(subset=[col])
        if grp.empty or grp["innings"].sum() == 0:
            render_head(head, "pulse", "Batter role · entry position", "No entry-position pattern for these filters")
            empty_state()
            return

        best_idx = grp[col].idxmax()
        colors = [PINK if i == best_idx else CYAN for i in grp.index]
        sx, sy = [], []
        for e, v in zip(grp["entry_group"], grp[col]):
            sx += [e, e, None]
            sy += [0, v, None]
        fmt = (lambda v: f"{v:.1f}") if metric == "Strike rate" else (lambda v: f"{v:,.0f}")
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=sx, y=sy, mode="lines", line=dict(color="rgba(148,163,184,.45)", width=3),
                                 hoverinfo="skip", showlegend=False))
        fig.add_trace(go.Scatter(
            x=grp["entry_group"], y=grp[col], mode="markers+text", showlegend=False,
            marker=dict(size=24, color=colors, line=dict(color="#061225", width=3)),
            text=[f"<b>{fmt(v)}</b><br>n={int(n):,}" for v, n in zip(grp[col], grp["innings"])],
            textposition="top center", textfont=dict(size=11, color="#E2E8F0"),
            customdata=np.column_stack([grp["runs"], grp["sixes"], grp["sr"], grp["innings"], grp["batters"]]),
            hovertemplate="<b>Entry No. %{x}</b><br>Runs: %{customdata[0]:,.0f}<br>Sixes: %{customdata[1]:,.0f}<br>"
                          "Strike rate: %{customdata[2]:.1f}<br>Batter-innings: %{customdata[3]:,.0f}<br>"
                          "Batters: %{customdata[4]:,.0f}<extra></extra>",
        ))
        if metric == "Strike rate":
            pooled_sr = sdiv(grp["runs"].sum() * 100, grp["balls"].sum())
            if np.isfinite(pooled_sr):
                fig.add_hline(y=pooled_sr, line_dash="dot", line_color=AMBER,
                              annotation_text=f"Pool SR {pooled_sr:.1f}", annotation_position="top left",
                              annotation_font=dict(color=AMBER, size=10))
        style_fig(fig, 330, legend=False)
        fig.update_xaxes(type="category", categoryorder="array", categoryarray=ENTRY_ORDER,
                         tickvals=ENTRY_ORDER, ticktext=[f"No. {e}" for e in ENTRY_ORDER], showgrid=False)
        fig.update_yaxes(range=[0, grp[col].max() * 1.3], title=metric)

        b = grp.loc[best_idx]
        if metric == "Runs":
            title = f"Batters entering at No. {b['entry_group']} produce the most runs ({b[col]:,.0f})"
        elif metric == "Sixes":
            title = f"Batters entering at No. {b['entry_group']} hit the most sixes ({b[col]:,.0f})"
        else:
            title = f"Batters entering at No. {b['entry_group']} score fastest ({b[col]:.1f} SR)"
        sub = (f"{metric} by batting entry position · {int(grp['innings'].sum()):,} batter-innings · "
               f"{int(es['batters'].sum()):,} batters · minimum {min_balls} legal balls per batter")
        render_head(head, "pulse", "Batter role · entry position", title, sub)
        show_chart(fig, "chart_lollipop")


def render_scatter(g):
    with module("scatter"):
        head = st.empty()
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            season = chart_season("scat", g["season"])
        with c2:
            extra_b = st.number_input("Min balls", 0, 5000, 0, 25, key="scat_minballs",
                                      help="Applied on top of the global minimum.")
        with c3:
            extra_r = st.number_input("Min runs", 0, 10000, 0, 25, key="scat_minruns",
                                      help="Applied on top of the global minimum.")
        with c4:
            hands = chart_hands("scat", g["hand"])

        min_balls, min_runs = max(g["min_balls"], int(extra_b)), max(g["min_runs"], int(extra_r))
        pool = batter_pool(season, "All", min_balls, min_runs)
        if not pool.empty:
            pool = pool[pool["batting_hand"].isin(hands + ["Unknown"] if hands else [])]
            if not hands:
                pool = pool.iloc[0:0]
        if pool.empty:
            render_head(head, "target", "Elite batter map", "No batters qualify for this map")
            empty_state()
            return

        lg = league_baseline(season)
        sizeref = 2.0 * pool["balls"].max() / (40.0 ** 2)
        top_labels = set(pool.nlargest(10, "runs")["batter"])
        fig = go.Figure()
        xmax = pool["avg"].max() * 1.08
        xmin = max(0, pool["avg"].min() * 0.85)
        ymax = pool["sr"].max() * 1.04
        ymin = pool["sr"].min() * 0.96
        if np.isfinite(lg["avg"]) and np.isfinite(lg["sr"]):
            fig.add_shape(type="rect", x0=lg["avg"], x1=xmax, y0=lg["sr"], y1=ymax, xref="x", yref="y",
                          fillcolor="rgba(34,211,238,.06)", line=dict(color="rgba(34,211,238,.25)", width=1, dash="dot"))
        for hand in HANDS + ["Unknown"]:
            sub = pool[pool["batting_hand"] == hand]
            if sub.empty:
                continue
            fig.add_trace(go.Scatter(
                x=sub["avg"], y=sub["sr"], mode="markers+text", name=hand,
                marker=dict(size=sub["balls"], sizemode="area", sizeref=sizeref, sizemin=5, opacity=0.82,
                            color=HAND_COLORS[hand], line=dict(color="rgba(255,255,255,.55)", width=1)),
                text=[b if b in top_labels else "" for b in sub["batter"]], textposition="top center",
                textfont=dict(size=10, color="#CBD5E1"),
                customdata=np.column_stack([sub["batter"], sub["runs"], sub["balls"], sub["outs"], sub["fours"], sub["sixes"]]),
                hovertemplate="<b>%{customdata[0]}</b><br>Runs: %{customdata[1]:,.0f}<br>Balls: %{customdata[2]:,.0f}<br>"
                              "Dismissals: %{customdata[3]:,.0f}<br>Average: %{x:.2f}<br>Strike rate: %{y:.1f}<br>"
                              "Fours: %{customdata[4]:,.0f} · Sixes: %{customdata[5]:,.0f}<extra></extra>",
            ))
        if np.isfinite(lg["sr"]):
            fig.add_hline(y=lg["sr"], line_dash="dot", line_color=AMBER, annotation_text=f"League SR {lg['sr']:.1f}",
                          annotation_position="bottom right", annotation_font=dict(color=AMBER, size=10))
        if np.isfinite(lg["avg"]):
            fig.add_vline(x=lg["avg"], line_dash="dot", line_color=AMBER, annotation_text=f"League avg {lg['avg']:.1f}",
                          annotation_position="top left", annotation_font=dict(color=AMBER, size=10))
        style_fig(fig, 380)
        fig.update_xaxes(title="Batting average", range=[xmin, xmax])
        fig.update_yaxes(title="Strike rate", range=[ymin, ymax])

        elite = pool[(pool["avg"] > lg["avg"]) & (pool["sr"] > lg["sr"])] if np.isfinite(lg["avg"]) and np.isfinite(lg["sr"]) else pool.iloc[0:0]
        if elite.empty:
            title = "No batter clears both league benchmarks at this sample size"
        else:
            lead = elite.loc[elite["runs"].idxmax()]
            title = f"{len(elite)} batters beat the league on both strike rate and average — led by {lead['batter']}"
        sub = (f"Each bubble is one batter, sized by legal balls · {len(pool)} batters · "
               f"minimum {min_balls} balls and {min_runs} runs · shaded zone = above league on both")
        render_head(head, "target", "Elite batter map", title, sub)
        show_chart(fig, "chart_scatter")


def render_treemap(g):
    with module("tree"):
        head = st.empty()
        c1, c2, c3 = st.columns(3)
        with c1:
            season = chart_season("tree", g["season"])
        with c2:
            metric = st.selectbox("Size metric", ["Runs", "Balls faced", "Sixes"], key="tree_metric")
        with c3:
            extra = st.number_input("Min balls", 0, 5000, 0, 25, key="tree_minballs",
                                    help="Applied on top of the global minimum.")
        min_balls = max(g["min_balls"], int(extra))
        es = entry_stats(season, g["hand"], min_balls, g["min_runs"])
        es = es[es["batting_hand"].isin(HANDS)] if not es.empty else es
        size_col = {"Runs": "runs", "Balls faced": "balls", "Sixes": "sixes"}[metric]
        if not es.empty:
            es = es[es[size_col] > 0]
        if es.empty:
            render_head(head, "grid", "Role map", "No role distribution for these filters")
            empty_state()
            return

        ids, labels, parents, values, colors, texts, custom = [], [], [], [], [], [], []
        for hand, sub in es.groupby("batting_hand"):
            sr_h = sdiv(sub["runs"].sum() * 100, sub["balls"].sum())
            ids.append(hand); labels.append(hand); parents.append("")
            values.append(float(sub[size_col].sum())); colors.append(sr_h)
            texts.append(f"{sub[size_col].sum():,.0f} · SR {fnum(sr_h, 1)}")
            custom.append([int(sub["batters"].sum()), float(sub["balls"].sum()), float(sub["runs"].sum()), sr_h])
            for _, r in sub.iterrows():
                sr_l = sdiv(r["runs"] * 100, r["balls"])
                ids.append(f"{hand}|{r['entry_group']}"); labels.append(f"No. {r['entry_group']}")
                parents.append(hand); values.append(float(r[size_col])); colors.append(sr_l)
                texts.append(f"{r[size_col]:,.0f} · SR {fnum(sr_l, 1)}")
                custom.append([int(r["batters"]), float(r["balls"]), float(r["runs"]), sr_l])
        finite = [c for c in colors if np.isfinite(c)]
        fig = go.Figure(go.Treemap(
            ids=ids, labels=labels, parents=parents, values=values, text=texts, branchvalues="total",
            texttemplate="<b>%{label}</b><br>%{text}", customdata=custom,
            marker=dict(colors=[c if np.isfinite(c) else 0 for c in colors], colorscale=NEON_SCALE,
                        cmin=min(finite) if finite else 0, cmax=max(finite) if finite else 1,
                        line=dict(width=2, color="#061225"),
                        colorbar=dict(title=dict(text="SR", font=dict(color=MUTED)), thickness=10,
                                      outlinewidth=0, tickfont=dict(color=MUTED))),
            tiling=dict(pad=4), textfont=dict(color="#F8FAFC", size=13),
            hovertemplate="<b>%{label}</b><br>" + metric + ": %{value:,.0f}<br>Batters: %{customdata[0]:,.0f}<br>"
                          "Balls: %{customdata[1]:,.0f}<br>Runs: %{customdata[2]:,.0f}<br>"
                          "Strike rate: %{customdata[3]:.1f}<extra></extra>",
        ))
        style_fig(fig, 380, legend=False)

        leaf = es.loc[es[size_col].idxmax()]
        share = leaf[size_col] * 100 / es[size_col].sum()
        mtxt = {"Runs": "runs", "Balls faced": "balls faced", "Sixes": "sixes"}[metric]
        title = f"{short_hand(leaf['batting_hand']).capitalize()} batters at No. {leaf['entry_group']} supply the biggest share of {mtxt} ({share:.0f}%)"
        sub = (f"Size = {metric.lower()} · colour = strike rate · {int(es['batters'].sum()):,} batters across "
               f"{len(es)} role cells · minimum {min_balls} legal balls")
        render_head(head, "grid", "Role map · hand → entry", title, sub)
        show_chart(fig, "chart_treemap")


def render_universe_tab():
    render_universe_header()
    render_ticker()
    with bar_container("global"):
        html('<div class="bar-title">Global filters · define the batter pool</div>')
        f1, f2, f3, f4 = st.columns(4)
        with f1:
            season = st.selectbox("Season", ["All"] + SEASONS, key="g_season")
        with f2:
            hand = st.selectbox("Batting hand", ["All"] + HANDS, key="g_hand")
        with f3:
            min_balls = int(st.number_input("Minimum legal balls", 0, 5000, 250, 25, key="g_min_balls"))
        with f4:
            min_runs = int(st.number_input("Minimum runs", 0, 10000, 250, 25, key="g_min_runs"))
    g = dict(season=season, hand=hand, min_balls=min_balls, min_runs=min_runs)

    pool = batter_pool(season, hand, min_balls, min_runs)
    hp = hand_phase_table(season, hand, min_balls, min_runs)

    k1, k2, k3 = st.columns(3)
    with k1:
        kpi_card("users", "Batters analysed", fnum(len(pool)),
                 f"of {SCALE['batters']:,} in the database · ≥{min_balls} balls · ≥{min_runs} runs", CYAN)
    with k2:
        pr, pb = pool["runs"].sum() if not pool.empty else 0, pool["balls"].sum() if not pool.empty else 0
        kpi_card("target", "Runs in sample", fnum(pr),
                 f"{fnum(pb)} legal balls · pooled SR {fnum(sdiv(pr * 100, pb), 1)}", VIOLET)
    with k3:
        best_txt, best_note = "—", "No qualifying hand/phase combination"
        if not hp.empty:
            hp2 = hp[hp["balls"] > 0].copy()
            if not hp2.empty:
                hp2["sr"] = ratio(hp2["runs"], hp2["balls"], 100)
                b = hp2.loc[hp2["sr"].idxmax()]
                best_txt = f"{esc(short_hand(b['batting_hand']))} · {esc(b['phase'])}"
                best_note = f"Highest strike rate: {b['sr']:.1f} across {fnum(b['balls'])} legal balls"
        kpi_card("bolt", "Best scoring profile", best_txt, best_note, PINK)

    if pool.empty:
        empty_state()
        return

    render_dumbbell(g)
    a, b = st.columns(2)
    with a:
        render_heatmap(g)
    with b:
        render_lollipop(g)
    c, d = st.columns(2)
    with c:
        render_scatter(g)
    with d:
        render_treemap(g)


# ============================================================
# 9. PLAYER LAB TAB
# ============================================================
def render_player_header():
    html("""
    <div class="hero-banner">
        <div class="eyebrow">IPL · Scouting report · Single batter</div>
        <h1>PLAYER LAB</h1>
        <p class="hero-sub">Deconstruct one batter's scoring behaviour, matchups and consistency.</p>
        <div class="reader"><b>Reader</b>For the batting coach, deciding which batter to pick and for which role.</div>
    </div>
    """)


def player_chart_season(key, slug, seasons_p, page_season):
    pick = st.selectbox("Season", ["As selected above"] + seasons_p, key=f"{key}_season_{slug}")
    return page_season if pick == "As selected above" else pick


def render_timeline(batter, pdf_all, seasons_p, slug):
    with module("timeline"):
        head = st.empty()
        c1, c2, c3 = st.columns([1.5, 1, 1.5])
        with c1:
            if len(seasons_p) >= 2:
                lo, hi = st.select_slider("Season range", options=seasons_p,
                                          value=(seasons_p[0], seasons_p[-1]), key=f"tl_range_{slug}")
            else:
                lo = hi = seasons_p[0]
                st.caption(f"Single season on record: {seasons_p[0]}")
        with c2:
            metric = st.selectbox("Metric", ["Runs", "Strike rate", "Balls faced"], key="tl_metric")
        with c3:
            st.caption("The timeline uses its own season range and ignores the page-level season filter.")

        sel = seasons_p[seasons_p.index(lo): seasons_p.index(hi) + 1]
        sub = pdf_all[pdf_all["season"].isin(sel)]
        if sub.empty:
            render_head(head, "chart", "Performance timeline", "No innings in this season range")
            empty_state("No innings recorded in this season range.")
            return
        t = sub.groupby("season", as_index=False).agg(runs=("runs", "sum"), balls=("balls", "sum"))
        t["sr"] = ratio(t["runs"], t["balls"], 100)
        t = t.merge(league_season_table(), on="season", how="left")
        vcol, lcol, unit = {"Runs": ("runs", "lg_runs", "runs"), "Strike rate": ("sr", "lg_sr", "SR"),
                            "Balls faced": ("balls", "lg_balls", "balls")}[metric]
        t = t.dropna(subset=[vcol])
        if t.empty:
            render_head(head, "chart", "Performance timeline", "No data for this metric")
            empty_state()
            return
        dec = 1 if metric == "Strike rate" else 0
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=t["season"], y=t[vcol], mode="lines+markers+text", name=batter, fill="tozeroy",
            fillcolor="rgba(34,211,238,.08)", line=dict(color=CYAN, width=3, shape="spline", smoothing=0.5),
            marker=dict(size=9, color=CYAN, line=dict(color="#061225", width=2)),
            text=[f"{v:,.{dec}f}" for v in t[vcol]], textposition="top center", textfont=dict(size=10, color="#CBD5E1"),
            customdata=np.column_stack([t["balls"], t["runs"], t["sr"]]),
            hovertemplate="<b>%{x}</b><br>" + metric + ": %{y:,.1f}<br>Runs: %{customdata[1]:,.0f}<br>"
                          "Balls: %{customdata[0]:,.0f}<br>SR: %{customdata[2]:.1f}<extra></extra>",
        ))
        lg_t = t.dropna(subset=[lcol])
        if not lg_t.empty:
            fig.add_trace(go.Scatter(
                x=lg_t["season"], y=lg_t[lcol], mode="lines", name="League average (batters with 50+ balls)",
                line=dict(color=AMBER, width=2, dash="dot"),
                hovertemplate="League %{x}: %{y:,.1f}<extra></extra>",
            ))
        peak = t.loc[t[vcol].idxmax()]
        fig.add_trace(go.Scatter(
            x=[peak["season"]], y=[peak[vcol]], mode="markers", showlegend=False, hoverinfo="skip",
            marker=dict(size=19, color="rgba(240,171,252,.20)", line=dict(color=PINK, width=2)),
        ))
        style_fig(fig, 390)
        fig.update_xaxes(type="category", categoryorder="array", categoryarray=list(t["season"]), showgrid=False)
        fig.update_yaxes(title=metric, rangemode="tozero")

        lgv = peak.get(lcol, np.nan)
        pct = (peak[vcol] - lgv) * 100 / lgv if np.isfinite(lgv) and lgv > 0 else np.nan
        if len(t) == 1:
            title = f"{batter} has a single season on record: {peak['season']} with {peak[vcol]:,.{dec}f} {unit}"
        elif np.isfinite(pct):
            title = (f"{batter} peaked in {peak['season']} with {peak[vcol]:,.{dec}f} {unit} — "
                     f"{abs(pct):.0f}% {'above' if pct >= 0 else 'below'} the league average that year")
        else:
            title = f"{batter} peaked in {peak['season']} with {peak[vcol]:,.{dec}f} {unit}"
        sub_txt = f"{metric} per IPL season · {len(t)} seasons · {fnum(t['balls'].sum())} legal balls in range"
        render_head(head, "chart", "Performance timeline", title, sub_txt)
        show_chart(fig, "chart_timeline")


def render_radar(batter, seasons_p, slug, page_season):
    with module("radar"):
        head = st.empty()
        c1, c2 = st.columns(2)
        with c1:
            season = player_chart_season("radar", slug, seasons_p, page_season)
        with c2:
            metric = st.selectbox("Metric", PHASE_METRICS, key="radar_metric")
        ph = filter_season(D().phase, season)
        pp = ph[ph["batter"] == batter].groupby("phase")[["runs", "balls", "dots", "outs"]].sum().reindex(PHASES).fillna(0).reset_index()
        lg = ph.groupby("phase")[["runs", "balls", "dots", "outs"]].sum().reindex(PHASES).fillna(0).reset_index()
        if pp["balls"].sum() == 0:
            render_head(head, "target", "Phase scouting radar", "No phase data for this selection")
            empty_state("No deliveries faced by this batter in the selected season.")
            return
        pv = phase_metric_values(pp, metric)
        lv = phase_metric_values(lg, metric)
        r_p = pv["value"].fillna(0).tolist()
        r_l = lv["value"].fillna(0).tolist()
        theta = PHASES + [PHASES[0]]
        fig = go.Figure()
        fig.add_trace(go.Scatterpolar(
            r=r_l + [r_l[0]], theta=theta, name="League", mode="lines", line=dict(color=AMBER, width=2, dash="dot"),
            hovertemplate="League · %{theta}: %{r:.1f}<extra></extra>",
        ))
        fig.add_trace(go.Scatterpolar(
            r=r_p + [r_p[0]], theta=theta, name=batter, fill="toself", fillcolor="rgba(34,211,238,.20)",
            mode="lines+markers+text", line=dict(color=CYAN, width=3), marker=dict(size=9, color=CYAN),
            text=[fmt_metric(v, metric) for v in r_p] + [""], textposition="top center",
            textfont=dict(color="#E2E8F0", size=12),
            customdata=np.column_stack([list(pp["balls"]) + [pp["balls"].iloc[0]], list(pp["runs"]) + [pp["runs"].iloc[0]]]),
            hovertemplate="<b>" + esc(batter) + "</b> · %{theta}<br>" + metric + ": %{r:.1f}<br>"
                          "Balls: %{customdata[0]:,.0f}<br>Runs: %{customdata[1]:,.0f}<extra></extra>",
        ))
        rmax = max(max(r_p), max(r_l), 1) * 1.22
        style_fig(fig, 360)
        fig.update_layout(polar=dict(
            bgcolor="rgba(0,0,0,0)",
            radialaxis=dict(range=[0, rmax], gridcolor=GRID, linecolor=GRID, tickfont=dict(color=MUTED, size=10), angle=90),
            angularaxis=dict(gridcolor=GRID, linecolor=GRID, tickfont=dict(color="#CBD5E1", size=13)),
        ))
        i = int(np.nanargmax(r_p))
        ph_name = PHASES[i]
        if metric == "Strike rate":
            title = f"{batter} is most dangerous in the {ph_name} phase — {r_p[i]:.1f} SR"
        elif metric == "Run share":
            title = f"{batter} banks the most runs in the {ph_name} phase ({r_p[i]:.0f}% of runs)"
        else:
            title = f"{batter} faces the most dot balls in the {ph_name} phase ({r_p[i]:.0f}%)"
        sub = f"Phase profile vs league · {fnum(pp['balls'].sum())} legal balls · {fnum(pp['runs'].sum())} runs"
        render_head(head, "target", "Phase scouting radar", title, sub)
        show_chart(fig, "chart_radar")


def render_opponents(batter, pdf_all, seasons_p, slug, page_season):
    with module("opp"):
        head = st.empty()
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            season = player_chart_season("opp", slug, seasons_p, page_season)
        with c2:
            mb = int(st.number_input("Min balls", 0, 2000, 50, 10, key=f"opp_minballs_{slug}"))
        with c3:
            top_n = int(st.slider("Top N", 3, 15, 8, key=f"opp_topn_{slug}"))
        with c4:
            metric = st.selectbox("Metric", ["Strike rate", "Runs", "Average"], key="opp_metric")

        sub = filter_season(pdf_all, season)
        grp = sub.groupby("opponent", as_index=False).agg(
            runs=("runs", "sum"), balls=("balls", "sum"), outs=("outs", "sum"), innings=("match_id", "size"))
        grp = grp[grp["balls"] >= max(mb, 1)].copy()
        if grp.empty:
            render_head(head, "pin", "Opponent matchups", f"No opponent reaches {mb}+ legal balls", f"Minimum {mb} legal balls")
            empty_state(f"No opponent reaches {mb} legal balls for this selection. Try lowering the minimum sample size.")
            return
        grp["sr"] = ratio(grp["runs"], grp["balls"], 100)
        grp["avg"] = np.where(grp["outs"] > 0, grp["runs"] / grp["outs"].replace(0, np.nan), grp["runs"])
        col = {"Strike rate": "sr", "Runs": "runs", "Average": "avg"}[metric]
        grp = grp.dropna(subset=[col]).sort_values(col, ascending=False).head(top_n)
        plot_df = grp.sort_values(col, ascending=True)

        lg = league_baseline(season)
        if metric == "Strike rate":
            ref, ref_txt = lg["sr"], f"League SR {lg['sr']:.1f}"
        elif metric == "Average":
            ref, ref_txt = lg["avg"], f"League avg {lg['avg']:.1f}"
        else:
            ref, ref_txt = float(grp["runs"].mean()), f"Mean of shown {grp['runs'].mean():,.0f}"
        dec = 0 if metric == "Runs" else 1
        fig = go.Figure(go.Bar(
            x=plot_df[col], y=plot_df["opponent"], orientation="h",
            marker=dict(color=plot_df[col], colorscale=NEON_SCALE, line=dict(color="rgba(255,255,255,.25)", width=1)),
            text=[f"{v:,.{dec}f} · {int(b):,}b" for v, b in zip(plot_df[col], plot_df["balls"])],
            textposition="outside", textfont=dict(color="#CBD5E1", size=11), cliponaxis=False,
            customdata=np.column_stack([plot_df["balls"], plot_df["runs"], plot_df["outs"], plot_df["sr"], plot_df["avg"], plot_df["innings"]]),
            hovertemplate="<b>%{y}</b><br>Runs: %{customdata[1]:,.0f}<br>Balls: %{customdata[0]:,.0f}<br>"
                          "Dismissals: %{customdata[2]:,.0f}<br>SR: %{customdata[3]:.1f}<br>Average: %{customdata[4]:.1f}<br>"
                          "Innings: %{customdata[5]:,.0f}<extra></extra>",
        ))
        if ref is not None and np.isfinite(ref):
            fig.add_vline(x=ref, line_dash="dot", line_color=AMBER, annotation_text=ref_txt,
                          annotation_position="top", annotation_font=dict(color=AMBER, size=10))
        style_fig(fig, 380, legend=False)
        xmax = max(plot_df[col].max(), ref if ref is not None and np.isfinite(ref) else 0) * 1.32
        fig.update_xaxes(range=[0, xmax], title=metric)
        fig.update_yaxes(showgrid=False)

        top = grp.iloc[0]
        verb = {"Strike rate": "accelerates fastest against", "Runs": "scores most heavily against",
                "Average": "averages best against"}[metric]
        title = f"{batter} {verb} {top['opponent']} ({top[col]:,.{dec}f}) — {mb}+ balls"
        sub_txt = f"Ranked by {metric.lower()} · minimum {mb} legal balls · {len(grp)} opponents shown · labels show metric · balls faced"
        render_head(head, "pin", "Opponent matchups", title, sub_txt)
        show_chart(fig, "chart_opponents")


def render_venues(batter, pdf_all, seasons_p, slug, page_season):
    with module("venue"):
        head = st.empty()
        c1, c2, c3 = st.columns(3)
        with c1:
            season = player_chart_season("ven", slug, seasons_p, page_season)
        with c2:
            top_n = int(st.slider("Top N", 3, 15, 8, key=f"ven_topn_{slug}"))
        with c3:
            mb = int(st.number_input("Min balls", 0, 2000, 50, 10, key=f"ven_minballs_{slug}"))

        sub = filter_season(pdf_all, season)
        grp = sub.groupby("venue", as_index=False).agg(
            runs=("runs", "sum"), balls=("balls", "sum"), outs=("outs", "sum"), innings=("match_id", "size"))
        grp = grp[grp["balls"] >= max(mb, 1)].copy()
        if grp.empty:
            render_head(head, "pin", "Venue performance", f"No venue reaches {mb}+ legal balls", f"Minimum {mb} legal balls")
            empty_state(f"No venue reaches {mb} legal balls for this selection. Try lowering the minimum sample size.")
            return
        grp["sr"] = ratio(grp["runs"], grp["balls"], 100)
        grp = grp.dropna(subset=["sr"]).sort_values("runs", ascending=False).head(top_n)
        grp["short"] = grp["venue"].map(short_venue)
        colors = [PALETTE[i % len(PALETTE)] for i in range(len(grp))]
        sizeref = 2.0 * grp["balls"].max() / (46.0 ** 2)
        fig = go.Figure(go.Scatter(
            x=grp["runs"], y=grp["sr"], mode="markers+text", text=grp["short"], textposition="top center",
            textfont=dict(size=10, color="#CBD5E1"),
            marker=dict(size=grp["balls"], sizemode="area", sizeref=sizeref, sizemin=9, color=colors, opacity=0.85,
                        line=dict(color="rgba(255,255,255,.5)", width=1)),
            customdata=np.column_stack([grp["venue"], grp["balls"], grp["innings"], grp["outs"]]),
            hovertemplate="<b>%{customdata[0]}</b><br>Runs: %{x:,.0f}<br>Strike rate: %{y:.1f}<br>"
                          "Balls: %{customdata[1]:,.0f}<br>Innings: %{customdata[2]:,.0f}<br>"
                          "Dismissals: %{customdata[3]:,.0f}<extra></extra>",
        ))
        overall_sr = sdiv(sub["runs"].sum() * 100, sub["balls"].sum())
        if np.isfinite(overall_sr):
            fig.add_hline(y=overall_sr, line_dash="dot", line_color=AMBER, annotation_text=f"{batter} overall {overall_sr:.1f} SR",
                          annotation_position="bottom right", annotation_font=dict(color=AMBER, size=10))
        style_fig(fig, 380, legend=False)
        xr = pad_range(list(grp["runs"]), 0.22)
        yr = pad_range(list(grp["sr"]) + ([overall_sr] if np.isfinite(overall_sr) else []), 0.25)
        fig.update_xaxes(title="Runs at venue", range=xr)
        fig.update_yaxes(title="Strike rate", range=yr)

        best = grp.iloc[0]
        title = f"{short_venue(best['venue'])} is {batter}'s most productive venue — {best['runs']:,.0f} runs at {best['sr']:.1f} SR"
        sub_txt = (f"Bubble size = legal balls · venue comparison — minimum {mb} legal balls · "
                   f"{len(grp)} venues shown · {fnum(grp['balls'].sum())} balls")
        render_head(head, "pin", "Venue performance", title, sub_txt)
        show_chart(fig, "chart_venues")


def render_dismissals(batter, seasons_p, slug, page_season):
    with module("dismiss"):
        head = st.empty()
        dis_all = D().dis
        dis_all = dis_all[dis_all["batter"] == batter]
        all_kinds = sorted(dis_all["kind"].unique().tolist())
        c1, c2 = st.columns(2)
        with c1:
            season = player_chart_season("dis", slug, seasons_p, page_season)
        with c2:
            kinds = st.multiselect("Dismissal type", all_kinds, default=all_kinds, key=f"dis_kinds_{slug}")
        sub = filter_season(dis_all, season)
        sub = sub[sub["kind"].isin(kinds)]
        grp = sub.groupby("kind", as_index=False)["n"].sum().sort_values("n", ascending=False)
        grp = grp[grp["n"] > 0]
        if grp.empty:
            render_head(head, "shield", "Dismissal profile", "No dismissals recorded for this selection")
            empty_state("No dismissals recorded for this selection (the batter may have been not out, or the type filter is empty).")
            return
        total = int(grp["n"].sum())
        grp["pct"] = grp["n"] * 100 / total
        fig = go.Figure(go.Pie(
            labels=grp["kind"], values=grp["n"], hole=0.62, sort=False,
            marker=dict(colors=[PALETTE[i % len(PALETTE)] for i in range(len(grp))], line=dict(color="#061225", width=3)),
            textinfo="label+percent", textfont=dict(color="#F8FAFC", size=12),
            pull=[0.05 if i == 0 else 0 for i in range(len(grp))],
            hovertemplate="<b>%{label}</b><br>Count: %{value}<br>Share: %{percent}<extra></extra>",
        ))
        fig.add_annotation(text=f"<b>{total}</b><br><span style='font-size:11px;color:#7F97B0'>dismissals</span>",
                           x=0.5, y=0.5, xref="paper", yref="paper", showarrow=False, font=dict(size=26, color="#F8FAFC"))
        style_fig(fig, 340, legend=False)
        top = grp.iloc[0]
        title = f"{batter} falls most often to {top['kind']} — {top['pct']:.0f}% of dismissals"
        sub_txt = f"Dismissal mix for the selected types · {total} dismissals · percentages are shares of the filtered total"
        render_head(head, "shield", "Dismissal profile", title, sub_txt)
        show_chart(fig, "chart_dismissals")
        insight_card("Insight", f"Most common dismissal: <b>{esc(top['kind'])}</b> — {top['pct']:.1f}% ({int(top['n'])} of {total}).")


def render_player_lab():
    render_player_header()
    default_idx = DATA.batters.index(DATA.top_batter) if DATA.top_batter in DATA.batters else 0
    with bar_container("player"):
        html('<div class="bar-title">Player selector</div>')
        p1, p2, p3 = st.columns([2.4, 1, 1])
        with p1:
            batter = st.selectbox("Search / select batter", DATA.batters, index=default_idx, key="pl_batter")
        slug = re.sub(r"\W+", "_", str(batter))
        pdf_all = DATA.inn[DATA.inn["batter"] == batter]
        seasons_p = sorted(pdf_all["season"].unique().tolist())
        with p2:
            page_season = st.selectbox("Season", ["All"] + seasons_p, key=f"pl_season_{slug}")
        with p3:
            min_balls = int(st.number_input("Minimum balls", 0, 5000, 50, 25, key="pl_min_balls"))

    pdf = filter_season(pdf_all, page_season)
    runs, balls, outs = pdf["runs"].sum(), pdf["balls"].sum(), pdf["outs"].sum()
    if balls < min_balls or balls <= 0:
        st.warning(f"{batter} has {fnum(balls)} legal balls in this selection, below the {min_balls}-ball minimum. "
                   "Try lowering the minimum sample size or choosing another season.")
        return
    sr = sdiv(runs * 100, balls)
    avg = runs / outs if outs > 0 else runs
    season_txt = "all seasons" if page_season == "All" else f"season {page_season}"

    k1, k2, k3 = st.columns(3)
    with k1:
        kpi_card("target", "Runs + balls", f"{fnum(runs)} <span style='font-size:16px;color:#7F97B0'>off {fnum(balls)}</span>",
                 f"{esc(batter)} · {season_txt} · {len(pdf)} innings", CYAN)
    with k2:
        kpi_card("bolt", "Strike rate", fnum(sr, 2), f"Sample size: {fnum(balls)} legal balls", VIOLET)
    with k3:
        note = (f"{fnum(outs)} dismissals" if outs > 0
                else "No dismissals — average shown equals runs scored")
        kpi_card("shield", "Batting average", fnum(avg, 2), note, PINK)

    render_timeline(batter, pdf_all, seasons_p, slug)
    a, b = st.columns(2)
    with a:
        render_radar(batter, seasons_p, slug, page_season)
    with b:
        render_opponents(batter, pdf_all, seasons_p, slug, page_season)
    c, d = st.columns(2)
    with c:
        render_venues(batter, pdf_all, seasons_p, slug, page_season)
    with d:
        render_dismissals(batter, seasons_p, slug, page_season)


# ============================================================
# TABS
# ============================================================
tab_universe, tab_player = st.tabs(["◈  BATTER UNIVERSE", "◉  PLAYER LAB"])
with tab_universe:
    render_universe_tab()
with tab_player:
    render_player_lab()


# ============================================================
# 10. FOOTER
# ============================================================
updated = datetime.fromtimestamp(DB_MTIME).strftime("%d %b %Y, %H:%M")
latest = f" · latest match in data <b>{esc(DATA.latest_date)}</b>" if DATA.latest_date else ""
html(f"""
<div class="footer-strip">
    <span class="footer-tag">Last updated / dataset scale</span>
    <span>Database file updated <b>{updated}</b>{latest}</span>
    <span><b>{SCALE['matches']:,}</b> matches</span>
    <span><b>{SCALE['balls']:,}</b> legal balls</span>
    <span><b>{SCALE['batters']:,}</b> batters</span>
    <span><b>{SCALE['runs']:,}</b> batter runs</span>
    <span>Source: <b>{esc(DB_PATH.name)}</b></span>
</div>
""")