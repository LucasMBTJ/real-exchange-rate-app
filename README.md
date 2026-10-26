# IMF Real Exchange Rate explorer

Streamlit app (Python 3.12) that downloads monthly CPI and exchange-rate data from the IMF
and computes the real exchange rate between any two IMF countries or the Euro area.

## Run
```bash
pip install -r requirements.txt
streamlit run app.py
```
On Streamlit Community Cloud choose Python 3.12 under *Advanced settings*; `app.py` and
`requirements.txt` must be in the repository root.

## Method
* `S(t)` = units of Country 2 currency per 1 unit of Country 1 currency = `E2(t) / E1(t)`,
  where `E` is the IMF rate in local currency per USD (USD itself = 1).
* `RER(t) = S(t) x P1(t) / P2(t)`.
* `RER*` = mean of `RER(t)` over the valid months of the selected sample (months where any of
  the four series is missing are dropped). It is recomputed whenever the sample period changes.
* `Real Index(t) = 100 x RER(t) / RER*`. Nominal `S(t)` is plotted in actual currency units on its own axis.
* If the latest `RER(t)` in the sample is above `RER*`, Country 1's currency is flagged as **overvalued**.

## IMF data
| Series | Dataflow | Key |
|---|---|---|
| Monthly CPI, all items, index | `IMF.STA/CPI` | `{ISO3}.CPI._T.IX.M` |
| Exchange rate, period average, LCU per USD | `IMF.STA/ER` | `{ISO3}.XDC_USD.PA_RT.M` |

Base URL: `https://api.imf.org/external/sdmx/3.0`. Euro area = `G163` (its CPI is published as
`G163.HICP._T.IX.M` if `G163.CPI...` is empty). Each series is downloaded in full, filtered to
January 1976 onward locally, and cached for 6 hours. The app tries several dataflow versions
(`~`, `+`, pinned) and response formats (CSV, SDMX-JSON, XML), then the SDMX 2.1 endpoint.

If the IMF gateway requires a key, set `IMF_SUBSCRIPTION_KEY` as an environment variable or
Streamlit secret.

## Data storage
Each series is a `float64` pandas Series on a month-start `DatetimeIndex`; the pair is a single
DataFrame of contiguous `float64` columns. No Python objects per observation.

## Notes and limits
* Coverage varies: a country needs both CPI and an exchange rate. If a pair fails, the app shows
  which series/requests failed (also under *Data sources* in the sidebar).
* Euro area exchange rates start in 1999. Euro-adopting countries report in their own series, so
  history before adoption may be in the legacy currency or converted - check the first months.
* Flags are emoji: Windows browsers may display two letters instead of a flag.
* The drop-down search matches country name, currency name and 3-letter code.
* USD-using economies (e.g. Ecuador, El Salvador, Panama) use an exchange rate of 1.
