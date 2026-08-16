import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest import mock


def purge_app_modules() -> None:
    for name in list(sys.modules):
        if name == "app" or name.startswith("app."):
            sys.modules.pop(name)


class RecipePaginationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.env = mock.patch.dict(os.environ, {
            "ENV": "dev", "APP_INSTANCE": "dev", "SECRET_KEY": "dev-secret",
            "DATABASE_URL": f"sqlite:///{Path(self.tmp.name) / 'recipes.db'}",
            "MEAL_PLANNER_LOAD_ENV_FILE": "0",
        }, clear=True)
        self.env.start()
        from fastapi.testclient import TestClient
        from app.core.security import get_current_user
        from app.db.models.user import User
        import app.main as main_module

        self.main = main_module
        self.db = main_module.SessionLocal()
        self.user = User(username="pager", hashed_password="x", role="user")
        self.db.add(self.user)
        self.db.commit()
        self.db.refresh(self.user)
        self.main.app.dependency_overrides[get_current_user] = lambda: self.user
        self.client = TestClient(self.main.app)

        from app.db.models.recipe import Recipe
        for index in range(5):
            self.db.add(Recipe(
                name=f"Recipe {index}",
                description="special" if index == 4 else "ordinary",
                ingredients="rice" if index == 3 else "water",
                instructions="cook",
                user_id=self.user.id,
                created_at=datetime.utcnow() - timedelta(minutes=index),
            ))
        self.db.commit()

    def tearDown(self) -> None:
        self.main.app.dependency_overrides.clear()
        self.db.close()
        from app.core.database import engine
        engine.dispose()
        self.env.stop()
        self.tmp.cleanup()
        purge_app_modules()

    def test_pages_are_deterministic_and_advertise_end(self) -> None:
        first = self.client.get("/api/v1/recipes/?page=1&page_size=2")
        second = self.client.get("/api/v1/recipes/?page=2&page_size=2")
        last = self.client.get("/api/v1/recipes/?page=3&page_size=2")
        self.assertEqual(first.status_code, 200)
        self.assertEqual([item["name"] for item in first.json()], ["Recipe 0", "Recipe 1"])
        self.assertEqual(first.headers["X-Recipes-Has-Next"], "true")
        self.assertEqual([item["name"] for item in second.json()], ["Recipe 2", "Recipe 3"])
        self.assertEqual(last.headers["X-Recipes-Has-Next"], "false")
        ids = [item["id"] for item in first.json() + second.json() + last.json()]
        self.assertEqual(len(ids), len(set(ids)))

    def test_search_is_applied_before_pagination(self) -> None:
        response = self.client.get("/api/v1/recipes/?page=1&page_size=1&search=rice")
        self.assertEqual(response.status_code, 200)
        self.assertEqual([item["name"] for item in response.json()], ["Recipe 3"])
        self.assertEqual(response.headers["X-Recipes-Has-Next"], "false")

    def test_invalid_page_is_rejected(self) -> None:
        self.assertEqual(self.client.get("/api/v1/recipes/?page=0").status_code, 422)


if __name__ == "__main__":
    unittest.main()
