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
        # Extra space keeps Plotly axis titles and tick labels visible on every chart.
        margin=dict(l=58, r=22, t=42, b=58),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, sans-serif", color="#BFD0E3", size=12),
        showlegend=legend,
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color="#AFC1D4"), orientation="h",
                    yanchor="bottom", y=1.02, xanchor="right", x=1),
        hoverlabel=dict(bgcolor="#0B1B31", bordercolor=CYAN, font=dict(color="#F8FAFC", family="Inter, sans-serif")),
    )
    fig.update_xaxes(
        gridcolor=GRID, zeroline=False, linecolor=GRID,
        tickfont=dict(color=MUTED, size=11),
        title_font=dict(color="#DCE8F5", size=12),
        title_standoff=12,
        automargin=True,
    )
    fig.update_yaxes(
        gridcolor=GRID, zeroline=False, linecolor=GRID,
        tickfont=dict(color=MUTED, size=11),
        title_font=dict(color="#DCE8F5", size=12),
        title_standoff=12,
        automargin=True,
    )
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


def readable_axis_label(metric):
    """Turn technical metric names into reader-friendly chart axis labels."""
    return {
        "Strike rate": "Strike rate (runs per 100 balls)",
        "Batting average": "Batting average (runs per dismissal)",
        "Run share": "Run share (%)",
        "Dot-ball %": "Dot balls (%)",
        "Runs": "Total runs",
        "Balls faced": "Legal balls faced",
        "Sixes": "Sixes",
        "Average": "Batting average (runs per dismissal)",
    }.get(metric, str(metric))


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
HERO_CHARTS = ["Comparison Bars", "Trend Line", "Dot Plot", "Slope Chart"]
HAND_FILLS = {"Left hand Bat": "rgba(167,139,250,.22)", "Right hand Bat": "rgba(34,211,238,.20)"}
DONUT_SHADES = {"Left hand Bat": ["#C4B5FD", "#8B5CF6", "#6D28D9"], "Right hand Bat": ["#67E8F9", "#22D3EE", "#0E7490"]}


def hero_alt_figure(chart, metric, look):
    """Simple presentation charts for the batting-hand comparison."""
    key = HERO_METRICS[metric]
    dec = 0 if key == "runs" else 1
    phases = PHASES
    def val(phase, hand):
        return look.get((phase, hand), {}).get(key, np.nan)
    def label(v):
        return f"{v:,.{dec}f}" if np.isfinite(v) else ""

    fig = go.Figure()
    if chart == "Comparison Bars":
        for hand in HANDS:
            vals = [val(p, hand) for p in phases]
            fig.add_trace(go.Bar(x=phases, y=vals, name=short_hand(hand), marker_color=HAND_COLORS[hand],
                                 text=[label(v) for v in vals], textposition="outside", cliponaxis=False))
        fig.update_layout(barmode="group")
        fig.update_xaxes(title="Match phase")
        fig.update_yaxes(title=readable_axis_label(metric), rangemode="tozero")
    elif chart == "Trend Line":
        for hand in HANDS:
            vals = [val(p, hand) for p in phases]
            fig.add_trace(go.Scatter(x=phases, y=vals, mode="lines+markers+text", name=short_hand(hand),
                                     line=dict(color=HAND_COLORS[hand], width=4),
                                     marker=dict(size=11, color=HAND_COLORS[hand]),
                                     text=[label(v) for v in vals], textposition="top center"))
        fig.update_xaxes(title="Match phase")
        fig.update_yaxes(title=readable_axis_label(metric), rangemode="tozero")
    elif chart == "Dot Plot":
        for hand, offset in zip(HANDS, [-0.14, 0.14]):
            vals = [val(p, hand) for p in phases]
            y = np.arange(len(phases)) + offset
            fig.add_trace(go.Scatter(x=vals, y=y, mode="markers+text", name=short_hand(hand),
                                     marker=dict(size=17, color=HAND_COLORS[hand]),
                                     text=[label(v) for v in vals], textposition="middle right"))
        fig.update_yaxes(tickmode="array", tickvals=np.arange(len(phases)), ticktext=phases, title="Match phase")
        fig.update_xaxes(title=readable_axis_label(metric), rangemode="tozero")
    else:  # Slope Chart
        x=[0,1]
        for hand in HANDS:
            overall=look.get(("Overall", hand), {}).get(key, np.nan)
            death=look.get(("Death", hand), {}).get(key, np.nan)
            vals=[overall, death]
            fig.add_trace(go.Scatter(x=x, y=vals, mode="lines+markers+text", name=short_hand(hand),
                                     line=dict(color=HAND_COLORS[hand], width=4), marker=dict(size=13, color=HAND_COLORS[hand]),
                                     text=[label(v) for v in vals], textposition="middle right"))
        fig.update_xaxes(tickmode="array", tickvals=[0,1], ticktext=["Overall", "Death phase"], title="Comparison")
        fig.update_yaxes(title=readable_axis_label(metric), rangemode="tozero")
    style_fig(fig, 390, legend=True)
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
        c1, c2, c3 = st.columns([1, 1, 1.3])
        with c1:
            season = chart_season("hero", g["season"])
        with c2:
            extra = st.number_input("Extra minimum balls", 0, 5000, 0, 25, key="hero_minballs")
        with c3:
            hero_metric = st.selectbox("What should we compare?", list(HERO_METRICS.keys()), key="hero_metric")
        hero_chart = st.radio("Choose a simple visual", HERO_CHARTS, horizontal=True, key="hero_chart_pick")
        st.caption("Question answered: do left-hand and right-hand batters score differently across the match phases?")

        min_balls = max(g["min_balls"], int(extra)); min_runs = g["min_runs"]
        pool = batter_pool(season, "All", min_balls, min_runs)
        pool = pool[pool["batting_hand"].isin(HANDS)]
        if pool.empty or pool["batting_hand"].nunique() < 2:
            render_head(head, "bolt", "1 · Which batting hand scores better?", "Not enough batters on both sides to compare")
            empty_state(); return
        overall = pool.groupby("batting_hand").agg(runs=("runs","sum"), balls=("balls","sum"), outs=("outs","sum"), batters=("batter","nunique"))
        ptbl = hand_phase_table(season, "All", min_balls, min_runs)
        ptbl = ptbl[ptbl["batting_hand"].isin(HANDS) & ptbl["phase"].isin(PHASES)]
        look={}
        for hand in HANDS:
            if hand in overall.index:
                o=overall.loc[hand]; look[("Overall",hand)] = dict(runs=o["runs"],balls=o["balls"],outs=o["outs"],batters=o["batters"])
        for _,r in ptbl.iterrows(): look[(r["phase"],r["batting_hand"])] = dict(runs=r["runs"],balls=r["balls"],outs=r["outs"],batters=r["batters"])
        for v in look.values(): v["sr"]=sdiv(v["runs"]*100,v["balls"]); v["avg"]=sdiv(v["runs"],v["outs"])
        base=league_baseline(season); render_hud(look,base)
        fig=hero_alt_figure(hero_chart,hero_metric,look)
        ol=look.get(("Overall",HANDS[0]),{}); or_=look.get(("Overall",HANDS[1]),{})
        lv=ol.get(HERO_METRICS[hero_metric],np.nan); rv=or_.get(HERO_METRICS[hero_metric],np.nan)
        if np.isfinite(lv) and np.isfinite(rv):
            winner=short_hand(HANDS[0]) if lv>rv else short_hand(HANDS[1]); gap=abs(lv-rv)
            title=f"{winner} leads by {gap:.1f} {hero_metric.lower()} points overall" if hero_metric!="Runs" else f"{winner} scores {gap:,.0f} more runs in the sample"
        else: title="Left-hand and right-hand batters compared across the IPL"
        sub=f"{hero_chart} · {hero_metric} · {int(ol.get('batters',0))} left-hand vs {int(or_.get('batters',0))} right-hand batters"
        render_head(head,"bolt","1 · Which batting hand scores better?",title,sub)
        show_chart(fig,"chart_hero_alt")
        render_hero_insight(hand_test(pool))


