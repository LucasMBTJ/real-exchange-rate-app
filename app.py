"""
IMF Real Exchange Rate (RER) explorer  -  Streamlit app (Python 3.12)

    S(t)   = units of Country-2 currency per 1 unit of Country-1 currency
    RER(t) = S(t) * P1(t) / P2(t)
    RER*   = mean of RER(t) over the valid months of the selected sample
    Index  = 100 * RER(t) / RER*

Data: IMF SDMX 3.0 API  https://api.imf.org/external/sdmx/3.0
    CPI (monthly, all items, index) : dataflow IMF.STA/CPI  key {ISO3}.CPI._T.IX.M
    FX  (LCU per USD, period avg.)  : dataflow IMF.STA/ER   key {ISO3}.XDC_USD.PA_RT.M
Euro area = IMF code G163.

Storage: every series is a pandas float64 Series on a DatetimeIndex (month start);
the pair dataset is one DataFrame of contiguous float64 columns (no Python objects).
"""
from __future__ import annotations

import io
import os
import re
import time
import xml.etree.ElementTree as ET

import numpy as np
import pandas as pd
import requests
import streamlit as st

# =============================================================================
# 1. COUNTRY / CURRENCY METADATA   (iso3, iso2 for the flag, name, currency, code)
# =============================================================================
_COUNTRY_TABLE = """
G163|EU|Euro area|Euro|EUR
AFG|AF|Afghanistan|Afghan Afghani|AFN
ALB|AL|Albania|Albanian Lek|ALL
DZA|DZ|Algeria|Algerian Dinar|DZD
AGO|AO|Angola|Angolan Kwanza|AOA
ATG|AG|Antigua and Barbuda|East Caribbean Dollar|XCD
ARG|AR|Argentina|Argentine Peso|ARS
ARM|AM|Armenia|Armenian Dram|AMD
ABW|AW|Aruba|Aruban Florin|AWG
AUS|AU|Australia|Australian Dollar|AUD
AUT|AT|Austria|Euro|EUR
AZE|AZ|Azerbaijan|Azerbaijani Manat|AZN
BHS|BS|Bahamas, The|Bahamian Dollar|BSD
BHR|BH|Bahrain|Bahraini Dinar|BHD
BGD|BD|Bangladesh|Bangladeshi Taka|BDT
BRB|BB|Barbados|Barbadian Dollar|BBD
BLR|BY|Belarus|Belarusian Ruble|BYN
BEL|BE|Belgium|Euro|EUR
BLZ|BZ|Belize|Belize Dollar|BZD
BEN|BJ|Benin|West African CFA Franc|XOF
BTN|BT|Bhutan|Bhutanese Ngultrum|BTN
BOL|BO|Bolivia|Boliviano|BOB
BIH|BA|Bosnia and Herzegovina|Convertible Mark|BAM
BWA|BW|Botswana|Botswana Pula|BWP
BRA|BR|Brazil|Brazilian Real|BRL
BRN|BN|Brunei Darussalam|Brunei Dollar|BND
BGR|BG|Bulgaria|Euro|EUR
BFA|BF|Burkina Faso|West African CFA Franc|XOF
BDI|BI|Burundi|Burundian Franc|BIF
CPV|CV|Cabo Verde|Cape Verdean Escudo|CVE
KHM|KH|Cambodia|Cambodian Riel|KHR
CMR|CM|Cameroon|Central African CFA Franc|XAF
CAN|CA|Canada|Canadian Dollar|CAD
CAF|CF|Central African Republic|Central African CFA Franc|XAF
TCD|TD|Chad|Central African CFA Franc|XAF
CHL|CL|Chile|Chilean Peso|CLP
CHN|CN|China, P.R.: Mainland|Chinese Yuan|CNY
COL|CO|Colombia|Colombian Peso|COP
COM|KM|Comoros|Comorian Franc|KMF
COD|CD|Congo, Dem. Rep. of the|Congolese Franc|CDF
COG|CG|Congo, Republic of|Central African CFA Franc|XAF
CRI|CR|Costa Rica|Costa Rican Colon|CRC
CIV|CI|Cote d'Ivoire|West African CFA Franc|XOF
HRV|HR|Croatia|Euro|EUR
CUW|CW|Curacao|Caribbean Guilder|XCG
CYP|CY|Cyprus|Euro|EUR
CZE|CZ|Czech Republic|Czech Koruna|CZK
DNK|DK|Denmark|Danish Krone|DKK
DJI|DJ|Djibouti|Djiboutian Franc|DJF
DMA|DM|Dominica|East Caribbean Dollar|XCD
DOM|DO|Dominican Republic|Dominican Peso|DOP
ECU|EC|Ecuador|US Dollar|USD
EGY|EG|Egypt, Arab Rep. of|Egyptian Pound|EGP
SLV|SV|El Salvador|US Dollar|USD
GNQ|GQ|Equatorial Guinea|Central African CFA Franc|XAF
ERI|ER|Eritrea|Eritrean Nakfa|ERN
EST|EE|Estonia|Euro|EUR
SWZ|SZ|Eswatini|Swazi Lilangeni|SZL
ETH|ET|Ethiopia|Ethiopian Birr|ETB
FJI|FJ|Fiji|Fijian Dollar|FJD
FIN|FI|Finland|Euro|EUR
FRA|FR|France|Euro|EUR
GAB|GA|Gabon|Central African CFA Franc|XAF
GMB|GM|Gambia, The|Gambian Dalasi|GMD
GEO|GE|Georgia|Georgian Lari|GEL
DEU|DE|Germany|Euro|EUR
GHA|GH|Ghana|Ghanaian Cedi|GHS
GRC|GR|Greece|Euro|EUR
GRD|GD|Grenada|East Caribbean Dollar|XCD
GTM|GT|Guatemala|Guatemalan Quetzal|GTQ
GIN|GN|Guinea|Guinean Franc|GNF
GNB|GW|Guinea-Bissau|West African CFA Franc|XOF
GUY|GY|Guyana|Guyanese Dollar|GYD
HTI|HT|Haiti|Haitian Gourde|HTG
HND|HN|Honduras|Honduran Lempira|HNL
HKG|HK|Hong Kong SAR|Hong Kong Dollar|HKD
HUN|HU|Hungary|Hungarian Forint|HUF
ISL|IS|Iceland|Icelandic Krona|ISK
IND|IN|India|Indian Rupee|INR
IDN|ID|Indonesia|Indonesian Rupiah|IDR
IRN|IR|Iran, Islamic Rep. of|Iranian Rial|IRR
IRQ|IQ|Iraq|Iraqi Dinar|IQD
IRL|IE|Ireland|Euro|EUR
ISR|IL|Israel|Israeli New Shekel|ILS
ITA|IT|Italy|Euro|EUR
JAM|JM|Jamaica|Jamaican Dollar|JMD
JPN|JP|Japan|Japanese Yen|JPY
JOR|JO|Jordan|Jordanian Dinar|JOD
KAZ|KZ|Kazakhstan|Kazakhstani Tenge|KZT
KEN|KE|Kenya|Kenyan Shilling|KES
KIR|KI|Kiribati|Australian Dollar|AUD
KOR|KR|Korea, Republic of|South Korean Won|KRW
KWT|KW|Kuwait|Kuwaiti Dinar|KWD
KGZ|KG|Kyrgyz Republic|Kyrgyzstani Som|KGS
LAO|LA|Lao People's Democratic Republic|Lao Kip|LAK
LVA|LV|Latvia|Euro|EUR
LBN|LB|Lebanon|Lebanese Pound|LBP
LSO|LS|Lesotho|Lesotho Loti|LSL
LBR|LR|Liberia|Liberian Dollar|LRD
LBY|LY|Libya|Libyan Dinar|LYD
LTU|LT|Lithuania|Euro|EUR
LUX|LU|Luxembourg|Euro|EUR
MAC|MO|Macao SAR|Macanese Pataca|MOP
MDG|MG|Madagascar|Malagasy Ariary|MGA
MWI|MW|Malawi|Malawian Kwacha|MWK
MYS|MY|Malaysia|Malaysian Ringgit|MYR
MDV|MV|Maldives|Maldivian Rufiyaa|MVR
MLI|ML|Mali|West African CFA Franc|XOF
MLT|MT|Malta|Euro|EUR
MHL|MH|Marshall Islands|US Dollar|USD
MRT|MR|Mauritania|Mauritanian Ouguiya|MRU
MUS|MU|Mauritius|Mauritian Rupee|MUR
MEX|MX|Mexico|Mexican Peso|MXN
FSM|FM|Micronesia, Fed. States of|US Dollar|USD
MDA|MD|Moldova|Moldovan Leu|MDL
MNG|MN|Mongolia|Mongolian Togrog|MNT
MNE|ME|Montenegro|Euro|EUR
MAR|MA|Morocco|Moroccan Dirham|MAD
MOZ|MZ|Mozambique|Mozambican Metical|MZN
MMR|MM|Myanmar|Myanmar Kyat|MMK
NAM|NA|Namibia|Namibian Dollar|NAD
NRU|NR|Nauru|Australian Dollar|AUD
NPL|NP|Nepal|Nepalese Rupee|NPR
NLD|NL|Netherlands, The|Euro|EUR
NZL|NZ|New Zealand|New Zealand Dollar|NZD
NIC|NI|Nicaragua|Nicaraguan Cordoba|NIO
NER|NE|Niger|West African CFA Franc|XOF
NGA|NG|Nigeria|Nigerian Naira|NGN
MKD|MK|North Macedonia|Macedonian Denar|MKD
NOR|NO|Norway|Norwegian Krone|NOK
OMN|OM|Oman|Omani Rial|OMR
PAK|PK|Pakistan|Pakistani Rupee|PKR
PLW|PW|Palau|US Dollar|USD
PAN|PA|Panama|US Dollar|USD
PNG|PG|Papua New Guinea|Papua New Guinean Kina|PGK
PRY|PY|Paraguay|Paraguayan Guarani|PYG
PER|PE|Peru|Peruvian Sol|PEN
PHL|PH|Philippines|Philippine Peso|PHP
POL|PL|Poland|Polish Zloty|PLN
PRT|PT|Portugal|Euro|EUR
QAT|QA|Qatar|Qatari Riyal|QAR
ROU|RO|Romania|Romanian Leu|RON
RUS|RU|Russian Federation|Russian Ruble|RUB
RWA|RW|Rwanda|Rwandan Franc|RWF
WSM|WS|Samoa|Samoan Tala|WST
SMR|SM|San Marino|Euro|EUR
STP|ST|Sao Tome and Principe|Sao Tome Dobra|STN
SAU|SA|Saudi Arabia|Saudi Riyal|SAR
SEN|SN|Senegal|West African CFA Franc|XOF
SRB|RS|Serbia|Serbian Dinar|RSD
SYC|SC|Seychelles|Seychellois Rupee|SCR
SLE|SL|Sierra Leone|Sierra Leonean Leone|SLE
SGP|SG|Singapore|Singapore Dollar|SGD
SXM|SX|Sint Maarten|Caribbean Guilder|XCG
SVK|SK|Slovak Republic|Euro|EUR
SVN|SI|Slovenia|Euro|EUR
SLB|SB|Solomon Islands|Solomon Islands Dollar|SBD
SOM|SO|Somalia|Somali Shilling|SOS
ZAF|ZA|South Africa|South African Rand|ZAR
SSD|SS|South Sudan|South Sudanese Pound|SSP
ESP|ES|Spain|Euro|EUR
LKA|LK|Sri Lanka|Sri Lankan Rupee|LKR
SDN|SD|Sudan|Sudanese Pound|SDG
SUR|SR|Suriname|Surinamese Dollar|SRD
SWE|SE|Sweden|Swedish Krona|SEK
CHE|CH|Switzerland|Swiss Franc|CHF
SYR|SY|Syrian Arab Republic|Syrian Pound|SYP
TWN|TW|Taiwan Province of China|New Taiwan Dollar|TWD
TJK|TJ|Tajikistan|Tajikistani Somoni|TJS
TZA|TZ|Tanzania|Tanzanian Shilling|TZS
THA|TH|Thailand|Thai Baht|THB
TLS|TL|Timor-Leste|US Dollar|USD
TGO|TG|Togo|West African CFA Franc|XOF
TON|TO|Tonga|Tongan Pa'anga|TOP
TTO|TT|Trinidad and Tobago|Trinidad and Tobago Dollar|TTD
TUN|TN|Tunisia|Tunisian Dinar|TND
TUR|TR|Turkiye, Republic of|Turkish Lira|TRY
TKM|TM|Turkmenistan|Turkmenistani Manat|TMT
TUV|TV|Tuvalu|Australian Dollar|AUD
UGA|UG|Uganda|Ugandan Shilling|UGX
UKR|UA|Ukraine|Ukrainian Hryvnia|UAH
ARE|AE|United Arab Emirates|UAE Dirham|AED
GBR|GB|United Kingdom|Pound Sterling|GBP
USA|US|United States|US Dollar|USD
URY|UY|Uruguay|Uruguayan Peso|UYU
UZB|UZ|Uzbekistan|Uzbekistani Som|UZS
VUT|VU|Vanuatu|Vanuatu Vatu|VUV
VEN|VE|Venezuela, Rep. Bolivariana de|Venezuelan Bolivar|VES
VNM|VN|Vietnam|Vietnamese Dong|VND
YEM|YE|Yemen|Yemeni Rial|YER
ZMB|ZM|Zambia|Zambian Kwacha|ZMW
ZWE|ZW|Zimbabwe|Zimbabwe Gold|ZWG
"""


