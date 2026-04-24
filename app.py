import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, timedelta, time as dt_time
import numpy as np
import feedparser
import pytz
import yfinance as yf
import time

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(
    page_title="Nasdaq Price Projection - Facutom",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# 2. CONTROL DE REFRESCO (Optimizado)
# No uses 2 segundos, Streamlit Cloud se bloquea. 30 segundos es lo ideal.
ny_tz = pytz.timezone('America/New_York')
now_ny = datetime.now(ny_tz)
is_weekday = now_ny.weekday() < 5
m_open, m_close = dt_time(9, 30), dt_time(16, 0)
market_is_open = is_weekday and (m_open <= now_ny.time() <= m_close)

# Refresco automático cada 30 segundos usando un componente nativo sutil
if market_is_open:
    st.empty() # Placeholder para forzar actualización
    # Este script hará que la página se refresque cada 30 seg solo si el mercado abre
    st.markdown('<script>setTimeout(function(){window.location.reload();}, 30000);</script>', unsafe_allow_html=True)

AVATAR_URL = "https://ugc.production.linktr.ee/2fb027da-4522-4b25-8855-39f77182ce8b_mQO6eyvY-400x400.png?io=true&size=avatar-v3_0"

# 3. CSS INTEGRADO (Corregido y Limpio)
st.markdown("""
<style>
header {visibility: hidden !important;}
[data-testid="stHeader"] {display: none !important;}
footer {visibility: hidden;}
[data-testid="stMarkdownContainer"] > p { margin-bottom: 0px !important; }
[data-testid="stMarkdownContainer"] { padding: 0px !important; }
section.main > div { padding-top: 0rem !important; }
.block-container { padding-top: 2rem !important; padding-bottom: 2rem !important; }
.stApp { background-color: #0b0e11 !important; }

@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');

.header-centered { text-align: center; margin-bottom: 20px; }
.main-title { font-size: 3.2rem; font-weight: 800; color: #ffffff !important; letter-spacing: -2px; line-height: 1.1; }
.date-sub { font-size: 0.85rem; color: #787b86 !important; text-transform: uppercase; }

.status-tag { display: inline-flex; align-items: center; gap: 6px; font-size: 0.75rem; font-weight: 700; margin-top: 8px; }
.dot-live { height: 10px; width: 10px; background-color: #00ff41; border-radius: 50%; animation: pulse-green 2s infinite; }
.dot-closed { height: 10px; width: 10px; background-color: #f23645; border-radius: 50%; }

@keyframes pulse-green {
    0% { transform: scale(0.9); box-shadow: 0 0 0 0 rgba(0, 255, 65, 0.7); }
    70% { transform: scale(1.1); box-shadow: 0 0 0 8px rgba(0, 255, 65, 0); }
    100% { transform: scale(0.9); box-shadow: 0 0 0 0 rgba(0, 255, 65, 0); }
}

.cards-container { display: flex; justify-content: center; gap: 20px; margin-bottom: 20px; width: 100%; flex-wrap: wrap; }
.card-item { background: #1e222d !important; border: 1px solid #2a2e39 !important; border-radius: 12px; padding: 20px 40px; text-align: center; min-width: 280px; flex: 1; }
.card-label { color: #787b86 !important; font-size: 0.7rem; font-weight: 700; text-transform: uppercase; }
.card-value-green { color: #00ff41 !important; font-size: 2.5rem; font-weight: 800; }
.card-value-teal { color: #26a69a !important; font-size: 2.5rem; font-weight: 800; }

.indicator-row { display: flex; justify-content: center; gap: 30px; margin: 0 auto 20px; font-size: 0.8rem; font-weight: 700; background: #1e222d !important; padding: 12px 25px; border-radius: 10px; border: 1px solid #2a2e39 !important; width: fit-content; }
.ind-item { display: flex; align-items: center; gap: 8px; color: #ffffff !important; }
.dot { width: 8px; height: 8px; border-radius: 50%; }

.section-container { background: #131722 !important; border: 1px solid #2a2e39 !important; border-radius: 12px; padding: 30px; margin: 20px 0; }
.section-title { color: #ffffff !important; font-size: 1.3rem; font-weight: 700; margin-bottom: 20px; border-left: 4px solid #2962ff; padding-left: 15px; }

.table-scroll { max-height: 350px; overflow-y: auto; border: 1px solid #2a2e39; border-radius: 8px; background: #0b0e11; }
.audit-table { width: 100%; border-collapse: collapse; color: #d1d4dc; font-size: 0.9rem; }
.audit-table th { position: sticky; top: 0; background: #2a2e39; color: #787b86; padding: 12px; text-transform: uppercase; font-size: 0.75rem; text-align: center; }
.audit-table td { padding: 12px; border-bottom: 1px solid #2a2e39; text-align: center; }
.hit-high { color: #00ff41; font-weight: 700; }

.author-box { display: flex; align-items: center; justify-content: center; margin: 15px 0 20px; }
.avatar-img { width: 30px; height: 30px; margin-right: 10px; border-radius: 50%; border: 2px solid #2962ff; }
.author-text { font-size: 1rem; color: #ffffff !important; font-weight: 600; }
</style>
""", unsafe_allow_html=True)

# 4. LÓGICA DE DATOS
@st.cache_data(ttl=60)
def load_data():
    try:
        info = dict(st.secrets["connections"]["gsheets"])
        info["private_key"] = info["private_key"].replace("\\n", "\n")
        creds = Credentials.from_service_account_info(info, scopes=["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"])
        gc = gspread.authorize(creds)
        sh = gc.open_by_key("1-ni2_Fn_-IU9Pka4EJlZH8rpAeLsKMGheJzl3CzLsqU")
        ws = sh.worksheet("Proyeccion_Maestra")
        raw = ws.get_all_values()
        df = pd.DataFrame(raw[1:], columns=raw[0])
        for col in ["Precio Real", "Precio Sintético", "SMA 50", "SMA 200"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '.').str.replace(r'[^0-9.-]', '', regex=True), errors="coerce")
        df["Fecha"] = pd.to_datetime(df["Fecha"], dayfirst=True, errors="coerce")
        return df.dropna(subset=["Fecha"]).sort_values("Fecha").reset_index(drop=True)
    except Exception as e:
        st.error(f"Error cargando datos: {e}")
        return pd.DataFrame()