def render_heatmap(g):
    with module("heat"):
        head=st.empty(); c1,c2,c3=st.columns(3)
        with c1: season=chart_season("heat",g["season"])
        with c2: hands=chart_hands("heat",g["hand"])
        with c3: metric=st.selectbox("Measure",PHASE_METRICS,key="heat_metric")
        tbl=hand_phase_table(season,"All",g["min_balls"],g["min_runs"])
        if not tbl.empty: tbl=tbl[tbl["batting_hand"].isin(hands)&tbl["phase"].isin(PHASES)]
        if tbl.empty: render_head(head,"grid","2 · When do batters score best?","No phase data for these filters"); empty_state(); return
        vals=phase_metric_values(tbl,metric,group="batting_hand").dropna(subset=["value"])
        fig=go.Figure()
        for hand in HANDS:
            sub=vals[vals["batting_hand"]==hand].set_index("phase").reindex(PHASES).reset_index()
            if sub["value"].notna().any():
                fig.add_trace(go.Bar(x=sub["phase"],y=sub["value"],name=short_hand(hand),marker_color=HAND_COLORS[hand],text=[fmt_metric(v,metric) if pd.notna(v) else "" for v in sub["value"]],textposition="outside",cliponaxis=False))
        style_fig(fig,360,legend=True); fig.update_layout(barmode="group")
        fig.update_xaxes(title="Match phase"); fig.update_yaxes(title=readable_axis_label(metric),rangemode="tozero")
        best=vals.loc[vals["value"].idxmax()]
        render_head(head,"grid","2 · When do batters score best?",f"{best['phase']} is the strongest phase at {fmt_metric(best['value'],metric)}",f"Direct comparison of Powerplay, Middle and Death · Measure: {metric}")
        show_chart(fig,"chart_heatmap")