def _flag(iso2: str) -> str:
    """ISO-2 code -> flag emoji (two regional-indicator symbols)."""
    return "".join(chr(0x1F1E6 + ord(c) - ord("A")) for c in iso2.upper())


COUNTRIES: list[dict] = []
for _line in _COUNTRY_TABLE.strip().splitlines():
    _iso3, _iso2, _name, _cur, _code = _line.split("|")
    COUNTRIES.append(
        {"iso3": _iso3, "name": _name, "currency": _cur, "code": _code, "flag": _flag(_iso2)}
    )
COUNTRIES.sort(key=lambda c: (c["iso3"] != "G163", c["name"]))  # Euro area first, rest A-Z


def country_label(c: dict) -> str:
    """Drop-down text: flag, country, currency name, 3-letter code.
    Streamlit's built-in type-ahead matches any part of this text, so users can
    search by country name, currency name or 3-letter currency code."""
    return f"{c['flag']}  {c['name']} - {c['currency']} ({c['code']})"


# =============================================================================
# 2. BACKEND: IMF DATA ACCESS
# =============================================================================
IMF_BASE_30 = "https://api.imf.org/external/sdmx/3.0"
IMF_BASE_21 = "https://api.imf.org/external/sdmx/2.1"
AGENCY = "IMF.STA"
PINNED_VERSION = {"CPI": "5.0.0", "ER": "4.0.1"}  # last-resort pins; "~"/"+" tried first
START = pd.Timestamp("1976-01-01")

