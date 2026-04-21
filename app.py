import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, timedelta
import numpy as np

# ─────────────────────────────────────────────────────────────────────────────
#  PAGE CONFIG
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Nasdaq Price Projection",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─────────────────────────────────────────────────────────────────────────────
#  CSS  — ultra minimal, Bitbo-inspired
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

html, body, [class*="css"] {
    background-color: #131722 !important;
    color: #d1d4dc !important;
    font-family: 'Inter', sans-serif !important;
}
header[data-testid="stHeader"]  { display: none; }
[data-testid="stSidebar"]       { background: #1e222d !important; border-right: 1px solid #2a2e39; }
[data-testid="stSidebar"] *     { color: #d1d4dc !important; }
.main .block-container          { padding: 1rem 1.5rem 2rem !important; max-width: 100% !important; }

/* Top bar */
.topbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: .6rem 0 1rem;
    border-bottom: 1px solid #2a2e39;
    margin-bottom: 1rem;
}
.topbar-title {
    font-size: 1.15rem;
    font-weight: 700;
    color: #ffffff;
    letter-spacing: -.01em;
}
.topbar-date {
    font-size: .75rem;
    color: #787b86;
    margin-top: .1rem;
}
.price-main  { font-size: 1.8rem; font-weight: 700; color: #26a69a; font-variant-numeric: tabular-nums; }
.price-delta { font-size: .8rem; margin-top: .1rem; }
.up   { color: #26a69a; }
.down { color: #ef5350; }

/* Legend row */
.legend-row {
    display: flex;
    gap: 1.5rem;
    align-items: center;
    padding: .5rem 0 .6rem;
    font-size: .78rem;
    color: #787b86;
}
.leg-item { display: flex; align-items: center; gap: .45rem; }
.leg-line  { width: 22px; height: 2px; border-radius: 1px; }
.leg-dashed { width: 22px; height: 0px; border-top: 2px dashed; border-radius: 1px; }

/* Stat pills */
.stat-row { display: flex; gap: .8rem; margin: .7rem 0; flex-wrap: wrap; }
.stat-pill {
    background: #1e222d;
    border: 1px solid #2a2e39;
    border-radius: 5px;
    padding: .45rem .9rem;
    font-size: .72rem;
    color: #787b86;
}
.stat-pill b { color: #d1d4dc; font-weight: 600; }

/* Footer */
.footer {
    margin-top: 1.5rem;
    padding-top: .8rem;
    border-top: 1px solid #2a2e39;
    font-size: .72rem;
    color: #ffffff;
    letter-spacing: .04em;
}
.footer a { color: #2962ff !important; text-decoration: none; }

/* Scrollbar */
::-webkit-scrollbar { width: 4px; }
::-webkit-scrollbar-track { background: #131722; }
::-webkit-scrollbar-thumb { background: #2a2e39; border-radius: 2px; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
#  DATA
# ─────────────────────────────────────────────────────────────────────────────
SHEET_KEY = "1-ni2_Fn_-IU9Pka4EJlZH8rpAeLsKMGheJzl3CzLsqU"
WORKSHEET  = "Proyeccion_Maestra"

@st.cache_data(ttl=300, show_spinner=False)
def load_data():
    try:
        raw = dict(st.secrets["connections"]["gsheets"])
        raw.pop("spreadsheet", None)
        sa_keys = [
            "type","project_id","private_key_id","private_key","client_email",
            "client_id","auth_uri","token_uri",
            "auth_provider_x509_cert_url","client_x509_cert_url",
        ]
        info = {k: raw[k] for k in sa_keys if k in raw}
        info.setdefault("type", "service_account")
        creds = Credentials.from_service_account_info(info, scopes=[
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive",
        ])
        gc = gspread.authorize(creds)
        ws = gc.open_by_key(SHEET_KEY).worksheet(WORKSHEET)
        df = pd.DataFrame(ws.get_all_records())
    except Exception as e:
        st.sidebar.warning(f"⚠️ Usando datos demo — {e}")
        return _demo()
    return _clean(df)


def _clean(df):
    # A=Fecha  B=Precio Real  C=Precio Proyectado  D=SMA50  E=SMA200
    mapping = {}
    for c in df.columns:
        cl = str(c).lower().strip()
        if "fecha" in cl or "date" in cl:                                       mapping[c] = "fecha"
        elif ("real" in cl) or (("precio" in cl or "price" in cl)
              and "proy" not in cl and "sint" not in cl):                        mapping[c] = "precio_real"
        elif "proy" in cl or "sint" in cl or "proj" in cl or "synt" in cl:       mapping[c] = "precio_proy"
        elif "50"  in cl:                                                        mapping[c] = "sma50"
        elif "200" in cl:                                                        mapping[c] = "sma200"
    df = df.rename(columns=mapping)
    cols = ["fecha","precio_real","precio_proy","sma50","sma200"]
    if not all(c in df.columns for c in cols) and len(df.columns) >= 5:
        df.columns = cols + list(df.columns[5:])
    df["fecha"] = pd.to_datetime(df["fecha"], dayfirst=True, errors="coerce")
    for c in ["precio_real","precio_proy","sma50","sma200"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df.dropna(subset=["fecha"]).sort_values("fecha").reset_index(drop=True)


def _demo():
    import random; random.seed(42)
    rows, price = [], 12000.0
    base = datetime(2020, 1, 1)
    for i in range(6 * 365):
        d = base + timedelta(days=i)
        price = max(price * random.gauss(1.00055, 0.012), 6000)
        rows.append({"fecha": d, "precio_real": round(price,2),
                     "precio_proy": None, "sma50": None, "sma200": None})
    df = pd.DataFrame(rows)
    df["sma50"]  = df["precio_real"].rolling(50,  min_periods=1).mean().round(2)
    df["sma200"] = df["precio_real"].rolling(200, min_periods=1).mean().round(2)
    last = df["precio_real"].iloc[-1]
    for i in range(1, 4*365):
        d = df["fecha"].iloc[-1] + timedelta(days=i)
        last = max(last * random.gauss(1.00045, 0.008), 6000)
        rows.append({"fecha": d, "precio_real": None,
                     "precio_proy": round(last,2), "sma50": None, "sma200": None})
    return pd.DataFrame(rows).sort_values("fecha").reset_index(drop=True)

# ─────────────────────────────────────────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def fp(v):
    if v is None or (isinstance(v, float) and np.isnan(v)): return "—"
    return f"${v:,.2f}"

def pct(a, b):
    if b and b != 0: return (a - b) / b * 100
    return 0.0

# ─────────────────────────────────────────────────────────────────────────────
#  CHART
# ─────────────────────────────────────────────────────────────────────────────
def build_chart(df, log_scale):
    fig = go.Figure()

    # SMA 200 — naranja (Bitbo style)
    s2 = df[df["sma200"].notna()]
    if not s2.empty:
        fig.add_trace(go.Scatter(
            x=s2["fecha"], y=s2["sma200"], name="SMA 200",
            line=dict(color="#ff9800", width=2),
            hovertemplate="SMA 200: $%{y:,.2f}<extra></extra>",
        ))

    # SMA 50 — azul claro
    s5 = df[df["sma50"].notna()]
    if not s5.empty:
        fig.add_trace(go.Scatter(
            x=s5["fecha"], y=s5["sma50"], name="SMA 50",
            line=dict(color="#5b9cf6", width=2),
            hovertemplate="SMA 50: $%{y:,.2f}<extra></extra>",
        ))

    # Precio Proyectado — verde claro punteado
    pp = df[df["precio_proy"].notna()]
    if not pp.empty:
        fig.add_trace(go.Scatter(
            x=pp["fecha"], y=pp["precio_proy"], name="Precio Proyectado",
            line=dict(color="#26a69a", width=2, dash="dot"),
            hovertemplate="Proyectado: $%{y:,.2f}<extra></extra>",
        ))

    # Precio Real — verde neón (top layer, Bitbo style)
    rr = df[df["precio_real"].notna()]
    if not rr.empty:
        fig.add_trace(go.Scatter(
            x=rr["fecha"], y=rr["precio_real"], name="Price end of day",
            line=dict(color="#4caf50", width=1.5),
            hovertemplate="Precio: $%{y:,.2f}<extra></extra>",
        ))

    # ── Línea vertical fecha actual ──────────────────────────────────────
    today = pd.Timestamp(datetime.now().date())
    if df["fecha"].min() <= today <= df["fecha"].max():
        fig.add_vline(
            x=today.timestamp() * 1000,
            line_color="rgba(255,255,255,0.25)",
            line_dash="dash", line_width=1.5,
            annotation_text=today.strftime("%Y-%m-%d"),
            annotation_font=dict(color="#c8c8c8", size=11, family="Inter"),
            annotation_bgcolor="#2a2e39",
            annotation_bordercolor="#555",
            annotation_borderwidth=1,
            annotation_position="top",
        )

    # ── Anotaciones extremo derecho de cada serie ────────────────────────
    ann_specs = [
        ("precio_real", "#4caf50",  "Price end of day"),
        ("precio_proy", "#26a69a",  "Precio Proyectado"),
        ("sma200",      "#ff9800",  "SMA 200"),
        ("sma50",       "#5b9cf6",  "SMA 50"),
    ]
    annotations = []
    for col, color, label in ann_specs:
        sub = df[df[col].notna()]
        if sub.empty: continue
        row = sub.iloc[-1]
        annotations.append(dict(
            x=row["fecha"], y=row[col],
            xref="x", yref="y",
            text=f"<b>{label}&nbsp;&nbsp;${row[col]:,.2f}</b>",
            showarrow=False,
            xanchor="left", xshift=8,
            font=dict(color=color, size=11, family="Inter, sans-serif"),
            bgcolor="rgba(19,23,34,0.85)",
            bordercolor=color, borderwidth=1, borderpad=4,
        ))

    # Watermark centrado
    annotations.append(dict(
        xref="paper", yref="paper", x=0.5, y=0.5,
        text="Nasdaq Price Projection · Facutom",
        showarrow=False,
        font=dict(size=18, color="rgba(255,255,255,0.03)", family="Inter"),
        align="center",
    ))

    # ── Layout ───────────────────────────────────────────────────────────
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="#131722",
        plot_bgcolor="#131722",
        font=dict(family="Inter, sans-serif", color="#d1d4dc", size=12),
        hovermode="x unified",
        hoverlabel=dict(
            bgcolor="#1e222d", bordercolor="#2a2e39",
            font=dict(family="Inter", size=12),
        ),
        xaxis=dict(
            showgrid=True, gridcolor="#1e222d", gridwidth=1,
            zeroline=False, linecolor="#2a2e39",
            tickfont=dict(size=11, family="Inter"),
            rangeslider=dict(visible=False),
            title="",
            # Range selector buttons — Bitbo style
            rangeselector=dict(
                buttons=[
                    dict(count=1,  label="1A",   step="year",  stepmode="backward"),
                    dict(count=3,  label="3A",   step="year",  stepmode="backward"),
                    dict(count=5,  label="5A",   step="year",  stepmode="backward"),
                    dict(step="all", label="MAX"),
                ],
                bgcolor="#1e222d",
                activecolor="#2962ff",
                bordercolor="#2a2e39",
                borderwidth=1,
                font=dict(size=11, family="Inter", color="#d1d4dc"),
                x=0.0, y=1.03,
            ),
        ),
        yaxis=dict(
            type="log" if log_scale else "linear",
            showgrid=True, gridcolor="#1e222d", gridwidth=1,
            zeroline=False, linecolor="#2a2e39",
            tickfont=dict(size=11, family="Inter"),
            tickprefix="$", tickformat=",.0f",
            side="left",
            title="",
        ),
        legend=dict(
            orientation="v",
            yanchor="bottom", y=0.04,
            xanchor="right",  x=0.99,
            bgcolor="rgba(19,23,34,0.80)",
            bordercolor="#2a2e39", borderwidth=1,
            font=dict(size=11, family="Inter"),
        ),
        margin=dict(l=20, r=140, t=50, b=30),
        height=600,
        annotations=annotations,
        dragmode="zoom",
    )

    return fig

# ─────────────────────────────────────────────────────────────────────────────
#  SIDEBAR  (minimal)
# ─────────────────────────────────────────────────────────────────────────────
def render_sidebar():
    with st.sidebar:
        st.markdown("### ⚙️ Opciones")
        log_scale = st.toggle("Escala logarítmica", value=True)
        st.markdown("---")
        st.markdown("""
        <div style='font-size:.7rem;color:#787b86;line-height:2'>
          <b style='color:#d1d4dc'>Hoja:</b> Proyeccion_Maestra<br>
          <b style='color:#d1d4dc'>Columnas:</b><br>
          &nbsp;A — Fecha<br>
          &nbsp;B — Precio Real<br>
          &nbsp;C — Precio Proyectado<br>
          &nbsp;D — SMA 50<br>
          &nbsp;E — SMA 200
        </div>""", unsafe_allow_html=True)
    return log_scale

# ─────────────────────────────────────────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────────────────────────────────────────
def main():
    log_scale = render_sidebar()

    with st.spinner("Cargando datos..."):
        df = load_data()

    # ── Pull latest values ───────────────────────────────────────────────
    rr   = df[df["precio_real"].notna()]
    pp   = df[df["precio_proy"].notna()]
    s5r  = df[df["sma50"].notna()]
    s2r  = df[df["sma200"].notna()]

    last_real  = rr["precio_real"].iloc[-1]   if not rr.empty  else None
    prev_real  = rr["precio_real"].iloc[-2]   if len(rr) > 1   else last_real
    last_date  = rr["fecha"].iloc[-1]          if not rr.empty  else df["fecha"].iloc[-1]
    last_proy  = pp["precio_proy"].iloc[-1]   if not pp.empty  else None
    last_sma50 = s5r["sma50"].iloc[-1]         if not s5r.empty else None
    last_sma200= s2r["sma200"].iloc[-1]        if not s2r.empty else None

    d_abs  = (last_real - prev_real) if (last_real and prev_real) else 0
    d_pct  = pct(last_real, prev_real)
    d_cls  = "up" if d_pct >= 0 else "down"
    d_arr  = "▲" if d_pct >= 0 else "▼"

    # ── TOP BAR ─────────────────────────────────────────────────────────
    st.markdown(f"""
    <div class="topbar">
      <div>
        <div class="topbar-title">📈 Nasdaq Price Projection</div>
        <div class="topbar-date">{last_date.strftime('%A %d %B %Y').upper()}</div>
      </div>
      <div style="text-align:right">
        <div class="price-main">{fp(last_real)}</div>
        <div class="price-delta">
          <span class="{d_cls}">{d_arr} {fp(abs(d_abs))} &nbsp;({d_pct:+.2f}%)</span>
          <span style="color:#787b86;font-size:.72rem"> vs día anterior</span>
        </div>
      </div>
    </div>""", unsafe_allow_html=True)

    # ── LEGEND ROW ───────────────────────────────────────────────────────
    st.markdown(f"""
    <div class="legend-row">
      <div class="leg-item">
        <div class="leg-line" style="background:#4caf50"></div>
        <span>Price end of day &nbsp;<b style="color:#4caf50">{fp(last_real)}</b></span>
      </div>
      <div class="leg-item">
        <div class="leg-dashed" style="border-color:#26a69a;width:22px"></div>
        <span>Precio Proyectado &nbsp;<b style="color:#26a69a">{fp(last_proy)}</b></span>
      </div>
      <div class="leg-item">
        <div class="leg-line" style="background:#ff9800"></div>
        <span>SMA 200 &nbsp;<b style="color:#ff9800">{fp(last_sma200)}</b></span>
      </div>
      <div class="leg-item">
        <div class="leg-line" style="background:#5b9cf6"></div>
        <span>SMA 50 &nbsp;<b style="color:#5b9cf6">{fp(last_sma50)}</b></span>
      </div>
    </div>""", unsafe_allow_html=True)

    # ── CHART ────────────────────────────────────────────────────────────
    fig = build_chart(df, log_scale)
    st.plotly_chart(fig, width='stretch', config={
        "displayModeBar": True,
        "displaylogo":    False,
        "scrollZoom":     True,
        "modeBarButtonsToRemove": ["autoScale2d","lasso2d","select2d"],
        "toImageButtonOptions": {
            "format":   "png",
            "filename": "nasdaq_projection",
            "width":    1800,
            "height":   700,
            "scale":    2,
        },
    })

    # ── STAT PILLS ───────────────────────────────────────────────────────
    real_s = df[df["precio_real"].notna()]["precio_real"]
    vol    = real_s.pct_change().std() * np.sqrt(252) * 100 if len(real_s) > 30 else 0
    gap200 = pct(last_real, last_sma200) if (last_real and last_sma200) else 0
    gap50  = pct(last_real, last_sma50)  if (last_real and last_sma50)  else 0
    n_real = df["precio_real"].notna().sum()
    n_proy = df["precio_proy"].notna().sum()
    all_time_high = real_s.max() if not real_s.empty else 0
    drawdown = pct(last_real, all_time_high) if last_real else 0

    st.markdown(f"""
    <div class="stat-row">
      <div class="stat-pill">All-Time High &nbsp;<b>{fp(all_time_high)}</b></div>
      <div class="stat-pill">Drawdown vs ATH &nbsp;<b class="{'down' if drawdown < 0 else 'up'}">{drawdown:+.1f}%</b></div>
      <div class="stat-pill">vs SMA 200 &nbsp;<b class="{'up' if gap200 >= 0 else 'down'}">{gap200:+.1f}%</b></div>
      <div class="stat-pill">vs SMA 50 &nbsp;<b class="{'up' if gap50 >= 0 else 'down'}">{gap50:+.1f}%</b></div>
      <div class="stat-pill">Volatilidad anual &nbsp;<b>{vol:.1f}%</b></div>
      <div class="stat-pill">Días de datos &nbsp;<b>{n_real}</b> reales · <b>{n_proy}</b> proyectados</div>
    </div>""", unsafe_allow_html=True)

    # ── FOOTER ───────────────────────────────────────────────────────────
    st.markdown("""
    <div class="footer">
      NASDAQ PRICE PROJECTION &nbsp;·&nbsp;
      Creado por <a href="https://linktr.ee/facutom" target="_blank">Facutom</a>
      &nbsp;·&nbsp; Datos: Google Sheets &nbsp;·&nbsp; Actualización diaria
    </div>""", unsafe_allow_html=True)


if __name__ == "__main__":
    main()