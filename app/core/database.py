from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import DATABASE_URL

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
)


def enable_sqlite_foreign_keys(dbapi_connection, connection_record) -> None:
    """SQLite ignoruje klucze obce, dopóki nie włączy się tego per połączenie.

    Modele przepisu polegają na ON DELETE CASCADE po stronie bazy
    (passive_deletes=True w RecipeTranslation/RecipeIngredient). PostgreSQL na
    produkcji egzekwuje to sam; bez tej pragmy dev i testy na SQLite po cichu
    zostawiałyby osierocone tłumaczenia i składniki zamiast je kasować.
    """
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute("PRAGMA foreign_keys=ON")
    finally:
        cursor.close()


if engine.dialect.name == "sqlite":
    event.listen(engine, "connect", enable_sqlite_foreign_keys)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

print("DB FILE:", engine.url.render_as_string(hide_password=True))
