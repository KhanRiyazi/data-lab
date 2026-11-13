import html
import re
import time
from collections import Counter

import requests
from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/api", tags=["career"])

UA = {"User-Agent": "DataLab/1.0 (personal career research)"}
CACHE_SECONDS = 12 * 3600  # both sources ask for gentle use: a few calls a day
_cache = {"t": 0.0, "data": None}

REMOTIVE = "https://remotive.com/api/remote-jobs"
JOBICY = "https://jobicy.com/api/v2/remote-jobs"
REMOTIVE_SEARCHES = ["ai", "trainer"]
JOBICY_TAGS = ["trainer", "tutor"]

CATEGORIES = [
    ("AI training", r"ai trainer|ai training|annotat|rlhf|data label|labell?ing|model evaluat|llm evaluat|\brater\b|prompt (writer|engineer)|ai tutor"),
    ("Teaching and training", r"tutor|instructor|trainer|teacher|curriculum|lecturer|educator|coach|facilitator"),
    ("Data and AI", r"data analyst|data scientist|machine learning|ml engineer|ai engineer|analytics|business intelligence"),
]
VOCAB = {
    "python": r"python", "sql": r"sql", "statistics": r"statistics|statistical",
    "mathematics": r"math|maths|mathematics|mathematical", "physics": r"physics",
    "chemistry": r"chemistry", "biology": r"biology", "stem": r"stem",
    "machine learning": r"machine learning|ml", "deep learning": r"deep learning|neural networks?",
    "llm": r"llms?|large language models?|generative ai|genai",
    "prompt engineering": r"prompt engineering|prompts?|prompting",
    "rlhf": r"rlhf|reinforcement learning from human feedback",
    "data annotation": r"annotation|labell?ing", "model evaluation": r"evaluat\w+|rubrics?|red[- ]team\w*",
    "data analysis": r"data analysis|analytics|data analyst", "excel / sheets": r"excel|google sheets|spreadsheets?",
    "tableau / looker": r"tableau|power bi|looker", "bigquery": r"bigquery",
    "tutoring": r"tutor\w*", "teaching": r"teach\w*|instruct\w*|curriculum|lesson",
    "research": r"research", "writing": r"writing|writer|content creation", "coding": r"coding|programming|software",
}
VOCAB_RX = {k: re.compile(r"\b(?:" + v + r")\b", re.I) for k, v in VOCAB.items()}
CAT_RX = [(n, re.compile(p, re.I)) for n, p in CATEGORIES]
INDIA_RX = re.compile(r"worldwide|anywhere|global|asia|apac|india", re.I)


def _text(s):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s or ""))).strip()


def _join(v):
    return ", ".join(v) if isinstance(v, list) else (v or "")


def classify(title, body):
    hay = f"{title} {body[:400]}"
    for name, rx in CAT_RX:
        if rx.search(hay):
            return name
    return None


def build(job):
    """job: dict with title, company, source, location, type, posted, salary, url, body."""
    cat = classify(job["title"], job["body"])
    if not cat:
        return None
    hay = f"{job['title']} {job['body'][:3000]}"
    needs = [k for k, rx in VOCAB_RX.items() if rx.search(hay)]
    loc = job["location"]
    return {
        "title": job["title"], "company": job["company"], "source": job["source"],
        "location": loc or "Not stated", "type": job["type"], "posted": job["posted"],
        "salary": job["salary"], "url": job["url"], "category": cat, "needs": needs,
        "india_ok": (not loc) or bool(INDIA_RX.search(loc)),
    }


def _remotive(term):
    r = requests.get(REMOTIVE, params={"search": term, "limit": 100}, headers=UA, timeout=15)
    r.raise_for_status()
    for j in r.json().get("jobs", []):
        yield {"title": j.get("title", ""), "company": j.get("company_name", ""), "source": "Remotive",
               "location": j.get("candidate_required_location", ""), "type": (j.get("job_type") or "").replace("_", " "),
               "posted": (j.get("publication_date") or "")[:10], "salary": j.get("salary", ""),
               "url": j.get("url", ""), "body": _text(j.get("description"))}


def _jobicy(tag):
    r = requests.get(JOBICY, params={"count": 50, "tag": tag}, headers=UA, timeout=15)
    r.raise_for_status()
    for j in r.json().get("jobs", []):
        sal = ""
        if j.get("annualSalaryMin"):
            sal = f"{j.get('salaryCurrency', '')} {j['annualSalaryMin']}-{j.get('annualSalaryMax', '')}/yr".strip()
        yield {"title": html.unescape(j.get("jobTitle", "")), "company": j.get("companyName", ""), "source": "Jobicy",
               "location": _join(j.get("jobGeo")), "type": _join(j.get("jobType")),
               "posted": (j.get("pubDate") or "")[:10], "salary": sal,
               "url": j.get("url", ""), "body": _text(j.get("jobDescription"))}


@router.get("/career")
def career():
    if _cache["data"] and time.time() - _cache["t"] < CACHE_SECONDS:
        return _cache["data"]
    raw, errors = [], []
    plan = [(_remotive, t) for t in REMOTIVE_SEARCHES] + [(_jobicy, t) for t in JOBICY_TAGS]
    for fn, term in plan:
        try:
            raw += list(fn(term))
        except (requests.RequestException, ValueError) as exc:
            errors.append(f"{fn.__name__} {term}: {str(exc)[:80]}")
        time.sleep(1)  # be gentle with free APIs
    seen, jobs = set(), []
    for j in raw:
        if not j["url"] or j["url"] in seen:
            continue
        seen.add(j["url"])
        b = build(j)
        if b:
            jobs.append(b)
    if not jobs:
        if _cache["data"]:
            return _cache["data"]
        raise HTTPException(status_code=502, detail="Job sources returned nothing: " + "; ".join(errors))
    jobs.sort(key=lambda j: j["posted"], reverse=True)
    demand = Counter(n for j in jobs for n in j["needs"])
    data = {
        "total": len(jobs),
        "demand": [{"skill": k, "count": v} for k, v in demand.most_common(14)],
        "sources": ["Remotive", "Jobicy"],
        "errors": errors,
        "jobs": jobs[:200],
    }
    _cache.update(t=time.time(), data=data)
    return data