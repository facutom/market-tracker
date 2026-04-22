import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, timedelta, time
import numpy as np
import feedparser
import pytz
from streamlit_autorefresh import st_autorefresh

# 1. REFRESCO CADA 30 SEGUNDOS
st_autorefresh(interval=30000, limit=None, key="nasdaq_live_v3")

# ─────────────────────────────────────────────────────────────────────────────
#  PÁGINA Y CSS (CERO AIRE ARRIBA/ABAJO)
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(page_title="Nasdaq Projection", layout="wide", initial_sidebar_state="collapsed")

AVATAR_URL = "https://ugc.production.linktr.ee/2fb027da-4522-4b25-8855-39f77182ce8b_mQO6eyvY-400x400.png?io=true&size=avatar-v3_0"

st.markdown(f"""
<style>
/* MATAR CUALQUIER ESPACIO DE STREAMLIT */
[data-testid="stHeader"], .stAppHeader {{ display: none !important; }}
footer {{ display: none !important; }}

/* SUBIR TODO EL CONTENIDO AL BORDE SUPERIOR */
.main .block-container {{ 
    padding-top: 0rem !important; 
    padding-bottom: 0rem !important; 
    margin-top: -105px !important; /* MUY agresivo para ocultar la barra fantasma */
}}

.stApp {{ background-color: #0b0e11 !important; }}
html, body {{ overflow-x: hidden; background-color: #0b0e11 !important; }}

/* MOBILE FRIENDLY - TÍTULO GIGANTE Y CARDS LADO A LADO */
@media (max-width: 768px) {{
    .main-title {{ font-size: 3rem !important; line-height: 0.9 !important; letter-spacing: -3px !important; }}
    .cards-container {{ flex-direction: row !important; flex-wrap: wrap !important; gap: 6px !important; }}
    .card-item {{ flex: 1 1 47% !important; padding: 10px 5px !important; }}
    .card-value-green, .card-value-teal {{ font-size: 1.6rem !important; }}
}}

/* ESTILOS INTERNOS */
.header-centered {{ text-align: center; margin-bottom: 5px; }}
.main-title {{ font-size: 3.5rem; font-weight: 800; color: #ffffff !important; letter-spacing: -3px; }}
.date-sub {{ font-size: 0.85rem; color: #787b86 !important; text-transform: uppercase; }}

.status-tag {{ display: inline-flex; align-items: center; gap: 6px; font-size: 0.75rem; font-weight: 700; }}
.dot-live {{ height: 10px; width: 10px; background-color: #00ff41; border-radius: 50%; animation: pulse 2s infinite; }}
@keyframes pulse {{
    0% {{ transform: scale(0.9); box-shadow: 0 0 0 0 rgba(0, 255, 65, 0.7); }}
    70% {{ transform: scale(1.1); box-shadow: 0 0 0 10px rgba(0, 255, 65, 0); }}
    100% {{ transform: scale(0.9); box-shadow: 0 0 0 0 rgba(0, 255, 65, 0); }}
}}

.author-box {{ display: flex; align-items: center; justify-content: center; margin: 10px 0; }}
.avatar-img {{ width: 35px; height: 35px; border-radius: 50%; border: 2px solid #2962ff; margin-right: 10px; }}

.cards-container {{ display: flex; justify-content: center; gap: 20px; margin-bottom: 15px; }}
.card-item {{ background: #1e222d !important; border: 1px solid #2a2e39 !important; border-radius: 12px; padding: 15px 25px; text-align: center; min-width: 250px; }}
.card-label {{ color: #787b86 !important; font-size: 0.7rem; font-weight: 700; text-transform: uppercase; }}
.card-value-green {{ color: #00ff41 !important; font-size: 2.2rem; font-weight: 800; }}
.card-value-teal {{ color: #26a69a !important; font-size: 2.2rem; font-weight: 800; }}

.indicator-row {{ display: flex; justify-content: center; gap: 30px; padding: 10px; border-radius: 10px; background: #1e222d; width: fit-content; margin: 0 auto 1rem; border: 1px solid #2a2e39; }}
.ind-item {{ font-size: 0.8rem; font-weight: 700; color: #ffffff !important; display: flex; align-items: center; gap: 6px; }}

.section-container {{ background: #131722 !important; border-top: 1px solid #2a2e39 !important; padding: 30px 10%; }}
.disclaimer {{ text-align: center; font-size: 0.7rem; color: #ffffff !important; padding: 15px; opacity: 0.7; }}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
#  DATA LOGIC (LECTURA FORZADA G1)
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=2) # CACHE DE 2 SEGUNDOS PARA QUE G1 SEA INSTANTÁNEO
def load_data():
    try:
        info = dict(st.secrets["connections"]["gsheets"])
        info["private_key"] = info["private_key"].replace("\\n", "\n")
        creds = Credentials.from_service_account_info(info, scopes=["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"])
        gc = gspread.authorize(creds)
        sh = gc.open_by_key("1-ni2_Fn_-IU9Pka4EJlZH8rpAeLsKMGheJzl3CzLsqU")
        ws = sh.worksheet("Proyeccion_Maestra")
        
        # LEER CELDA G1 (LIVE)
        live_val = ws.acell('G1').value
        # Limpieza robusta de la celda G1
        live_price = float(str(live_val).replace(',', '.')) if live_val else None

        # LEER TABLA
        raw = ws.get_all_values()
        df = pd.DataFrame(raw[1:], columns=raw[0])
        for col in ["Precio Real", "Precio Sintético", "SMA 50", "SMA 200"]:
            df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '.').str.replace(r'[^0-9.-]', '', regex=True), errors="coerce")
        df["Fecha"] = pd.to_datetime(df["Fecha"], dayfirst=True, errors="coerce")
        return df.dropna(subset=["Fecha"]).sort_values("Fecha").reset_index(drop=True), live_price
    except: return pd.DataFrame(), None

def get_market_status():
    ny_tz = pytz.timezone('America/New_York')
    now = datetime.now(ny_tz)
    is_weekday = now.weekday() < 5
    if is_weekday and (time(9, 30) <= now.time() <= time(16, 0)):
        return "LIVE", "dot-live", "#00ff41", now.date()
    return "CLOSED", "dot-closed", "#787b86", now.date()

# ─────────────────────────────────────────────────────────────────────────────
#  UI
# ─────────────────────────────────────────────────────────────────────────────
df, live_price = load_data()

if not df.empty:
    status_txt, dot_cls, s_color, today_date = get_market_status()
    df_real_history = df[(df["Precio Real"] > 0) & (df["Fecha"].dt.date < today_date)]
    last_yesterday = df_real_history.iloc[-1]
    
    # USAR G1 SIEMPRE QUE EXISTA, SINO CIERRE
    val_real = live_price if live_price else last_yesterday["Precio Real"]
    
    # RESTAURACIÓN DE MONTO EN $ Y %
    delta_abs = val_real - last_yesterday["Precio Real"]
    delta_pct = (delta_abs / last_yesterday["Precio Real"] * 100)

    # Proyecciones
    today_row = df[df["Fecha"].dt.date == today_date]
    val_proy = today_row["Precio Sintético"].values[0] if not today_row.empty else last_yesterday["Precio Sintético"]
    target_date = today_date + timedelta(days=365)
    one_year_target = df[df["Fecha"].dt.date >= target_date].iloc[0]["Precio Sintético"] if not df[df["Fecha"].dt.date >= target_date].empty else 0

    st.markdown(f"""
    <div class="header-centered">
        <div class="main-title">Nasdaq Price Projection</div>
        <div class="date-sub">{datetime.now().strftime('%A %d %B %Y')}</div>
        <div class="status-tag" style="color: {s_color};"><span class="{dot_cls}"></span> MARKET {status_txt}</div>
        <div class="author-box"><img src="{AVATAR_URL}" class="avatar-img"><div style="color:white; font-weight:600;">Created by <a href="https://linktr.ee/facutom" target="_blank" style="color:#2962ff; text-decoration:none;">Facutom</a></div></div>
    </div>
    <div class="cards-container">
        <div class="card-item">
            <div class="card-label">Current Price</div>
            <div class="card-value-green">${val_real:,.2f}</div>
            <div style="color:{'#00ff41' if delta_abs >=0 else '#f23645'}; font-size:0.85rem; font-weight:700;">
                {'▲' if delta_abs >=0 else '▼'} ${abs(delta_abs):,.2f} ({delta_pct:+.2f}%)
            </div>
        </div>
        <div class="card-item">
            <div class="card-label">Estimated Price in 1 Year</div>
            <div class="card-value-teal">${one_year_target:,.2f}</div>
            <div style="color:#787b86; font-size:0.7rem;">Target: {target_date.strftime('%d %b %Y')}</div>
        </div>
    </div>
    <div class="indicator-row">
        <div class="ind-item" style="color:#00d2ff !important;"><span style="color:#00d2ff">●</span> TODAY'S PROJECTION: ${val_proy:,.2f}</div>
        <div class="ind-item"><span>●</span> MA 50d: ${last_yesterday["SMA 50"]:,.2f}</div>
        <div class="ind-item"><span>●</span> MA 200d: ${last_yesterday["SMA 200"]:,.2f}</div>
    </div>
    """, unsafe_allow_html=True)

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["Fecha"], y=df["SMA 200"], name="MA200d", line=dict(color="#f7931a", width=1.5)))
    fig.add_trace(go.Scatter(x=df["Fecha"], y=df["SMA 50"], name="MA50d", line=dict(color="#2962ff", width=1.5)))
    fig.add_trace(go.Scatter(x=df["Fecha"], y=df["Precio Sintético"], name="Projection", line=dict(color="#26a69a", width=2, dash="dot")))
    fig.add_trace(go.Scatter(x=df_real_history["Fecha"], y=df_real_history["Precio Real"], name="Price", line=dict(color="#00ff41", width=3)))
    fig.update_layout(template="plotly_dark", paper_bgcolor="#0b0e11", plot_bgcolor="#0b0e11", height=500, margin=dict(l=0, r=0, t=5, b=0), yaxis=dict(side="right", type="log"))
    st.plotly_chart(fig, use_container_width=True, config={'displaylogo': False})

    # News & Methodology
    feed = feedparser.parse("https://news.google.com/rss/search?q=nasdaq+stock+market&hl=en-US&gl=US&ceid=US:en")
    entries = sorted(feed.entries, key=lambda x: x.published_parsed, reverse=True)[:3]
    st.markdown('<div class="section-container"><div class="section-title">Latest Nasdaq News</div>', unsafe_allow_html=True)
    for n in entries:
        st.markdown(f"""<div style="margin-bottom:12px; border-bottom:1px solid #1e222d; padding-bottom:8px;"><div style="color:#787b86; font-size:0.75rem;">{n.published}</div><div style="color:white; font-weight:600;">{n.title}</div><a href="{n.link}" style="color:#2962ff; font-size:0.8rem; text-decoration:none;" target="_blank">Read more →</a></div>""", unsafe_allow_html=True)
    
    st.markdown(f"""<div style="margin-top:30px;"></div><div class="section-title">Our Methodology</div><div style="color:#b2b5be; font-size:0.9rem;">This projection is based on a proprietary <b>Synthetic Price Model</b> that combines historical cycle analysis and technical indicators. We use 200-day and 50-day SMAs for macro trends and Fibonacci-based algorithms for price pathways.</div></div>""", unsafe_allow_html=True)
    st.markdown("""<div class="disclaimer">INVESTMENT DISCLAIMER: This analysis is for informational purposes only.</div>""", unsafe_allow_html=True)
