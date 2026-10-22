import datetime
import re
import io
import pandas as pd
import numpy as np
import requests
import plotly.graph_objects as go
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

# Custom CSS for dark UI, cards, and radio toggle styling
st.markdown("""
<style>
    .stApp {
        background-color: #0F172A;
        color: #F8FAFC;
    }
    .metric-card {
        background-color: #1E293B;
        border-radius: 12px;
        padding: 18px;
        border: 1px solid #334155;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        margin-bottom: 12px;
    }
    .metric-title {
        font-size: 0.85rem;
        color: #94A3B8;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    .metric-value {
        font-size: 1.6rem;
        font-weight: 700;
        color: #F8FAFC;
        margin-top: 4px;
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
        padding: 8px 20px;
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
    {"name": "Euro Area", "iso3": "G163", "alt_iso": "EUR", "currency_name": "Euro", "currency_code": "EUR", "flag": "🇪🇺"},
    {"name": "United States", "iso3": "USA", "alt_iso": "USA", "currency_name": "US Dollar", "currency_code": "USD", "flag": "🇺🇸"},
    {"name": "United Kingdom", "iso3": "GBR", "alt_iso": "GBR", "currency_name": "British Pound", "currency_code": "GBP", "flag": "🇬🇧"},
    {"name": "Japan", "iso3": "JPN", "alt_iso": "JPN", "currency_name": "Japanese Yen", "currency_code": "JPY", "flag": "🇯🇵"},
    {"name": "Canada", "iso3": "CAN", "alt_iso": "CAN", "currency_name": "Canadian Dollar", "currency_code": "CAD", "flag": "🇨🇦"},
    {"name": "Switzerland", "iso3": "CHE", "alt_iso": "CHE", "currency_name": "Swiss Franc", "currency_code": "CHF", "flag": "🇨🇭"},
    {"name": "Australia", "iso3": "AUS", "alt_iso": "AUS", "currency_name": "Australian Dollar", "currency_code": "AUD", "flag": "🇦🇺"},
    {"name": "Brazil", "iso3": "BRA", "alt_iso": "BRA", "currency_name": "Brazilian Real", "currency_code": "BRL", "flag": "🇧🇷"},
    {"name": "Mexico", "iso3": "MEX", "alt_iso": "MEX", "currency_name": "Mexican Peso", "currency_code": "MXN", "flag": "🇲🇽"},
    {"name": "China", "iso3": "CHN", "alt_iso": "CHN", "currency_name": "Chinese Yuan", "currency_code": "CNY", "flag": "🇨🇳"},
    {"name": "India", "iso3": "IND", "alt_iso": "IND", "currency_name": "Indian Rupee", "currency_code": "INR", "flag": "🇮🇳"},
    {"name": "South Korea", "iso3": "KOR", "alt_iso": "KOR", "currency_name": "South Korean Won", "currency_code": "KRW", "flag": "🇰🇷"},
    {"name": "South Africa", "iso3": "ZAF", "alt_iso": "ZAF", "currency_name": "South African Rand", "currency_code": "ZAR", "flag": "🇿🇦"},
    {"name": "Chile", "iso3": "CHL", "alt_iso": "CHL", "currency_name": "Chilean Peso", "currency_code": "CLP", "flag": "🇨🇱"},
    {"name": "Norway", "iso3": "NOR", "alt_iso": "NOR", "currency_name": "Norwegian Krone", "currency_code": "NOK", "flag": "🇳🇴"},
    {"name": "Sweden", "iso3": "SWE", "alt_iso": "SWE", "currency_name": "Swedish Krona", "currency_code": "SEK", "flag": "🇸🇪"},
    {"name": "New Zealand", "iso3": "NZL", "alt_iso": "NZL", "currency_name": "New Zealand Dollar", "currency_code": "NZD", "flag": "🇳🇿"},
    {"name": "Singapore", "iso3": "SGP", "alt_iso": "SGP", "currency_name": "Singapore Dollar", "currency_code": "SGD", "flag": "🇸🇬"},
    {"name": "Colombia", "iso3": "COL", "alt_iso": "COL", "currency_name": "Colombian Peso", "currency_code": "COP", "flag": "🇨🇴"},
    {"name": "Turkey", "iso3": "TUR", "alt_iso": "TUR", "currency_name": "Turkish Lira", "currency_code": "TRY", "flag": "🇹🇷"},
]


# ==========================================
# 3. ROBUST IMF DATA RETRIEVAL ENGINE
# ==========================================
def parse_date_index(series_df: pd.DataFrame) -> pd.Series:
    """Helper to clean IMF date strings (e.g. '2020-M01' or '2020-01') into datetime."""
    if series_df.empty:
        return pd.Series(dtype=float)
    
    series_df = series_df.copy()
    series_df["Period"] = series_df["Period"].astype(str).str.replace("-M", "-").str.replace("M", "-")
    series_df["Date"] = pd.to_datetime(series_df["Period"], format="%Y-%m", errors="coerce")
    series_df = series_df.dropna(subset=["Date"]).sort_values("Date")
    series_df = series_df.set_index("Date")["Value"]
    return series_df[~series_df.index.duplicated(keep="first")]


@st.cache_data(ttl=86400, show_spinner=False)
def fetch_imf_series(iso3: str, series_type: str, alt_iso: str = None) -> pd.Series:
    """
    Fetches monthly time series from the IMF API with multiple endpoint fallbacks:
    1. SDMX 3.0 REST API (JSON)
    2. SDMX 3.0 REST API (CSV)
    3. Legacy SDMX 2.1 JSON structure
    """
    codes_to_try = [iso3]
    if alt_iso and alt_iso != iso3:
        codes_to_try.append(alt_iso)

    for code in codes_to_try:
        if series_type == "CPI":
            series_code = f"{code}.CPI._T.IX.M"
            dataflow = "IMF.STA/CPI"
        else:
            series_code = f"{code}.XDC_USD.PA_RT.M"
            dataflow = "IMF.STA/IFS"

        # Strategy 1: SDMX 3.0 REST CSV Endpoint
        url_csv = f"https://api.imf.org/external/sdmx/3.0/data/dataflow/{dataflow}/~/{series_code}"
        headers_csv = {"Accept": "text/csv", "User-Agent": "RER-Calculator-App/2.0"}
        try:
            res = requests.get(url_csv, headers=headers_csv, timeout=10)
            if res.status_code == 200 and len(res.text) > 50:
                df = pd.read_csv(io.StringIO(res.text))
                time_col = [c for c in df.columns if "TIME" in c.upper() or "PERIOD" in c.upper()]
                val_col = [c for c in df.columns if "VAL" in c.upper() or "OBS" in c.upper()]
                if time_col and val_col:
                    raw_df = pd.DataFrame({"Period": df[time_col[0]], "Value": pd.to_numeric(df[val_col[0]], errors="coerce")})
                    parsed = parse_date_index(raw_df)
                    if not parsed.empty:
                        return parsed
        except Exception:
            pass

        # Strategy 2: Direct SDMX 3.0 REST JSON Endpoint
        url_json = f"https://api.imf.org/external/sdmx/3.0/data/{series_code}"
        headers_json = {"Accept": "application/json", "User-Agent": "RER-Calculator-App/2.0"}
        try:
            res = requests.get(url_json, headers=headers_json, timeout=10)
            if res.status_code == 200:
                data = res.json()
                parsed = parse_sdmx_json(data)
                if not parsed.empty:
                    return parsed
        except Exception:
            pass

        # Strategy 3: SDMX 2.1 Compact JSON Fallback
        url_v2 = f"https://dataservices.imf.org/REST/SDMX_JSON.svc/CompactData/CPI/M.{code}.CPI._T.IX" if series_type == "CPI" else f"https://dataservices.imf.org/REST/SDMX_JSON.svc/CompactData/IFS/M.{code}.ENDA_XDC_USD_RATE"
        try:
            res = requests.get(url_v2, timeout=10)
            if res.status_code == 200:
                data = res.json()
                obs = data.get("CompactData", {}).get("DataSet", {}).get("Series", {}).get("Obs", [])
                if isinstance(obs, dict):
                    obs = [obs]
                records = [{"Period": o.get("@TIME_PERIOD"), "Value": float(o.get("@OBS_VALUE"))} for o in obs if "@TIME_PERIOD" in o and "@OBS_VALUE" in o]
                if records:
                    parsed = parse_date_index(pd.DataFrame(records))
                    if not parsed.empty:
                        return parsed
        except Exception:
            pass

    return pd.Series(dtype=float)


def parse_sdmx_json(json_data: dict) -> pd.Series:
    """Parses observation keys/values from SDMX 3.0 JSON structures."""
    records = []
    try:
        data_sets = json_data.get("data", {}).get("dataSets", []) or json_data.get("dataSets", [])
        structures = json_data.get("data", {}).get("structures", []) or [json_data.get("structure", {})]

        time_periods = []
        for struct in structures:
            dimensions = struct.get("dimensions", {}).get("observation", [])
            for dim in dimensions:
                if dim.get("id") == "TIME_PERIOD":
                    time_periods = [val.get("id") for val in dim.get("values", [])]
                    break

        for ds in data_sets:
            series_dict = ds.get("series", {})
            for _, s_info in series_dict.items():
                observations = s_info.get("observations", {})
                for obs_key, obs_val in observations.items():
                    obs_idx = int(obs_key.split(":")[0]) if ":" in obs_key else int(obs_key)
                    if obs_idx < len(time_periods):
                        records.append({"Period": time_periods[obs_idx], "Value": float(obs_val[0])})
    except Exception:
        return pd.Series(dtype=float)

    return parse_date_index(pd.DataFrame(records))


def fetch_country_pair_data(c1_dict: dict, c2_dict: dict):
    """Fetches CPI and Exchange Rate data for both countries and aligns them into a single Master DataFrame."""
    with st.spinner(f"Fetching IMF data for {c1_dict['name']} and {c2_dict['name']}..."):
        # Fetch Country 1
        c1_cpi = fetch_imf_series(c1_dict["iso3"], "CPI", c1_dict.get("alt_iso"))
        if c1_dict["iso3"] == "USA":
            c1_fx = pd.Series(1.0, index=c1_cpi.index if not c1_cpi.empty else pd.date_range("1976-01-01", datetime.date.today(), freq="MS"))
        else:
            c1_fx = fetch_imf_series(c1_dict["iso3"], "FX", c1_dict.get("alt_iso"))

        # Fetch Country 2
        c2_cpi = fetch_imf_series(c2_dict["iso3"], "CPI", c2_dict.get("alt_iso"))
        if c2_dict["iso3"] == "USA":
            c2_fx = pd.Series(1.0, index=c2_cpi.index if not c2_cpi.empty else pd.date_range("1976-01-01", datetime.date.today(), freq="MS"))
        else:
            c2_fx = fetch_imf_series(c2_dict["iso3"], "FX", c2_dict.get("alt_iso"))

    # Combine into unified dataset
    df = pd.DataFrame({"P1": c1_cpi, "E1": c1_fx, "P2": c2_cpi, "E2": c2_fx}).dropna()
    
    if df.empty:
        return None

    # Calculate Nominal Exchange Rate S(t) = units of Currency 2 per 1 unit of Currency 1
    # E1 = LCU1 / USD, E2 = LCU2 / USD => S(t) = E2 / E1
    df["S_t"] = df["E2"] / df["E1"]

    # Calculate Real Exchange Rate RER(t) = S(t) * P1(t) / P2(t)
    df["RER_t"] = df["S_t"] * (df["P1"] / df["P2"])

    return df


# ==========================================
# 4. FRONTEND APP & PERIOD CONTROL LOGIC
# ==========================================
st.title("💱 IMF Real Exchange Rate (RER) Analytics")
st.caption("Calculate relative purchasing power parity and currency valuation using official IMF SDMX data.")

st.subheader("1. Select Target Countries")

def format_country_option(c):
    return f"{c['flag']} {c['name']} ({c['currency_name']} - {c['currency_code']})"

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
        index=2, # Default to GBR (UK) for easy demonstration
        key="c2_select"
    )

if c1_selected["iso3"] == c2_selected["iso3"]:
    st.warning("Please select two different countries for comparative RER analysis.")
    st.stop()

# Load master overlapping data
master_df = fetch_country_pair_data(c1_selected, c2_selected)

if master_df is None or master_df.empty:
    st.error("Insufficient overlapping monthly CPI or exchange rate data retrieved from the IMF for this country pair.")
    st.stop()

# Determine full available date boundaries for the selected country pair
earliest_avail_date = master_df.index.min().date()
latest_avail_date = master_df.index.max().date()

# Sidebar: Period Selection Control
st.sidebar.header("🗓️ Period Selection")
st.sidebar.info(f"**Available Data Coverage:**\n{earliest_avail_date.strftime('%b %Y')} to {latest_avail_date.strftime('%b %Y')}")

customize_period = st.sidebar.checkbox("Customize Period Selection", value=False)

if customize_period:
    start_date = st.sidebar.date_input(
        "Start Month",
        value=earliest_avail_date,
        min_value=earliest_avail_date,
        max_value=latest_avail_date
    )
    end_date = st.sidebar.date_input(
        "End Month",
        value=latest_avail_date,
        min_value=earliest_avail_date,
        max_value=latest_avail_date
    )
    if start_date >= end_date:
        st.sidebar.error("Error: Start date must be before End date.")
        st.stop()
else:
    start_date = earliest_avail_date
    end_date = latest_avail_date

# Filter master dataset by sample period
sample_df = master_df.loc[(master_df.index >= pd.Timestamp(start_date)) & (master_df.index <= pd.Timestamp(end_date))].copy()

if sample_df.empty:
    st.error("No valid data available within the selected custom date range.")
    st.stop()

# Compute RER* (Average over valid months) and Real Index
rer_star = sample_df["RER_t"].mean()
sample_df["Real_Index"] = 100.0 * (sample_df["RER_t"] / rer_star)

# Key Analytics Summaries
latest_row = sample_df.iloc[-1]
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
        <div class="metric-value">{latest_index:.2f} <span style="font-size: 0.9rem;">(Base = 100)</span></div>
    </div>
    """, unsafe_allow_html=True)

