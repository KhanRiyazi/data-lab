import time
from collections import Counter

import requests
from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/api", tags=["jobs"])

# Remotive public API: please keep requests rare, show the source and link back.
SOURCE_URL = "https://remotive.com/api/remote-jobs"
CACHE_SECONDS = 6 * 3600
_cache = {"t": 0.0, "jobs": []}


def _load_jobs():
    """Return cached jobs; call the source at most once per CACHE_SECONDS."""
    if _cache["jobs"] and time.time() - _cache["t"] < CACHE_SECONDS:
        return _cache["jobs"]
    try:
        r = requests.get(
            SOURCE_URL,
            params={"category": "data", "limit": 100},
            headers={"User-Agent": "DataLab/1.0 (learning project)"},
            timeout=15,
        )
        r.raise_for_status()
        jobs = r.json().get("jobs", [])
    except (requests.RequestException, ValueError) as exc:
        if _cache["jobs"]:  # serve stale data rather than fail
            return _cache["jobs"]
        raise HTTPException(status_code=502, detail=f"Jobs source unavailable: {exc}")
    _cache["t"] = time.time()
    _cache["jobs"] = jobs
    return jobs


@router.get("/jobs")
def jobs():
    all_jobs = _load_jobs()
    skills = Counter(t.strip().lower() for j in all_jobs for t in j.get("tags", []) if t.strip())
    rows = [
        {
            "title": j.get("title", ""),
            "company": j.get("company_name", ""),
            "job_type": j.get("job_type", ""),
            "location": j.get("candidate_required_location", ""),
            "posted": (j.get("publication_date") or "")[:10],
            "salary": j.get("salary", ""),
            "url": j.get("url", ""),
        }
        for j in all_jobs
    ]
    return {
        "source": "Remotive",
        "source_url": "https://remotive.com",
        "total": len(all_jobs),
        "shown": len(rows),
        "with_salary": sum(1 for j in all_jobs if j.get("salary")),
        "top_skills": [{"skill": k, "count": v} for k, v in skills.most_common(10)],
        "jobs": rows,
    }