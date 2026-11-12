from pathlib import Path

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from app.db.database import SessionLocal, Reading

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

app = FastAPI(title="Data Lab")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://khanriyazi.in",
        "https://www.khanriyazi.in",
        "http://127.0.0.1:8000",
        "http://localhost:8000",
    ],
    allow_methods=["GET"],
    allow_headers=["*"],
)


def get_db():
    """Open a DB session per request and always close it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/data")
def data(db: Session = Depends(get_db)):
    rows = (
        db.query(Reading)
        .order_by(Reading.id.desc())
        .limit(24)
        .all()
    )
    rows.reverse()  # oldest -> newest for the chart

    if not rows:
        return {"labels": [], "values": [], "message": "No data yet. Run the collector."}

    return {
        "labels": [r.label[-5:] for r in rows],  # "2026-11-12T05:00" -> "05:00"
        "values": [r.value for r in rows],
    }


# Must stay LAST, otherwise it swallows the API routes above.
app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")