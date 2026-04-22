import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, timedelta, time
import numpy as np
import feedparser
import pytz

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
#  CSS MOBILE FIRST & RESPONSIVE
# ─────────────────────────────────────────────────────────────────────────────
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');
.stApp, [data-testid="stAppViewContainer"], .main {{ background-color: #0b0e11 !important; max-width: 100vw; overflow-x: hidden; }}
[data-testid="stHeader"] {{ display: none !important; }}
.main .block-container {{ padding: 0.5rem 0.8rem !important; margin-top: -45px !important; }}

@media (max-width: 768px) {{
    .main-title {{ font-size: 2rem !important; }}
    .cards-container {{ flex-direction: row !important; flex-wrap: wrap !important; gap: 8px !important; justify-content: space-between !important; }}
    .card-item {{ flex: 1 1 46% !important; padding: 12px 8px !important; min-width: 0 !important; }}
    .card-value-green, .card-value-teal {{ font-size: 1.4rem !important; }}
    .indicator-row {{ flex-wrap: wrap !important; gap: 8px !important; width: 100% !important; padding: 10px !important; }}
}}

.header-centered {{ text-align: center; margin-bottom: 8px; }}
.main-title {{ font-size: 3.2rem; font-weight: 800; color: #ffffff !important; letter-spacing: -2px; }}
.date-sub {{ font-size: 0.8rem; color: #787b86 !important; text-transform: uppercase; }}
.status-tag {{ display: inline-flex; align-items: center; gap: 5px; font-size: 0.7rem; font-weight: 700; margin-top: 4px; }}
.dot-live {{ height: 7px; width: 7px; background-color: #00ff41; border-radius: 50%; box-shadow: 0 0 6px #00ff41; }}
.dot-closed {{ height: 7px; width: 7px; background-color: #f23645; border-radius: 50%; }}
.author-box {{ display: flex; align-items: center; justify-content: center; margin: 8px 0 15px; }}
.avatar-img {{ width: 32px; height: 32px; margin-right: 8px; border-radius: 50%; border: 2px solid #2962ff; }}
.author-text {{ font-size: 0.9rem; color: #ffffff !important; font-weight: 600; }}
.cards-container {{ display: flex; justify-content: center; gap: 15px; margin-bottom: 15px; width: 100%; }}
.card-item {{ background: #1e222d !important; border: 1px solid #2a2e39 !important; border-radius: 10px; padding: 15px 25px; text-align: center; min-width: 200px; }}
.card-label {{ color: #787b86 !important; font-size: 0.65rem; font-weight: 700; text-transform: uppercase; }}
.card-value-green {{ color: #00ff41 !important; font-size: 2.1rem; font-weight: 800; }}
.card-value-teal {{ color: #26a69a !important; font-size: 2.1rem; font-weight: 800; }}
.indicator-row {{ display: flex; justify-content: center; gap: 20px; margin-bottom: 1rem; font-size: 0.8rem; font-weight: 700; background: #1e222d !important; padding: 10px 20px; border-radius: 8px; border: 1px solid #2a2e39 !important; width: fit-content; margin: 0 auto; }}
.ind-item {{ display: flex; align-items: center; gap: 6px; color: #ffffff !important; }}
.dot {{ width: 7px; height: 7px; border-radius: 50%; }}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
#  LOGICA DE DATOS MEJORADA
# ─────────────────────────────────────────────────────────────────────────────
SHEET_KEY = "1-ni2_Fn_-IU9Pka4EJlZH8rpAeLsKMGheJzl3CzLsqU"

@st.cache_data(ttl=30) # Cache bajo para captar cambios de Google Finance (G1)
def load_data():
    try:
        info = dict(st.secrets["connections"]["gsheets"])
        info["private_key"] = info["private_key"].replace("\\n", "\n")
        creds = Credentials.from_service_account_info(info, scopes=["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"])
        gc = gspread.authorize(creds)
        sh = gc.open_by_key(SHEET_KEY)
        ws = sh.worksheet("Proyeccion_Maestra")
        
        # 1. Obtener precio LIVE de G1
        live_val_str = ws.acell('G1').value
        # Limpiar posibles comas/formatos
        live_price = float(live_val_str.replace(',', '.')) if live_val_str else None

        # 2. Obtener Tabla de datos
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
    m_open, m_close = time(9, 30), time(16, 0)
    if is_weekday and (m_open <= now.time() <= m_close):
        return "LIVE", "dot-live", "#00ff41", now.date()
    return "CLOSED", "dot-closed", "#787b86", now.date()

# ─────────────────────────────────────────────────────────────────────────────
#  UI RENDERING
# ─────────────────────────────────────────────────────────────────────────────
df, live_price = load_data()

if not df.empty:
    status_txt, dot_cls, s_color, today_date = get_market_status()
    
    # FILTRO CRÍTICO: La línea de "Precio Real" termina estrictamente AYER
    # Esto evita que tu fórmula de la columna B se superponga a la proyección de hoy
    df_real_chart = df[(df["Precio Real"] > 0) & (df["Fecha"].dt.date < today_date)].dropna(subset=["Precio Real"])
    
    # Para los cálculos de encabezado usamos el último cierre disponible (Ayer)
    last_close_row = df_real_chart.iloc[-1]
    
    # Precio actual del header: Si es LIVE usamos G1, sino el último de la tabla
    current_display_price = live_price if (status_txt == "LIVE" and live_price) else last_close_row["Precio Real"]
    
    # Variación respecto al cierre previo (anteayer)
    prev_val = df_real_chart["Precio Real"].iloc[-2]
    delta_abs = current_display_price - last_close_row["Precio Real"]
    delta_pct = (delta_abs / last_close_row["Precio Real"] * 100)

    # Proyección de hoy (Extraída de la columna C para la fecha de hoy)
    today_row = df[df["Fecha"].dt.date == today_date]
    val_proy = today_row["Precio Sintético"].values[0] if not today_row.empty else last_close_row["Precio Sintético"]

    # Predicción 1 Año
    target_date = pd.Timestamp(today_date) + pd.Timedelta(days=365)
    df_future = df[df["Fecha"] >= target_date]
    one_year_target = df_future.iloc[0]["Precio Sintético"] if not df_future.empty else 0

    # Header HTML
    st.markdown(f"""
    <div class="header-centered">
        <div class="main-title">Nasdaq Price Projection</div>
        <div class="date-sub">{datetime.now().strftime('%A %d %B %Y')}</div>
        <div class="status-tag" style="color: {s_color};">
            <span class="{dot_cls}"></span> MARKET {status_txt}
        </div>
        <div class="author-box">
            <img src="{AVATAR_URL}" class="avatar-img">
            <div class="author-text">Created by <a href="https://linktr.ee/facutom" target="_blank" style="color:#2962ff; text-decoration:none;">Facutom</a></div>
        </div>
    </div>
    <div class="cards-container">
        <div class="card-item">
            <div class="card-label">Current Price (G1)</div>
            <div class="card-value-green">${current_display_price:,.2f}</div>
            <div style="color:{'#00ff41' if delta_abs >=0 else '#f23645'}; font-size:0.8rem; font-weight:700;">
                {'▲' if delta_abs >=0 else '▼'} ${abs(delta_abs):,.2f} ({delta_pct:+.2f}%)
            </div>
        </div>
        <div class="card-item">
            <div class="card-label">Est. Price 1 Year</div>
            <div class="card-value-teal">${one_year_target:,.2f}</div>
            <div style="color:#787b86; font-size:0.7rem;">Target: {target_date.strftime('%d %b %Y')}</div>
        </div>
    </div>
    <div class="indicator-row">
        <div class="ind-item" style="color:#00d2ff !important;"><div class="dot" style="background:#00d2ff"></div> TODAY'S PROJECTION: ${val_proy:,.2f}</div>
        <div class="ind-item"><div class="dot" style="background:#2962ff"></div> MA 50d: ${last_close_row["SMA 50"]:,.2f}</div>
        <div class="ind-item"><div class="dot" style="background:#f7931a"></div> MA 200d: ${last_close_row["SMA 200"]:,.2f}</div>
    </div>
    """, unsafe_allow_html=True)

    # GRÁFICO
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["Fecha"], y=df["SMA 200"], name="MA200d", line=dict(color="#f7931a", width=1.5)))
    fig.add_trace(go.Scatter(x=df["Fecha"], y=df["SMA 50"], name="MA50d", line=dict(color="#2962ff", width=1.5)))
    fig.add_trace(go.Scatter(x=df["Fecha"], y=df["Precio Sintético"], name="Projection", line=dict(color="#26a69a", width=2, dash="dot")))
    
    # LA LÍNEA REAL TERMINA AYER (usando df_real_chart)
    fig.add_trace(go.Scatter(x=df_real_chart["Fecha"], y=df_real_chart["Precio Real"], name="Historical Close", line=dict(color="#00ff41", width=3)))

    # Box de Proyección técnica
    df_2028 = df[(df["Fecha"] > pd.Timestamp(today_date)) & (df["Fecha"] <= pd.Timestamp(2028, 12, 31))]
    next_high = df_2028["Precio Sintético"].max() if not df_2028.empty else 0
    next_low = df_2028["Precio Sintético"].min() if not df_2028.empty else 0
    fig.add_annotation(xref="paper", yref="paper", x=0.02, y=0.95, text=f"<b>PROJECTION TO 2028</b><br>Next High: <span style='color:#00ff41'>${next_high:,.2f}</span><br>Next Low: <span style='color:#f23645'>${next_low:,.2f}</span>", showarrow=False, align="left", bgcolor="rgba(30, 34, 45, 0.9)", bordercolor="#2a2e39", borderwidth=1, borderpad=10, font=dict(size=12, color="#ffffff"))

    fig.update_layout(template="plotly_dark", paper_bgcolor="#0b0e11", plot_bgcolor="#0b0e11", height=500, margin=dict(l=0, r=0, t=5, b=0), hovermode="x unified", xaxis=dict(showgrid=True, gridcolor="#1e222d"), yaxis=dict(side="right", gridcolor="#1e222d", tickprefix="$", tickformat=",.0f", type="log"), legend=dict(orientation="h", yanchor="bottom", y=0.01, xanchor="right", x=0.99, bgcolor="rgba(11, 14, 17, 0.8)"))
    st.plotly_chart(fig, use_container_width=True, config={'displaylogo': False})

    # Footer Disclaimer
    st.markdown("""<div style="text-align:center; padding:20px; font-size:0.7rem; color:white; border-top:1px solid #1e222d; opacity:0.7;">INVESTMENT DISCLAIMER: This analysis is for informational purposes only and does NOT constitute investment advice.</div>""", unsafe_allow_html=True)