def render_lollipop(g):
    with module("lolli"):
        head=st.empty(); c1,c2,c3=st.columns(3)
        with c1: season=chart_season("lolli",g["season"])
        with c2: metric=st.selectbox("Measure",["Runs","Sixes","Strike rate"],key="lolli_metric")
        with c3: extra=st.number_input("Extra minimum balls",0,5000,0,25,key="lolli_minballs")
        min_balls=max(g["min_balls"],int(extra)); es=entry_stats(season,g["hand"],min_balls,g["min_runs"])
        if es.empty: render_head(head,"pulse","3 · Does batting position matter?","No entry-position data for these filters"); empty_state(); return
        grp=es.groupby("entry_group").agg(runs=("runs","sum"),balls=("balls","sum"),sixes=("sixes","sum"),innings=("innings","sum"),batters=("batters","sum")).reindex(ENTRY_ORDER).fillna(0).reset_index(); grp["sr"]=ratio(grp["runs"],grp["balls"],100)
        col={"Runs":"runs","Sixes":"sixes","Strike rate":"sr"}[metric]; plot=grp.dropna(subset=[col]).sort_values(col,ascending=True)
        fig=go.Figure()
        fig.add_trace(go.Scatter(x=plot[col],y=[f"No. {x}" for x in plot["entry_group"]],mode="markers+text",name=metric,marker=dict(size=18,color=[PINK if v==plot[col].max() else CYAN for v in plot[col]]),text=[f"{v:.1f}" if metric=="Strike rate" else f"{v:,.0f}" for v in plot[col]],textposition="middle right",cliponaxis=False,customdata=np.column_stack([plot["runs"],plot["sixes"],plot["sr"],plot["innings"]]),hovertemplate="<b>%{y}</b><br>"+esc(metric)+": %{x}<br>Runs: %{customdata[0]:,.0f}<br>Sixes: %{customdata[1]:,.0f}<br>Strike rate: %{customdata[2]:.1f}<br>Batter-innings: %{customdata[3]:,.0f}<extra></extra>"))
        style_fig(fig,350,legend=False); fig.update_xaxes(title=readable_axis_label(metric),rangemode="tozero"); fig.update_yaxes(title="Batting entry position",showgrid=False)
        best=grp.loc[grp[col].idxmax()]; render_head(head,"pulse","3 · Does batting position matter?",f"No. {best['entry_group']} has the highest {metric.lower()}",f"No. 1 = opener · compare how batting output changes by entry position")
        show_chart(fig,"chart_lollipop")


def render_scatter(g):
    with module("scatter"):
        head=st.empty(); c1,c2,c3,c4=st.columns(4)
        with c1: season=chart_season("scat",g["season"])
        with c2: extra_b=st.number_input("Extra minimum balls",0,5000,0,25,key="scat_minballs")
        with c3: extra_r=st.number_input("Extra minimum runs",0,10000,0,25,key="scat_minruns")
        with c4: hands=chart_hands("scat",g["hand"])
        min_balls=max(g["min_balls"],int(extra_b)); min_runs=max(g["min_runs"],int(extra_r)); pool=batter_pool(season,"All",min_balls,min_runs)
        if not pool.empty: pool=pool[pool["batting_hand"].isin(hands+["Unknown"] if hands else [])]
        if pool.empty: render_head(head,"target","4 · Which batters are both fast and consistent?","No batters qualify for this sample"); empty_state(); return
        lg=league_baseline(season); fig=go.Figure()
        sizeref=2*pool["balls"].max()/(34**2); labels=set(pool.nlargest(8,"runs")["batter"])
        for hand in HANDS+["Unknown"]:
            sub=pool[pool["batting_hand"]==hand]
            if sub.empty: continue
            fig.add_trace(go.Scatter(x=sub["avg"],y=sub["sr"],mode="markers+text",name=short_hand(hand),marker=dict(size=sub["balls"],sizemode="area",sizeref=sizeref,sizemin=6,opacity=.82,color=HAND_COLORS[hand],line=dict(color="#fff",width=1)),text=[b if b in labels else "" for b in sub["batter"]],textposition="top center",customdata=np.column_stack([sub["batter"],sub["runs"],sub["balls"]]),hovertemplate="<b>%{customdata[0]}</b><br>Average: %{x:.1f}<br>Strike rate: %{y:.1f}<br>Runs: %{customdata[1]:,.0f}<br>Legal balls: %{customdata[2]:,.0f}<extra></extra>"))
        if np.isfinite(lg["avg"]): fig.add_vline(x=lg["avg"],line_dash="dot",line_color=AMBER,annotation_text=f"League average {lg['avg']:.1f}",annotation_position="top left")
        if np.isfinite(lg["sr"]): fig.add_hline(y=lg["sr"],line_dash="dot",line_color=AMBER,annotation_text=f"League SR {lg['sr']:.1f}",annotation_position="bottom right")
        style_fig(fig,390,legend=True); fig.update_xaxes(title="Batting average (runs per dismissal)"); fig.update_yaxes(title="Strike rate (runs per 100 balls)")
        elite=pool[(pool["avg"]>lg["avg"])&(pool["sr"]>lg["sr"])] if np.isfinite(lg["avg"]) and np.isfinite(lg["sr"]) else pool.iloc[0:0]
        lead=elite.loc[elite["runs"].idxmax()] if not elite.empty else None
        title=f"{len(elite)} batters beat both league benchmarks"+(f" — {lead['batter']} leads them" if lead is not None else "")
        render_head(head,"target","4 · Which batters are both fast and consistent?",title,"Each bubble is one batter · bigger bubble = more legal balls · upper-right = stronger overall profile")
        show_chart(fig,"chart_scatter")


