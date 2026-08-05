#!/usr/bin/env python3
import argparse
import os
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a Meal Planner production environment file.")
    parser.add_argument("--checkout", default=".", help="Meal Planner checkout containing .env")
    parser.add_argument("--check-connection", action="store_true", help="Run read-only SELECT current_database()")
    args = parser.parse_args()

    checkout = Path(args.checkout).resolve()
    sys.path.insert(0, str(checkout))

    # Keep the module import independent from the operator's shell environment.
    os.environ.update(
        {
            "MEAL_PLANNER_LOAD_ENV_FILE": "0",
            "ENV": "prod",
            "APP_INSTANCE": "validator",
            "SECRET_KEY": "validator-only",
            "DATABASE_URL": "postgresql://validator:validator@127.0.0.1:5432/meal_planner_validator",
        }
    )

    from app.core.config import load_settings

    env_file = checkout / ".env"
    try:
        settings = load_settings(load_env_file=True, env_file=env_file, environ={})
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"Configuration validation failed: {exc}", file=sys.stderr)
        return 1

    checks = {
        "ENV": settings.ENV == "prod",
        "APP_INSTANCE": settings.APP_INSTANCE == "production",
        "DATABASE_NAME": settings.DATABASE_NAME == "fastapi_db",
        "COOKIE_SECURE": settings.COOKIE_SECURE is True,
        "AUTO_CREATE_SCHEMA": settings.AUTO_CREATE_SCHEMA is False,
        "DATABASE_URL": not settings.DATABASE_URL.lower().startswith("sqlite"),
    }
    for name, value in (
        ("ENV", settings.ENV),
        ("APP_INSTANCE", settings.APP_INSTANCE),
        ("DATABASE_NAME", settings.DATABASE_NAME),
        ("COOKIE_SECURE", settings.COOKIE_SECURE),
        ("AUTO_CREATE_SCHEMA", settings.AUTO_CREATE_SCHEMA),
    ):
        print(f"{name}={value}")

    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        print(f"Invalid production configuration: {', '.join(failed)}", file=sys.stderr)
        return 1

    if args.check_connection:
        from sqlalchemy import create_engine, text

        engine = create_engine(settings.DATABASE_URL)
        with engine.connect() as connection:
            database_name = connection.execute(text("SELECT current_database()")).scalar_one()
        if database_name != "fastapi_db":
            print(f"Read-only connection reached unexpected database: {database_name}", file=sys.stderr)
            return 1
        print("CONNECTION=ok")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
