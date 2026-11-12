import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Float
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime

load_dotenv()
engine = create_engine(os.getenv("DATABASE_URL"))
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

class Reading(Base):
    __tablename__ = "readings"
    id = Column(Integer, primary_key=True)
    source = Column(String(100))
    label = Column(String(200))
    value = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(engine)