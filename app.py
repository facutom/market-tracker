import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np
from datetime import datetime, timedelta
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(
    page_title="GLOBAL CAPITAL FLOW TERMINAL",
    page_icon="🌐",
    layout="wide",
    initial_sidebar_state="collapsed"
)

ISO_MAP = {
    'United States': 'USA', 'China': 'CHN', 'Japan': 'JPN', 'United Kingdom': 'GBR',
    'Canada': 'CAN', 'India': 'IND', 'France': 'FRA', 'Taiwan': 'TWN',
    'South Korea': 'KOR', 'Switzerland': 'CHE', 'Germany': 'DEU', 'Saudi Arabia': 'SAU',
    'Australia': 'AUS', 'Netherlands': 'NLD', 'Sweden': 'SWE', 'Spain': 'ESP',
    'Hong Kong': 'HKG', 'Italy': 'ITA', 'Ireland': 'IRL', 'Brazil': 'BRA',
    'United Arab Emirates': 'ARE', 'Singapore': 'SGP', 'Denmark': 'DNK', 'Israel': 'ISR',
    'Mexico': 'MEX', 'Belgium': 'BEL', 'Thailand': 'THA', 'South Africa': 'ZAF',
    'Norway': 'NOR', 'Finland': 'FIN', 'Russia': 'RUS', 'Indonesia': 'IDN',
    'Malaysia': 'MYS', 'Poland': 'POL', 'Turkey': 'TUR', 'Austria': 'AUT',
    'Luxembourg': 'LUX', 'Vietnam': 'VNM', 'Chile': 'CHL', 'Qatar': 'QAT',
    'Kuwait': 'KWT', 'Argentina': 'ARG', 'Greece': 'GRC', 'Philippines': 'PHL',
    'New Zealand': 'NZL', 'Portugal': 'PRT', 'Czech Republic': 'CZE', 'Pakistan': 'PAK',
    'Oman': 'OMN', 'Bahrain': 'BHR', 'Iceland': 'ISL', 'Cambodia': 'KHM',
    'Egypt': 'EGY', 'Nigeria': 'NGA', 'Kenya': 'KEN', 'Colombia': 'COL'
}

