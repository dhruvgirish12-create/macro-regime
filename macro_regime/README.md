# Macro Regime Early Warning System

**Live dashboard:** [your-app.railway.app](https://your-app.railway.app)  
**Built by:** Dhruv Girish, University of Warwick

---

## What it does

Classifies the current global macro environment into one of four regimes using
real-time data, and shows what that means for carry trading and asset classes.

| Regime | VIX | PMI | Carry Signal |
|---|---|---|---|
| R1 Risk-On / Expanding | < 20 | > 50 | **ACTIVE** |
| R2 Risk-On / Contracting | < 20 | ≤ 50 | Flat |
| R3 Risk-Off / Expanding | ≥ 20 | > 50 | Flat |
| R4 Risk-Off / Contracting | ≥ 20 | ≤ 50 | Flat |

Expected returns per regime derived from a 19-year backtest (2005–2024).  
Regime conditioning improved Sharpe from **1.08 → 1.43** (+32%) and cut max drawdown by **38%**.

---

## Run locally

```bash
pip install -r requirements.txt
python app.py
# Open http://localhost:5000
```

## Deploy to Railway (5 minutes)

1. Push this folder to a GitHub repo
2. Go to railway.app → New Project → Deploy from GitHub repo
3. Select your repo — Railway auto-detects Python and deploys
4. Optional: add `FRED_API_KEY` environment variable for higher API rate limits
   (free key at fred.stlouisfed.org/docs/api)
5. Your live URL appears in the Railway dashboard

## Data sources

| Data | Source | Series | Cost |
|---|---|---|---|
| VIX | FRED | `VIXCLS` | Free |
| PMI | FRED | `NAPM` (ISM) | Free |
| S&P 500 | FRED | `SP500` | Free |
| Gold | FRED | `GOLDAMGBD228NLBM` | Free |
| 10Y Yield | FRED | `GS10` | Free |
| USD Index | FRED | `DTWEXBGS` | Free |

All data via the St. Louis Fed FRED API — no Bloomberg or Refinitiv needed.

## API

The dashboard exposes a JSON API:

```
GET /api/regime   → current regime, VIX, PMI, signal, expected returns
GET /api/refresh  → force data refresh
```

## File structure

```
macro_regime/
├── app.py           # Flask server
├── data.py          # FRED data fetching + regime classifier
├── templates/
│   └── index.html   # Dashboard UI
├── requirements.txt
├── Procfile         # Railway/Heroku deployment
└── railway.json     # Railway config
```