CSV_ACCEPT = "application/vnd.sdmx.data+csv;version=2.0.0"
JSON_ACCEPT = "application/vnd.sdmx.data+json;version=2.0.0"


class SeriesUnavailable(Exception):
    """Raised when a series cannot be fetched; carries a request-by-request log."""

    def __init__(self, message: str, log: list[str]):
        super().__init__(message)
        self.log = log


# ---- period / value normalisation -------------------------------------------
_PERIOD_RE = r"^(\d{4})[-]?M?[-]?(\d{2})(?:-\d{2})?$"  # 1976-M01, 1976-01, 1976M01, 197601, 1976-01-31


def _to_monthly_series(periods: pd.Series, values: pd.Series) -> pd.Series:
    """Raw period strings + values -> clean float64 Series on a month-start DatetimeIndex.
    Annual/quarterly labels (no month) simply fail the regex and are dropped."""
    p = periods.astype(str).str.strip().str.extract(_PERIOD_RE)
    month = pd.to_numeric(p[1], errors="coerce")
    ok = p[0].notna() & month.between(1, 12)
    dates = pd.to_datetime(p[0][ok] + "-" + p[1][ok] + "-01", format="%Y-%m-%d", errors="coerce")
    vals = pd.to_numeric(values[ok], errors="coerce").astype("float64")
    s = pd.Series(vals.to_numpy(), index=pd.DatetimeIndex(dates, name="Date"), dtype="float64")
    s = s[s.index.notna() & np.isfinite(s) & (s > 0)]  # drop gaps and non-positive values
    s = s[~s.index.duplicated(keep="first")].sort_index()
    return s[s.index >= START]