def render_treemap(g):
    with module("tree"):
        head=st.empty(); c1,c2,c3=st.columns(3)
        with c1: season=chart_season("tree",g["season"])
        with c2: metric=st.selectbox("What should we rank?",["Runs","Balls faced","Sixes"],key="tree_metric")
        with c3: extra=st.number_input("Extra minimum balls",0,5000,0,25,key="tree_minballs")
        min_balls=max(g["min_balls"],int(extra)); es=entry_stats(season,g["hand"],min_balls,g["min_runs"])
        if es.empty: render_head(head,"grid","5 · Which batting roles produce the most?","No role data for these filters"); empty_state(); return
        size={"Runs":"runs","Balls faced":"balls","Sixes":"sixes"}[metric]; grp=es.groupby(["batting_hand","entry_group"],as_index=False).agg(value=(size,"sum"),runs=("runs","sum"),balls=("balls","sum"),batters=("batters","sum")); grp["role"]=grp.apply(lambda r:f"{short_hand(r['batting_hand'])} · No. {r['entry_group']}",axis=1); plot=grp.nlargest(8,"value").sort_values("value")
        fig=go.Figure(go.Bar(x=plot["value"],y=plot["role"],orientation="h",marker_color=[HAND_COLORS.get(h,CYAN) for h in plot["batting_hand"]],text=[f"{v:,.0f}" for v in plot["value"]],textposition="outside",cliponaxis=False,customdata=np.column_stack([plot["runs"],plot["balls"],plot["batters"]]),hovertemplate="<b>%{y}</b><br>"+esc(metric)+": %{x:,.0f}<br>Runs: %{customdata[0]:,.0f}<br>Legal balls: %{customdata[1]:,.0f}<br>Batters: %{customdata[2]:,.0f}<extra></extra>"))
        style_fig(fig,370,legend=False); fig.update_xaxes(title=readable_axis_label(metric),rangemode="tozero"); fig.update_yaxes(title="Batting role (hand + entry)",showgrid=False)
        best=grp.loc[grp["value"].idxmax()]; render_head(head,"grid","5 · Which batting roles produce the most?",f"{best['role']} leads in {metric.lower()}","Top 8 combinations of batting hand and entry position · longer bar = larger contribution")
        show_chart(fig,"chart_treemap")



def render_top_runs(g):
    with module("topruns"):
        head=st.empty(); c1,c2=st.columns([1,1])
        with c1: season=chart_season("topruns",g["season"])
        with c2: top_n=int(st.slider("How many batters",5,15,10,key="topruns_n"))
        pool=batter_pool(season,g["hand"],g["min_balls"],g["min_runs"])
        if pool.empty: render_head(head,"chart","1 · Who scores the most runs?","No qualifying batters"); empty_state(); return
        plot=pool.nlargest(top_n,"runs").sort_values("runs")
        fig=go.Figure(go.Bar(x=plot["runs"],y=plot["batter"],orientation="h",marker_color=CYAN,text=[f"{v:,.0f}" for v in plot["runs"]],textposition="outside",cliponaxis=False,customdata=np.column_stack([plot["sr"],plot["balls"],plot["innings"]]),hovertemplate="<b>%{y}</b><br>Total runs: %{x:,.0f}<br>Strike rate: %{customdata[0]:.1f}<br>Legal balls: %{customdata[1]:,.0f}<br>Innings: %{customdata[2]:,.0f}<extra></extra>"))
        style_fig(fig,390,False); fig.update_xaxes(title="Total runs scored",rangemode="tozero"); fig.update_yaxes(title="Batter",showgrid=False)
        best=pool.loc[pool["runs"].idxmax()]
        render_head(head,"chart","1 · Who scores the most runs?",f"{best['batter']} leads the selected batter pool",f"Top {top_n} batters by total runs · each bar represents one batter")
        show_chart(fig,"chart_top_runs")


def render_top_strike_rate(g):
    with module("topsr"):
        head=st.empty(); c1,c2=st.columns([1,1])
        with c1: season=chart_season("topsr",g["season"])
        with c2: top_n=int(st.slider("How many batters",5,15,10,key="topsr_n"))
        pool=batter_pool(season,g["hand"],g["min_balls"],g["min_runs"])
        if pool.empty: render_head(head,"pulse","2 · Who scores fastest?","No qualifying batters"); empty_state(); return
        plot=pool.nlargest(top_n,"sr").sort_values("sr")
        fig=go.Figure(go.Scatter(x=plot["sr"],y=plot["batter"],mode="markers+text",marker=dict(size=17,color=VIOLET,line=dict(color="#fff",width=1)),text=[f"{v:.1f}" for v in plot["sr"]],textposition="middle right",cliponaxis=False,customdata=np.column_stack([plot["runs"],plot["balls"],plot["avg"]]),hovertemplate="<b>%{y}</b><br>Strike rate: %{x:.1f}<br>Runs: %{customdata[0]:,.0f}<br>Legal balls: %{customdata[1]:,.0f}<br>Average: %{customdata[2]:.1f}<extra></extra>"))
        style_fig(fig,390,False); fig.update_xaxes(title="Strike rate (runs per 100 balls)",rangemode="tozero"); fig.update_yaxes(title="Batter",showgrid=False)
        best=pool.loc[pool["sr"].idxmax()]
        render_head(head,"pulse","2 · Who scores fastest?",f"{best['batter']} has the highest strike rate in this pool",f"Top {top_n} qualifying batters · minimum {g['min_balls']} legal balls and {g['min_runs']} runs")
        show_chart(fig,"chart_top_sr")


