from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db.models.user import User
from app.db.models.recipe import Recipe

SQLITE_URL = "sqlite:///app/db/app.db"
POSTGRES_URL = "postgresql://fastapi_user:DatabaseError404@localhost:5432/fastapi_db"

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
