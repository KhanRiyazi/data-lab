import datetime as dt
import html
import re
import time
import xml.etree.ElementTree as ET

import requests
from fastapi import APIRouter

router = APIRouter(prefix="/api", tags=["google"])

ATOM = "{http://www.w3.org/2005/Atom}"
UA = {"User-Agent": "DataLab/1.0 (personal learning project)"}
CACHE_SECONDS = 3600
DAYS = 90

# Official Google feeds. If one fails, the others still work.
FEEDS = [
    {"name": "Workspace Updates", "url": "https://workspaceupdates.googleblog.com/atom.xml", "tag": None},
    {"name": "BigQuery", "url": "https://docs.cloud.google.com/feeds/bigquery-release-notes.xml", "tag": "BigQuery"},
    {"name": "Looker", "url": "https://docs.cloud.google.com/feeds/looker-release-notes.xml", "tag": "Looker"},
    {"name": "Looker Studio", "url": "https://cloud.google.com/feeds/lookerstudio-release-notes.xml", "tag": "Looker Studio"},
]
PRODUCTS = {
    "Gemini": r"\bgemini\b",
    "Antigravity": r"\bantigravity\b",
    "AI Studio": r"ai studio",
    "Apps Script": r"apps script",
    "Sheets": r"\bsheets\b",
    "BigQuery": r"\bbigquery\b",
    "Looker": r"\blooker\b(?! studio)",
    "Looker Studio": r"looker studio|data studio",
    "NotebookLM": r"notebooklm|gemini notebook",
}
_cache = {"t": 0.0, "data": None}


def _text(s):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s or ""))).strip()


def parse_feed(xml_bytes, feed):
    root = ET.fromstring(xml_bytes)
    items = []
    for e in root.iter(ATOM + "entry"):
        title = (e.findtext(ATOM + "title") or "").strip()
        day = (e.findtext(ATOM + "updated") or e.findtext(ATOM + "published") or "")[:10]
        link = ""
        for l in e.findall(ATOM + "link"):
            if l.get("rel", "alternate") == "alternate":
                link = l.get("href", "")
                break
        body = _text(e.findtext(ATOM + "content") or e.findtext(ATOM + "summary"))
        if feed["tag"]:  # cloud release notes use the date as the title
            title = f"{feed['name']} release notes, {title}"
        hay = f"{title} {body}".lower()
        tags = [p for p, rx in PRODUCTS.items() if re.search(rx, hay)]
        if feed["tag"] and feed["tag"] not in tags:
            tags.insert(0, feed["tag"])
        if tags:
            items.append({"date": day, "title": title, "summary": body[:200], "url": link,
                          "source": feed["name"], "tags": tags})
    return items


@router.get("/google-pulse")
def google_pulse():
    if _cache["data"] and time.time() - _cache["t"] < CACHE_SECONDS:
        return _cache["data"]
    cutoff = (dt.date.today() - dt.timedelta(days=DAYS)).isoformat()
    items, feeds = [], []
    for f in FEEDS:
        try:
            r = requests.get(f["url"], headers=UA, timeout=12)
            r.raise_for_status()
            got = [i for i in parse_feed(r.content, f) if i["date"] >= cutoff]
            items += got
            feeds.append({"name": f["name"], "ok": True, "count": len(got)})
        except (requests.RequestException, ET.ParseError) as exc:
            feeds.append({"name": f["name"], "ok": False, "count": 0, "error": str(exc)[:100]})
    items.sort(key=lambda i: i["date"], reverse=True)
    counts = {}
    for i in items:
        for t in i["tags"]:
            counts[t] = counts.get(t, 0) + 1
    data = {
        "since": cutoff,
        "feeds": feeds,
        "counts": [{"product": k, "count": v} for k, v in sorted(counts.items(), key=lambda kv: -kv[1])],
        "items": items[:80],
    }
    if any(f["ok"] for f in feeds):
        _cache.update(t=time.time(), data=data)
    return data