def render_consistency_map(g):
    with module("consistency"):
        head=st.empty(); c1,c2=st.columns(2)
        with c1: season=chart_season("consistency",g["season"])
        with c2: hands=chart_hands("consistency",g["hand"])
        pool=batter_pool(season,"All",g["min_balls"],g["min_runs"])
        if hands: pool=pool[pool["batting_hand"].isin(hands)]
        if pool.empty: render_head(head,"target","3 · Who is both consistent and aggressive?","No qualifying batters"); empty_state(); return
        lg=league_baseline(season); fig=go.Figure()
        for hand in HANDS+["Unknown"]:
            sub=pool[pool["batting_hand"]==hand]
            if sub.empty: continue
            sizeref=max(1,2*sub["balls"].max()/(28**2)); labels=set(sub.nlargest(6,"runs")["batter"])
            fig.add_trace(go.Scatter(x=sub["avg"],y=sub["sr"],mode="markers+text",name=short_hand(hand),marker=dict(size=sub["balls"],sizemode="area",sizeref=sizeref,sizemin=6,opacity=.82,color=HAND_COLORS.get(hand,MUTED),line=dict(color="#fff",width=1)),text=[n if n in labels else "" for n in sub["batter"]],textposition="top center",customdata=np.column_stack([sub["runs"],sub["balls"]]),hovertemplate="<b>%{text}</b><br>Average: %{x:.1f}<br>Strike rate: %{y:.1f}<br>Runs: %{customdata[0]:,.0f}<br>Legal balls: %{customdata[1]:,.0f}<extra></extra>"))
        if np.isfinite(lg["avg"]): fig.add_vline(x=lg["avg"],line_dash="dot",line_color=AMBER,annotation_text=f"League average {lg['avg']:.1f}",annotation_position="top left")
        if np.isfinite(lg["sr"]): fig.add_hline(y=lg["sr"],line_dash="dot",line_color=AMBER,annotation_text=f"League SR {lg['sr']:.1f}",annotation_position="bottom right")
        style_fig(fig,430,True); fig.update_xaxes(title="Batting average (runs per dismissal)"); fig.update_yaxes(title="Strike rate (runs per 100 balls)")
        elite=pool[(pool["avg"]>=lg["avg"])&(pool["sr"]>=lg["sr"])] if np.isfinite(lg["avg"]) and np.isfinite(lg["sr"]) else pool.iloc[0:0]
        render_head(head,"target","3 · Who is both consistent and aggressive?",f"{len(elite)} batters are at or above both league benchmarks","Each bubble is one batter · bigger bubble = more legal balls · upper-right is the strongest zone")
        show_chart(fig,"chart_consistency")


def render_phase_overview(g):
    with module("phaseall"):
        head=st.empty(); c1,c2=st.columns(2)
        with c1: season=chart_season("phaseall",g["season"])
        with c2: metric=st.selectbox("What should we compare?",["Strike rate","Runs","Dot-ball %"],key="phaseall_metric")
        pool=batter_pool(season,g["hand"],g["min_balls"],g["min_runs"])
        if pool.empty: render_head(head,"grid","4 · When do IPL batters score best?","No qualifying batters"); empty_state(); return
        ph=filter_season(DATA.phase,season); ph=ph[ph["batter"].isin(pool["batter"])]
        agg=ph.groupby("phase",as_index=False).agg(runs=("runs","sum"),balls=("balls","sum"),dots=("dots","sum")); vals=phase_metric_values(agg,metric); vals["phase"]=pd.Categorical(vals["phase"],PHASES,ordered=True); vals=vals.sort_values("phase")
        fig=go.Figure(go.Bar(x=vals["phase"].astype(str),y=vals["value"],marker_color=[VIOLET,CYAN,PINK],text=[fmt_metric(v,metric) for v in vals["value"]],textposition="outside",cliponaxis=False))
        style_fig(fig,370,False); fig.update_xaxes(title="Match phase"); fig.update_yaxes(title=readable_axis_label(metric),rangemode="tozero")
        best=vals.loc[vals["value"].idxmax()]
        render_head(head,"grid","4 · When do IPL batters score best?",f"{best['phase']} is the strongest phase",f"All qualifying batters combined · measure: {metric}")
        show_chart(fig,"chart_phase_all")


def render_entry_overview(g):
    with module("entryall"):
        head=st.empty(); c1,c2=st.columns(2)
        with c1: season=chart_season("entryall",g["season"])
        with c2: metric=st.selectbox("What should we rank?",["Runs","Sixes","Strike rate"],key="entryall_metric")
        es=entry_stats(season,g["hand"],g["min_balls"],g["min_runs"])
        if es.empty: render_head(head,"pulse","5 · Does batting position change output?","No entry-position data"); empty_state(); return
        grp=es.groupby("entry_group",as_index=False).agg(runs=("runs","sum"),balls=("balls","sum"),sixes=("sixes","sum"),innings=("innings","sum"),batters=("batters","sum")); grp["sr"]=ratio(grp["runs"],grp["balls"],100); grp["entry_order"]=grp["entry_group"].map({str(i):i for i in range(1,5)}).fillna(5); grp=grp.sort_values("entry_order")
        col={"Runs":"runs","Sixes":"sixes","Strike rate":"sr"}[metric]
        fig=go.Figure(go.Bar(x=[f"No. {x}" for x in grp["entry_group"]],y=grp[col],marker_color=CYAN,text=[f"{v:.1f}" if metric=="Strike rate" else f"{v:,.0f}" for v in grp[col]],textposition="outside",cliponaxis=False,customdata=np.column_stack([grp["runs"],grp["sixes"],grp["sr"],grp["batters"]]),hovertemplate="<b>%{x}</b><br>"+esc(metric)+": %{y}<br>Runs: %{customdata[0]:,.0f}<br>Sixes: %{customdata[1]:,.0f}<br>Strike rate: %{customdata[2]:.1f}<br>Batters: %{customdata[3]:,.0f}<extra></extra>"))
        style_fig(fig,370,False); fig.update_xaxes(title="Batting entry position"); fig.update_yaxes(title=readable_axis_label(metric),rangemode="tozero")
        best=grp.loc[grp[col].idxmax()]
        render_head(head,"pulse","5 · Does batting position change output?",f"No. {best['entry_group']} leads in {metric.lower()}","No. 1 = opener · No. 5+ groups later-entry batters together")
        show_chart(fig,"chart_entry_all")


