import datetime as dt
import time

import requests
from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/api", tags=["prices"])

# Frankfurter: free exchange rates (European Central Bank reference data).
BASES = ["https://api.frankfurter.dev/v1", "https://api.frankfurter.app"]
CACHE_SECONDS = 3600
_cache = {"t": 0.0, "data": None}


def _get(path, params):
    last = None
    for base in BASES:
        try:
            r = requests.get(base + path, params=params, timeout=10)
            r.raise_for_status()
            return r.json()
        except (requests.RequestException, ValueError) as exc:
            last = exc
    raise last


@router.get("/prices")
def prices():
    if _cache["data"] and time.time() - _cache["t"] < CACHE_SECONDS:
        return _cache["data"]
    try:
        latest = _get("/latest", {"base": "USD", "symbols": "INR,EUR,GBP,JPY"})
        end = dt.date.today()
        start = end - dt.timedelta(days=30)
        series = _get(f"/{start}..{end}", {"base": "USD", "symbols": "INR"})
        r = latest["rates"]
        inr = r["INR"]
        days = sorted(series["rates"])
        values = [series["rates"][d]["INR"] for d in days]
    except (requests.RequestException, KeyError, TypeError) as exc:
        if _cache["data"]:
            return _cache["data"]
        raise HTTPException(status_code=502, detail=f"Prices source unavailable: {exc}")

    data = {
        "date": latest.get("date"),
        "inr_per": {
            "USD": inr,
            "EUR": inr / r["EUR"],
            "GBP": inr / r["GBP"],
            "JPY (per 100)": inr / r["JPY"] * 100,
        },
        "change_pct": (values[-1] - values[0]) / values[0] * 100 if values else 0.0,
        "history": {"labels": [d[5:] for d in days], "values": values},
        "source": "European Central Bank via Frankfurter",
    }
    _cache["t"] = time.time()
    _cache["data"] = data
    return data