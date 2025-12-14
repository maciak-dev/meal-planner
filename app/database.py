from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATABASE_URL = f"sqlite:///{os.path.join(BASE_DIR, 'meal_etl.db')}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}  # wymagane przy SQLite
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


# Dependency dla FastAPI (będziemy używać w routerach)
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
