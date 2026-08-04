from app.core.config import AUTO_CREATE_SCHEMA
from app.core.database import Base, engine


def initialize_database_schema() -> None:
    if AUTO_CREATE_SCHEMA:
        Base.metadata.create_all(bind=engine)