with m_col2:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">Nominal Rate S(t)</div>
        <div class="metric-value">{latest_s:.4f} <span style="font-size: 0.9rem;">{c2_selected['currency_code']}/{c1_selected['currency_code']}</span></div>
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
# 5. INTERACTIVE PLOTLY CHART
# ==========================================
fig = make_subplots(specs=[[{"secondary_y": True}]]) if chart_mode == "Both" else go.Figure()

hover_date_format = "%b %Y"

if chart_mode in ["Real Index", "Both"]:
    real_trace = go.Scatter(
        x=sample_df.index,
        y=sample_df["Real_Index"],
        name="Real Index (Base = 100)",
        line=dict(color="#38BDF8", width=2.5),
        hovertemplate=f"<b>Date</b>: %{{x|{hover_date_format}}}<br><b>Real Index</b>: %{{y:.2f}}<extra></extra>"
    )
    if chart_mode == "Both":
        fig.add_trace(real_trace, secondary_y=False)
    else:
        fig.add_trace(real_trace)

if chart_mode in ["Nominal Exchange Rate", "Both"]:
    nom_trace = go.Scatter(
        x=sample_df.index,
        y=sample_df["S_t"],
        name=f"Nominal Rate S(t) ({c2_selected['currency_code']}/{c1_selected['currency_code']})",
        line=dict(color="#F59E0B", width=2.0, dash="solid"),
        hovertemplate=f"<b>Date</b>: %{{x|{hover_date_format}}}<br><b>Nominal Rate S(t)</b>: %{{y:.4f}} {c2_selected['currency_code']}<extra></extra>"
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
# 6. CSV DATA DOWNLOAD
# ==========================================
st.markdown("<br>", unsafe_allow_html=True)
st.subheader("3. Export Observations & Calculations")

export_df = sample_df.copy()
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
