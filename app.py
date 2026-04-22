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
st_autorefresh(interval=30000, limit=None, key="nasdaq_final_v1")

# ─────────────────────────────────────────────────────────────────────────────
#  CONFIGURACIÓN DE PÁGINA
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Nasdaq Price Projection - Facutom",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed",
)

AVATAR_URL = "https://ugc.production.linktr.ee/2fb027da-4522-4b25-8855-39f77182ce8b_mQO6eyvY-400x400.png?io=true&size=avatar-v3_0"

# ─────────────────────────────────────────────────────────────────────────────
#  CSS "FORCE TOP" Y DISEÑO COMPLETO
# ─────────────────────────────────────────────────────────────────────────────
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');

/* 1. ELIMINAR ESPACIO SUPERIOR (ESTO CORRIGE TU CAPTURA) */
header {{ visibility: hidden; height: 0px !important; }}
[data-testid="stHeader"] {{ display: none !important; }}
.stApp {{ background-color: #0b0e11 !important; }}

.main .block-container {{
    padding-top: 0rem !important; 
    padding-bottom: 0rem !important;
    margin-top: -80px !important; /* Tira el contenido hacia arriba */
}}

/* 2. RESPONSIVE ENGINE */
@media (max-width: 768px) {{
    .main .block-container {{ margin-top: -40px !important; }}
    .main-title {{ font-size: 2.2rem !important; }}
    .cards-container {{ flex-direction: row !important; flex-wrap: wrap !important; gap: 8px !important; }}
    .card-item {{ flex: 1 1 45% !important; padding: 12px 8px !important; min-width: 0 !important; }}
    .indicator-row {{ flex-wrap: wrap !important; gap: 8px !important; width: 100% !important; }}
}}

/* 3. ESTILOS DE COMPONENTES */
.header-centered {{ text-align: center; margin-bottom: 10px; }}
.main-title {{ font-size: 3.2rem; font-weight: 800; color: #ffffff !important; letter-spacing: -2px; }}
.date-sub {{ font-size: 0.85rem; color: #787b86 !important; text-transform: uppercase; }}

.status-tag {{ display: inline-flex; align-items: center; gap: 6px; font-size: 0.75rem; font-weight: 700; margin-top: 5px; }}
.dot-live {{ height: 10px; width: 10px; background-color: #00ff41; border-radius: 50%; display: inline-block; animation: pulse-green 2s infinite; }}
.dot-closed {{ height: 10px; width: 10px; background-color: #f23645; border-radius: 50%; display: inline-block; }}

@keyframes pulse-green {{
    0% {{ transform: scale(0.9); box-shadow: 0 0 0 0 rgba(0, 255, 65, 0.7); }}
    70% {{ transform: scale(1.1); box-shadow: 0 0 0 8px rgba(0, 255, 65, 0); }}
    100% {{ transform: scale(0.9); box-shadow: 0 0 0 0 rgba(0, 255, 65, 0); }}
}}

.author-box {{ display: flex; align-items: center; justify-content: center; margin: 10px 0 20px; }}
.avatar-img {{ width: 35px; height: 35px; margin-right: 10px; border-radius: 50%; border: 2px solid #2962ff; }}
.author-text {{ font-size: 1rem; color: #ffffff !important; font-weight: 600; }}

.cards-container {{ display: flex; justify-content: center; gap: 20px; margin-bottom: 20px; width: 100%; }}
.card-item {{ background: #1e222d !important; border: 1px solid #2a2e39 !important; border-radius: 12px; padding: 20px 40px; text-align: center; min-width: 280px; }}
.card-label {{ color: #787b86 !important; font-size: 0.7rem; font-weight: 700; text-transform: uppercase; }}
.card-value-green {{ color: #00ff41 !important; font-size: 2.4rem; font-weight: 800; }}
.card-value-teal {{ color: #26a69a !important; font-size: 2.4rem; font-weight: 800; }}

.indicator-row {{ display: flex; justify-content: center; gap: 30px; margin-bottom: 1.5rem; font-size: 0.85rem; font-weight: 700; background: #1e222d !important; padding: 12px 30px; border-radius: 10px; border: 1px solid #2a2e39 !important; width: fit-content; margin: 0 auto; }}
.ind-item {{ display: flex; align-items: center; gap: 8px; color: #ffffff !important; }}
.dot {{ width: 8px; height: 8px; border-radius: 50%; }}

.section-container {{ background: #131722 !important; border-top: 1px solid #2a2e39 !important; padding: 40px 10%; margin-top: 30px; }}
.section-title {{ color: #ffffff !important; font-size: 1.3rem; font-weight: 700; margin-bottom: 20px; border-left: 4px solid #2962ff; padding-left: 15px; }}
.news-item {{ border-bottom: 1px solid #1e222d !important; padding-bottom: 15px; margin-bottom: 15px; }}
.news-text {{ color: #d1d4dc !important; font-size: 0.95rem; font-weight: 600; line-height: 1.4; }}
.disclaimer {{ text-align: center; font-size: 0.7rem; color: #ffffff !important; padding: 25px; border-top: 1px solid #1e222d !important; opacity: 0.7; }}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
#  DATA LOGIC
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
        
        live_val = ws.acell('G1').value
        live_price = float(live_val.replace(',', '.')) if live_val else None

        raw = ws.get_all_values()
        df = pd.DataFrame(raw[1:], columns=raw[0])
        for col in ["Precio Real", "Precio Sintético", "SMA 50", "SMA 200"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '.').str.replace(r'[^0-9.-]', '', regex=True), errors="coerce")
        df["Fecha"] = pd.to_datetime(df["Fecha"], dayfirst=True, errors="coerce")
        return df.dropna(subset=["Fecha"]).sort_values("Fecha").reset_index(drop=True), live_price
    except: return pd.DataFrame(), None

def get_market_status():
    ny_tz = pytz.timezone('America/New_York')
    now = datetime.now(ny_tz)
    is_weekday = now.weekday() < 5
    m_open, m_close = time(9, 30), time(16, 0)
    if is_weekday and (m_open <= now.time() <= m_close):
        return "LIVE", "dot-live", "#00ff41", now.date()
    return "CLOSED", "dot-closed", "#787b86", now.date()

def fetch_news():
    try:
        feed = feedparser.parse("https://news.google.com/rss/search?q=nasdaq+stock+market&hl=en-US&gl=US&ceid=US:en")
        return [{"title": e.title, "link": e.link, "date": e.published} for e in feed.entries[:3]]
    except: return []

# ─────────────────────────────────────────────────────────────────────────────
#  UI RENDERING
# ─────────────────────────────────────────────────────────────────────────────
df, live_price = load_data()

if not df.empty:
    status_txt, dot_cls, s_color, today_date = get_market_status()
    df_real_history = df[(df["Precio Real"] > 0) & (df["Fecha"].dt.date < today_date)]
    last_yesterday = df_real_history.iloc[-1]
    
    val_real = live_price if live_price is not None else last_yesterday["Precio Real"]
    delta_abs = val_real - last_yesterday["Precio Real"]
    delta_pct = (delta_abs / last_yesterday["Precio Real"] * 100)

    today_row = df[df["Fecha"].dt.date == today_date]
    val_proy = today_row["Precio Sintético"].values[0] if not today_row.empty else last_yesterday["Precio Sintético"]
    
    target_date = today_date + timedelta(days=365)
    one_year_target = df[df["Fecha"].dt.date >= target_date].iloc[0]["Precio Sintético"] if not df[df["Fecha"].dt.date >= target_date].empty else 0

    # HEADER Y CARDS
    st.markdown(f"""
    <div class="header-centered">
        <div class="main-title">Nasdaq Price Projection</div>
        <div class="date-sub">{datetime.now().strftime('%A %d %B %Y')}</div>
        <div class="status-tag" style="color: {s_color};"><span class="{dot_cls}"></span> MARKET {status_txt}</div>
        <div class="author-box"><img src="{AVATAR_URL}" class="avatar-img"><div class="author-text">Created by <a href="https://linktr.ee/facutom" target="_blank" style="color:#2962ff; text-decoration:none;">Facutom</a></div></div>
    </div>
    <div class="cards-container">
        <div class="card-item">
            <div class="card-label">Current Price</div>
            <div class="card-value-green">${val_real:,.2f}</div>
            <div style="color:{'#00ff41' if delta_abs >=0 else '#f23645'}; font-size:0.9rem; font-weight:700;">{'▲' if delta_abs >=0 else '▼'} ${abs(delta_abs):,.2f} ({delta_pct:+.2f}%)</div>
        </div>
        <div class="card-item">
            <div class="card-label">Estimated Price in 1 Year</div>
            <div class="card-value-teal">${one_year_target:,.2f}</div>
            <div style="color:#787b86; font-size:0.8rem;">Target: {target_date.strftime('%d %b %Y')}</div>
        </div>
    </div>
    <div class="indicator-row">
        <div class="ind-item" style="color:#00d2ff !important;"><div class="dot" style="background:#00d2ff"></div> TODAY'S PROJECTION: ${val_proy:,.2f}</div>
        <div class="ind-item"><div class="dot" style="background:#2962ff"></div> MA 50d: ${last_yesterday["SMA 50"]:,.2f}</div>
        <div class="ind-item"><div class="dot" style="background:#f7931a"></div> MA 200d: ${last_yesterday["SMA 200"]:,.2f}</div>
    </div>
    """, unsafe_allow_html=True)

    # GRÁFICO
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["Fecha"], y=df["SMA 200"], name="MA200d", line=dict(color="#f7931a", width=1.5)))
    fig.add_trace(go.Scatter(x=df["Fecha"], y=df["SMA 50"], name="MA50d", line=dict(color="#2962ff", width=1.5)))
    fig.add_trace(go.Scatter(x=df["Fecha"], y=df["Precio Sintético"], name="Projection", line=dict(color="#26a69a", width=2, dash="dot")))
    fig.add_trace(go.Scatter(x=df_real_history["Fecha"], y=df_real_history["Precio Real"], name="Price", line=dict(color="#00ff41", width=3)))
    fig.update_layout(template="plotly_dark", paper_bgcolor="#0b0e11", plot_bgcolor="#0b0e11", height=500, margin=dict(l=0, r=0, t=5, b=0), yaxis=dict(side="right", type="log"), legend=dict(orientation="h", yanchor="bottom", y=0.01, xanchor="right", x=0.99, bgcolor="rgba(11, 14, 17, 0.8)"))
    st.plotly_chart(fig, use_container_width=True, config={'displaylogo': False})

    # FOOTER: NOTICIAS Y METODOLOGÍA
    news = fetch_news()
    st.markdown('<div class="section-container"><div class="section-title">Latest Nasdaq Insights & News</div>', unsafe_allow_html=True)
    if news:
        for item in news:
            st.markdown(f"""<div class="news-item"><div style="color:#787b86; font-size:0.8rem;">{item['date']}</div><div class="news-text">{item['title']}</div><a href="{item['link']}" style="color:#2962ff; font-size:0.85rem; text-decoration:none;" target="_blank">Read full article →</a></div>""", unsafe_allow_html=True)
    st.markdown(f"""<div style="margin-top: 40px;"></div><div class="section-title">Our Methodology</div><div style="color:#b2b5be; line-height:1.7; font-size:0.95rem;">This projection is based on a proprietary <b>Synthetic Price Model</b> that combines historical cycle analysis and technical indicators. We use 200-day and 50-day SMAs for macro trends and Fibonacci-based algorithms for price pathways.</div></div>""", unsafe_allow_html=True)
    st.markdown("""<div class="disclaimer"><b>INVESTMENT DISCLAIMER:</b> This analysis is for informational purposes only and does NOT constitute investment advice.</div>""", unsafe_allow_html=True)