def render_hand_overview(g):
    with module("handall"):
        head=st.empty(); c1,c2=st.columns(2)
        with c1: season=chart_season("handall",g["season"])
        with c2: metric=st.selectbox("Compare by",["Strike rate","Batting average","Runs per batter"],key="handall_metric")
        pool=batter_pool(season,"All",g["min_balls"],g["min_runs"])
        if pool.empty: render_head(head,"chart","6 · Does batting hand make a difference?","No qualifying batters"); empty_state(); return
        h=pool[pool["batting_hand"].isin(HANDS)].groupby("batting_hand",as_index=False).agg(runs=("runs","sum"),batters=("batter","nunique"),balls=("balls","sum"),sr=("sr","mean"),avg=("avg","mean")); h["runs_per_batter"]=h["runs"]/h["batters"]
        col={"Strike rate":"sr","Batting average":"avg","Runs per batter":"runs_per_batter"}[metric]
        fig=go.Figure(go.Bar(x=h["batting_hand"].map(short_hand),y=h[col],marker_color=[HAND_COLORS[x] for x in h["batting_hand"]],text=[f"{v:.1f}" for v in h[col]],textposition="outside",cliponaxis=False,customdata=np.column_stack([h["batters"],h["runs"],h["balls"]]),hovertemplate="<b>%{x}</b><br>"+esc(metric)+": %{y:.1f}<br>Batters: %{customdata[0]:,.0f}<br>Total runs: %{customdata[1]:,.0f}<br>Legal balls: %{customdata[2]:,.0f}<extra></extra>"))
        style_fig(fig,360,False); fig.update_xaxes(title="Batting hand"); fig.update_yaxes(title=readable_axis_label("Strike rate" if metric=="Strike rate" else ("Batting average" if metric=="Batting average" else "Runs")),rangemode="tozero")
        winner=h.loc[h[col].idxmax()]
        render_head(head,"chart","6 · Does batting hand make a difference?",f"{short_hand(winner['batting_hand'])} leads on {metric.lower()}","Average result per batter for the selected population · this is an association, not a cause-and-effect test")
        show_chart(fig,"chart_hand_all")


def render_season_overview(g):
    with module("seasonall"):
        head=st.empty(); c1,c2=st.columns(2)
        with c1: metric=st.selectbox("Trend measure",["Total runs","Average strike rate","Total sixes"],key="seasonall_metric")
        with c2: _=st.caption("Uses the current global batter filters")
        inn=DATA.inn.copy()
        if g["hand"]!="All": inn=inn[inn["batting_hand"]==g["hand"]]
        if g["season"]!="All": inn=inn[inn["season"]==g["season"]]
        if inn.empty: render_head(head,"chart","7 · How has batting changed across IPL seasons?","No data for these filters"); empty_state(); return
        if metric=="Total runs": t=inn.groupby("season",as_index=False)["runs"].sum(); col="runs"; label="Total runs"
        elif metric=="Total sixes": t=inn.groupby("season",as_index=False)["sixes"].sum(); col="sixes"; label="Total sixes"
        else: t=inn.groupby("season",as_index=False).agg(runs=("runs","sum"),balls=("balls","sum")); t["sr"]=ratio(t["runs"],t["balls"],100); col="sr"; label="Average strike rate"
        t=t.sort_values("season")
        fig=go.Figure(go.Scatter(x=t["season"],y=t[col],mode="lines+markers+text",line=dict(color=CYAN,width=4),marker=dict(size=9,color=VIOLET),text=[f"{v:,.1f}" if metric=="Average strike rate" else f"{v:,.0f}" for v in t[col]],textposition="top center",fill="tozeroy",fillcolor="rgba(34,211,238,.07)"))
        style_fig(fig,370,False); fig.update_xaxes(title="IPL season",showgrid=False); fig.update_yaxes(title=label,rangemode="tozero")
        peak=t.loc[t[col].idxmax()]
        render_head(head,"chart","7 · How has batting changed across IPL seasons?",f"Peak {label.lower()}: {peak['season']}","Season-by-season trend across the selected batter population")
        show_chart(fig,"chart_season_all")


def render_sixes_overview(g):
    with module("sixesall"):
        head=st.empty(); c1,c2=st.columns(2)
        with c1: season=chart_season("sixesall",g["season"])
        with c2: top_n=int(st.slider("How many batters",5,15,10,key="sixesall_n"))
        pool=batter_pool(season,g["hand"],g["min_balls"],g["min_runs"])
        if pool.empty: render_head(head,"bolt","8 · Who hits the most sixes?","No qualifying batters"); empty_state(); return
        plot=pool.nlargest(top_n,"sixes").sort_values("sixes")
        fig=go.Figure(go.Bar(x=plot["sixes"],y=plot["batter"],orientation="h",marker_color=PINK,text=[f"{v:,.0f}" for v in plot["sixes"]],textposition="outside",cliponaxis=False,customdata=np.column_stack([plot["runs"],plot["sr"]]),hovertemplate="<b>%{y}</b><br>Sixes: %{x:,.0f}<br>Runs: %{customdata[0]:,.0f}<br>Strike rate: %{customdata[1]:.1f}<extra></extra>"))
        style_fig(fig,390,False); fig.update_xaxes(title="Sixes hit",rangemode="tozero"); fig.update_yaxes(title="Batter",showgrid=False)
        best=pool.loc[pool["sixes"].idxmax()]
        render_head(head,"bolt","8 · Who hits the most sixes?",f"{best['batter']} leads the six-hitting chart","Top qualifying batters · easy to compare power hitting at a glance")
        show_chart(fig,"chart_sixes_all")


