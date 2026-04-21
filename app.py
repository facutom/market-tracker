import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import numpy as np
import base64

# ─────────────────────────────────────────────────────────────────────────────
#  CONFIGURACIÓN DE PÁGINA & LOGO
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Nasdaq Price Projection - Facutom",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed",
)

def get_base64_of_bin_file(bin_file):
    try:
        with open(bin_file, 'rb') as f:
            data = f.read()
        return base64.b64encode(data).decode()
    except:
        return ""

# Intentar cargar el logo (debe llamarse logo.png en la misma carpeta)
img_base64 = get_base64_of_bin_file("logo.png")
logo_html = f'<img src="data:image/png;base64,{img_base64}" style="width:24px; vertical-align:middle; margin-right:8px; border-radius:50%;">' if img_base64 else ""

# ─────────────────────────────────────────────────────────────────────────────
#  CSS ULTRA-PRO (ELIMINACIÓN DE AIRE)
# ─────────────────────────────────────────────────────────────────────────────
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');

/* Reset de márgenes de Streamlit */
.main .block-container {{ 
    padding-top: 0.5rem !important; 
    padding-bottom: 0rem !important; 
    padding-left: 2rem !important;
    padding-right: 2rem !important;
}}
header[data-testid="stHeader"] {{ visibility: hidden; height: 0px; }}
footer {{ visibility: hidden; }}

html, body, [class*="css"] {{
    background-color: #0b0e11 !important;
    color: #d1d4dc !important;
    font-family: 'Inter', sans-serif !important;
}}