# ---- format parsers (the response format is detected from the content) -------
def _parse_csv(text: str) -> pd.Series:
    df = pd.read_csv(io.StringIO(text), dtype=str)
    cols = {c.split(":")[0].strip().upper(): c for c in df.columns}
    if "TIME_PERIOD" not in cols or "OBS_VALUE" not in cols:
        raise ValueError(f"CSV has no TIME_PERIOD/OBS_VALUE columns (found {list(df.columns)[:8]})")
    vals = pd.to_numeric(df[cols["OBS_VALUE"]], errors="coerce")
    if "SCALE" in cols:  # power-of-ten multiplier, when published
        sc = pd.to_numeric(df[cols["SCALE"]], errors="coerce").fillna(0)
        vals = vals * np.power(10.0, sc)
    return _to_monthly_series(df[cols["TIME_PERIOD"]], vals)


def _parse_json(text: str) -> pd.Series:
    import json

    js = json.loads(text)
    root = js.get("data", js)  # SDMX-JSON 2.0 nests under "data"; 1.0 does not
    structs = root.get("structures") or ([root["structure"]] if "structure" in root else [])
    if not structs:
        raise ValueError("SDMX-JSON without structure block")
    obs_dims = structs[0]["dimensions"]["observation"]
    time_dim = next(d for d in obs_dims if d.get("id") == "TIME_PERIOD")
    labels = [v.get("id") or v.get("value") or v.get("name") for v in time_dim["values"]]
    per, val = [], []
    for ds in root.get("dataSets", []):
        for ser in ds.get("series", {}).values():
            for idx, ob in ser.get("observations", {}).items():
                per.append(labels[int(idx)])
                val.append(ob[0] if ob else None)
    return _to_monthly_series(pd.Series(per, dtype=str), pd.Series(val))