def render_dismissals_overview(g):
    with module("dismissall"):
        head=st.empty(); season=chart_season("dismissall",g["season"])
        pool=batter_pool(season,g["hand"],g["min_balls"],g["min_runs"])
        if pool.empty: render_head(head,"shield","9 · How are IPL batters usually dismissed?","No qualifying batters"); empty_state(); return
        dis=DATA.dis[DATA.dis["batter"].isin(pool["batter"])]; dis=filter_season(dis,season)
        grp=dis.groupby("kind",as_index=False)["n"].sum().sort_values("n",ascending=True)
        if grp.empty: render_head(head,"shield","9 · How are IPL batters usually dismissed?","No dismissal data"); empty_state(); return
        total=grp["n"].sum(); grp["share"]=grp["n"]*100/total
        fig=go.Figure(go.Bar(x=grp["share"],y=grp["kind"],orientation="h",marker_color=PALETTE[:len(grp)],text=[f"{p:.1f}%" for p in grp["share"]],textposition="outside",cliponaxis=False,customdata=grp[["n"]],hovertemplate="<b>%{y}</b><br>Share: %{x:.1f}%<br>Dismissals: %{customdata[0]:,.0f}<extra></extra>"))
        style_fig(fig,370,False); fig.update_xaxes(title="Share of dismissals (%)",rangemode="tozero"); fig.update_yaxes(title="Dismissal type",showgrid=False)
        top=grp.iloc[-1]
        render_head(head,"shield","9 · How are IPL batters usually dismissed?",f"{top['kind']} is the most common dismissal",f"All qualifying batters combined · {int(total):,} dismissals")
        show_chart(fig,"chart_dismiss_all")


def render_universe_tab():
    render_universe_header()
    render_ticker()
    with bar_container("global"):
        html('<div class="bar-title">Global filters · choose the batter population</div>')
        f1,f2,f3,f4=st.columns(4)
        with f1: season=st.selectbox("Season",["All"]+SEASONS,key="g_season")
        with f2: hand=st.selectbox("Batting hand",["All"]+HANDS,key="g_hand")
        with f3: min_balls=int(st.number_input("Minimum legal balls",0,5000,250,25,key="g_min_balls"))
        with f4: min_runs=int(st.number_input("Minimum runs",0,10000,250,25,key="g_min_runs"))
    g=dict(season=season,hand=hand,min_balls=min_balls,min_runs=min_runs)
    pool=batter_pool(season,hand,min_balls,min_runs)
    k1,k2,k3,k4=st.columns(4)
    with k1: kpi_card("users","Batters in population",fnum(len(pool)),f"of {SCALE['batters']:,} total IPL batters",CYAN)
    with k2: kpi_card("target","Total runs",fnum(pool["runs"].sum() if not pool.empty else 0),f"Across {fnum(pool['balls'].sum() if not pool.empty else 0)} legal balls",VIOLET)
    with k3: kpi_card("pulse","Average strike rate",fnum(pool["sr"].mean() if not pool.empty else np.nan,1),"Mean strike rate across qualifying batters",PINK)
    with k4: kpi_card("bolt","Total sixes",fnum(pool["sixes"].sum() if not pool.empty else 0),"Sixes hit by the selected population",AMBER)
    if pool.empty:
        empty_state("No batters match these filters. Lower the minimum balls or runs."); return
    render_top_runs(g)
    a,b=st.columns(2)
    with a: render_top_strike_rate(g)
    with b: render_consistency_map(g)
    c,d=st.columns(2)
    with c: render_phase_overview(g)
    with d: render_entry_overview(g)
    e,f=st.columns(2)
    with e: render_hand_overview(g)
    with f: render_season_overview(g)
    gcol,h=st.columns(2)
    with gcol: render_sixes_overview(g)
    with h: render_dismissals_overview(g)


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
            render_head(head, "chart", "Runs by season", "No innings in this season range")
            empty_state("No innings recorded in this season range.")
            return
        t = sub.groupby("season", as_index=False).agg(runs=("runs", "sum"), balls=("balls", "sum"))
        t["sr"] = ratio(t["runs"], t["balls"], 100)
        t = t.merge(league_season_table(), on="season", how="left")
        vcol, lcol, unit = {"Runs": ("runs", "lg_runs", "runs"), "Strike rate": ("sr", "lg_sr", "SR"),
                            "Balls faced": ("balls", "lg_balls", "balls")}[metric]
        t = t.dropna(subset=[vcol])
        if t.empty:
            render_head(head, "chart", "Runs by season", "No data for this metric")
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
        render_head(head, "chart", "Runs by season", title, sub_txt)
        show_chart(fig, "chart_timeline")


