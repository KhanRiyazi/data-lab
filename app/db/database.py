import os
from datetime import date, datetime, timezone

from dotenv import load_dotenv
from sqlalchemy import Column, Date, DateTime, Float, Integer, String, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

load_dotenv()
engine = create_engine(os.getenv("DATABASE_URL"), pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


def _now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Reading(Base):
    __tablename__ = "readings"
    id = Column(Integer, primary_key=True)
    source = Column(String(100))
    label = Column(String(200))
    value = Column(Float)
    created_at = Column(DateTime, default=_now)


class Application(Base):
    """One job or training application. Your own results are your best career data."""
    __tablename__ = "applications"
    id = Column(Integer, primary_key=True)
    company = Column(String(120), nullable=False)
    role = Column(String(160), nullable=False)
    source = Column(String(60), default="")
    url = Column(String(500), default="")
    status = Column(String(20), default="Applied")
    notes = Column(String(1000), default="")
    applied_on = Column(Date, default=date.today)
    created_at = Column(DateTime, default=_now)


Base.metadata.create_all(engine)