def _parse_xml(text: str) -> pd.Series:
    local = lambda t: t.rsplit("}", 1)[-1]
    per, val = [], []
    for el in ET.fromstring(text).iter():
        if local(el.tag) != "Obs":
            continue
        t, v = el.attrib.get("TIME_PERIOD"), el.attrib.get("OBS_VALUE")
        if t is None:  # generic SDMX-ML: <ObsDimension value=.../><ObsValue value=.../>
            for ch in el:
                if local(ch.tag) == "ObsDimension":
                    t = ch.attrib.get("value")
                elif local(ch.tag) == "ObsValue":
                    v = ch.attrib.get("value")
        if t is not None:
            per.append(t)
            val.append(v)
    return _to_monthly_series(pd.Series(per, dtype=str), pd.Series(val))


def parse_sdmx(text: str) -> pd.Series:
    """Sniff JSON / XML / CSV and return a clean monthly series."""
    head = text.lstrip()[:1]
    if head in "{[":
        return _parse_json(text)
    if head == "<":
        return _parse_xml(text)
    return _parse_csv(text)


# ---- HTTP -------------------------------------------------------------------
def _subscription_key() -> str | None:
    """Optional: some IMF gateway configurations require an API key."""
    key = os.environ.get("IMF_SUBSCRIPTION_KEY")
    if not key:
        try:
            key = st.secrets.get("IMF_SUBSCRIPTION_KEY")  # type: ignore[attr-defined]
        except Exception:
            key = None
    return key or None


