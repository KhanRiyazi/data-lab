from pathlib import Path

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from app.db.database import SessionLocal, Reading
from app.routers import jobs, prices

STATIC_DIR = Path(__file__).resolve().parent / "static"

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

app.include_router(jobs.router)
app.include_router(prices.router)


def get_db():
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
    rows = db.query(Reading).order_by(Reading.id.desc()).limit(24).all()
    rows.reverse()
    if not rows:
        return {"labels": [], "values": [], "message": "No data yet. Run the collector."}
    return {"labels": [r.label[-5:] for r in rows], "values": [r.value for r in rows]}


# Must stay LAST, otherwise it swallows the API routes above.
app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")