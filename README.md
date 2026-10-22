# IMF Real Exchange Rate (RER) Calculator

An interactive Python application built with **Streamlit** and **Plotly** to compute and visualize Real Exchange Rates (RER) between world currencies using official **IMF SDMX 3.0 REST API** consumer price index (CPI) and exchange rate data.

---

## Key Features

- **Automatic Coverage Detection**: Automatically calculates the exact overlapping time window for any pair of chosen countries (e.g., Euro Area vs UK).
- **Customizable Sample Period**: Optional toggle allows users to define custom Start and End dates within valid bounds.
- **Resilient IMF Data Fetcher**: Uses primary SDMX 3.0 REST endpoints with CSV and SDMX-JSON fallback channels to ensure continuous fetching.
- **Valuation Indicator**: Automatically alerts whether Country 1's currency is overvalued or undervalued relative to the sample period mean ($RER^*$).
- **Interactive Visualizations**: Seamlessly switch between **Real Index**, **Nominal Rate $S(t)$**, or **Both** on dual axes.
- **CSV Data Export**: Download calculated observations directly for research or reporting.

---

## Quickstart Guide

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
