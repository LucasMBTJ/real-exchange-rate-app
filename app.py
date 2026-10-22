import datetime
import re
import pandas as pd
import numpy as np
import requests
import plotly.graph_objects as _go
from plotly.subplots import make_subplots
import streamlit as st

# ==========================================
# 1. PAGE CONFIGURATION & CUSTOM STYLING
# ==========================================
st.set_page_config(
    page_title="IMF Real Exchange Rate (RER) Calculator",
    page_icon="💱",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inject custom CSS for responsive design, rounded toggle buttons, and metrics
st.markdown("""
<style>
    .stApp {
        background-color: #0F172A;
        color: #F8FAFC;
    }
    .metric-card {
        background-color: #1E293B;
        border-radius: 12px;
        padding: 20px;
        border: 1px solid #334155;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        margin-bottom: 15px;
    }
    .metric-title {
        font-size: 0.875rem;
        color: #94A3B8;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    .metric-value {
        font-size: 1.75rem;
        font-weight: 700;
        color: #F8FAFC;
        margin-top: 5px;
    }
    .status-overvalued {
        color: #EF4444;
        font-weight: 700;
    }
    .status-undervalued {
        color: #10B981;
        font-weight: 700;
    }
    /* Rounded Selection Box Styling */
    div.row-widget.stRadio > div {
        flex-direction: row;
        gap: 15px;
        justify-content: center;
        background-color: #1E293B;
        padding: 8px;
        border-radius: 30px;
        border: 1px solid #334155;
    }
    div.row-widget.stRadio > div > label {
        background-color: #0F172A;
        padding: 10px 24px;
        border-radius: 20px;
        color: #94A3B8;
        font-weight: 600;
        border: 1px solid #334155;
        cursor: pointer;
        transition: all 0.2s ease-in-out;
    }
    div.row-widget.stRadio > div > label:hover {
        border-color: #38BDF8;
        color: #F8FAFC;
    }
</style>
""", unsafe_allow_html=True)


# ==========================================
# 2. COUNTRY & CURRENCY METADATA
# ==========================================
COUNTRY_DATA = [
    {"name": "Euro Area", "iso3": "G163", "currency_name": "Euro", "currency_code": "EUR", "flag": "🇪🇺"},
    {"name": "United States", "iso3": "USA", "currency_name": "US Dollar", "currency_code": "USD", "flag": "🇺🇸"},
    {"name": "United Kingdom", "iso3": "GBR", "currency_name": "British Pound", "currency_code": "GBP", "flag": "🇬🇧"},
    {"name": "Japan", "iso3": "JPN", "currency_name": "Japanese Yen", "currency_code": "JPY", "flag": "🇯🇵"},
    {"name": "Canada", "iso3": "CAN", "currency_name": "Canadian Dollar", "currency_code": "CAD", "flag": "🇨🇦"},
    {"name": "Switzerland", "iso3": "CHE", "currency_name": "Swiss Franc", "currency_code": "CHF", "flag": "🇨🇭"},
    {"name": "Australia", "iso3": "AUS", "currency_name": "Australian Dollar", "currency_code": "AUD", "flag": "🇦🇺"},
    {"name": "Brazil", "iso3": "BRA", "currency_name": "Brazilian Real", "currency_code": "BRL", "flag": "🇧🇷"},
    {"name": "Mexico", "iso3": "MEX", "currency_name": "Mexican Peso", "currency_code": "MXN", "flag": "🇲🇽"},
    {"name": "China", "iso3": "CHN", "currency_name": "Chinese Yuan", "currency_code": "CNY", "flag": "🇨🇳"},
    {"name": "India", "iso3": "IND", "currency_name": "Indian Rupee", "currency_code": "INR", "flag": "🇮🇳"},
    {"name": "South Korea", "iso3": "KOR", "currency_name": "South Korean Won", "currency_code": "KRW", "flag": "🇰🇷"},
    {"name": "South Africa", "iso3": "ZAF", "currency_name": "South African Rand", "currency_code": "ZAR", "flag": "🇿🇦"},
    {"name": "Chile", "iso3": "CHL", "currency_name": "Chilean Peso", "currency_code": "CLP", "flag": "🇨🇱"},
    {"name": "Norway", "iso3": "NOR", "currency_name": "Norwegian Krone", "currency_code": "NOK", "flag": "🇳🇴"},
    {"name": "Sweden", "iso3": "SWE", "currency_name": "Swedish Krona", "currency_code": "SEK", "flag": "🇸🇪"},
    {"name": "New Zealand", "iso3": "NZL", "currency_name": "New Zealand Dollar", "currency_code": "NZD", "flag": "🇳🇿"},
    {"name": "Singapore", "iso3": "SGP", "currency_name": "Singapore Dollar", "currency_code": "SGD", "flag": "🇸🇬"},
    {"name": "Colombia", "iso3": "COL", "currency_name": "Colombian Peso", "currency_code": "COP", "flag": "🇨🇴"},
    {"name": "Turkey", "iso3": "TUR", "currency_name": "Turkish Lira", "currency_code": "TRY", "flag": "🇹🇷"},
]


# ==========================================
# 3. IMF API DATA RETRIEVAL ENGINE
# ==========================================
@st.cache_data(ttl=86400, show_spinner=False)
def fetch_imf_series(iso3: str, series_key_template: str, start_year: int = 1976) -> pd.Series:
    """
    Fetches monthly time series from the official IMF SDMX 3.0 REST API endpoint.
    Handles SDMX-JSON response formats with robust fallback parsing.
    """
    series_code = series_key_template.format(ISO3=iso3)
    
    # IMF SDMX 3.0 REST API Endpoint
    url = f"https://api.imf.org/external/sdmx/3.0/data/IMF.STA,CPI,1.0/{series_code}"
    params = {"startPeriod": f"{start_year}-01"}
    headers = {"Accept": "application/json", "User-Agent": "RER-Calculator-App/1.0"}

    try:
        response = requests.get(url, params=params, headers=headers, timeout=12)
        if response.status_code == 200:
            data = response.json()
            return parse_sdmx_3_json(data)
    except Exception:
        pass

    # Secondary Endpoint / Legacy Structure Fallback
    fallback_url = f"https://api.imf.org/external/sdmx/3.0/data/CPI/{series_code}"
    try:
        response = requests.get(fallback_url, params=params, headers=headers, timeout=12)
        if response.status_code == 200:
            return parse_sdmx_3_json(response.json())
    except Exception:
        pass

    return pd.Series(dtype=float)


def parse_sdmx_3_json(json_data: dict) -> pd.Series:
    """Extracts date-value pairs from SDMX-JSON structures."""
    records = {}
    try:
        data_sets = json_data.get("data", {}).get("dataSets", [])
        if not data_sets:
            data_sets = json_data.get("dataSets", [])

        structures = json_data.get("data", {}).get("structures", [])
        if not structures:
            structures = [json_data.get("structure", {})]

        # Extract Time Dimension values
        time_periods = []
        for struct in structures:
            dimensions = struct.get("dimensions", {}).get("observation", [])
            for dim in dimensions:
                if dim.get("id") == "TIME_PERIOD":
                    time_periods = [val.get("id") for val in dim.get("values", [])]
                    break

        # Extract Series Observations
        for ds in data_sets:
            series_dict = ds.get("series", {})
            for _, s_info in series_dict.items():
                observations = s_info.get("observations", {})
                for obs_key, obs_val in observations.items():
                    obs_idx = int(obs_key.split(":")[0]) if ":" in obs_key else int(obs_key)
                    if obs_idx < len(time_periods):
                        date_str = time_periods[obs_idx]
                        records[date_str] = float(obs_val[0])
    except Exception:
        return pd.Series(dtype=float)

    if not records:
        return pd.Series(dtype=float)

    # Convert to Monthly Datetime Index
    df = pd.DataFrame(list(records.items()), columns=["Period", "Value"])
    df["Date"] = pd.to_datetime(df["Period"], format="%Y-%m", errors="coerce")
    df = df.dropna(subset=["Date"]).sort_values("Date")
    return pd.Series(data=df["Value"].values, index=df["Date"])


def get_country_data(country_dict: dict):
    """Retrieves both CPI and Exchange Rate series for a country."""
    iso3 = country_dict["iso3"]
    cpi = fetch_imf_series(iso3, "{ISO3}.CPI._T.IX.M")
    
    # Fixed USD exchange rate for USA
    if iso3 == "USA":
        idx = cpi.index if not cpi.empty else pd.date_range("1976-01-01", datetime.date.today(), freq="MS")
        fx = pd.Series(1.0, index=idx)
    else:
        fx = fetch_imf_series(iso3, "{ISO3}.XDC_USD.PA_RT.M")

    return cpi, fx


# ==========================================
# 4. BACKEND RER CALCULATION ENGINE
# ==========================================
def calculate_rer_dataset(c1_dict, c2_dict, start_date, end_date):
    """
    Computes S(t), RER(t), RER*, and Real Index(t) according to specification.
    """
    with st.spinner(f"Fetching IMF data for {c1_dict['name']} and {c2_dict['name']}..."):
        c1_cpi, c1_fx = get_country_data(c1_dict)
        c2_cpi, c2_fx = get_country_data(c2_dict)

    # Combine into unified master DataFrame
    df = pd.DataFrame({
        "P1": c1_cpi,
        "E1": c1_fx,
        "P2": c2_cpi,
        "E2": c2_fx
    }).dropna()

    if df.empty:
        return None, None

    # Calculate Nominal Exchange Rate S(t) = units of C2 per 1 unit of C1
    # E1 = LCU1 / USD, E2 = LCU2 / USD  => S(t) = E2 / E1
    df["S_t"] = df["E2"] / df["E1"]

    # Calculate Real Exchange Rate: RER(t) = S(t) * P1(t) / P2(t)
    df["RER_t"] = df["S_t"] * (df["P1"] / df["P2"])

    # Filter by user-selected sample period
    sample_df = df.loc[(df.index >= pd.Timestamp(start_date)) & (df.index <= pd.Timestamp(end_date))].copy()

    if sample_df.empty:
        return None, None

    # Calculate RER* (Average over valid months in sample period)
    rer_star = sample_df["RER_t"].mean()

    # Calculate Real Index(t) = 100 * RER(t) / RER*
    sample_df["Real_Index"] = 100.0 * (sample_df["RER_t"] / rer_star)

    return sample_df, rer_star


# ==========================================
# 5. FRONTEND INTERFACE & NAVIGATION
# ==========================================
st.title("💱 IMF Real Exchange Rate (RER) Analytics")
st.caption("Calculate relative purchasing power parity and currency valuation using IMF SDMX data.")

# Sidebar Controls
st.sidebar.header("🗓️ Sample Period")
min_date = datetime.date(1976, 1, 1)
max_date = datetime.date.today()

start_date = st.sidebar.date_input("Start Month", min_date, min_value=min_date, max_value=max_date)
end_date = st.sidebar.date_input("End Month", max_date, min_value=min_date, max_value=max_date)

if start_date >= end_date:
    st.error("Error: Start date must be prior to End date.")
    st.stop()

# Helper for country formatting in dropdowns
def format_country_option(c):
    return f"{c['flag']} {c['name']} ({c['currency_name']} - {c['currency_code']})"

st.subheader("1. Select Target Countries")
col1, col2 = st.columns(2)

with col1:
    c1_selected = st.selectbox(
        "Country 1 (Base Currency):",
        options=COUNTRY_DATA,
        format_func=format_country_option,
        index=0,
        key="c1_select"
    )

with col2:
    c2_selected = st.selectbox(
        "Country 2 (Price/Quote Currency):",
        options=COUNTRY_DATA,
        format_func=format_country_option,
        index=1,
        key="c2_select"
    )

if c1_selected["iso3"] == c2_selected["iso3"]:
    st.warning("Please select two different countries for comparative RER analysis.")
    st.stop()

# Calculate RER Data
df_res, rer_star = calculate_rer_dataset(c1_selected, c2_selected, start_date, end_date)

if df_res is None or df_res.empty:
    st.error("Insufficient overlapping monthly CPI or exchange rate data for the selected countries and period.")
    st.stop()

# Metric & Valuation Summary Cards
latest_row = df_res.iloc[-1]
latest_rer = latest_row["RER_t"]
latest_index = latest_row["Real_Index"]
latest_s = latest_row["S_t"]
is_overvalued = latest_rer > rer_star
dev_pct = ((latest_rer - rer_star) / rer_star) * 100.0

st.markdown("<br>", unsafe_allow_html=True)
m_col1, m_col2, m_col3 = st.columns(3)

with m_col1:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">Latest Real Exchange Index</div>
        <div class="metric-value">{latest_index:.2f} <span style="font-size: 1rem;">(Base = 100)</span></div>
    </div>
    """, unsafe_allow_html=True)

with m_col2:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">Nominal Rate S(t)</div>
        <div class="metric-value">{latest_s:.4f} <span style="font-size: 1rem;">{c2_selected['currency_code']}/{c1_selected['currency_code']}</span></div>
    </div>
    """, unsafe_allow_html=True)

