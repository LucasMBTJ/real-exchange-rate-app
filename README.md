# real-exchange-rate-app
Calculates RER for all currencies monitored by the IMF
# IMF Real Exchange Rate (RER) Calculator

An interactive Python application built with **Streamlit** and **Plotly** to compute and visualize Real Exchange Rates (RER) between world currencies using official **IMF SDMX 3.0 REST API** consumer price index (CPI) and exchange rate data.

---

## Features

- **Direct IMF SDMX API Integration**: Fetches monthly CPI (`{ISO3}.CPI._T.IX.M`) and exchange rate (`{ISO3}.XDC_USD.PA_RT.M`) data directly from the IMF starting from January 1976.
- **RER & Real Index Calculations**:
  - $S(t) = \text{Units of Country 2 currency per 1 unit of Country 1 currency} = \frac{E_2(t)}{E_1(t)}$
  - $RER(t) = S(t) \times \frac{P_1(t)}{P_2(t)}$
  - $RER^* = \text{Mean}(RER(t))$ across selected valid months.
  - $\text{Real Index}(t) = 100 \times \frac{RER(t)}{RER^*}$
- **Valuation Indicator**: Automatically alerts whether Country 1's currency is overvalued or undervalued relative to the sample period mean ($RER^*$).
- **Interactive Plotting**: Toggles between **Real Index**, **Nominal Rate $S(t)$**, or **Both** on dual axes with hover tooltips.
- **Side-by-Side Country Dropdowns**: Features country flags, country names, currency names, 3-letter ISO codes, and instant search functionality.
- **CSV Data Export**: Download all fetched time series and intermediate calculations for external audit or research.

---

## Installation & Setup

### Prerequisites
- **Python 3.12** or higher.

### 1. Clone or Extract Project Files
Ensure your project directory contains:
```text
├── app.py
├── requirements.txt
└── README.md
