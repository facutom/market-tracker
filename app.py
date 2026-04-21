import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import numpy as np

# ─────────────────────────────────────────────────────────────────────────────
#  CONFIGURACIÓN DE PÁGINA
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Nasdaq Price Projection - Facutom",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# URL de tu imagen de Linktree
AVATAR_URL = "https://ugc.production.linktr.ee/2fb027da-4522-4b25-8855-39f77182ce8b_mQO6eyvY-400x400.png?io=true&size=avatar-v3_0"

# ─────────────────────────────────────────────────────────────────────────────
#  CSS ULTRA-LIMPIO (ELIMINACIÓN DE CABECERA Y ESPACIOS)
# ─────────────────────────────────────────────────────────────────────────────
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');

/* ELIMINAR CABECERA STREAMLIT Y ESPACIOS MUERTOS */
[data-testid="stHeader"], 
.stAppHeader, 
.st-emotion-cache-wyoiad,
.st-emotion-cache-12fmjuu {{
    display: none !important;
    height: 0px !important;
    margin: 0 !important;
    padding: 0 !important;
}}

/* AJUSTE DEL CONTENEDOR PRINCIPAL - SUBIR TODO */
.main .block-container {{ 
    padding-top: 0rem !important; 
    padding-bottom: 0rem !important; 
    margin-top: -60px !important; /* COMPENSA EL ESPACIO DE LA BARRA */
}}

footer {{ display: none !important; }}

html, body {{
    background-color: #0b0e11 !important;
    color: #d1d4dc !important;
    font-family: 'Inter', sans-serif !important;
}}

