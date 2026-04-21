import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px

# 1. Configuración de página con estética "Terminal Bloomberg"
st.set_page_config(page_title="Capital Flow Tracker", page_icon="🌐", layout="wide")

# CSS personalizado para colores financieros sobrios
st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    [data-testid="stMetricValue"] { font-family: 'JetBrains Mono', monospace; font-size: 36px; color: #ffffff; }
    .stMetric { background-color: #1e2227; padding: 15px; border-radius: 10px; border-left: 5px solid #3b82f6; }
    </style>
    """, unsafe_allow_html=True)

st.title("📊 Global Capital Flow Tracker")
st.markdown("---")

try:
    # 2. Conexión y Limpieza Quirúrgica
    conn = st.connection("gsheets", type=GSheetsConnection)
    df_raw = conn.read(worksheet="Flujo_Diario")
    
    # Filtramos la fila de "Total" para que no sesgue los gráficos
    df = df_raw[df_raw['Región'] != 'Total'].copy()
    
    # Convertimos a número quitando posibles caracteres extraños
    for col in ['Market Cap Hoy (T)', 'Variación %']:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    # 3. Métricas de Alto Impacto (Storytelling)
    ganador = df.sort_values(by='Variación %', ascending=False).iloc[0]
    perdedor = df.sort_values(by='Variación %', ascending=True).iloc[0]

    # Contenedor de Insights con lógica de color
    with st.container():
        st.subheader("💡 Market Insights")
        c1, c2 = st.columns(2)
        c1.success(f"**Top Inflow:** {ganador['Región']} lidera la captura de capital (+{ganador['Variación %']:.2%})")
        c2.error(f"**Top Outflow:** {perdedor['Región']} presenta la mayor fuga relativa ({perdedor['Variación %']:.2%})")

    st.markdown("### Monitor Regional")
    
    # 4. Grid de Métricas con diseño limpio
    cols = st.columns(len(df))
    for i, row in df.iterrows():
        with cols[i % len(df)]:
            st.metric(
                label=row['Región'],
                value=f"{row['Market Cap Hoy (T)']:,.2f} T",
                delta=f"{row['Variación %']:.2%}"
            )

    st.markdown("---")

    # 5. Visualización Avanzada (Plotly en lugar de gráficos básicos)
    col_chart1, col_chart2 = st.columns([2, 1])

    with col_chart1:
        st.subheader("Distribución de Dominancia vs. Variación")
        # Usamos un gráfico de burbujas para dar más dimensión
        fig = px.scatter(df, 
                         x="Market Cap Hoy (T)", 
                         y="Variación %", 
                         size="Market Cap Hoy (T)", 
                         color="Región",
                         hover_name="Región", 
                         log_x=False, 
                         size_max=60,
                         template="plotly_dark",
                         color_discrete_sequence=px.colors.qualitative.Safe)
        
        fig.add_hline(y=0, line_dash="dash", line_color="gray")
        st.plotly_chart(fig, use_container_width=True)

    with col_chart2:
        st.subheader("Participación por Bloque")
        fig_pie = px.pie(df, values='Market Cap Hoy (T)', names='Región', 
                         hole=.4, template="plotly_dark",
                         color_discrete_sequence=px.colors.qualitative.Pastel)
        fig_pie.update_traces(textinfo='percent+label')
        st.plotly_chart(fig_pie, use_container_width=True)

except Exception as e:
    st.error("Error al procesar los datos. Verifica que en Google Sheets los números no tengan texto ni símbolos de '%' escritos a mano.")
    st.info("Tip: La columna 'Variación %' debe tener valores como 0.015 para representar 1.5%")