def _attempts(flow: str, key: str):
    """Ordered (url, Accept) candidates. The first one that yields data wins."""
    d30 = f"{IMF_BASE_30}/data/dataflow/{AGENCY}/{flow}"
    yield f"{d30}/~/{key}", CSV_ACCEPT
    yield f"{d30}/+/{key}", CSV_ACCEPT
    yield f"{d30}/{PINNED_VERSION[flow]}/{key}", CSV_ACCEPT
    yield f"{d30}/~/{key}", JSON_ACCEPT
    yield f"{d30}/~/{key}", "text/csv"
    d21 = f"{IMF_BASE_21}/data/{AGENCY},{flow}"
    yield f"{d21}/{key}", "application/json"
    yield f"{d21}/{key}", "*/*"


@st.cache_data(ttl=6 * 3600, show_spinner=False, max_entries=512)
def fetch_series(flow: str, key: str) -> pd.Series:
    """Download one complete monthly series. Failures raise (and are therefore NOT cached)."""
    log: list[str] = []
    headers_base = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124 Safari/537.36",
    }
    sub = _subscription_key()
    if sub:
        headers_base["Ocp-Apim-Subscription-Key"] = sub
    sess = requests.Session()

    for url, accept in _attempts(flow, key):
        resp = None
        for retry in range(2):  # one retry on throttling / transient server errors
            try:
                resp = sess.get(url, headers={**headers_base, "Accept": accept}, timeout=(6, 40))
            except requests.RequestException as exc:
                log.append(f"{url} [{accept.split(';')[0]}] -> {type(exc).__name__}: {str(exc)[:120]}")
                resp = None
                break
            if resp.status_code in (429, 500, 502, 503, 504) and retry == 0:
                time.sleep(1.5)
                continue
            break
        if resp is None:
            continue
        body = resp.text or ""
        note = f"{url} [{accept.split(';')[0]}] -> HTTP {resp.status_code}, {len(body)} bytes"
        if resp.status_code != 200 or len(body.strip()) < 20:
            log.append(note + (f": {body[:140].strip()}" if body else ""))
            if resp.status_code in (401, 403):
                log.append("   (access denied: the IMF gateway may require IMF_SUBSCRIPTION_KEY)")
            if resp.status_code == 404 and re.search(r"no ?(records|results|data)", body, re.I):
                break  # the series genuinely does not exist - stop early
            continue
        try:
            s = parse_sdmx(body)
        except Exception as exc:  # parsing problem -> try next format
            log.append(note + f", parse error: {type(exc).__name__}: {str(exc)[:120]}")
            continue
        if s.empty:
            log.append(note + ", parsed OK but 0 valid monthly observations")
            continue
        return s

    raise SeriesUnavailable(f"No data for {flow}/{key}", log)


def _series_candidates(country: dict) -> dict[str, list[tuple[str, str]]]:
    iso = country["iso3"]
    cpi = [("CPI", f"{iso}.CPI._T.IX.M")]
    if iso == "G163":  # euro-area all-items index is published as HICP
        cpi.append(("CPI", f"{iso}.HICP._T.IX.M"))
    return {"cpi": cpi, "fx": [("ER", f"{iso}.XDC_USD.PA_RT.M")]}


def load_country(country: dict) -> tuple[pd.Series, pd.Series, dict]:
    """Return (CPI, FX in local-currency-units per USD, diagnostics)."""
    diag: dict = {}
    cands = _series_candidates(country)

    def first_available(kind: str) -> pd.Series | None:
        logs = []
        for flow, key in cands[kind]:
            try:
                s = fetch_series(flow, key)
                diag[kind] = {"key": f"{flow}: {key}", "months": int(len(s)),
                              "first": s.index.min().strftime("%Y-%m"), "last": s.index.max().strftime("%Y-%m")}
                return s
            except SeriesUnavailable as exc:
                logs.append({"key": f"{flow}: {key}", "requests": exc.log})
        diag[kind] = {"months": 0, "failed": logs}
        return None

    cpi = first_available("cpi")
    if country["code"] == "USD":  # USD per USD is 1 by definition
        fx = pd.Series(1.0, index=cpi.index if cpi is not None else pd.DatetimeIndex([], name="Date"))
        diag["fx"] = {"key": "USD per USD = 1 (identity)", "months": int(len(fx))}
    else:
        fx = first_available("fx")
    empty = pd.Series(dtype="float64", index=pd.DatetimeIndex([], name="Date"))
    return (cpi if cpi is not None else empty), (fx if fx is not None else empty), diag


