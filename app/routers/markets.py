import datetime as dt
import time
from urllib.parse import quote

import requests
from fastapi import APIRouter, HTTPException

from app.routers.prices import prices as fx_prices

router = APIRouter(prefix="/api", tags=["markets"])

# Yahoo Finance public chart service: unofficial, for personal learning only.
# To switch to an official provider later, change only _fetch().
URL = "https://query1.finance.yahoo.com/v8/finance/chart/{sym}"
HEADERS = {"User-Agent": "Mozilla/5.0 (DataLab learning project)"}
INDICES = [
    ("^NSEI", "Nifty 50", "India"),
    ("^BSESN", "Sensex", "India"),
    ("^GSPC", "S&P 500", "US"),
    ("^IXIC", "Nasdaq", "US"),
    ("^DJI", "Dow Jones", "US"),
]
CACHE_SECONDS = 900
_cache = {"t": 0.0, "data": None}


def _fetch(sym):
    r = requests.get(
        URL.format(sym=quote(sym, safe="")),
        params={"range": "1mo", "interval": "1d"},
        headers=HEADERS,
        timeout=10,
    )
    r.raise_for_status()
    res = r.json()["chart"]["result"][0]
    off = res["meta"].get("gmtoffset", 0)
    closes = res["indicators"]["quote"][0]["close"]
    pts = {}
    for t, c in zip(res["timestamp"], closes):
        if c is not None:
            day = dt.datetime.fromtimestamp(t + off, dt.timezone.utc).strftime("%Y-%m-%d")
            pts[day] = c
    if len(pts) < 2:
        raise ValueError("not enough data")
    return pts


@router.get("/markets")
def markets():
    if _cache["data"] and time.time() - _cache["t"] < CACHE_SECONDS:
        return _cache["data"]

    series, out = {}, []
    for sym, name, region in INDICES:
        try:
            series[sym] = _fetch(sym)
        except (requests.RequestException, KeyError, IndexError, TypeError, ValueError) as exc:
            out.append({"symbol": sym, "name": name, "region": region, "error": str(exc)[:120]})
    if not series:
        if _cache["data"]:
            return _cache["data"]
        raise HTTPException(status_code=502, detail="Market data source unavailable right now")

    dates = sorted({d for pts in series.values() for d in pts})
    good = []
    for sym, name, region in INDICES:
        pts = series.get(sym)
        if not pts:
            continue
        days = sorted(pts)
        first, last, prev = pts[days[0]], pts[days[-1]], pts[days[-2]]
        good.append({
            "symbol": sym, "name": name, "region": region,
            "price": last,
            "day_pct": (last / prev - 1) * 100,
            "month_pct": (last / first - 1) * 100,
            "rebased": [round(pts[d] / first * 100, 2) if d in pts else None for d in dates],
        })
    try:
        fx = fx_prices()
    except HTTPException:
        fx = None

    data = {"dates": dates, "indices": good + out, "fx": fx, "source": "Yahoo Finance (unofficial)"}
    _cache.update(t=time.time(), data=data)
    return data