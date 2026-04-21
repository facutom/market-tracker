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
    page_title="Nasdaq Price Projection",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# CSS Estilo Bitbo Compacto y Centrado
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');

html, body, [class*="css"] {
    background-color: #0b0e11 !important;
    color: #d1d4dc !important;
    font-family: 'Inter', sans-serif !important;
}
header[data-testid="stHeader"]  { display: none; }

/* Reducción de espacios arriba y abajo */
.main .block-container { 
    padding: 0.5rem 1.5rem !important; 
    max-width: 100% !important; 
}

/* Encabezado Centrado */
.header-centered { 
    text-align: center; 
    margin-bottom: 0.5rem; 
}
.main-title { 
    font-size: 2rem; 
    font-weight: 700; 
    color: #ffffff; 
    margin-bottom: 0px;
}
.date-sub { 
    font-size: 0.9rem; 
    color: #787b86; 
    text-transform: uppercase;
    margin-bottom: 2px;
}
.author { font-size: 0.8rem; color: #d1d4dc; margin-bottom: 10px; }
.author a { color: #2962ff !important; text-decoration: none; font-weight: 600; }

/* Precio y Variación */
.price-box { text-align: center; margin-bottom: 1rem; }
.price-big { font-size: 3rem; font-weight: 700; color: #00ff41; line-height: 1; }
.price-delta { font-size: 1rem; font-weight: 600; margin-top: 5px; }
.up { color: #00ff41; } .down { color: #f23645; }

/* Fila de Indicadores */
.indicator-row {
    display: flex;
    justify-content: center;
    gap: 25px;
    margin-bottom: 10px;
    font-size: 0.85rem;
    font-weight: 600;
    color: #ffffff;
}
.ind-item { display: flex; align-items: center; gap: 8px; }
.dot { width: 10px; height: 10px; border-radius: 50%; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
#  DATA LOADING & CLEANING
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

        # Limpieza de números
        for col in ["Precio Real", "Precio Sintético", "SMA 50", "SMA 200"]:
            if col in df.columns:
                df[col] = df[col].astype(str).str.replace(',', '.').str.replace(r'[^0-9.-]', '', regex=True)
                df[col] = pd.to_numeric(df[col], errors="coerce")
        
        df["Fecha"] = pd.to_datetime(df["Fecha"], dayfirst=True, errors="coerce")
        return df.dropna(subset=["Fecha"]).sort_values("Fecha").reset_index(drop=True)
    except Exception as e:
        st.error(f"Error de conexión: {e}")
        return pd.DataFrame()

# ─────────────────────────────────────────────────────────────────────────────
#  LÓGICA DE DATOS PARA "HOY"
# ─────────────────────────────────────────────────────────────────────────────
df = load_data()

if not df.empty:
    # 1. Encontrar la última fila que tiene un "Precio Real" (el día de hoy en los datos)
    df_con_precio = df[df["Precio Real"].notna() & (df["Precio Real"] > 0)]
    
    if not df_con_precio.empty:
        last_row_today = df_con_precio.iloc[-1]
        idx_today = df_con_precio.index[-1]
        
        # Valores exactos de ESA fila (para que coincidan todos los indicadores)
        val_real = last_row_today["Precio Real"]
        val_date = last_row_today["Fecha"]
        val_sma50 = last_row_today["SMA 50"]
        val_sma200 = last_row_today["SMA 200"]
        val_proy = last_row_today["Precio Sintético"]
        
        # Variación vs fila anterior
        prev_val = df_con_precio["Precio Real"].iloc[-2] if len(df_con_precio) > 1 else val_real
        delta_abs = val_real - prev_val
        delta_pct = (delta_abs / prev_val * 100)
    else:
        st.error("No hay datos de precio real en la hoja.")
        st.stop()

    # ENCABEZADO CENTRADO
    st.markdown(f"""
    <div class="header-centered">
        <div class="main-title">Nasdaq Price Projection</div>
        <div class="date-sub">{val_date.strftime('%A %d %B %Y')}</div>
        <div class="author">Creado por <a href="https://linktr.ee/facutom" target="_blank">Facutom</a></div>
    </div>
    <div class="price-box">
        <div class="price-big">${val_real:,.2f}</div>
        <div class="price-delta {'up' if delta_abs >= 0 else 'down'}">
            {'▲' if delta_abs >= 0 else '▼'} ${abs(delta_abs):,.2f} ({delta_pct:+.2f}%)
            <span style="color:#787b86; font-weight:400; font-size:0.8rem"> vs día anterior</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # INDICADORES SINCRONIZADOS (Valores de la misma fecha que el precio real)
    st.markdown(f"""
    <div class="indicator-row">
        <div class="ind-item"><div class="dot" style="background:#00ff41"></div> PRECIO: ${val_real:,.2f}</div>
        <div class="ind-item"><div class="dot" style="background:#26a69a"></div> PROYECTADO: ${val_proy:,.2f}</div>
        <div class="ind-item"><div class="dot" style="background:#2962ff"></div> MA 50d: ${val_sma50:,.2f}</div>
        <div class="ind-item"><div class="dot" style="background:#f7931a"></div> MA 200d: ${val_sma200:,.2f}</div>
    </div>
    """, unsafe_allow_html=True)

    # GRÁFICO
    fig = go.Figure()

    # Líneas de Medias Móviles
    fig.add_trace(go.Scatter(x=df["Fecha"], y=df["SMA 200"], name="MA200d", line=dict(color="#f7931a", width=1.5)))
    fig.add_trace(go.Scatter(x=df["Fecha"], y=df["SMA 50"], name="MA50d", line=dict(color="#2962ff", width=1.5)))
    
    # Línea Proyectada (Toda la serie)
    fig.add_trace(go.Scatter(
        x=df["Fecha"], y=df["Precio Sintético"], name="Proyectado",
        line=dict(color="#26a69a", width=2, dash="dot")
    ))

    # Línea Real (Solo hasta hoy)
    fig.add_trace(go.Scatter(
        x=df_con_precio["Fecha"], y=df_con_precio["Precio Real"], name="Precio Real",
        line=dict(color="#00ff41", width=2.5)
    ))

    # Layout
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="#0b0e11",
        plot_bgcolor="#0b0e11",
        height=600,
        margin=dict(l=10, r=10, t=10, b=10),
        hovermode="x unified",
        xaxis=dict(
            showgrid=True, gridcolor="#1e222d", 
            tickfont=dict(color="#ffffff", size=12, weight='bold'), # Eje X más blanco y visible
            linecolor="#434651"
        ),
        yaxis=dict(
            side="right", showgrid=True, gridcolor="#1e222d",
            tickprefix="$", tickformat=",.0f",
            tickfont=dict(color="#ffffff", size=11),
            type="log"
        ),
        legend=dict(
            orientation="v", yanchor="bottom", y=0.05, xanchor="right", x=0.98,
            bgcolor="rgba(19, 23, 34, 0.9)", bordercolor="#2a2e39", borderwidth=1
        )
    )

    st.plotly_chart(fig, use_container_width=True, config={'displaylogo': False})

    # Selector de escala en la sidebar para no ocupar espacio arriba
    st.sidebar.radio("Escala Y", ["Logarítmica", "Lineal"], key="scale_option")
    if st.session_state.scale_option == "Lineal":
        fig.update_layout(yaxis_type="linear")
        st.rerun()