def render_radar(batter, seasons_p, slug, page_season):
    """Readable phase bars: batter versus league baseline."""
    with module("phase"):
        head = st.empty()
        c1, c2 = st.columns(2)
        with c1: season = player_chart_season("radar", slug, seasons_p, page_season)
        with c2: metric = st.selectbox("Metric", PHASE_METRICS, key="radar_metric")
        ph = filter_season(D().phase, season)
        pp = ph[ph["batter"] == batter].groupby("phase")[["runs","balls","dots","outs"]].sum().reindex(PHASES).fillna(0).reset_index()
        lg = ph.groupby("phase")[["runs","balls","dots","outs"]].sum().reindex(PHASES).fillna(0).reset_index()
        if pp["balls"].sum() == 0:
            render_head(head, "target", "Strike rate by phase", "No phase data for this selection"); empty_state(); return
        pv = phase_metric_values(pp, metric); lv = phase_metric_values(lg, metric)
        merged = pv[["phase","value"]].rename(columns={"value":"batter_value"}).merge(lv[["phase","value"]].rename(columns={"value":"league_value"}), on="phase")
        fig = go.Figure()
        fig.add_trace(go.Bar(x=merged["phase"], y=merged["batter_value"], name=batter, marker_color=CYAN, text=[fmt_metric(v, metric) for v in merged["batter_value"]], textposition="outside"))
        fig.add_trace(go.Bar(x=merged["phase"], y=merged["league_value"], name="League", marker_color=AMBER, text=[fmt_metric(v, metric) for v in merged["league_value"]], textposition="outside"))
        style_fig(fig, 360, legend=True); fig.update_layout(barmode="group"); fig.update_xaxes(showgrid=False, title="Match phase"); fig.update_yaxes(title=metric)
        i = int(np.nanargmax(merged["batter_value"].to_numpy())); ph_name = merged.iloc[i]["phase"]
        title = f"{batter} performs best in the {ph_name} phase"
        sub = f"{metric} compared with the league · {fnum(pp['balls'].sum())} legal balls · {fnum(pp['runs'].sum())} runs"
        render_head(head, "target", "Strike rate by phase", title, sub)
        show_chart(fig, "chart_phase")

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
            render_head(head, "pin", "Runs against opponent", f"No opponent reaches {mb}+ legal balls", f"Minimum {mb} legal balls")
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
        render_head(head, "pin", "Runs against opponent", title, sub_txt)
        show_chart(fig, "chart_opponents")


def render_venues(batter, pdf_all, seasons_p, slug, page_season):
    """Rank venues by runs so the best places are immediately visible."""
    with module("venue"):
        head = st.empty(); c1,c2,c3=st.columns(3)
        with c1: season=player_chart_season("ven",slug,seasons_p,page_season)
        with c2: top_n=int(st.slider("Top N",3,15,8,key=f"ven_topn_{slug}"))
        with c3: mb=int(st.number_input("Min balls",0,2000,50,10,key=f"ven_minballs_{slug}"))
        sub=filter_season(pdf_all,season)
        grp=sub.groupby("venue",as_index=False).agg(runs=("runs","sum"),balls=("balls","sum"),outs=("outs","sum"),innings=("match_id","size"))
        grp=grp[grp["balls"]>=max(mb,1)].copy()
        if grp.empty:
            render_head(head,"pin","Runs by venue",f"No venue reaches {mb}+ legal balls"); empty_state(f"No venue reaches {mb} legal balls for this selection."); return
        grp["sr"]=ratio(grp["runs"],grp["balls"],100); grp=grp.dropna(subset=["sr"]).sort_values("runs",ascending=False).head(top_n); grp["short"]=grp["venue"].map(short_venue)
        plot_df=grp.sort_values("runs",ascending=True)
        fig=go.Figure(go.Bar(x=plot_df["runs"],y=plot_df["short"],orientation="h",marker_color=CYAN,text=[f"{v:,.0f}" for v in plot_df["runs"]],textposition="outside",cliponaxis=False,customdata=np.column_stack([plot_df["balls"],plot_df["sr"],plot_df["innings"],plot_df["outs"]]),hovertemplate="<b>%{y}</b><br>Runs: %{x:,.0f}<br>Strike rate: %{customdata[1]:.1f}<br>Balls: %{customdata[0]:,.0f}<br>Innings: %{customdata[2]:,.0f}<br>Dismissals: %{customdata[3]:,.0f}<extra></extra>"))
        style_fig(fig,380,legend=False); fig.update_xaxes(title="Runs",rangemode="tozero"); fig.update_yaxes(showgrid=False)
        best=grp.iloc[0]; title=f"{best['short']} is {batter}'s top venue by runs"; sub_txt=f"Ranked by total runs · minimum {mb} legal balls · {len(grp)} venues shown"
        render_head(head,"pin","Runs by venue",title,sub_txt); show_chart(fig,"chart_venues")

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
            render_head(head, "shield", "Dismissal type", "No dismissals recorded for this selection")
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
        render_head(head, "shield", "Dismissal type", title, sub_txt)
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

    # Selected-batter profile, matching the presentation sketch.
    hand = "—"
    if "batting_hand" in pdf.columns and not pdf["batting_hand"].dropna().empty:
        hand = str(pdf["batting_hand"].dropna().mode().iloc[0])
    html(f"""
    <div class="module" style="margin:12px 0 18px;padding:16px 18px;border:1px solid rgba(148,163,184,.16);
         border-radius:16px;background:linear-gradient(135deg,rgba(15,23,42,.82),rgba(30,58,138,.22));">
      <div style="font-size:11px;letter-spacing:.14em;text-transform:uppercase;color:#7F97B0;font-weight:700;">Selected batter</div>
      <div style="font-size:24px;font-weight:800;color:#F8FAFC;margin-top:5px;">{esc(batter)}</div>
      <div style="font-size:12px;color:#94A3B8;margin-top:3px;">Batting hand: {esc(hand)} · {season_txt}</div>
    </div>
    """)

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