/* Header Compacto */
.header-centered {{ text-align: center; margin-bottom: 0.2rem; }}
.main-title {{ font-size: 1.8rem; font-weight: 700; color: #ffffff; margin-bottom: -5px; letter-spacing: -0.5px; }}
.date-sub {{ font-size: 0.8rem; color: #787b86; text-transform: uppercase; margin-top: 2px; }}
.author {{ font-size: 0.85rem; color: #ffffff; margin-top: 5px; display: flex; align-items: center; justify-content: center; }}
.author a {{ color: #2962ff !important; text-decoration: none; font-weight: 700; }}

/* Precio y Variación (Estilo Bitbo) */
.price-box {{ text-align: center; margin-bottom: 0.5rem; }}
.price-big {{ font-size: 3.2rem; font-weight: 700; color: #00ff41; line-height: 1; display: inline-block; }}
.price-delta {{ font-size: 1.1rem; font-weight: 600; display: inline-block; margin-left: 15px; vertical-align: middle; }}
.up {{ color: #00ff41; }} .down {{ color: #f23645; }}

/* Indicadores Compactos */
.indicator-row {{
    display: flex; justify-content: center; gap: 30px;
    margin-bottom: 0.5rem; font-size: 0.8rem; font-weight: 600; color: #ffffff;
    background: #1e222d; padding: 6px; border-radius: 6px; width: fit-content; margin-left: auto; margin-right: auto;
}}
.ind-item {{ display: flex; align-items: center; gap: 8px; }}
.dot {{ width: 8px; height: 8px; border-radius: 50%; }}

/* Disclaimer Footer */
.disclaimer {{
    text-align: center; font-size: 0.65rem; color: #434651;
    margin-top: 10px; padding-bottom: 10px; line-height: 1.2;
}}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
#  DATA LOADING & CLEANING (Keep logic)
# ─────────────────────────────────────────────────────────────────────────────
SHEET_KEY = "1-ni2_Fn_-IU9Pka4EJlZH8rpAeLsKMGheJzl3CzLsqU"

@st.cache_data(ttl=60)
def load_data():
    try:
        info = dict(st.secrets["connections"]["gsheets"])
        info["private_key"] = info["private_key"].replace("\\n", "\n")
        creds = Credentials.from_service_account_info(info, scopes=[
            "https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"
        ])
        gc = gspread.authorize(creds)
        ws = gc.open_by_key(SHEET_KEY).worksheet("Proyeccion_Maestra")
        raw = ws.get_all_values()
        df = pd.DataFrame(raw[1:], columns=raw[0])
        for col in ["Precio Real", "Precio Sintético", "SMA 50", "SMA 200"]:
            if col in df.columns:
                df[col] = df[col].astype(str).str.replace(',', '.').str.replace(r'[^0-9.-]', '', regex=True)
                df[col] = pd.to_numeric(df[col], errors="coerce")
        df["Fecha"] = pd.to_datetime(df["Fecha"], dayfirst=True, errors="coerce")
        return df.dropna(subset=["Fecha"]).sort_values("Fecha").reset_index(drop=True)
    except: return pd.DataFrame()

# ─────────────────────────────────────────────────────────────────────────────
#  LÓGICA Y RENDERIZADO
# ─────────────────────────────────────────────────────────────────────────────
df = load_data()

if not df.empty:
    df_con_precio = df[df["Precio Real"].notna() & (df["Precio Real"] > 0)]
    last_row = df_con_precio.iloc[-1]
    
    val_real = last_row["Precio Real"]
    val_date = last_row["Fecha"]
    val_sma50 = last_row["SMA 50"]
    val_sma200 = last_row["SMA 200"]
    val_proy = last_row["Precio Sintético"]
    
    prev_val = df_con_precio["Precio Real"].iloc[-2] if len(df_con_precio) > 1 else val_real
    delta_abs = val_real - prev_val
    delta_pct = (delta_abs / prev_val * 100)

    # HEADER CENTRADO CON LOGO
    st.markdown(f"""
    <div class="header-centered">
        <div class="main-title">Nasdaq Price Projection</div>
        <div class="date-sub">{val_date.strftime('%A %d %B %Y')}</div>
        <div class="author">
            {logo_html} Created by&nbsp;<a href="https://linktr.ee/facutom" target="_blank">Facutom</a>
        </div>
    </div>
    <div class="price-box">
        <div class="price-big">${val_real:,.2f}</div>
        <div class="price-delta {'up' if delta_abs >= 0 else 'down'}">
            {'▲' if delta_abs >= 0 else '▼'} ${abs(delta_abs):,.2f} ({delta_pct:+.2f}%)
        </div>
    </div>
    """, unsafe_allow_html=True)

    # INDICADORES SINCRONIZADOS
    st.markdown(f"""
    <div class="indicator-row">
        <div class="ind-item"><div class="dot" style="background:#00ff41"></div> PRICE: ${val_real:,.2f}</div>
        <div class="ind-item"><div class="dot" style="background:#26a69a"></div> PROJECTED: ${val_proy:,.2f}</div>
        <div class="ind-item"><div class="dot" style="background:#2962ff"></div> MA 50d: ${val_sma50:,.2f}</div>
        <div class="ind-item"><div class="dot" style="background:#f7931a"></div> MA 200d: ${val_sma200:,.2f}</div>
    </div>
    """, unsafe_allow_html=True)

    # GRÁFICO (Altura ajustada para evitar scroll)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["Fecha"], y=df["SMA 200"], name="MA200d", line=dict(color="#f7931a", width=1.5)))
    fig.add_trace(go.Scatter(x=df["Fecha"], y=df["SMA 50"], name="MA50d", line=dict(color="#2962ff", width=1.5)))
    fig.add_trace(go.Scatter(x=df["Fecha"], y=df["Precio Sintético"], name="Projected", line=dict(color="#26a69a", width=2, dash="dot")))
    fig.add_trace(go.Scatter(x=df_con_precio["Fecha"], y=df_con_precio["Precio Real"], name="Price Real", line=dict(color="#00ff41", width=2.5)))

    fig.update_layout(
        template="plotly_dark", paper_bgcolor="#0b0e11", plot_bgcolor="#0b0e11",
        height=520, margin=dict(l=0, r=0, t=5, b=0),
        hovermode="x unified",
        xaxis=dict(showgrid=True, gridcolor="#1e222d", tickfont=dict(color="#ffffff", size=11, weight='bold')),
        yaxis=dict(side="right", showgrid=True, gridcolor="#1e222d", tickprefix="$", tickformat=",.0f", tickfont=dict(color="#ffffff", size=11), type="log"),
        legend=dict(orientation="h", yanchor="bottom", y=0.01, xanchor="right", x=0.99, bgcolor="rgba(11, 14, 17, 0.7)")
    )
    st.plotly_chart(fig, use_container_width=True, config={'displaylogo': False})

    # DISCLAIMER INGLÉS
    st.markdown("""
    <div class="disclaimer">
        <b>DISCLAIMER:</b> This content is for informational and educational purposes only and does NOT constitute financial, investment, or trading advice.<br>
        Past performance is not indicative of future results. Always conduct your own research before making any investment decisions.
    </div>
    """, unsafe_allow_html=True)

    # Sidebar oculta pero funcional
    st.sidebar.radio("Scale", ["Log", "Linear"], key="scale_opt")
    if st.session_state.scale_opt == "Linear":
        fig.update_layout(yaxis_type="linear")
        st.rerun()