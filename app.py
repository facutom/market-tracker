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

# ─────────────────────────────────────────────────────────────────────────────
#  CONFIGURACIÓN DE PÁGINA
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Nasdaq Price Projection - Facutom",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─────────────────────────────────────────────────────────────────────────────
#  CONTROL DE REFRESCO Y ESTADO DEL MERCADO
# ─────────────────────────────────────────────────────────────────────────────
ny_tz = pytz.timezone('America/New_York')
now_ny = datetime.now(ny_tz)
is_weekday = now_ny.weekday() < 5
m_open, m_close = dt_time(9, 30), dt_time(16, 0)
market_is_open = is_weekday and (m_open <= now_ny.time() <= m_close)

# Inicializar estado si no existe
if 'last_market_open' not in st.session_state:
    st.session_state.last_market_open = market_is_open

# Lógica de rerun automático
if st.session_state.last_market_open != market_is_open:
    st.session_state.last_market_open = market_is_open
    st.rerun()

AVATAR_URL = "https://ugc.production.linktr.ee/2fb027da-4522-4b25-8855-39f77182ce8b_mQO6eyvY-400x400.png?io=true&size=avatar-v3_0"

# ─────────────────────────────────────────────────────────────────────────────
#  CSS INTEGRADO
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
header {visibility: hidden !important;}
[data-testid="stHeader"] {display: none !important;}
[data-testid="stToolbar"] {display: none !important;}
[data-testid="stDecoration"] {display: none !important;}
footer {visibility: hidden;}
[data-testid="stMarkdownContainer"] > p { margin-bottom: 0px !important; }
[data-testid="stMarkdownContainer"] { padding: 0px !important; }
section.main > div { padding-top: 0rem !important; }
.block-container { padding-top: 0.5rem !important; padding-bottom: 2rem !important; }
.stApp { background-color: #0b0e11 !important; }
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');
.header-centered { text-align: center; margin-bottom: 20px; }
.main-title { font-size: 3.5rem; font-weight: 800; color: #ffffff !important; letter-spacing: -2px; line-height: 1.1; }
.date-sub { font-size: 0.95rem; color: #787b86 !important; text-transform: uppercase; margin-top: 5px; }
.status-tag { display: inline-flex; align-items: center; gap: 6px; font-size: 0.75rem; font-weight: 700; margin-top: 8px; }
.dot-live { height: 10px; width: 10px; background-color: #00ff41; border-radius: 50%; animation: pulse-green 2s infinite; }
.dot-closed { height: 10px; width: 10px; background-color: #f23645; border-radius: 50%; }
@keyframes pulse-green {
    0% { transform: scale(0.9); box-shadow: 0 0 0 0 rgba(0, 255, 65, 0.7); }
    70% { transform: scale(1.1); box-shadow: 0 0 0 8px rgba(0, 255, 65, 0); }
    100% { transform: scale(0.9); box-shadow: 0 0 0 0 rgba(0, 255, 65, 0); }
}
.cards-container { display: flex; justify-content: center; gap: 15px; margin-bottom: 20px; width: 100%; flex-wrap: wrap; }
.card-item { background: #1e222d !important; border: 1px solid #2a2e39 !important; border-radius: 12px; padding: 20px 40px; text-align: center; min-width: 280px; }
.card-label { color: #787b86 !important; font-size: 0.75rem; font-weight: 700; text-transform: uppercase; margin-bottom: 5px; }
.card-value-green { color: #00ff41 !important; font-size: 2.5rem; font-weight: 800; line-height: 1; }
.card-value-teal { color: #26a69a !important; font-size: 2.5rem; font-weight: 800; line-height: 1; }
.mini-card { background: #131722 !important; border: 1px solid #2a2e39 !important; border-radius: 8px; padding: 12px; text-align: center; flex: 1; min-width: 120px; }
.mini-value { color: #26a69a !important; font-size: 1.6rem; font-weight: 800; }
.mini-value.signal-buy { color: #00ff41 !important; }
.mini-value.signal-sell { color: #f23645 !important; }
.mini-value.signal-hold { color: #787b86 !important; }
.mini-value.signal-na { color: #787b86 !important; }
.signal-return { font-size: 1.2rem; font-weight: 700; margin-top: 0; }
.indicator-row { display: flex; justify-content: center; gap: 30px; margin: 0 auto 20px auto; font-size: 0.8rem; font-weight: 700; background: #1e222d !important; padding: 12px 25px; border-radius: 10px; border: 1px solid #2a2e39 !important; width: fit-content; }
.ind-item { display: flex; align-items: center; gap: 8px; color: #ffffff !important; }
.dot { width: 8px; height: 8px; border-radius: 50%; }
.tooltip-wrapper { position: relative; display: inline-flex; margin-left: 6px; cursor: help; }
.tooltip-icon { display: inline-flex; align-items: center; justify-content: center; width: 16px; height: 16px; background: #2962ff; color: white; border-radius: 50%; font-size: 10px; font-weight: bold; }
.tooltip-text { visibility: hidden; position: absolute; bottom: 130%; left: 50%; transform: translateX(-50%); background: #1e222d; color: #ffffff; padding: 10px; border-radius: 8px; border: 1px solid #2a2e39; font-size: 0.75rem; width: 180px; opacity: 0; transition: 0.2s; z-index: 100; }
.tooltip-wrapper:hover .tooltip-text { visibility: visible; opacity: 1; }
.section-box { background: #1e222d !important; border: 1px solid #2a2e39 !important; border-radius: 12px; padding: 25px; margin-top: 20px; }
.section-title { color: #ffffff !important; font-size: 1.3rem; font-weight: 700; margin-bottom: 20px; border-left: 4px solid #2962ff; padding-left: 15px; }
.table-scroll { max-height: 350px; overflow-y: auto; border: 1px solid #2a2e39; border-radius: 8px; }
.audit-table { width: 100%; border-collapse: collapse; color: #d1d4dc; }
.audit-table th { position: sticky; top: 0; background: #2a2e39; padding: 12px; font-size: 0.7rem; }
.audit-table td { padding: 12px; border-bottom: 1px solid #2a2e39; text-align: center; }
.hit-high { color: #00ff41; font-weight: 700; }
.author-box { display: flex; align-items: center; justify-content: center; margin: 15px 0 20px; }
.avatar-img { width: 30px; height: 30px; margin-right: 10px; border-radius: 50%; border: 2px solid #2962ff; }
.author-text { font-size: 0.95rem; color: #ffffff !important; font-weight: 600; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
#  LÓGICA DE DATOS
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=300)
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
        st.error(f"Error loading data: {e}")
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
        if not hist.empty and len(hist) >= 2:
            return hist['Close'].iloc[-1], hist['Close'].iloc[-2]
        elif not hist.empty:
            return hist['Close'].iloc[-1], None
        return None, None
    except: return None, None

# ─────────────────────────────────────────────────────────────────────────────
#  EJECUCIÓN
# ─────────────────────────────────────────────────────────────────────────────
df = load_data()
live_price, yf_yesterday = get_live_price()

if not df.empty:
    status_txt = "LIVE" if market_is_open else "CLOSED"
    dot_cls = "dot-live" if market_is_open else "dot-closed"
    s_color = "#00ff41" if market_is_open else "#787b86"
    today_date = now_ny.date()
    
    # Datos históricos
    if market_is_open:
        df_real_history = df[(df["Precio Real"] > 0) & (df["Fecha"].dt.date < today_date)].copy()
    else:
        df_real_history = df[(df["Precio Real"] > 0) & (df["Fecha"].dt.date <= today_date)].copy()
    
    last_row_real = df_real_history.iloc[-1] if not df_real_history.empty else df.iloc[0]
    val_real = live_price if live_price is not None else last_row_real["Precio Real"]
    
    # Cálculo de deltas
    ref_price = yf_yesterday if yf_yesterday else last_row_real["Precio Real"]
    delta_abs = val_real - ref_price
    delta_pct = (delta_abs / ref_price * 100) if ref_price != 0 else 0

    # Proyecciones
    today_row = df[df["Fecha"].dt.date == today_date]
    val_proy = today_row["Precio Sintético"].values[0] if not today_row.empty else last_row_real["Precio Sintético"]
    
    target_date_1y = today_date + timedelta(days=365)
    df_future = df[df["Fecha"].dt.date >= target_date_1y]
    one_year_target = df_future.iloc[0]["Precio Sintético"] if not df_future.empty else 0

    # Señal del modelo (90 días)
    target_date_90d = today_date + timedelta(days=90)
    df_future_90d = df[df["Fecha"].dt.date >= target_date_90d]
    price_90d = df_future_90d.iloc[0]["Precio Sintético"] if not df_future_90d.empty else None
    
    if price_90d is not None and val_real > 0:
        expected_return_90d = (price_90d / val_real - 1) * 100
        if expected_return_90d > 5:
            signal, signal_color = "BUY", "#00ff41"
        elif expected_return_90d < -5:
            signal, signal_color = "SELL", "#f23645"
        else:
            signal, signal_color = "HOLD", "#787b86"
    else:
        expected_return_90d, signal, signal_color = 0.0, "NA", "#787b86"

    # UI HEADER
    st.markdown(f"""
    <div class="header-centered">
        <div class="main-title">Nasdaq Price Projection $QQQ</div>
        <div class="date-sub">{now_ny.strftime('%A %d %B %Y')}</div>
        <div class="status-tag" style="color: {s_color};"><span class="{dot_cls}"></span> MARKET {status_txt}</div>
        <div class="author-box"><img src="{AVATAR_URL}" class="avatar-img"><div class="author-text">Created by <a href="https://linktr.ee/facutom" target="_blank" style="color:#2962ff; text-decoration:none;">Facutom</a></div></div>
    </div>
    <div class="cards-container">
        <div class="card-item">
            <div class="card-label">Current Price</div>
            <div class="card-value-green">${val_real:,.2f}</div>
            <div style="color:{'#00ff41' if delta_abs >=0 else '#f23645'}; font-size:0.85rem; font-weight:700;">{'▲' if delta_abs >=0 else '▼'} ${abs(delta_abs):,.2f} ({delta_pct:+.2f}%)</div>
        </div>
        <div class="card-item">
            <div class="card-label">Estimated Price in 1 Year</div>
            <div class="card-value-teal">${one_year_target:,.2f}</div>
            <div style="color:#787b86; font-size:0.75rem;">Target: {target_date_1y.strftime('%d %b %Y')}</div>
        </div>
    </div>
    <div class="indicator-row">
        <div class="ind-item" style="color:#00d2ff !important;"><div class="dot" style="background:#00d2ff"></div> TODAY'S PROJECTION: ${val_proy:,.2f}</div>
        <div class="ind-item" style="color:#2962ff !important;"><div class="dot" style="background:#2962ff"></div> MA 50d: ${last_row_real["SMA 50"]:,.2f}</div>
        <div class="ind-item" style="color:#f7931a !important;"><div class="dot" style="background:#f7931a"></div> MA 200d: ${last_row_real["SMA 200"]:,.2f}</div>
    </div>
    """, unsafe_allow_html=True)

    # PLOTLY CHART
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["Fecha"], y=df["SMA 200"], name="MA200d", line=dict(color="#f7931a", width=1.5)))
    fig.add_trace(go.Scatter(x=df["Fecha"], y=df["SMA 50"], name="MA50d", line=dict(color="#2962ff", width=1.5)))
    fig.add_trace(go.Scatter(x=df["Fecha"], y=df["Precio Sintético"], name="Projection", line=dict(color="#26a69a", width=2, dash="dot")))
    fig.add_trace(go.Scatter(x=df_real_history["Fecha"], y=df_real_history["Precio Real"], name="Price", line=dict(color="#00ff41", width=3)))
    fig.update_layout(template="plotly_dark", paper_bgcolor="#0b0e11", plot_bgcolor="#0b0e11", height=500, margin=dict(l=0, r=0, t=5, b=0), yaxis=dict(side="right", type="log"), legend=dict(orientation="h", yanchor="bottom", y=0.01, xanchor="right", x=0.99, bgcolor="rgba(11, 14, 17, 0.8)"))
    st.plotly_chart(fig, use_container_width=True, config={'displaylogo': False})

    # MODEL AUDIT
    df_m = df_real_history.tail(90).copy()
    if not df_m.empty:
        err_p = (df_m["Precio Sintético"] - df_m["Precio Real"]) / df_m["Precio Real"]
        mape = err_p.abs().mean() * 100
        v_err = err_p.std() * 100
        bias = err_p.mean() * 100
        
        audit_rows_df = df_m.sort_values("Fecha", ascending=False)
        table_rows = ""
        for _, r in audit_rows_df.iterrows():
            hit_rate = 100 - (abs(r['Precio Sintético'] - r['Precio Real']) / r['Precio Real'] * 100)
            hit_class = "hit-high" if hit_rate >= 98 else ""
            table_rows += f"<tr><td>{r['Fecha'].strftime('%d %b %Y')}</td><td>${r['Precio Real']:,.2f}</td><td>${r['Precio Sintético']:,.2f}</td><td class='{hit_class}'>{hit_rate:.2f}%</td></tr>"

        st.markdown(f"""
        <div class="section-box">
            <div class="section-title">Daily Model Audit (Rolling 90 Days)</div>
            <div class="cards-container" style="gap:10px; margin-bottom:20px;">
                <div class="mini-card">
                    <div class="card-label">Model Accuracy <span class="tooltip-wrapper"><span class="tooltip-icon">ⓘ</span><span class="tooltip-text">100% minus MAPE. Higher is better.</span></span></div>
                    <div class="mini-value">{100-mape:.1f}%</div>
                </div>
                <div class="mini-card">
                    <div class="card-label">Model Signal (90d)</div>
                    <div style="display: flex; align-items: center; justify-content: center; gap: 8px;">
                        <div class="mini-value signal-{signal.lower()}">{signal}</div>
                        <div class="signal-return" style="color:{signal_color};">{f'{expected_return_90d:+.1f}%' if signal != 'NA' else 'N/A'}</div>
                    </div>
                </div>
                <div class="mini-card">
                    <div class="card-label">Error Vol.</div>
                    <div class="mini-value">{v_err:.2f}%</div>
                </div>
                <div class="mini-card">
                    <div class="card-label">Model Bias</div>
                    <div class="mini-value">{bias:+.2f}%</div>
                </div>
            </div>
            <div class="table-scroll"><table class="audit-table"><thead><tr><th>Date</th><th>Market Close</th><th>Projection</th><th>Hit Rate</th></tr></thead><tbody>{table_rows}</tbody></table></div>
        </div>
        """, unsafe_allow_html=True)

    # NEWS & METHODOLOGY
    news = fetch_news()
    news_html = "".join([f'<div style="border-bottom:1px solid #2a2e39; padding-bottom:12px; margin-bottom:12px;"><div style="color:#787b86; font-size:0.75rem;">{n["date"]}</div><div style="color:white; font-weight:600;">{n["title"]}</div><a href="{n["link"]}" style="color:#2962ff; font-size:0.8rem; text-decoration:none;" target="_blank">READ ARTICLE →</a></div>' for n in news])
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f'<div class="section-box"><div class="section-title">Latest Nasdaq Insights</div>{news_html if news else "No news available."}</div>', unsafe_allow_html=True)
    with col2:
        st.markdown("""
        <div class="section-box">
            <div class="section-title">Our Methodology</div>
            <div style="color:#b2b5be; line-height:1.7; font-size:0.95rem;">
                This projection uses a proprietary <b>Synthetic Price Model</b> that analyzes historical cycle patterns and technical momentum via Fibonacci-based pathways and SMA filters.
            </div>
            <div style="margin-top:20px; text-align:center; font-size:0.7rem; color:#787b86;">DISCLAIMER: INFORMATIONAL PURPOSES ONLY.</div>
        </div>
        """, unsafe_allow_html=True)

# Loop de refresco para precio en vivo
if market_is_open:
    time.sleep(2)
    st.rerun()