def fetch_news():
    try:
        feed = feedparser.parse("https://news.google.com/rss/search?q=nasdaq+stock+market&hl=en-US&gl=US&ceid=US:en")
        return [{"title": e.title, "link": e.link, "date": e.published} for e in feed.entries[:3]]
    except: return []

def get_live_price():
    try:
        ticker = yf.Ticker("QQQ")
        hist = ticker.history(period="2d")
        if len(hist) >= 2:
            return ticker.fast_info['last_price'], hist['Close'].iloc[-2]
        return ticker.fast_info['last_price'], None
    except: return None, None

# 5. RENDERIZADO
df = load_data()
live_price, yf_yesterday = get_live_price()

if not df.empty:
    status_txt = "LIVE" if market_is_open else "CLOSED"
    dot_cls = "dot-live" if market_is_open else "dot-closed"
    s_color = "#00ff41" if market_is_open else "#787b86"
    today_date = now_ny.date()
    
    df_real_history = df[(df["Precio Real"] > 0) & (df["Fecha"].dt.date < today_date)]
    last_row = df_real_history.iloc[-1]
    val_real = live_price if live_price is not None else last_row["Precio Real"]
    
    if live_price and yf_yesterday:
        delta_abs, delta_pct = live_price - yf_yesterday, (live_price - yf_yesterday)/yf_yesterday*100
    else:
        delta_abs, delta_pct = val_real - last_row["Precio Real"], (val_real - last_row["Precio Real"])/last_row["Precio Real"]*100

    today_row = df[df["Fecha"].dt.date == today_date]
    val_proy = today_row["Precio Sintético"].values[0] if not today_row.empty else last_row["Precio Sintético"]
    
    one_year_target = df[df["Fecha"].dt.date >= (today_date + timedelta(days=365))].iloc[0]["Precio Sintético"]

    # UI HEADER
    st.markdown(f"""
    <div class="header-centered">
        <div class="main-title">Nasdaq Price Projection $QQQ</div>
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
            <div style="color:#787b86; font-size:0.8rem;">Target: {(today_date + timedelta(days=365)).strftime('%d %b %Y')}</div>
        </div>
    </div>
    <div class="indicator-row">
        <div class="ind-item" style="color:#00d2ff !important;"><div class="dot" style="background:#00d2ff"></div> TODAY'S PROJECTION: ${val_proy:,.2f}</div>
        <div class="ind-item"><div class="dot" style="background:#2962ff"></div> MA 50d: ${last_row["SMA 50"]:,.2f}</div>
        <div class="ind-item"><div class="dot" style="background:#f7931a"></div> MA 200d: ${last_row["SMA 200"]:,.2f}</div>
    </div>
    """, unsafe_allow_html=True)

    # GRAFICO
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["Fecha"], y=df["SMA 200"], name="MA200", line=dict(color="#f7931a", width=1.5)))
    fig.add_trace(go.Scatter(x=df["Fecha"], y=df["SMA 50"], name="MA50", line=dict(color="#2962ff", width=1.5)))
    fig.add_trace(go.Scatter(x=df["Fecha"], y=df["Precio Sintético"], name="Projection", line=dict(color="#26a69a", width=2, dash="dot")))
    fig.add_trace(go.Scatter(x=df_real_history["Fecha"], y=df_real_history["Precio Real"], name="Price", line=dict(color="#00ff41", width=3)))
    fig.update_layout(template="plotly_dark", paper_bgcolor="#0b0e11", plot_bgcolor="#0b0e11", height=500, margin=dict(l=0, r=0, t=5, b=0), yaxis=dict(side="right", type="log"))
    st.plotly_chart(fig, use_container_width=True, config={'displaylogo': False})

    # SECCIONES FINALES
    st.markdown('<div class="section-container"><div class="section-title">Daily Model Audit (Rolling 90 Days)</div>', unsafe_allow_html=True)
    
    # Métricas Audit
    df_m = df_real_history.tail(90).copy()
    mape = ((df_m["Precio Sintético"] - df_m["Precio Real"]) / df_m["Precio Real"]).abs().mean() * 100
    audit_rows = df_real_history.tail(90).sort_values("Fecha", ascending=False)
    table_html = "".join([f"<tr><td>{r['Fecha'].strftime('%d %b %Y')}</td><td>${r['Precio Real']:,.2f}</td><td>${r['Precio Sintético']:,.2f}</td><td class='{'hit-high' if (100-abs(r['Precio Sintético']-r['Precio Real'])/r['Precio Real']*100)>=98 else ''}'>{(100-abs(r['Precio Sintético']-r['Precio Real'])/r['Precio Real']*100):.2f}%</td></tr>" for _, r in audit_rows.iterrows()])

    st.markdown(f"""
        <div class="cards-container" style="gap:10px; margin-bottom:20px;">
            <div class="mini-card"><div class="card-label">Accuracy</div><div class="mini-value">{100-mape:.1f}%</div></div>
            <div class="mini-card"><div class="card-label">Metrics</div><div class="mini-value">Audited</div></div>
            <div class="mini-card"><div class="card-label">Window</div><div class="mini-value">90 Days</div></div>
            <div class="mini-card"><div class="card-label">Status</div><div class="mini-value" style="color:#00ff41">Optimal</div></div>
        </div>
        <div class="table-scroll"><table class="audit-table"><thead><tr><th>Date</th><th>Market</th><th>Projection</th><th>Hit Rate</th></tr></thead><tbody>{table_html}</tbody></table></div>
    </div>""", unsafe_allow_html=True)

    # NEWS
    news = fetch_news()
    news_html = "".join([f'<div style="border-bottom:1px solid #2a2e39; padding:10px 0;"><div style="color:#787b86; font-size:0.75rem;">{n["date"]}</div><div style="color:white; font-weight:600;">{n["title"]}</div><a href="{n["link"]}" target="_blank" style="color:#2962ff; text-decoration:none; font-size:0.8rem;">READ MORE →</a></div>' for n in news])
    st.markdown(f'<div class="section-container"><div class="section-title">Latest Nasdaq Insights & News</div>{news_html}</div>', unsafe_allow_html=True)

    # METHODOLOGY
    st.markdown("""<div class="section-container"><div class="section-title">Our Methodology</div><div style="color:#b2b5be; line-height:1.7; font-size:0.95rem;">This projection is based on a proprietary Synthetic Price Model that combines historical cycle analysis with macro technical filters (SMA 50/200). Accuracy is audited daily to ensure model consistency.</div><div style="text-align:center; padding-top:20px; color:#787b86; font-size:0.7rem; border-top:1px solid #2a2e39; margin-top:20px;">INVESTMENT DISCLAIMER: For informational purposes only.</div></div>""", unsafe_allow_html=True)
