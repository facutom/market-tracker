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

# 1. REFRESCO AUTOMÁTICO (Cada 30 segundos)
st_autorefresh(interval=30000, limit=None, key="nasdaq_pro_v5")

# ─────────────────────────────────────────────────────────────────────────────
#  CONFIGURACIÓN Y CSS (ELIMINACIÓN TOTAL DE AIRE ARRIBA)
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(page_title="Nasdaq Projection", layout="wide", initial_sidebar_state="collapsed")

AVATAR_URL = "https://ugc.production.linktr.ee/2fb027da-4522-4b25-8855-39f77182ce8b_mQO6eyvY-400x400.png?io=true&size=avatar-v3_0"

st.markdown(f"""
<style>
/* ELIMINAR TOTALMENTE LA CABECERA Y ESPACIO SUPERIOR */
header[data-testid="stHeader"], 
.stAppHeader, 
.st-emotion-cache-wyoiad {{
    display: none !important;
    height: 0px !important;
    visibility: hidden !important;
}}

/* REAJUSTE DEL CONTENEDOR PARA PEGARLO AL BORDE */
.main .block-container {{ 
    padding-top: 0rem !important; 
    padding-bottom: 0rem !important; 
    margin-top: -85px !important; /* COMPENSA EL ESPACIO DE LA BARRA DE MENÚ */
}}

/* ELIMINAR ESPACIO AL FINAL */
footer {{ display: none !important; }}
[data-testid="stVerticalBlock"] > [style*="flex-direction: column;"] > [data-testid="stVerticalBlock"] {{
    padding-bottom: 0px !important;
}}

.stApp {{ background-color: #0b0e11 !important; }}
html, body {{ background-color: #0b0e11 !important; overflow-x: hidden; }}

/* RESPONSIVE ENGINE - MÓVIL SIN AIRE Y TÍTULO GIGANTE */
@media (max-width: 768px) {{
    .main .block-container {{ margin-top: -95px !important; }} /* Sube un poco más en móvil */
    
    .main-title {{ 
        font-size: 2.8rem !important; 
        line-height: 0.9 !important; 
        letter-spacing: -2px !important;
        margin-bottom: 5px !important;
    }}
    .cards-container {{ 
        display: flex !important; 
        flex-direction: row !important; 
        gap: 8px !important; 
        justify-content: space-between !important;
    }}
    .card-item {{ 
        flex: 1 1 48% !important; 
        padding: 10px 5px !important; 
        min-width: 0 !important;
    }}
    .card-value-green, .card-value-teal {{ font-size: 1.4rem !important; }}
    .card-label {{ font-size: 0.6rem !important; }}
    .indicator-row {{ 
        display: grid !important; 
        grid-template-columns: 1fr 1fr 1fr !important;
        gap: 5px !important; 
        padding: 8px !important;
    }}
    .ind-item {{ font-size: 0.65rem !important; }}
}}

/* ESTILOS DE COMPONENTES */
.header-centered {{ text-align: center; margin-bottom: 5px; }}
.main-title {{ font-size: 3.5rem; font-weight: 800; color: #ffffff !important; letter-spacing: -3px; }}
.date-sub {{ font-size: 0.8rem; color: #787b86 !important; text-transform: uppercase; margin-top: -5px; }}

.status-tag {{ display: inline-flex; align-items: center; gap: 5px; font-size: 0.7rem; font-weight: 700; }}
.dot-live {{ height: 8px; width: 8px; background-color: #00ff41; border-radius: 50%; animation: pulse 2s infinite; }}
@keyframes pulse {{ 0% {{ transform: scale(0.9); opacity: 0.7; }} 70% {{ transform: scale(1.2); opacity: 1; }} 100% {{ transform: scale(0.9); opacity: 0.7; }} }}

.author-box {{ display: flex; align-items: center; justify-content: center; margin: 8px 0; }}
.avatar-img {{ width: 30px; height: 30px; border-radius: 50%; border: 1.5px solid #2962ff; margin-right: 8px; }}

.cards-container {{ display: flex; justify-content: center; gap: 15px; margin-bottom: 10px; }}
.card-item {{ background: #1e222d !important; border: 1px solid #2a2e39 !important; border-radius: 10px; padding: 15px 20px; text-align: center; min-width: 240px; }}
.card-label {{ color: #787b86 !important; font-size: 0.65rem; font-weight: 700; text-transform: uppercase; }}
.card-value-green {{ color: #00ff41 !important; font-size: 2.2rem; font-weight: 800; }}
.card-value-teal {{ color: #26a69a !important; font-size: 2.2rem; font-weight: 800; }}

.indicator-row {{ display: flex; justify-content: center; gap: 20px; padding: 10px; border-radius: 8px; background: #1e222d; width: fit-content; margin: 0 auto 0.5rem; border: 1px solid #2a2e39; }}
.ind-item {{ font-size: 0.75rem; font-weight: 700; color: #ffffff !important; text-align: center; }}

.section-container {{ background: #131722 !important; border-top: 1px solid #2a2e39 !important; padding: 20px 10%; }}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
#  DATA LOGIC (LECTURA G1)
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=5)
def load_data():
    try:
        info = dict(st.secrets["connections"]["gsheets"])
        info["private_key"] = info["private_key"].replace("\\n", "\n")
        creds = Credentials.from_service_account_info(info, scopes=["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"])
        gc = gspread.authorize(creds)
        sh = gc.open_by_key("1-ni2_Fn_-IU9Pka4EJlZH8rpAeLsKMGheJzl3CzLsqU")
        ws = sh.worksheet("Proyeccion_Maestra")
        
        # OBTENER LIVE DE G1
        live_val = ws.acell('G1').value
        live_price = float(str(live_val).replace(',', '.')) if live_val else None

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
#  UI RENDERING
# ─────────────────────────────────────────────────────────────────────────────
df, live_price = load_data()

if not df.empty:
    status_txt, dot_cls, s_color, today_date = get_market_status()
    df_real_history = df[(df["Precio Real"] > 0) & (df["Fecha"].dt.date < today_date)]
    last_yesterday = df_real_history.iloc[-1]
    
    # ASIGNAR PRECIO ACTUAL Y CALCULAR VARIACIÓN $ Y %
    val_real = live_price if live_price else last_yesterday["Precio Real"]
    delta_abs = val_real - last_yesterday["Precio Real"]
    delta_pct = (delta_abs / last_yesterday["Precio Real"] * 100)

    today_row = df[df["Fecha"].dt.date == today_date]
    val_proy = today_row["Precio Sintético"].values[0] if not today_row.empty else last_yesterday["Precio Sintético"]
    target_date = today_date + timedelta(days=365)
    one_year_target = df[df["Fecha"].dt.date >= target_date].iloc[0]["Precio Sintético"] if not df[df["Fecha"].dt.date >= target_date].empty else 0

    st.markdown(f"""
    <div class="header-centered">
        <div class="main-title">Nasdaq Price Projection</div>
        <div class="date-sub">{datetime.now().strftime('%A %d %B %Y')}</div>
        <div class="status-tag" style="color: {s_color};"><span class="{dot_cls}"></span> MARKET {status_txt}</div>
        <div class="author-box"><img src="{AVATAR_URL}" class="avatar-img"><div style="color:white; font-weight:600; font-size:0.85rem;">Created by <a href="https://linktr.ee/facutom" target="_blank" style="color:#2962ff; text-decoration:none;">Facutom</a></div></div>
    </div>
    <div class="cards-container">
        <div class="card-item">
            <div class="card-label">Current Price</div>
            <div class="card-value-green">${val_real:,.2f}</div>
            <div style="color:{'#00ff41' if delta_abs >=0 else '#f23645'}; font-size:0.75rem; font-weight:700;">{'▲' if delta_abs >=0 else '▼'} ${abs(delta_abs):,.2f} ({delta_pct:+.2f}%)</div>
        </div>
        <div class="card-item">
            <div class="card-label">Est. Price in 1 Year</div>
            <div class="card-value-teal">${one_year_target:,.2f}</div>
            <div style="color:#787b86; font-size:0.6rem;">Target: {target_date.strftime('%d %b %y')}</div>
        </div>
    </div>
    <div class="indicator-row">
        <div class="ind-item"><div style="color:#00d2ff">PROJECTION</div>${val_proy:,.2f}</div>
        <div class="ind-item"><div>MA 50d</div>${last_yesterday["SMA 50"]:,.2f}</div>
        <div class="ind-item"><div>MA 200d</div>${last_yesterday["SMA 200"]:,.2f}</div>
    </div>
    """, unsafe_allow_html=True)

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["Fecha"], y=df["SMA 200"], name="MA200d", line=dict(color="#f7931a", width=1.5)))
    fig.add_trace(go.Scatter(x=df["Fecha"], y=df["SMA 50"], name="MA50d", line=dict(color="#2962ff", width=1.5)))
    fig.add_trace(go.Scatter(x=df["Fecha"], y=df["Precio Sintético"], name="Projection", line=dict(color="#26a69a", width=2, dash="dot")))
    fig.add_trace(go.Scatter(x=df_real_history["Fecha"], y=df_real_history["Precio Real"], name="Price", line=dict(color="#00ff41", width=3)))
    fig.update_layout(template="plotly_dark", paper_bgcolor="#0b0e11", plot_bgcolor="#0b0e11", height=450, margin=dict(l=0, r=0, t=0, b=0), yaxis=dict(side="right", type="log"))
    st.plotly_chart(fig, use_container_width=True, config={'displaylogo': False})

    # Footer y Metodología pegados abajo
    st.markdown('<div class="section-container">', unsafe_allow_html=True)
    st.markdown('<div style="color:#b2b5be; font-size:0.8rem; line-height:1.4;">This projection is based on a proprietary Synthetic Price Model that combines historical cycle analysis and technical indicators. We use 200-day and 50-day SMAs for macro trends and Fibonacci-based algorithms for price pathways.</div>', unsafe_allow_html=True)
    st.markdown('<div style="text-align:center; padding-top:10px; font-size:0.6rem; color:white; opacity:0.5;">INVESTMENT DISCLAIMER: This analysis is for informational purposes only.</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
