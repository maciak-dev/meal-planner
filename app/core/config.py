import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy.engine import make_url


load_dotenv()

ENV = os.getenv("ENV", "dev").lower()
APP_INSTANCE = os.getenv("APP_INSTANCE", "production" if ENV == "prod" else ENV).lower()
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
COOKIE_SECURE = ENV == "prod"
AUTO_CREATE_SCHEMA = ENV == "dev"
PRODUCTION_DATABASE_NAME = os.getenv("PRODUCTION_DATABASE_NAME", "fastapi_db")
EXPECTED_DATABASE_NAME = os.getenv("EXPECTED_DATABASE_NAME")


def _require_env(name: str, *, allow_default: str | None = None) -> str:
    value = os.getenv(name)
    if value:
        return value

    if allow_default is not None:
        return allow_default

    raise RuntimeError(f"{name} environment variable is required")


def _database_name_from_url(database_url: str) -> str:
    url = make_url(database_url)

    if url.get_backend_name() == "sqlite":
        return Path(url.database or "").name

    return url.database or ""


DATABASE_URL = _require_env("DATABASE_URL")
SECRET_KEY = _require_env("SECRET_KEY", allow_default="dev-secret" if ENV == "dev" else None)
DATABASE_NAME = _database_name_from_url(DATABASE_URL)

if not EXPECTED_DATABASE_NAME and APP_INSTANCE == "rc":
    EXPECTED_DATABASE_NAME = "fastapi_db_rc"

if EXPECTED_DATABASE_NAME and DATABASE_NAME != EXPECTED_DATABASE_NAME:
    raise RuntimeError(
        f"Configured DATABASE_URL points to '{DATABASE_NAME}', expected '{EXPECTED_DATABASE_NAME}' for instance '{APP_INSTANCE}'"
    )

if APP_INSTANCE == "rc" and DATABASE_NAME == PRODUCTION_DATABASE_NAME:
    raise RuntimeError("RC instance cannot use the production database")
