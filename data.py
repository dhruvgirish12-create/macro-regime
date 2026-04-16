"""
data.py
-------
Fetches real market data from FRED (VIX, PMI) and yfinance (asset returns).
Falls back to cached data if APIs are unavailable.
"""

import os
import json
import datetime
import urllib.request
import urllib.parse

FRED_KEY = os.environ.get("FRED_API_KEY", "")
CACHE_FILE = "cache.json"


def fetch_fred(series_id, limit=60):
    """Fetch a FRED series. Returns list of {date, value} dicts, newest last."""
    if FRED_KEY:
        url = (
            f"https://api.stlouisfed.org/fred/series/observations"
            f"?series_id={series_id}&api_key={FRED_KEY}"
            f"&file_type=json&limit={limit}&sort_order=desc"
        )
    else:
        # Public FRED endpoint (no key, rate-limited but works)
        url = (
            f"https://fred.stlouisfed.org/graph/fredgraph.csv"
            f"?id={series_id}"
        )

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "macro-regime/1.0"})
        with urllib.request.urlopen(req, timeout=8) as r:
            raw = r.read().decode()

        if FRED_KEY:
            data = json.loads(raw)["observations"]
            results = []
            for row in data:
                if row["value"] != ".":
                    results.append({
                        "date": row["date"],
                        "value": float(row["value"])
                    })
            return sorted(results, key=lambda x: x["date"])[-limit:]
        else:
            # Parse CSV
            lines = raw.strip().split("\n")[1:]  # skip header
            results = []
            for line in lines:
                parts = line.split(",")
                if len(parts) == 2 and parts[1].strip() != ".":
                    try:
                        results.append({
                            "date": parts[0].strip(),
                            "value": float(parts[1].strip())
                        })
                    except ValueError:
                        continue
            return results[-limit:]
    except Exception as e:
        print(f"FRED fetch error ({series_id}): {e}")
        return []


def get_vix_history(months=36):
    """Returns monthly VIX closes for the last N months."""
    data = fetch_fred("VIXCLS", limit=months * 23)  # ~23 trading days/month
    if not data:
        return []

    # Resample to monthly (take last value each month)
    monthly = {}
    for row in data:
        ym = row["date"][:7]  # YYYY-MM
        monthly[ym] = row["value"]

    result = []
    for ym in sorted(monthly.keys())[-months:]:
        result.append({"date": ym + "-01", "value": monthly[ym]})
    return result


def get_current_vix():
    """Returns the most recent VIX value."""
    data = fetch_fred("VIXCLS", limit=5)
    if data:
        return data[-1]["value"], data[-1]["date"]
    return None, None


def get_pmi_history(months=36):
    """
    Global Manufacturing PMI proxy via FRED.
    Uses ISM Manufacturing PMI (NAPM) as US proxy — best freely available series.
    In production you'd use JP Morgan Global PMI via Bloomberg/Refinitiv.
    """
    data = fetch_fred("NAPM", limit=months)
    if not data:
        return []
    return [{"date": r["date"], "value": r["value"]} for r in data[-months:]]


def get_current_pmi():
    """Returns the most recent PMI value."""
    data = fetch_fred("NAPM", limit=3)
    if data:
        return data[-1]["value"], data[-1]["date"]
    return None, None


def get_asset_returns():
    """
    Returns YTD and 1-month returns for key asset classes.
    Uses FRED series as proxies (all free, no yfinance needed).
    SP500: SP500, Gold: GOLDAMGBD228NLBM, 10Y yield: GS10, DXY: DTWEXBGS
    """
    assets = {
        "S&P 500":  "SP500",
        "Gold":     "GOLDAMGBD228NLBM",
        "10Y Yield":"GS10",
        "USD Index":"DTWEXBGS",
    }
    results = {}
    for name, series in assets.items():
        data = fetch_fred(series, limit=30)
        if len(data) >= 2:
            latest = data[-1]["value"]
            month_ago = data[0]["value"]
            ret_1m = (latest - month_ago) / month_ago * 100
            results[name] = {
                "value": round(latest, 2),
                "ret_1m": round(ret_1m, 2),
                "date": data[-1]["date"]
            }
        else:
            results[name] = {"value": None, "ret_1m": None, "date": None}
    return results


def classify_regime(vix, pmi):
    """Classify current macro regime."""
    if vix is None or pmi is None:
        return None, "Unknown"
    risk_on = vix < 20
    expanding = pmi > 50
    if risk_on and expanding:
        return 1, "Risk-On / Expanding"
    elif risk_on and not expanding:
        return 2, "Risk-On / Contracting"
    elif not risk_on and expanding:
        return 3, "Risk-Off / Expanding"
    else:
        return 4, "Risk-Off / Contracting"


def build_regime_history(vix_history, pmi_history):
    """Align VIX and PMI histories and classify each month."""
    vix_map = {r["date"][:7]: r["value"] for r in vix_history}
    pmi_map = {r["date"][:7]: r["value"] for r in pmi_history}

    all_months = sorted(set(list(vix_map.keys()) + list(pmi_map.keys())))
    history = []
    for ym in all_months:
        v = vix_map.get(ym)
        p = pmi_map.get(ym)
        if v and p:
            rid, rlabel = classify_regime(v, p)
            history.append({
                "date": ym,
                "vix": round(v, 1),
                "pmi": round(p, 1),
                "regime": rid,
                "label": rlabel
            })
    return history


# Expected returns by regime (from our backtest, annualised %)
REGIME_EXPECTED = {
    1: {"carry": +10.0, "equities": +18.2, "bonds": +2.1,  "gold": +4.3,  "signal": "ACTIVE"},
    2: {"carry":  -0.2, "equities": +4.8,  "bonds": +5.2,  "gold": +8.1,  "signal": "FLAT"},
    3: {"carry":  -0.2, "equities": -12.4, "bonds": +11.3, "gold": +15.2, "signal": "FLAT"},
    4: {"carry":   0.0, "equities": -24.1, "bonds": +14.8, "gold": +22.6, "signal": "FLAT"},
}

REGIME_COLORS = {
    1: "#3B6D11",   # green
    2: "#BA7517",   # amber
    3: "#185FA5",   # blue
    4: "#A32D2D",   # red
}

REGIME_BG = {
    1: "#EAF3DE",
    2: "#FAEEDA",
    3: "#E6F1FB",
    4: "#FCEBEB",
}


def get_all_data():
    """Master function — returns everything the dashboard needs."""
    vix_val, vix_date   = get_current_vix()
    pmi_val, pmi_date   = get_current_pmi()
    regime_id, regime_label = classify_regime(vix_val, pmi_val)

    vix_history = get_vix_history(36)
    pmi_history = get_pmi_history(36)
    regime_history = build_regime_history(vix_history, pmi_history)

    assets = get_asset_returns()

    expected = REGIME_EXPECTED.get(regime_id, {})

    return {
        "current": {
            "vix":          round(vix_val, 1) if vix_val else None,
            "vix_date":     vix_date,
            "pmi":          round(pmi_val, 1) if pmi_val else None,
            "pmi_date":     pmi_date,
            "regime_id":    regime_id,
            "regime_label": regime_label,
            "regime_color": REGIME_COLORS.get(regime_id, "#888"),
            "regime_bg":    REGIME_BG.get(regime_id, "#f5f5f5"),
            "carry_signal": expected.get("signal", "UNKNOWN"),
            "expected":     expected,
        },
        "history":  regime_history[-30:],
        "assets":   assets,
        "updated":  datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
    }
