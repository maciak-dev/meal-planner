"""Regression coverage for the production-shaped Winiary confirm payload."""

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock


FIXTURE = Path(__file__).parent / "fixtures" / "recipe_import" / "winiary_paella.html"


class WiniaryConfirmWorkflowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory()
        self.env = mock.patch.dict(
            os.environ,
            {
                "ENV": "dev",
                "APP_INSTANCE": "dev",
                "SECRET_KEY": "test-secret",
                "DATABASE_URL": f"sqlite:///{Path(self.tmpdir.name) / 'winiary.db'}",
                "MEAL_PLANNER_LOAD_ENV_FILE": "0",
            },
            clear=True,
        )
        self.env.start()

        import app.main as main_module
        from fastapi.testclient import TestClient
        from app.core.database import SessionLocal
        from app.core.security import get_current_user
        from app.db.models.user import User

        self.main = main_module
        self.db = SessionLocal()
        self.user = User(username="winiary-importer", hashed_password="x", role="user")
        self.db.add(self.user)
        self.db.commit()
        self.db.refresh(self.user)
        main_module.app.dependency_overrides[get_current_user] = lambda: self.user
        self.client = TestClient(main_module.app)

    def tearDown(self) -> None:
        self.main.app.dependency_overrides.clear()
        self.db.close()
        from app.core.database import engine

        engine.dispose()
        self.env.stop()
        self.tmpdir.cleanup()
        for name in list(__import__("sys").modules):
            if name == "app" or name.startswith("app."):
                __import__("sys").modules.pop(name, None)

    def _fake_page(self, url: str):
        from app.services.recipe_import.fetcher import FetchedPage

        return FetchedPage(url=url, html=FIXTURE.read_text(encoding="utf-8"), content_type="text/html")

    def test_winiary_payload_variants_persist_and_cleanup(self) -> None:
        from app.db.models.recipe import Recipe
        from app.db.models.recipe_ingredient import RecipeIngredient
        from app.db.models.recipe_translation import RecipeTranslation

        async def fake_fetch(url: str):
            return self._fake_page(url)

        async def fake_image(_url: str):
            return "/static/uploads/winiary-regression.webp"

        before = self.db.query(Recipe).count()
        with mock.patch("app.api.v1.recipe_import.fetch_html", side_effect=fake_fetch), mock.patch(
            "app.api.v1.recipe_import.download_and_store_image", side_effect=fake_image
        ):
            for suffix, download_image, structured in (
                ("a", True, True),
                ("b", False, True),
                ("c", True, False),
                ("d", False, False),
            ):
                url = f"https://www.winiary.pl/przepisy/paella-z-kurczakiem-i-ostra-kielbasa/?test={suffix}"
                preview = self.client.post("/api/v1/recipe-import/preview", json={"url": url})
                self.assertEqual(preview.status_code, 200)
                draft = preview.json()
                self.assertEqual(len(draft["ingredients"]), 14)
                draft.pop("warnings", None)
                draft.update(
                    download_image=download_image,
                    save_structured_ingredients=structured,
                    is_public=False,
                )

                response = self.client.post("/api/v1/recipe-import/confirm", json=draft)
                self.assertEqual(response.status_code, 200, response.text)
                recipe_id = response.json()["recipe"]["id"]
                self.db.expire_all()
                recipe = self.db.get(Recipe, recipe_id)
                rows = self.db.query(RecipeIngredient).filter_by(recipe_id=recipe_id).all()
                self.assertEqual(len(rows), 14 if structured else 0)
                self.assertEqual(bool(recipe.image), download_image)
                self.assertTrue(all(row.recipe_id == recipe_id for row in rows))
                self.assertEqual(self.db.query(RecipeTranslation).filter_by(recipe_id=recipe_id).count(), 0)

                self.assertEqual(self.client.delete(f"/api/v1/recipes/{recipe_id}").status_code, 204)

        self.db.expire_all()
        self.assertEqual(self.db.query(Recipe).count(), before)
        self.assertEqual(self.db.query(RecipeIngredient).count(), 0)

    def test_integrity_error_returns_controlled_conflict_and_cleans_image(self) -> None:
        from sqlalchemy.exc import IntegrityError

        async def fake_fetch(url: str):
            return self._fake_page(url)

        async def fake_image(_url: str):
            return "/static/uploads/winiary-error.webp"

        with mock.patch("app.api.v1.recipe_import.fetch_html", side_effect=fake_fetch), mock.patch(
            "app.api.v1.recipe_import.download_and_store_image", side_effect=fake_image
        ), mock.patch(
            "app.api.v1.recipe_import.recipe_service.create_recipe_from_import",
            side_effect=IntegrityError("insert", {}, Exception("duplicate")),
        ), mock.patch("app.api.v1.recipe_import.delete_stored_image") as cleanup:
            preview = self.client.post(
                "/api/v1/recipe-import/preview",
                json={"url": "https://www.winiary.pl/przepisy/paella-z-kurczakiem-i-ostra-kielbasa/?error=1"},
            )
            payload = preview.json()
            payload.pop("warnings", None)
            payload.update(download_image=True, save_structured_ingredients=True, is_public=False)
            response = self.client.post("/api/v1/recipe-import/confirm", json=payload)

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["detail"]["error_code"], "recipe_persistence_conflict")
        cleanup.assert_called_once_with("/static/uploads/winiary-error.webp")


if __name__ == "__main__":
    unittest.main()
