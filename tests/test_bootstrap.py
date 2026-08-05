import importlib
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


def purge_app_modules() -> None:
    for name in list(sys.modules):
        if name == "app" or name.startswith("app."):
            sys.modules.pop(name)


class BootstrapTests(unittest.TestCase):
    def tearDown(self) -> None:
        purge_app_modules()

    def test_dev_calls_create_all(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "dev.db"
            env = {
                "ENV": "dev",
                "APP_INSTANCE": "dev",
                "SECRET_KEY": "dev-secret",
                "DATABASE_URL": f"sqlite:///{db_path}",
                "MEAL_PLANNER_LOAD_ENV_FILE": "0",
            }
            with mock.patch.dict(os.environ, env, clear=True):
                bootstrap = importlib.import_module("app.core.bootstrap")
                with mock.patch.object(bootstrap.Base.metadata, "create_all") as create_all:
                    bootstrap.initialize_database_schema()
                    create_all.assert_called_once_with(bind=bootstrap.engine)

    def test_prod_does_not_call_create_all(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "prod.db"
            env = {
                "ENV": "prod",
                "APP_INSTANCE": "production",
                "SECRET_KEY": "secret",
                "DATABASE_URL": f"sqlite:///{db_path}",
                "MEAL_PLANNER_LOAD_ENV_FILE": "0",
            }
            with mock.patch.dict(os.environ, env, clear=True):
                bootstrap = importlib.import_module("app.core.bootstrap")
                with mock.patch.object(bootstrap.Base.metadata, "create_all") as create_all:
                    bootstrap.initialize_database_schema()
                    create_all.assert_not_called()
