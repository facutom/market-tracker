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
#  CSS INTEGRADO
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
header {visibility: hidden !important;}
[data-testid="stHeader"] {display: none !important;}
[data-testid="stToolbar"] {display: none !important;}
[data-testid="stDecoration"] {display: none !important;}
footer {visibility: hidden;}

/* ELIMINAR ESTILOS POR DEFECTO DE ST MARKDOWN */
[data-testid="stMarkdownContainer"] > p { margin-bottom: 0px !important; }
[data-testid="stMarkdownContainer"] { padding: 0px !important; }

section.main > div { padding-top: 0rem !important; }
.block-container { padding-top: 0.5rem !important; padding-bottom: 2rem !important; }
.stApp { background-color: #0b0e11 !important; }

@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');

/* HEADER */
.header-centered { text-align: center; margin-bottom: 20px; }
.main-title { font-size: 3.5rem; font-weight: 800; color: #ffffff !important; letter-spacing: -2px; line-height: 1.1; }
.date-sub { font-size: 0.95rem; color: #787b86 !important; text-transform: uppercase; margin-top: 5px; }

/* STATUS */
.status-tag { display: inline-flex; align-items: center; gap: 6px; font-size: 0.75rem; font-weight: 700; margin-top: 8px; }
.dot-live { height: 10px; width: 10px; background-color: #00ff41; border-radius: 50%; animation: pulse-green 2s infinite; }
.dot-closed { height: 10px; width: 10px; background-color: #f23645; border-radius: 50%; }

@keyframes pulse-green {
    0% { transform: scale(0.9); box-shadow: 0 0 0 0 rgba(0, 255, 65, 0.7); }
    70% { transform: scale(1.1); box-shadow: 0 0 0 8px rgba(0, 255, 65, 0); }
    100% { transform: scale(0.9); box-shadow: 0 0 0 0 rgba(0, 255, 65, 0); }
}

/* CARDS GENERALES */
.cards-container { display: flex; justify-content: center; gap: 15px; margin-bottom: 20px; width: 100%; flex-wrap: wrap; }
.card-item { background: #1e222d !important; border: 1px solid #2a2e39 !important; border-radius: 12px; padding: 20px 40px; text-align: center; min-width: 280px; }
.card-label { color: #787b86 !important; font-size: 0.75rem; font-weight: 700; text-transform: uppercase; margin-bottom: 5px; }
.card-value-green { color: #00ff41 !important; font-size: 2.5rem; font-weight: 800; line-height: 1; }
.card-value-teal { color: #26a69a !important; font-size: 2.5rem; font-weight: 800; line-height: 1; }

/* MINI CARDS (AUDIT) */
.mini-card { background: #131722 !important; border: 1px solid #2a2e39 !important; border-radius: 8px; padding: 12px; text-align: center; flex: 1; min-width: 120px; }
.mini-value { color: #26a69a !important; font-size: 1.6rem; font-weight: 800; }
.mini-value.signal-buy { color: #00ff41 !important; }
.mini-value.signal-sell { color: #f23645 !important; }
.mini-value.signal-hold { color: #787b86 !important; }
.mini-value.signal-na { color: #787b86 !important; }
.signal-return { font-size: 1.2rem; font-weight: 700; margin-top: 0; }

/* INDICATORS */
.indicator-row { display: flex; justify-content: center; gap: 30px; margin: 0 auto 20px auto; font-size: 0.8rem; font-weight: 700; background: #1e222d !important; padding: 12px 25px; border-radius: 10px; border: 1px solid #2a2e39 !important; width: fit-content; }
.ind-item { display: flex; align-items: center; gap: 8px; color: #ffffff !important; }
.dot { width: 8px; height: 8px; border-radius: 50%; }

/* UNIFICACIÓN DE SECCIONES */
.section-box { 
    background: #1e222d !important; 
    border: 1px solid #2a2e39 !important; 
    border-radius: 12px;
    padding: 25px; 
    margin-top: 20px; 
}
.section-title { 
    color: #ffffff !important; 
    font-size: 1.3rem; 
    font-weight: 700; 
    margin-bottom: 20px; 
    border-left: 4px solid #2962ff; 
    padding-left: 15px; 
    line-height: 1;
}

/* TABLES */
.table-scroll { max-height: 350px; overflow-y: auto; border-radius: 8px; border: 1px solid #2a2e39; background: #131722; margin-top: 10px; }
.audit-table { width: 100%; border-collapse: collapse; color: #d1d4dc; font-size: 0.85rem; }
.audit-table th { position: sticky; top: 0; background: #2a2e39; color: #787b86; padding: 12px; text-transform: uppercase; font-size: 0.7rem; z-index: 10; text-align: center; }
.audit-table td { padding: 12px; border-bottom: 1px solid #2a2e39; text-align: center; }
.audit-table tbody tr:hover { background: #1e222d; }
.hit-high { color: #00ff41; font-weight: 700; }

.author-box { display: flex; align-items: center; justify-content: center; margin: 15px 0 20px; }
.avatar-img { width: 30px; height: 30px; margin-right: 10px; border-radius: 50%; border: 2px solid #2962ff; }
.author-text { font-size: 0.95rem; color: #ffffff !important; font-weight: 600; }

@media (max-width: 768px) {
    .main-title { font-size: 2rem !important; }
    .card-item { min-width: 45%; padding: 15px 20px; }
    .card-value-green, .card-value-teal { font-size: 1.8rem !important; }
    .indicator-row { font-size: 0.7rem; gap: 8px; padding: 10px 15px; }
}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
#  LÓGICA DE DATOS
# ─────────────────────────────────────────────────────────────────────────────
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
    except: return pd.DataFrame()

def get_market_status():
    ny_tz = pytz.timezone('America/New_York')
    now = datetime.now(ny_tz)
    is_weekday = now.weekday() < 5
    m_open, m_close = dt_time(9, 30), dt_time(16, 0)
    market_open = is_weekday and (m_open <= now.time() <= m_close)
    if market_open:
        return "LIVE", "dot-live", "#00ff41", now.date(), True
    return "CLOSED", "dot-closed", "#787b86", now.date(), False

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

# ─────────────────────────────────────────────────────────────────────────────
#  EJECUCIÓN
# ─────────────────────────────────────────────────────────────────────────────
df = load_data()
live_price, yf_yesterday = get_live_price()

if not df.empty:
    status_txt, dot_cls, s_color, today_date, market_is_open = get_market_status()
    
    if market_is_open:
        df_real_history = df[(df["Precio Real"] > 0) & (df["Fecha"].dt.date < today_date)]
    else:
        df_real_history = df[(df["Precio Real"] > 0) & (df["Fecha"].dt.date <= today_date)]
    
    last_yesterday_sheet = df_real_history.iloc[-1]
    
    val_real = live_price if live_price is not None else last_yesterday_sheet["Precio Real"]
    if live_price and yf_yesterday:
        delta_abs, delta_pct = live_price - yf_yesterday, (live_price - yf_yesterday)/yf_yesterday*100
    else:
        delta_abs, delta_pct = val_real - last_yesterday_sheet["Precio Real"], (val_real - last_yesterday_sheet["Precio Real"])/last_yesterday_sheet["Precio Real"]*100

    today_row = df[df["Fecha"].dt.date == today_date]
    val_proy = today_row["Precio Sintético"].values[0] if not today_row.empty else last_yesterday_sheet["Precio Sintético"]
    
    target_date = today_date + timedelta(days=365)
    df_future = df[df["Fecha"].dt.date >= target_date]
    one_year_target = df_future.iloc[0]["Precio Sintético"] if not df_future.empty else 0

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
        <div class="date-sub">{datetime.now().strftime('%A %d %B %Y')}</div>
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
            <div style="color:#787b86; font-size:0.75rem;">Target: {target_date.strftime('%d %b %Y')}</div>
        </div>
    </div>
    <div class="indicator-row">
        <div class="ind-item" style="color:#00d2ff !important;"><div class="dot" style="background:#00d2ff"></div> TODAY'S PROJECTION: ${val_proy:,.2f}</div>
        <div class="ind-item" style="color:#2962ff !important;"><div class="dot" style="background:#2962ff"></div> MA 50d: ${last_yesterday_sheet["SMA 50"]:,.2f}</div>
        <div class="ind-item" style="color:#f7931a !important;"><div class="dot" style="background:#f7931a"></div> MA 200d: ${last_yesterday_sheet["SMA 200"]:,.2f}</div>
    </div>
    """, unsafe_allow_html=True)

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["Fecha"], y=df["SMA 200"], name="MA200d", line=dict(color="#f7931a", width=1.5)))
    fig.add_trace(go.Scatter(x=df["Fecha"], y=df["SMA 50"], name="MA50d", line=dict(color="#2962ff", width=1.5)))
    fig.add_trace(go.Scatter(x=df["Fecha"], y=df["Precio Sintético"], name="Projection", line=dict(color="#26a69a", width=2, dash="dot")))
    fig.add_trace(go.Scatter(x=df_real_history["Fecha"], y=df_real_history["Precio Real"], name="Price", line=dict(color="#00ff41", width=3)))
    fig.update_layout(template="plotly_dark", paper_bgcolor="#0b0e11", plot_bgcolor="#0b0e11", height=500, margin=dict(l=0, r=0, t=5, b=0), yaxis=dict(side="right", type="log"), legend=dict(orientation="h", yanchor="bottom", y=0.01, xanchor="right", x=0.99, bgcolor="rgba(11, 14, 17, 0.8)"))
    st.plotly_chart(fig, width="stretch", config={'displaylogo': False})

    # AUDIT
    df_m = df_real_history.tail(90).copy()
    err_p = (df_m["Precio Sintético"] - df_m["Precio Real"]) / df_m["Precio Real"]
    mape, v_err, bias = err_p.abs().mean() * 100, err_p.std() * 100, err_p.mean() * 100
    audit_rows = df_real_history.tail(90).sort_values("Fecha", ascending=False)
    table_rows = "".join([f"<tr><td>{r['Fecha'].strftime('%d %b %Y')}</td><td>${r['Precio Real']:,.2f}</td><td>${r['Precio Sintético']:,.2f}</td><td class='{'hit-high' if (100 - abs(r['Precio Sintético'] - r['Precio Real']) / r['Precio Real'] * 100) >= 98 else ''}'>{(100 - abs(r['Precio Sintético'] - r['Precio Real']) / r['Precio Real'] * 100):.2f}%</td></tr>" for _, r in audit_rows.iterrows()])

    st.markdown(f"""
    <div class="section-box">
        <div class="section-title">Daily Model Audit (Rolling 90 Days)</div>
        <div class="cards-container" style="gap:10px; margin-bottom:20px;">
            <div class="mini-card"><div class="card-label">Model Accuracy</div><div class="mini-value">{100-mape:.1f}%</div></div>
            <div class="mini-card"><div class="card-label">Model Signal (90d)</div><div style="display: flex; align-items: center; justify-content: center; gap: 8px;"><div class="mini-value signal-{signal.lower()}">{signal}</div><div class="signal-return" style="color:{signal_color};">{f'{expected_return_90d:+.1f}%' if signal != 'NA' else 'N/A'}</div></div></div>
            <div class="mini-card"><div class="card-label">Error Vol.</div><div class="mini-value">{v_err:.2f}%</div></div>
            <div class="mini-card"><div class="card-label">Model Bias</div><div class="mini-value">{bias:+.2f}%</div></div>
        </div>
        <div class="table-scroll"><table class="audit-table"><thead><tr><th>Date</th><th>Market Close</th><th>Projection</th><th>Hit Rate</th></tr></thead><tbody>{table_rows}</tbody></table></div>
    </div>
    """, unsafe_allow_html=True)

    # NEWS & METHODOLOGY
    news = fetch_news()
    news_html = "".join([f'<div style="border-bottom:1px solid #2a2e39; padding-bottom:12px; margin-bottom:12px;"><div style="color:#787b86; font-size:0.75rem; margin-bottom:4px;">{n["date"]}</div><div style="color:white; font-weight:600; font-size:0.95rem; line-height:1.4;">{n["title"]}</div><a href="{n["link"]}" style="color:#2962ff; font-size:0.8rem; text-decoration:none; font-weight:700;" target="_blank">READ ARTICLE →</a></div>' for n in news])
    st.markdown(f"""
    <div class="section-box"><div class="section-title">Latest Nasdaq Insights & News</div>{news_html if news else '<div style="color:#787b86;">No news available.</div>'}</div>
    <div class="section-box"><div class="section-title">Our Methodology</div><div style="color:#b2b5be; line-height:1.7; font-size:0.95rem;">This projection uses a proprietary Synthetic Price Model.</div></div>
    """, unsafe_allow_html=True)

    # CONTROL DE RERUN AL FINAL
    if market_is_open:
        time.sleep(2)
        st.rerun()