def build_pair(c1: dict, c2: dict) -> tuple[pd.DataFrame | None, dict]:
    """Merge the four series on common valid months and compute S(t) and RER(t)."""
    p1, e1, d1 = load_country(c1)
    p2, e2, d2 = load_country(c2)
    diag = {c1["name"]: d1, c2["name"]: d2}
    df = pd.concat({"P1": p1, "E1": e1, "P2": p2, "E2": e2}, axis=1, join="inner").dropna()
    if df.empty:
        return None, diag
    df = df.astype("float64")
    df.index.name = "Date"
    # E = local currency per USD  =>  currency-2 per currency-1 = E2 / E1
    df["S"] = df["E2"] / df["E1"]
    df["RER"] = df["S"] * df["P1"] / df["P2"]
    return df, diag


def analyse(df: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> tuple[pd.DataFrame, float]:
    """Slice the sample and (re)compute RER* and the Real Index for that sample."""
    sample = df.loc[start:end].copy()
    rer_star = float(sample["RER"].mean())  # only valid months exist in df
    sample["RER_star"] = rer_star
    sample["Real_Index"] = 100.0 * sample["RER"] / rer_star
    return sample, rer_star


# =============================================================================
# 3. FRONT END
# =============================================================================
import plotly.graph_objects as go  # noqa: E402  (kept next to the UI code that uses it)

st.set_page_config(page_title="IMF Real Exchange Rate", page_icon="💱", layout="wide")
st.markdown(
    """
    <style>
      .block-container {max-width: 1150px; padding-top: 2rem;}
      div[data-testid="stSegmentedControl"] button {border-radius: 999px; padding: 0.35rem 1.6rem;}
      div[data-testid="stSegmentedControl"] > div {gap: 0.5rem;}
      div[data-testid="stSegmentedControl"] button[kind="segmented_controlActive"] {font-weight: 700;}
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("Real exchange rate from IMF data")
st.caption(
    "S(t) = units of Country 2 currency per 1 unit of Country 1 currency  |  "
    "RER(t) = S(t) x P1(t) / P2(t)  |  Real Index = 100 x RER(t) / RER*"
)

default_1 = next(i for i, c in enumerate(COUNTRIES) if c["iso3"] == "USA")
default_2 = next(i for i, c in enumerate(COUNTRIES) if c["iso3"] == "G163")

col_a, col_b = st.columns(2)
with col_a:
    c1 = st.selectbox("Country 1", COUNTRIES, index=default_1, format_func=country_label,
                      placeholder="Search by country, currency name or code", key="country_1")
with col_b:
    c2 = st.selectbox("Country 2", COUNTRIES, index=default_2, format_func=country_label,
                      placeholder="Search by country, currency name or code", key="country_2")

mode = st.segmented_control("Chart", ["Real", "Nominal", "Both"], default="Both",
                            selection_mode="single", label_visibility="collapsed", key="mode")
mode = mode or "Both"

if c1["iso3"] == c2["iso3"]:
    st.warning("Please choose two different countries.")
    st.stop()

with st.spinner("Downloading monthly CPI and exchange-rate series from the IMF..."):
    data, diagnostics = build_pair(c1, c2)

if data is None:
    st.error(
        "No overlapping monthly CPI and exchange-rate observations could be built for this pair. "
        "Details below show which series were missing or why the IMF request failed."
    )
    st.json(diagnostics, expanded=2)
    st.stop()

# ---- sample period (sidebar) -------------------------------------------------
months = list(data.index)
with st.sidebar:
    st.header("Sample period")
    first, last = st.select_slider(
        "Start and end month", options=months, value=(months[0], months[-1]),
        format_func=lambda d: d.strftime("%b %Y"), key=f"period_{c1['iso3']}_{c2['iso3']}",
    )
    st.caption(f"Overlapping data: {months[0]:%b %Y} - {months[-1]:%b %Y} ({len(months)} valid months)")
    with st.expander("Data sources"):
        st.json(diagnostics, expanded=1)

sample, rer_star = analyse(data, first, last)
if len(sample) < 2:
    st.warning("Please select a sample with at least two months.")
    st.stop()

last_row = sample.iloc[-1]
overvalued = bool(last_row["RER"] > rer_star)
gap = 100.0 * (last_row["RER"] / rer_star - 1.0)
cur1, cur2 = c1["code"], c2["code"]

m1, m2, m3, m4 = st.columns(4)
m1.metric("Latest month", f"{sample.index[-1]:%b %Y}")
m2.metric(f"Latest S(t) ({cur2} per {cur1})", f"{last_row['S']:,.4f}")
m3.metric("Real Index (average = 100)", f"{last_row['Real_Index']:.1f}")
m4.metric("RER* (sample average)", f"{rer_star:,.4f}")

if overvalued:
    st.error(f"Latest RER is above its sample average (+{gap:.1f}%): the **{c1['currency']} ({cur1})** is currently **overvalued** against the {c2['currency']}.")
else:
    st.success(f"Latest RER is at or below its sample average ({gap:.1f}%): the **{c1['currency']} ({cur1})** is **not overvalued** against the {c2['currency']}.")

# ---- chart -------------------------------------------------------------------
REAL_C, NOM_C = "#2563EB", "#EA580C"
fig = go.Figure()
if mode in ("Real", "Both"):
    fig.add_trace(go.Scatter(
        x=sample.index, y=sample["Real_Index"], name="Real Index (RER = 100 at average)",
        mode="lines", line=dict(color=REAL_C, width=2.4), yaxis="y",
        customdata=sample[["RER"]].to_numpy(),
        hovertemplate="Real Index: %{y:.2f}<br>RER: %{customdata[0]:.4f}<extra></extra>",
    ))
    fig.add_hline(y=100, line=dict(color=REAL_C, width=1, dash="dot"), opacity=0.5)
if mode in ("Nominal", "Both"):
    fig.add_trace(go.Scatter(
        x=sample.index, y=sample["S"], name=f"Nominal S(t) ({cur2} per {cur1})",
        mode="lines", line=dict(color=NOM_C, width=2.0), yaxis="y2" if mode == "Both" else "y",
        hovertemplate=f"S(t): %{{y:,.4f}} {cur2} per {cur1}<extra></extra>",
    ))

real_title = "Real Index (sample average = 100)"
nom_title = f"Nominal S(t), {cur2} per 1 {cur1}"
layout = dict(
    height=520, margin=dict(l=10, r=10, t=30, b=10), hovermode="x unified",
    legend=dict(orientation="h", y=1.08, x=0), template="plotly_white",
    xaxis=dict(title="Month", hoverformat="%b %Y", showspikes=True, spikemode="across", spikethickness=1),
)
if mode == "Both":
    layout["yaxis"] = dict(title=dict(text=real_title, font=dict(color=REAL_C)), tickfont=dict(color=REAL_C))
    layout["yaxis2"] = dict(title=dict(text=nom_title, font=dict(color=NOM_C)), tickfont=dict(color=NOM_C),
                            overlaying="y", side="right", showgrid=False)
else:
    layout["yaxis"] = dict(title=real_title if mode == "Real" else nom_title)
fig.update_layout(**layout)
st.plotly_chart(fig, use_container_width=True)

# ---- CSV download ------------------------------------------------------------
out = sample.reset_index()
out["Date"] = out["Date"].dt.strftime("%Y-%m")
out = out.rename(columns={
    "P1": f"CPI_{c1['iso3']}", "P2": f"CPI_{c2['iso3']}",
    "E1": f"{cur1}_per_USD", "E2": f"{cur2}_per_USD",
    "S": f"S_{cur2}_per_{cur1}", "RER": "RER", "RER_star": "RER_star", "Real_Index": "Real_Index",
})
st.download_button(
    "Download CSV (selected sample)", out.to_csv(index=False).encode("utf-8"),
    file_name=f"rer_{c1['iso3']}_{c2['iso3']}_{first:%Y%m}_{last:%Y%m}.csv", mime="text/csv",
)
st.caption("Source: IMF (api.imf.org). Months with a missing CPI or exchange rate for either country are excluded.")