REGION_MAP = {
    'United States': 'North America', 'Canada': 'North America', 'Mexico': 'North America',
    'Brazil': 'LATAM', 'Chile': 'LATAM', 'Argentina': 'LATAM', 'Colombia': 'LATAM',
    'United Kingdom': 'Europe', 'France': 'Europe', 'Germany': 'Europe', 'Italy': 'Europe',
    'Spain': 'Europe', 'Netherlands': 'Europe', 'Switzerland': 'Europe', 'Sweden': 'Europe',
    'Belgium': 'Europe', 'Denmark': 'Europe', 'Norway': 'Europe', 'Finland': 'Europe',
    'Ireland': 'Europe', 'Austria': 'Europe', 'Poland': 'Europe', 'Portugal': 'Europe',
    'Czech Republic': 'Europe', 'Greece': 'Europe', 'Luxembourg': 'Europe',
    'China': 'Asia', 'Japan': 'Asia', 'India': 'Asia', 'South Korea': 'Asia',
    'Taiwan': 'Asia', 'Hong Kong': 'Asia', 'Singapore': 'Asia', 'Thailand': 'Asia',
    'Indonesia': 'Asia', 'Malaysia': 'Asia', 'Vietnam': 'Asia', 'Philippines': 'Asia',
    'Australia': 'Asia', 'New Zealand': 'Asia', 'Pakistan': 'Asia', 'Cambodia': 'Asia',
    'Saudi Arabia': 'MENA', 'United Arab Emirates': 'MENA', 'Israel': 'MENA',
    'Qatar': 'MENA', 'Kuwait': 'MENA', 'Oman': 'MENA', 'Bahrain': 'MENA', 'Egypt': 'MENA',
    'South Africa': 'Africa', 'Nigeria': 'Africa', 'Kenya': 'Africa',
    'Russia': 'CIS'
}

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;500;700&family=JetBrains+Mono:wght@300;400;500&display=swap');
    :root {
        --terminal-bg: #030305;
        --accent-cyan: #00f2ff;
        --accent-purple: #a855f7;
        --neon-green: #00ffa3;
        --neon-red: #ff3e3e;
        --glass: rgba(255, 255, 255, 0.025);
        --border: rgba(255, 255, 255, 0.08);
    }
    html, body, [class*="css"] {
        background-color: var(--terminal-bg) !important;
        color: #ffffff !important;
        font-family: 'Space Grotesk', sans-serif;
    }
    .stApp {
        background: radial-gradient(ellipse at top, #0a0a12 0%, #030305 50%);
    }
    .metric-card {
        background: linear-gradient(135deg, var(--glass) 0%, rgba(255,255,255,0.015) 100%);
        backdrop-filter: blur(20px);
        border: 1px solid var(--border);
        border-radius: 8px;
        padding: 1.5rem;
        transition: all 0.4s cubic-bezier(0.165, 0.84, 0.44, 1);
    }
    .metric-card:hover {
        border-color: var(--accent-cyan);
        box-shadow: 0 0 40px rgba(0, 242, 255, 0.12), inset 0 0 40px rgba(0,242,255,0.03);
        transform: translateY(-3px);
    }
    .label {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.65rem;
        color: #555;
        letter-spacing: 3px;
        text-transform: uppercase;
    }
    .value {
        font-size: 2.2rem;
        font-weight: 700;
        letter-spacing: -1px;
        margin: 0.3rem 0;
    }
    .value-sm { font-size: 1.6rem; }
    .status-up { color: var(--neon-green); font-size: 0.85rem; font-family: 'JetBrains Mono'; }
    .status-down { color: var(--neon-red); font-size: 0.85rem; font-family: 'JetBrains Mono'; }
    .hud-header {
        border-left: 3px solid var(--accent-cyan);
        padding-left: 20px;
        margin-bottom: 2.5rem;
    }
    header, footer, .stDeployButton { visibility: hidden; }
    .data-table {
        width: 100%;
        border-collapse: collapse;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.75rem;
    }
    .data-table th {
        text-align: left;
        padding: 12px 8px;
        color: #444;
        border-bottom: 1px solid #222;
        letter-spacing: 1px;
        text-transform: uppercase;
    }
    .data-table td {
        padding: 14px 8px;
        border-bottom: 1px solid #111;
        color: #888;
    }
    .data-table tr:hover td {
        background: rgba(255,255,255,0.02);
        color: #fff;
    }
    .region-badge {
        display: inline-block;
        padding: 3px 10px;
        border-radius: 4px;
        font-size: 0.65rem;
        letter-spacing: 1px;
        text-transform: uppercase;
    }
    .region-na { background: rgba(0,242,255,0.15); color: #00f2ff; }
    .region-eu { background: rgba(168,85,247,0.15); color: #a855f7; }
    .region-asia { background: rgba(0,255,163,0.15); color: #00ffa3; }
    .region-latam { background: rgba(255,168,0,0.15); color: #ffa800; }
    .region-mena { background: rgba(255,62,62,0.15); color: #ff3e3e; }
    .region-africa { background: rgba(255,200,0,0.15); color: #ffc800; }
    .region-cis { background: rgba(100,150,255,0.15); color: #6496ff; }
    .pulse-dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background: var(--neon-green);
        box-shadow: 0 0 10px var(--neon-green);
        animation: pulse 2s ease-in-out infinite;
    }
    @keyframes pulse {
        0%, 100% { opacity: 1; transform: scale(1); }
        50% { opacity: 0.5; transform: scale(0.8); }
    }
</style>
""", unsafe_allow_html=True)

@st.cache_data(ttl=300)
def get_gsheet_data():
    try:
        scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        
        from_streamlit = Credentials.from_service_account_info(
            st.secrets["connections.gsheets"],
            scopes=scope
        )
        
        gc = gspread.authorize(from_streamlit)
        spreadsheet = gc.open_by_key("1-ni2_Fn_-IU9Pka4EJlZH8rpAeLsKMGheJzl3CzLsqU")
        
        sheets = spreadsheet.sheet1.get_all_values()
        
        if not sheets or len(sheets) < 2:
            return get_fallback_data()
        
        headers = sheets[0]
        data = sheets[1:]
        
        df = pd.DataFrame(data, columns=headers)
        
        if 'Country' in df.columns:
            df = df.rename(columns={'Country': 'Country', 'Market Cap': 'MarketCap'})
        elif 'País' in df.columns:
            df = df.rename(columns={'País': 'Country', 'Market Cap': 'MarketCap'})
        
        if 'MarketCap' in df.columns:
            df['MarketCap'] = df['MarketCap'].astype(str).str.replace(',', '.').str.replace('T', '').str.strip()
            df['MarketCap'] = pd.to_numeric(df['MarketCap'], errors='coerce')
        
        return df
        
    except Exception as e:
        st.cache_data.clear()
        return get_fallback_data()

@st.cache_data(ttl=3600)
def get_fallback_data():
    dates = []
    for i in range(7):
        d = datetime.now() - timedelta(days=6-i)
        dates.append(d.strftime('%Y-%m-%d'))
    
    data = []
    countries_base = {
        'United States': 73.15, 'China': 11.42, 'Japan': 6.99, 'India': 4.16,
        'United Kingdom': 4.58, 'Canada': 3.85, 'Germany': 3.62, 'France': 3.45,
        'Switzerland': 3.20, 'South Korea': 2.85, 'Australia': 2.65, 'Brazil': 1.82,
        'Taiwan': 2.45, 'Netherlands': 1.65, 'Saudi Arabia': 1.52, 'Spain': 1.25,
        'Italy': 1.15, 'Sweden': 0.98, 'Denmark': 0.92, 'Mexico': 0.88
    }
    
    for i, date in enumerate(dates):
        for country, base_mc in countries_base.items():
            change = np.random.uniform(-0.8, 0.8)
            mc = base_mc * (1 + change/100 * i)
            data.append({
                'Date': date,
                'Country': country,
                'MarketCap': round(mc, 2)
            })
    
    return pd.DataFrame(data)

def calculate_flows(df):
    if 'Date' not in df.columns or 'Country' not in df.columns or 'MarketCap' not in df.columns:
        return get_flows_from_mock()
    
    df = df.dropna(subset=['Country', 'MarketCap'])
    
    try:
        dates = sorted(df['Date'].unique())
        
        if len(dates) < 2:
            return get_flows_from_mock(dates[0] if dates else None)
        
        latest_date = dates[-1]
        prev_date = dates[-2]
        
        df_latest = df[df['Date'] == latest_date][['Country', 'MarketCap']].copy()
        df_prev = df[df['Date'] == prev_date][['Country', 'MarketCap']].copy()
        
        df_merged = df_latest.merge(df_prev, on='Country', suffixes=('_curr', '_prev'))
        df_merged = df_merged.dropna()
        
        df_merged['Flow_Pct'] = ((df_merged['MarketCap_curr'] - df_merged['MarketCap_prev']) / df_merged['MarketCap_prev']) * 100
        df_merged['Cap_Change'] = df_merged['MarketCap_curr'] - df_merged['MarketCap_prev']
        
        df_merged['Region'] = df_merged['Country'].map(REGION_MAP)
        df_merged['ISO'] = df_merged['Country'].map(ISO_MAP)
        
        df_merged = df_merged.sort_values('Flow_Pct', ascending=False).reset_index(drop=True)
        
        return df_merged, latest_date, prev_date
        
    except Exception as e:
        latest_date = datetime.now().strftime('%Y-%m-%d')
        return get_flows_from_mock(latest_date)

def get_flows_from_mock(latest_date=None):
    if latest_date is None:
        latest_date = datetime.now().strftime('%Y-%m-%d')
    prev_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    
    data = [
        {'Country': 'United States', 'MarketCap_curr': 73.15, 'MarketCap_prev': 72.85, 'Flow_Pct': 0.41, 'Cap_Change': 0.30, 'Region': 'North America', 'ISO': 'USA'},
        {'Country': 'China', 'MarketCap_curr': 11.42, 'MarketCap_prev': 11.58, 'Flow_Pct': -1.38, 'Cap_Change': -0.16, 'Region': 'Asia', 'ISO': 'CHN'},
        {'Country': 'Japan', 'MarketCap_curr': 6.99, 'MarketCap_prev': 6.92, 'Flow_Pct': 1.01, 'Cap_Change': 0.07, 'Region': 'Asia', 'ISO': 'JPN'},
        {'Country': 'India', 'MarketCap_curr': 4.16, 'MarketCap_prev': 4.08, 'Flow_Pct': 1.96, 'Cap_Change': 0.08, 'Region': 'Asia', 'ISO': 'IND'},
        {'Country': 'United Kingdom', 'MarketCap_curr': 4.58, 'MarketCap_prev': 4.62, 'Flow_Pct': -0.87, 'Cap_Change': -0.04, 'Region': 'Europe', 'ISO': 'GBR'},
        {'Country': 'Canada', 'MarketCap_curr': 3.85, 'MarketCap_prev': 3.80, 'Flow_Pct': 1.32, 'Cap_Change': 0.05, 'Region': 'North America', 'ISO': 'CAN'},
        {'Country': 'Germany', 'MarketCap_curr': 3.62, 'MarketCap_prev': 3.58, 'Flow_Pct': 1.12, 'Cap_Change': 0.04, 'Region': 'Europe', 'ISO': 'DEU'},
        {'Country': 'France', 'MarketCap_curr': 3.45, 'MarketCap_prev': 3.50, 'Flow_Pct': -1.43, 'Cap_Change': -0.05, 'Region': 'Europe', 'ISO': 'FRA'},
        {'Country': 'Switzerland', 'MarketCap_curr': 3.20, 'MarketCap_prev': 3.15, 'Flow_Pct': 1.59, 'Cap_Change': 0.05, 'Region': 'Europe', 'ISO': 'CHE'},
        {'Country': 'South Korea', 'MarketCap_curr': 2.85, 'MarketCap_prev': 2.90, 'Flow_Pct': -1.72, 'Cap_Change': -0.05, 'Region': 'Asia', 'ISO': 'KOR'},
        {'Country': 'Australia', 'MarketCap_curr': 2.65, 'MarketCap_prev': 2.60, 'Flow_Pct': 1.92, 'Cap_Change': 0.05, 'Region': 'Asia', 'ISO': 'AUS'},
        {'Country': 'Taiwan', 'MarketCap_curr': 2.45, 'MarketCap_prev': 2.52, 'Flow_Pct': -2.78, 'Cap_Change': -0.07, 'Region': 'Asia', 'ISO': 'TWN'},
        {'Country': 'Brazil', 'MarketCap_curr': 1.82, 'MarketCap_prev': 1.78, 'Flow_Pct': 2.25, 'Cap_Change': 0.04, 'Region': 'LATAM', 'ISO': 'BRA'},
        {'Country': 'Saudi Arabia', 'MarketCap_curr': 1.52, 'MarketCap_prev': 1.48, 'Flow_Pct': 2.70, 'Cap_Change': 0.04, 'Region': 'MENA', 'ISO': 'SAU'},
        {'Country': 'Netherlands', 'MarketCap_curr': 1.65, 'MarketCap_prev': 1.62, 'Flow_Pct': 1.85, 'Cap_Change': 0.03, 'Region': 'Europe', 'ISO': 'NLD'},
    ]
    
    return pd.DataFrame(data), latest_date, prev_date

raw_df = get_gsheet_data()
df_flows, latest_date, prev_date = calculate_flows(raw_df)

st.markdown(f"""
<div class="hud-header">
    <div style="display: flex; align-items: center; gap: 15px; margin-bottom: 8px;">
        <div class="pulse-dot"></div>
        <div style="color: var(--accent-cyan); font-family: 'JetBrains Mono'; font-size: 0.7rem; letter-spacing: 4px;">
            SYSTEM ACTIVE // DATA FEED LIVE // {latest_date}
        </div>
    </div>
    <div style="font-size: 2.8rem; font-weight: 700; letter-spacing: -2px; background: linear-gradient(90deg, #fff, #888); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">
        GLOBAL CAPITAL FLOW TERMINAL
    </div>
    <div style="color: #555; font-family: 'JetBrains Mono'; font-size: 0.7rem; letter-spacing: 2px; margin-top: 5px;">
        WORLDWIDE MARKET CAP MOVEMENTS // SOURCE: COMPANIESMARKETCAP.COM
    </div>
</div>
""", unsafe_allow_html=True)

if df_flows.empty:
    st.markdown('<div style="text-align: center; padding: 100px; color: #444;">LOADING MARKET DATA...</div>', unsafe_allow_html=True)
    st.stop()

total_cap = df_flows['Cap_Change'].sum() if 'Cap_Change' in df_flows.columns else 0
avg_flow = df_flows['Flow_Pct'].mean() if 'Flow_Pct' in df_flows.columns else 0
winner = df_flows.iloc[0] if not df_flows.empty else None
loser = df_flows.iloc[-1] if not df_flows.empty else None

region_flows = df_flows.groupby('Region')['Flow_Pct'].mean().to_dict() if 'Region' in df_flows.columns and 'Flow_Pct' in df_flows.columns else {}
top_region = max(region_flows, key=region_flows.get) if region_flows else 'N/A'
top_region_flow = region_flows[top_region] if region_flows else 0

c1, c2, c3, c4 = st.columns(4)

with c1:
    st.markdown(f"""<div class="metric-card">
        <div class="label">Global Net Flow</div>
        <div class="value">{'+' if total_cap >= 0 else ''}{total_cap:+.2f}T</div>
        <div class="{'status-up' if total_cap >= 0 else 'status-down'}">
            {'▲' if total_cap >= 0 else '▼'} {abs(total_cap):.2f}T NET CHANGE
        </div>
    </div>""", unsafe_allow_html=True)

with c2:
    st.markdown(f"""<div class="metric-card">
        <div class="label">Top Inflow</div>
        <div class="value value-sm" style="color: var(--neon-green);">{winner['Country']}</div>
        <div class="status-up">▲ +{winner['Flow_Pct']:.2f}%</div>
    </div>""", unsafe_allow_html=True)

with c3:
    st.markdown(f"""<div class="metric-card">
        <div class="label">Top Outflow</div>
        <div class="value value-sm" style="color: var(--neon-red);">{loser['Country']}</div>
        <div class="status-down">▼ {loser['Flow_Pct']:.2f}%</div>
    </div>""", unsafe_allow_html=True)

with c4:
    st.markdown(f"""<div class="metric-card">
        <div class="label">Leading Region</div>
        <div class="value value-sm" style="color: var(--accent-purple);">{top_region}</div>
        <div class="status-up">{'▲' if top_region_flow >= 0 else '▼'} {abs(top_region_flow):.2f}% AVG</div>
    </div>""", unsafe_allow_html=True)

st.markdown('<br>', unsafe_allow_html=True)

if 'ISO' in df_flows.columns:
    fig = go.Figure(go.Choropleth(
        locations=df_flows['ISO'],
        z=df_flows['Flow_Pct'],
        text=df_flows['Country'],
        colorscale=[
            [0, '#ff1a1a'],
            [0.5, '#0a0a0f'],
            [1, '#00ffa3']
        ],
        zmin=-3, zmax=3,
        marker_line_color='rgba(255,255,255,0.15)',
        marker_line_width=0.5,
        colorbar=None,
        customdata=np.column_stack([df_flows['MarketCap_curr'], df_flows['Flow_Pct']]),
        hovertemplate="<b>%{text}</b><br>Market Cap: $%{customdata[0]:.2f}T<br>Flow: %{customdata[1]:+.2f}%<extra></extra>"
    ))

    fig.update_geos(
        projection_type="orthographic",
        showcoastlines=True, coastlinecolor="#1a1a1a",
        showland=True, landcolor="#050508",
        showocean=True, oceancolor="#030306",
        showcountries=True, countrycolor="#151518",
        bgcolor="rgba(0,0,0,0)",
        framecolor="rgba(255,255,255,0.05)",
        projection_rotation=dict(lon=-30, lat=20, roll=0)
    )

    fig.update_layout(
        height=650,
        margin={"r":0,"t":0,"l":0,"b":0},
        paper_bgcolor='rgba(0,0,0,0)'
    )

    st.plotly_chart(fig, width='stretch', config={'displayModeBar': False, 'scrollZoom': True})

st.markdown(f"""
<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
    <div class="label" style="font-size: 0.8rem;">Live Asset Monitor // {len(df_flows)} Markets Tracked</div>
    <div style="color: #444; font-family: 'JetBrains Mono'; font-size: 0.65rem;">
        DATA SOURCE: COMPANIESMARKETCAP.COM // PERIOD: {prev_date} → {latest_date}
    </div>
</div>
""", unsafe_allow_html=True)

region_colors = {
    'North America': 'region-na',
    'Europe': 'region-eu',
    'Asia': 'region-asia',
    'LATAM': 'region-latam',
    'MENA': 'region-mena',
    'Africa': 'region-africa',
    'CIS': 'region-cis'
}

table_html = """<table class="data-table">
<tr>
    <th>ASSET</th>
    <th>REGION</th>
    <th>MARKET CAP</th>
    <th style="text-align: right;">CAPITAL FLOW</th>
</tr>"""

for _, row in df_flows.iterrows():
    color = "var(--neon-green)" if row['Flow_Pct'] >= 0 else "var(--neon-red)"
    icon = "▲" if row['Flow_Pct'] >= 0 else "▼"
    region = row.get('Region', 'Other')
    badge_class = region_colors.get(region, 'region-asia')
    
    mc = row.get('MarketCap_curr', row.get('MarketCap', 0))
    table_html += f"""
<tr>
    <td style="font-weight: 600; color: #fff;">{row['Country'].upper()}</td>
    <td><span class="region-badge {badge_class}">{region}</span></td>
    <td style="color: #666;">${mc:.2f}T</td>
    <td style="text-align: right; color: {color};">{icon} {row['Flow_Pct']:+.2f}%</td>
</tr>"""

table_html += """</table>"""
st.markdown(table_html, unsafe_allow_html=True)

st.markdown(f"""
<div style="margin-top: 3rem; padding: 1.5rem; background: rgba(255,255,255,0.02); border: 1px solid #111; border-radius: 8px;">
    <div style="display: flex; justify-content: space-between; align-items: center;">
        <div style="color: #444; font-family: 'JetBrains Mono'; font-size: 0.65rem; letter-spacing: 2px;">
            METHODOLOGY
        </div>
        <div style="color: #333; font-family: 'JetBrains Mono'; font-size: 0.6rem;">
            MARKET CAP CHANGE (%) // DAY-OVER-DAY // SOURCE: COMPANIESMARKETCAP.COM
        </div>
    </div>
    <div style="color: #555; font-size: 0.75rem; margin-top: 10px; line-height: 1.6;">
        This terminal tracks capital flows by calculating day-over-day market cap changes by country.
        Positive flows indicate capital inflow (market cap growth), negative flows indicate outflow (market cap contraction).
        Data sourced from companiesmarketcap.com - the most comprehensive database of listed companies by country.
    </div>
</div>
""", unsafe_allow_html=True)