with m_col3:
    status_class = "status-overvalued" if is_overvalued else "status-undervalued"
    status_text = f"OVERVALUED (+{dev_pct:.1f}%)" if is_overvalued else f"UNDERVALUED ({dev_pct:.1f}%)"
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">{c1_selected['currency_code']} Valuation Status</div>
        <div class="metric-value {status_class}">{status_text}</div>
    </div>
    """, unsafe_allow_html=True)

# Rounded Selection Toggle Boxes
st.markdown("<br>", unsafe_allow_html=True)
st.subheader("2. Chart Display Mode")
chart_mode = st.radio(
    "Select Display View:",
    options=["Real Index", "Nominal Exchange Rate", "Both"],
    index=2,
    horizontal=True,
    label_visibility="collapsed"
)

# ==========================================
# 6. INTERACTIVE PLOTLY CHART
# ==========================================
fig = make_subplots(specs=[[{"secondary_y": True}]]) if chart_mode == "Both" else _go.Figure()

hover_date_format = "%b %Y"

if chart_mode in ["Real Index", "Both"]:
    real_trace = _go.Scatter(
        x=df_res.index,
        y=df_res["Real_Index"],
        name=f"Real Index (Base = 100)",
        line=dict(color="#38BDF8", width=2.5),
        hovertemplate=f"<b>Date</b>: %{{x|{hover_date_format}}}<br><b>Real Index</b>: %{{y:.2f}}<extra></extra>"
    )
    if chart_mode == "Both":
        fig.add_trace(real_trace, secondary_y=False)
    else:
        fig.add_trace(real_trace)

if chart_mode in ["Nominal Exchange Rate", "Both"]:
    nom_trace = _go.Scatter(
        x=df_res.index,
        y=df_res["S_t"],
        name=f"Nominal Rate S(t) ({c2_selected['currency_code']}/{c1_selected['currency_code']})",
        line=dict(color="#F59E0B", width=2.0, dash="solid"),
        hovertemplate=f"<b>Date</b>: %{{x|{hover_date_format}}}<br><b>Nominal Rate</b>: %{{y:.4f}} {c2_selected['currency_code']}<extra></extra>"
    )
    if chart_mode == "Both":
        fig.add_trace(nom_trace, secondary_y=True)
    else:
        fig.add_trace(nom_trace)

# Layout customization
fig.update_layout(
    template="plotly_dark",
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(15,23,42,0.6)",
    hovermode="x unified",
    margin=dict(l=20, r=20, t=50, b=30),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    height=520
)

if chart_mode == "Both":
    fig.update_yaxes(title_text="<b>Real Exchange Index</b> (100 = Sample Average)", secondary_y=False, gridcolor="#334155")
    fig.update_yaxes(title_text=f"<b>Nominal Rate S(t)</b> ({c2_selected['currency_code']} per {c1_selected['currency_code']})", secondary_y=True, showgrid=False)
elif chart_mode == "Real Index":
    fig.update_yaxes(title_text="<b>Real Exchange Index</b> (100 = Sample Average)", gridcolor="#334155")
else:
    fig.update_yaxes(title_text=f"<b>Nominal Rate S(t)</b> ({c2_selected['currency_code']} per {c1_selected['currency_code']})", gridcolor="#334155")

fig.update_xaxes(gridcolor="#334155")
st.plotly_chart(fig, use_container_width=True)

# ==========================================
# 7. CSV DATA DOWNLOAD
# ==========================================
st.markdown("<br>", unsafe_allow_html=True)
st.subheader("3. Export Observations & Calculations")

export_df = df_res.copy()
export_df.index.name = "Date"
export_df = export_df.rename(columns={
    "P1": f"CPI_{c1_selected['iso3']}",
    "E1": f"FX_USD_{c1_selected['iso3']}",
    "P2": f"CPI_{c2_selected['iso3']}",
    "E2": f"FX_USD_{c2_selected['iso3']}",
    "S_t": f"Nominal_S_t_{c2_selected['currency_code']}_per_{c1_selected['currency_code']}",
    "RER_t": "Real_Exchange_Rate",
    "Real_Index": "Real_Index_Base100"
})

csv_data = export_df.to_csv().encode('utf-8')

st.download_button(
    label=f"📥 Download Observation CSV ({c1_selected['currency_code']} vs {c2_selected['currency_code']})",
    data=csv_data,
    file_name=f"RER_{c1_selected['iso3']}_{c2_selected['iso3']}_{start_date.strftime('%Y%m')}_{end_date.strftime('%Y%m')}.csv",
    mime="text/csv"
)
