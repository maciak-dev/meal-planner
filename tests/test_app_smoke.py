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


class AppSmokeTests(unittest.TestCase):
    def tearDown(self) -> None:
        purge_app_modules()

    def test_app_can_be_created_without_network(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            env = {
                "ENV": "dev",
                "APP_INSTANCE": "dev",
                "SECRET_KEY": "dev-secret",
                "DATABASE_URL": f"sqlite:///{Path(tmpdir) / 'smoke.db'}",
            }
            with mock.patch.dict(os.environ, env, clear=True):
                main = importlib.import_module("app.main")
                paths = {route.path for route in main.app.routes}
                self.assertIn("/", paths)
                self.assertIn("/login", paths)
                self.assertIn("/static", paths)
