import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db.models.user import User
from app.db.models.recipe import Recipe


def require_env(name):
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


SQLITE_URL = os.getenv("SQLITE_URL", "sqlite:///app/db/app.db")
POSTGRES_URL = require_env("DATABASE_URL")

sqlite_engine = create_engine(SQLITE_URL)
postgres_engine = create_engine(POSTGRES_URL)

SQLiteSession = sessionmaker(bind=sqlite_engine)
PostgresSession = sessionmaker(bind=postgres_engine)

sqlite_db = SQLiteSession()
postgres_db = PostgresSession()


def migrate(model):
    records = sqlite_db.query(model).all()
    print(f"Migrating {model.__name__}: {len(records)} records")

    for obj in records:
        data = obj.__dict__.copy()
        data.pop("_sa_instance_state", None)
        postgres_db.add(model(**data))

    postgres_db.commit()


try:
    migrate(User)
    migrate(Recipe)

    print("Business data migration completed successfully!")

finally:
    sqlite_db.close()
    postgres_db.close()
