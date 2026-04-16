"""
app.py
------
Flask web server for the Macro Regime Early Warning System.
Run locally:  python app.py
Deploy:       Push to GitHub → Railway auto-deploys
"""

import json
import datetime
from flask import Flask, render_template, jsonify
from data import get_all_data, REGIME_COLORS, REGIME_BG

app = Flask(__name__)

# Simple in-memory cache — refreshes every 60 minutes
_cache = {"data": None, "ts": None}
CACHE_MINUTES = 60


def get_cached_data():
    now = datetime.datetime.utcnow()
    if (
        _cache["data"] is None
        or _cache["ts"] is None
        or (now - _cache["ts"]).seconds > CACHE_MINUTES * 60
    ):
        print("Fetching fresh data...")
        try:
            _cache["data"] = get_all_data()
            _cache["ts"] = now
        except Exception as e:
            print(f"Data fetch error: {e}")
            if _cache["data"] is None:
                _cache["data"] = get_fallback_data()
    return _cache["data"]


def get_fallback_data():
    """Fallback if all APIs are down — shows demo data with clear label."""
    return {
        "current": {
            "vix": 18.4,
            "vix_date": "demo",
            "pmi": 52.1,
            "pmi_date": "demo",
            "regime_id": 1,
            "regime_label": "Risk-On / Expanding",
            "regime_color": "#3B6D11",
            "regime_bg": "#EAF3DE",
            "carry_signal": "ACTIVE",
            "expected": {"carry": 10.0, "equities": 18.2,
                         "bonds": 2.1, "gold": 4.3},
        },
        "history": [],
        "assets": {},
        "updated": "demo mode",
    }


@app.route("/")
def index():
    data = get_cached_data()
    return render_template("index.html", data=data)


@app.route("/api/regime")
def api_regime():
    """JSON endpoint — useful for anyone wanting to consume the data."""
    data = get_cached_data()
    return jsonify(data)


@app.route("/api/refresh")
def api_refresh():
    """Force cache refresh."""
    _cache["ts"] = None
    data = get_cached_data()
    return jsonify({"status": "refreshed", "updated": data["updated"]})


if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
