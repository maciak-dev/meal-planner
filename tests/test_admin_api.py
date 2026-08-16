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


class AdminApiTests(unittest.TestCase):
    def setUp(self) -> None:
        # Collection imports preview-token config under the outer release-test
        # environment. Re-import the application under this test's isolated DB.
        purge_app_modules()
        self._tmpdir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        db_path = Path(self._tmpdir.name) / "admin.db"
        self._env_patch = mock.patch.dict(
            os.environ,
            {
                "ENV": "dev",
                "APP_INSTANCE": "dev",
                "SECRET_KEY": "dev-secret",
                "DATABASE_URL": f"sqlite:///{db_path}",
                "MEAL_PLANNER_LOAD_ENV_FILE": "0",
                "MAP_CONTROL_CENTER_ORIGINS": "https://maciak.online",
            },
            clear=True,
        )
        self._env_patch.start()

        import app.main as main_module
        from fastapi.testclient import TestClient
        from app.core.database import SessionLocal
        from app.db.models.login_log import LoginLog, RequestLog

        self.main_module = main_module
        self.db = SessionLocal()
        self.db.add(LoginLog(username="owner", ip_address="127.0.0.1", success=True))
        self.db.add(RequestLog(path="/recipes-ui", ip_address="127.0.0.1", status_code=200))
        self.db.commit()
        self.client = TestClient(main_module.app)

    def tearDown(self) -> None:
        self.main_module.app.dependency_overrides.clear()
        self.db.close()
        from app.core.database import engine

        engine.dispose()
        self._env_patch.stop()
        self._tmpdir.cleanup()
        purge_app_modules()

    def test_admin_api_requires_meal_session_and_exposes_cors_to_configured_map(self) -> None:
        unauthenticated = self.client.get(
            "/api/v1/admin/login-logs",
            headers={"Origin": "https://maciak.online"},
        )
        self.assertEqual(unauthenticated.status_code, 401)
        self.assertEqual(
            unauthenticated.headers["access-control-allow-origin"],
            "https://maciak.online",
        )

        from app.core.dependencies import super_admin_required

        self.main_module.app.dependency_overrides[super_admin_required] = lambda: object()
        response = self.client.get(
            "/api/v1/admin/login-logs?range=all",
            headers={"Origin": "https://maciak.online"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()[0]["username"], "owner")
        self.assertEqual(response.headers["access-control-allow-origin"], "https://maciak.online")
        self.assertEqual(response.headers["access-control-allow-credentials"], "true")

        requests = self.client.get(
            "/api/v1/admin/requests?range=all",
            headers={"Origin": "https://maciak.online"},
        )
        self.assertEqual(requests.status_code, 200)
        self.assertIn("/recipes-ui", {entry["path"] for entry in requests.json()})

    def test_unconfigured_origin_does_not_receive_cors_access(self) -> None:
        from app.core.dependencies import super_admin_required

        self.main_module.app.dependency_overrides[super_admin_required] = lambda: object()
        response = self.client.get(
            "/api/v1/admin/login-logs?range=all",
            headers={"Origin": "https://attacker.example"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("access-control-allow-origin", response.headers)


if __name__ == "__main__":
    unittest.main()
