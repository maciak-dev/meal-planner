import importlib
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]


def purge_app_modules() -> None:
    for name in list(sys.modules):
        if name == "app" or name.startswith("app."):
            sys.modules.pop(name)


class ConfigTests(unittest.TestCase):
    def tearDown(self) -> None:
        purge_app_modules()

    def test_database_url_is_required_outside_dev_default(self) -> None:
        with mock.patch.dict(os.environ, {"ENV": "prod", "SECRET_KEY": "secret"}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "DATABASE_URL environment variable is required"):
                importlib.import_module("app.core.config")

    def test_rc_instance_cannot_point_to_production_database(self) -> None:
        env = {
            "ENV": "rc",
            "APP_INSTANCE": "rc",
            "SECRET_KEY": "secret",
            "DATABASE_URL": "postgresql://user:pass@127.0.0.1:5432/fastapi_db",
        }
        with mock.patch.dict(os.environ, env, clear=True):
            with self.assertRaisesRegex(RuntimeError, "expected 'fastapi_db_rc'"):
                importlib.import_module("app.core.config")

    def test_prod_uses_secure_cookie_and_disables_auto_create(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "prod.db"
            env = {
                "ENV": "prod",
                "APP_INSTANCE": "production",
                "SECRET_KEY": "secret",
                "DATABASE_URL": f"sqlite:///{db_path}",
            }
            with mock.patch.dict(os.environ, env, clear=True):
                config = importlib.import_module("app.core.config")
                self.assertTrue(config.COOKIE_SECURE)
                self.assertFalse(config.AUTO_CREATE_SCHEMA)

    def test_expected_database_name_can_differ_between_instances(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "rc.db"
            env = {
                "ENV": "rc",
                "APP_INSTANCE": "rc",
                "SECRET_KEY": "secret",
                "DATABASE_URL": f"sqlite:///{db_path}",
                "EXPECTED_DATABASE_NAME": "rc.db",
            }
            with mock.patch.dict(os.environ, env, clear=True):
                config = importlib.import_module("app.core.config")
                self.assertEqual(config.DATABASE_NAME, "rc.db")
                self.assertEqual(config.EXPECTED_DATABASE_NAME, "rc.db")
