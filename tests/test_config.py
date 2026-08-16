import importlib
import os
import unittest
from unittest import mock


def purge_app_modules() -> None:
    import sys

    for name in list(sys.modules):
        if name == "app" or name.startswith("app."):
            sys.modules.pop(name)


class ConfigTests(unittest.TestCase):
    def tearDown(self) -> None:
        purge_app_modules()

    def test_database_url_is_required_outside_dev_default(self) -> None:
        with mock.patch.dict(
            os.environ,
            {
                "DATABASE_URL": "postgresql://test:test@127.0.0.1:5432/meal_planner_test",
                "MEAL_PLANNER_LOAD_ENV_FILE": "0",
            },
            clear=True,
        ):
            config = importlib.import_module("app.core.config")
            with self.assertRaisesRegex(RuntimeError, "DATABASE_URL environment variable is required"):
                config.load_settings(load_env_file=False, environ={"ENV": "prod", "SECRET_KEY": "secret"})

    def test_rc_instance_cannot_point_to_production_database(self) -> None:
        env = {
            "ENV": "rc",
            "APP_INSTANCE": "rc",
            "SECRET_KEY": "secret",
            "DATABASE_URL": "postgresql://user:pass@127.0.0.1:5432/fastapi_db",
        }
        with mock.patch.dict(
            os.environ,
            {
                "DATABASE_URL": "postgresql://test:test@127.0.0.1:5432/meal_planner_test",
                "MEAL_PLANNER_LOAD_ENV_FILE": "0",
            },
            clear=True,
        ):
            config = importlib.import_module("app.core.config")
            with self.assertRaisesRegex(RuntimeError, "expected 'fastapi_db_rc'"):
                config.load_settings(load_env_file=False, environ=env)

    def test_prod_uses_secure_cookie_and_disables_auto_create(self) -> None:
        config = importlib.import_module("app.core.config")
        settings = config.load_settings(
            load_env_file=False,
            environ={
                "ENV": "prod",
                "APP_INSTANCE": "production",
                "SECRET_KEY": "secret",
                "DATABASE_URL": "postgresql://test:test@127.0.0.1:5432/meal_planner_test",
            },
        )
        self.assertTrue(settings.COOKIE_SECURE)
        self.assertFalse(settings.AUTO_CREATE_SCHEMA)

    def test_dev_uses_insecure_cookie_and_allows_auto_create(self) -> None:
        config = importlib.import_module("app.core.config")
        settings = config.load_settings(
            load_env_file=False,
            environ={
                "ENV": "dev",
                "APP_INSTANCE": "dev",
                "SECRET_KEY": "secret",
                "DATABASE_URL": "postgresql://test:test@127.0.0.1:5432/meal_planner_test",
            },
        )
        self.assertFalse(settings.COOKIE_SECURE)
        self.assertTrue(settings.AUTO_CREATE_SCHEMA)

    def test_expected_database_name_can_differ_between_instances(self) -> None:
        config = importlib.import_module("app.core.config")
        settings = config.load_settings(
            load_env_file=False,
            environ={
                "ENV": "rc",
                "APP_INSTANCE": "rc",
                "SECRET_KEY": "secret",
                "DATABASE_URL": "postgresql://test:test@127.0.0.1:5432/meal_planner_rc_test",
                "EXPECTED_DATABASE_NAME": "meal_planner_rc_test",
            },
        )
        self.assertEqual(settings.DATABASE_NAME, "meal_planner_rc_test")
        self.assertEqual(settings.EXPECTED_DATABASE_NAME, "meal_planner_rc_test")

    def test_explicit_environment_ignores_dotenv_file(self) -> None:
        config = importlib.import_module("app.core.config")
        with mock.patch("app.core.config.dotenv_values", return_value={"DATABASE_URL": "sqlite:///wrong.db"}):
            settings = config.load_settings(
                load_env_file=False,
                env_file="/tmp/should-not-be-read.env",
                environ={
                    "ENV": "prod",
                    "APP_INSTANCE": "test",
                    "SECRET_KEY": "secret",
                    "DATABASE_URL": "postgresql://test:test@127.0.0.1:5432/meal_planner_test",
                    "EXPECTED_DATABASE_NAME": "meal_planner_test",
                },
            )
        self.assertEqual(settings.DATABASE_NAME, "meal_planner_test")

    def test_control_center_origins_are_explicit_exact_origins(self) -> None:
        config = importlib.import_module("app.core.config")
        settings = config.load_settings(
            load_env_file=False,
            environ={
                "ENV": "dev",
                "DATABASE_URL": "sqlite:///meal-planner-test.sqlite3",
                "MAP_CONTROL_CENTER_ORIGINS": "https://maciak.online/,http://localhost:5173",
            },
        )
        self.assertEqual(
            settings.MAP_CONTROL_CENTER_ORIGINS,
            ("https://maciak.online", "http://localhost:5173"),
        )

        for invalid_origin in ("*", "https://*.example.com"):
            with self.subTest(origin=invalid_origin), self.assertRaisesRegex(RuntimeError, "exact http"):
                config.load_settings(
                    load_env_file=False,
                    environ={
                        "ENV": "dev",
                        "DATABASE_URL": "sqlite:///meal-planner-test.sqlite3",
                        "MAP_CONTROL_CENTER_ORIGINS": invalid_origin,
                    },
                )
