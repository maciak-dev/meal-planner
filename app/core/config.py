import os
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from dotenv import dotenv_values, find_dotenv
from sqlalchemy.engine import make_url


@dataclass(frozen=True)
class Settings:
    ENV: str
    APP_INSTANCE: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    COOKIE_SECURE: bool
    AUTO_CREATE_SCHEMA: bool
    PRODUCTION_DATABASE_NAME: str
    EXPECTED_DATABASE_NAME: str | None
    DATABASE_URL: str
    SECRET_KEY: str
    DATABASE_NAME: str


def _require_value(values: Mapping[str, str], name: str, *, allow_default: str | None = None) -> str:
    value = values.get(name)
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


def load_settings(
    *,
    load_env_file: bool = True,
    env_file: str | os.PathLike[str] | None = None,
    environ: Mapping[str, str] | None = None,
) -> Settings:
    """Build settings without mutating the process environment."""
    values: dict[str, str] = {}
    if load_env_file:
        dotenv_path = str(env_file) if env_file is not None else find_dotenv(usecwd=True)
        if dotenv_path:
            values.update({key: value for key, value in dotenv_values(dotenv_path).items() if value is not None})
    values.update(dict(os.environ if environ is None else environ))

    env = values.get("ENV", "dev").lower()
    app_instance = values.get("APP_INSTANCE", "production" if env == "prod" else env).lower()
    expected_database_name = values.get("EXPECTED_DATABASE_NAME")
    if not expected_database_name and app_instance == "rc":
        expected_database_name = "fastapi_db_rc"

    database_url = _require_value(values, "DATABASE_URL")
    secret_key = _require_value(values, "SECRET_KEY", allow_default="dev-secret" if env == "dev" else None)
    database_name = _database_name_from_url(database_url)
    production_database_name = values.get("PRODUCTION_DATABASE_NAME", "fastapi_db")

    if expected_database_name and database_name != expected_database_name:
        raise RuntimeError(
            f"Configured DATABASE_URL points to '{database_name}', expected '{expected_database_name}' for instance '{app_instance}'"
        )

    if app_instance == "rc" and database_name == production_database_name:
        raise RuntimeError("RC instance cannot use the production database")

    return Settings(
        ENV=env,
        APP_INSTANCE=app_instance,
        ALGORITHM=values.get("JWT_ALGORITHM", "HS256"),
        ACCESS_TOKEN_EXPIRE_MINUTES=int(values.get("ACCESS_TOKEN_EXPIRE_MINUTES", "60")),
        COOKIE_SECURE=env == "prod",
        AUTO_CREATE_SCHEMA=env == "dev",
        PRODUCTION_DATABASE_NAME=production_database_name,
        EXPECTED_DATABASE_NAME=expected_database_name,
        DATABASE_URL=database_url,
        SECRET_KEY=secret_key,
        DATABASE_NAME=database_name,
    )


_LOAD_ENV_FILE = os.getenv("MEAL_PLANNER_LOAD_ENV_FILE", "1").lower() not in {"0", "false", "no"}
settings = load_settings(load_env_file=_LOAD_ENV_FILE)

ENV = settings.ENV
APP_INSTANCE = settings.APP_INSTANCE
ALGORITHM = settings.ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES
COOKIE_SECURE = settings.COOKIE_SECURE
AUTO_CREATE_SCHEMA = settings.AUTO_CREATE_SCHEMA
PRODUCTION_DATABASE_NAME = settings.PRODUCTION_DATABASE_NAME
EXPECTED_DATABASE_NAME = settings.EXPECTED_DATABASE_NAME
DATABASE_URL = settings.DATABASE_URL
SECRET_KEY = settings.SECRET_KEY
DATABASE_NAME = settings.DATABASE_NAME
