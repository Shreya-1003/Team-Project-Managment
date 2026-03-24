# app/database.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config.config import settings
from contextlib import contextmanager
import logging

DATABASE_URL = settings.database_url

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,           
    pool_recycle=3600,            
    connect_args={
        "timeout": 30,
        "connect_timeout": 30
    } if "mssql" in DATABASE_URL else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


@contextmanager
def get_db_session():
    db = SessionLocal()
    try:
        yield db
        db.commit()  
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

def get_db():
    with get_db_session() as db:
        yield db