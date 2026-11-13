from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from app.db.database import Application, SessionLocal

Status = Literal["Saved", "Applied", "Screening", "Interview", "Offer", "Rejected", "No response"]
RESPONDED = {"Screening", "Interview", "Offer", "Rejected"}


def local_only(request: Request):
    """The tracker holds personal data: refuse anyone not on this laptop."""
    host = request.client.host if request.client else ""
    if host not in ("127.0.0.1", "::1", "localhost"):
        raise HTTPException(status_code=403, detail="Tracker is available on this computer only")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


router = APIRouter(prefix="/api/applications", tags=["tracker"], dependencies=[Depends(local_only)])


class ApplicationIn(BaseModel):
    company: str = Field(min_length=1, max_length=120)
    role: str = Field(min_length=1, max_length=160)
    source: str = Field("", max_length=60)
    url: str = Field("", max_length=500)
    status: Status = "Applied"
    notes: str = Field("", max_length=1000)

    @field_validator("url")
    @classmethod
    def http_only(cls, v):
        if v and not v.lower().startswith(("http://", "https://")):
            raise ValueError("Link must start with http:// or https://")
        return v


class StatusIn(BaseModel):
    status: Status


def _item(a):
    return {"id": a.id, "company": a.company, "role": a.role, "source": a.source or "", "url": a.url or "",
            "status": a.status, "notes": a.notes or "", "applied_on": a.applied_on.isoformat() if a.applied_on else ""}


@router.get("")
def list_applications(db: Session = Depends(get_db)):
    rows = db.query(Application).order_by(Application.id.desc()).all()
    counts = {}
    for a in rows:
        counts[a.status] = counts.get(a.status, 0) + 1
    applied = sum(v for k, v in counts.items() if k != "Saved")
    responded = sum(v for k, v in counts.items() if k in RESPONDED)
    return {
        "items": [_item(a) for a in rows],
        "stats": {
            "total": len(rows), "applied": applied, "responded": responded,
            "response_rate": round(responded / applied * 100, 1) if applied else 0.0,
            "interviews": counts.get("Interview", 0) + counts.get("Offer", 0),
            "by_status": counts,
        },
    }


@router.post("", status_code=201)
def add_application(body: ApplicationIn, db: Session = Depends(get_db)):
    a = Application(**body.model_dump())
    db.add(a)
    db.commit()
    db.refresh(a)
    return _item(a)


@router.patch("/{app_id}")
def set_status(app_id: int, body: StatusIn, db: Session = Depends(get_db)):
    a = db.get(Application, app_id)
    if not a:
        raise HTTPException(status_code=404, detail="Not found")
    a.status = body.status
    db.commit()
    return _item(a)


@router.delete("/{app_id}")
def delete_application(app_id: int, db: Session = Depends(get_db)):
    a = db.get(Application, app_id)
    if not a:
        raise HTTPException(status_code=404, detail="Not found")
    db.delete(a)
    db.commit()
    return {"deleted": app_id}