/* TÍTULO IMPACTANTE */
.header-centered {{ text-align: center; margin-bottom: 0px; padding-top: 0px; }}
.main-title {{ 
    font-size: 3.5rem; 
    font-weight: 800; 
    color: #ffffff; 
    letter-spacing: -2.5px;
    margin-bottom: -5px;
}}
.date-sub {{ font-size: 1rem; color: #787b86; text-transform: uppercase; letter-spacing: 2px; font-weight: 600; }}

/* AVATAR Y AUTOR */
.author-box {{ 
    display: flex; align-items: center; justify-content: center; 
    margin-top: 10px; margin-bottom: 10px;
}}
.avatar-img {{
    width: 40px; height: 40px; 
    vertical-align: middle; 
    margin-right: 12px; 
    border-radius: 50%; 
    border: 2px solid #2962ff;
}}
.author-text {{ font-size: 1.2rem; color: #ffffff; font-weight: 600; }}
.author-text a {{ color: #2962ff !important; text-decoration: none; }}

/* PRECIO */
.price-box {{ text-align: center; margin-bottom: 0.5rem; }}
.price-big {{ font-size: 4rem; font-weight: 700; color: #00ff41; line-height: 1; display: inline-block; }}
.price-delta {{ font-size: 1.4rem; font-weight: 600; display: inline-block; margin-left: 25px; vertical-align: middle; }}
.up {{ color: #00ff41; }} .down {{ color: #f23645; }}

/* INDICADORES */
.indicator-row {{
    display: flex; justify-content: center; gap: 35px;
    margin-bottom: 1rem; font-size: 0.9rem; font-weight: 700; color: #ffffff;
    background: #1e222d; padding: 10px 30px; border-radius: 12px; width: fit-content; margin: 0 auto;
}}
.ind-item {{ display: flex; align-items: center; gap: 10px; }}
.dot {{ width: 12px; height: 12px; border-radius: 50%; }}

/* DISCLAIMER BLANCO */
.disclaimer {{
    text-align: center; font-size: 0.75rem; color: #ffffff !important; 
    margin-top: 15px; padding-bottom: 20px; line-height: 1.5; font-weight: 500;
    max-width: 900px; margin-left: auto; margin-right: auto;
}}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
#  DATA LOADING (Manteniendo tu lógica funcional)
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
#  UI RENDERING
# ─────────────────────────────────────────────────────────────────────────────
df = load_data()

if not df.empty:
    df_con_precio = df[df["Precio Real"].notna() & (df["Precio Real"] > 0)]
    last_row = df_con_precio.iloc[-1]
    
    val_real, val_date = last_row["Precio Real"], last_row["Fecha"]
    val_sma50, val_sma200 = last_row["SMA 50"], last_row["SMA 200"]
    val_proy = last_row["Precio Sintético"]
    
    prev_val = df_con_precio["Precio Real"].iloc[-2] if len(df_con_precio) > 1 else val_real
    delta_abs = val_real - prev_val
    delta_pct = (delta_abs / prev_val * 100)

    # HEADER (IMPORTANTE: Sin sangrías al inicio para evitar bloque de código)
    st.markdown(f"""<div class="header-centered">
<div class="main-title">Nasdaq Price Projection</div>
<div class="date-sub">{val_date.strftime('%A %d %B %Y')}</div>
<div class="author-box">
<img src="{AVATAR_URL}" class="avatar-img">
<div class="author-text">Created by <a href="https://linktr.ee/facutom" target="_blank">Facutom</a></div>
</div>
</div>
<div class="price-box">
<div class="price-big">${val_real:,.2f}</div>
<div class="price-delta {'up' if delta_abs >= 0 else 'down'}">
{'▲' if delta_abs >= 0 else '▼'} ${abs(delta_abs):,.2f} ({delta_pct:+.2f}%)
</div>
</div>""", unsafe_allow_html=True)

    # INDICADORES
    st.markdown(f"""<div class="indicator-row">
<div class="ind-item"><div class="dot" style="background:#00ff41"></div> PRICE: ${val_real:,.2f}</div>
<div class="ind-item"><div class="dot" style="background:#26a69a"></div> PROJECTED: ${val_proy:,.2f}</div>
<div class="ind-item"><div class="dot" style="background:#2962ff"></div> MA 50d: ${val_sma50:,.2f}</div>
<div class="ind-item"><div class="dot" style="background:#f7931a"></div> MA 200d: ${val_sma200:,.2f}</div>
</div>""", unsafe_allow_html=True)

    # CHART (Log scale by default)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["Fecha"], y=df["SMA 200"], name="MA200d", line=dict(color="#f7931a", width=1.5)))
    fig.add_trace(go.Scatter(x=df["Fecha"], y=df["SMA 50"], name="MA50d", line=dict(color="#2962ff", width=1.5)))
    fig.add_trace(go.Scatter(x=df["Fecha"], y=df["Precio Sintético"], name="Projected", line=dict(color="#26a69a", width=2, dash="dot")))
    fig.add_trace(go.Scatter(x=df_con_precio["Fecha"], y=df_con_precio["Precio Real"], name="Price Real", line=dict(color="#00ff41", width=3)))

    fig.update_layout(
        template="plotly_dark", paper_bgcolor="#0b0e11", plot_bgcolor="#0b0e11",
        height=540, margin=dict(l=0, r=0, t=5, b=0),
        hovermode="x unified",
        xaxis=dict(showgrid=True, gridcolor="#1e222d", tickfont=dict(color="#ffffff", size=12, weight='bold')),
        yaxis=dict(side="right", showgrid=True, gridcolor="#1e222d", tickprefix="$", tickformat=",.0f", tickfont=dict(color="#ffffff", size=11), type="log"),
        legend=dict(orientation="h", yanchor="bottom", y=0.01, xanchor="right", x=0.99, bgcolor="rgba(11, 14, 17, 0.8)")
    )
    st.plotly_chart(fig, use_container_width=True, config={'displaylogo': False})

    # DISCLAIMER BLANCO
    st.markdown("""<div class="disclaimer">
<b>INVESTMENT DISCLAIMER:</b> This analysis is for informational and educational purposes only and does NOT constitute financial, investment, or trading advice. 
Cryptocurrency and stock market trading involves significant risk. Past performance is not indicative of future results. 
Always conduct your own due diligence before making any financial decisions.
</div>""", unsafe_allow_html=True)