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


FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures" / "recipe_import"


def load_fixture(name: str) -> str:
    return (FIXTURES_DIR / name).read_text(encoding="utf-8")


class RecipeImportEndpointTests(unittest.TestCase):
    """Endpoint-level tests via FastAPI's TestClient. fetch_html/fetch_image
    are always mocked (patched where the router imports them) - no real
    network calls, no dependency on real websites."""

    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        db_path = Path(self._tmpdir.name) / "endpoints.db"
        self._env_patch = mock.patch.dict(
            os.environ,
            {
                "ENV": "dev",
                "APP_INSTANCE": "dev",
                "SECRET_KEY": "dev-secret",
                "DATABASE_URL": f"sqlite:///{db_path}",
                "MEAL_PLANNER_LOAD_ENV_FILE": "0",
            },
            clear=True,
        )
        self._env_patch.start()

        import app.main as main_module
        from fastapi.testclient import TestClient

        from app.core.database import SessionLocal
        from app.core.security import get_current_user
        from app.db.models.user import User

        self.main_module = main_module
        self.db = SessionLocal()
        self.user = User(username="importer", hashed_password="x", role="user")
        self.db.add(self.user)
        self.db.commit()
        self.db.refresh(self.user)

        main_module.app.dependency_overrides[get_current_user] = lambda: self.user
        self.client = TestClient(main_module.app)

    def tearDown(self) -> None:
        self.main_module.app.dependency_overrides.clear()
        self.db.close()
        from app.core.database import engine

        engine.dispose()
        self._env_patch.stop()
        self._tmpdir.cleanup()
        purge_app_modules()

    def _fake_fetch_html(self, html: str, url: str = "https://blog.example.com/recipe"):
        from app.services.recipe_import.fetcher import FetchedPage

        page = FetchedPage(url=url, html=html, content_type="text/html")

        async def fake(_url):
            return page

        return fake

    # ---- preview ----

    def test_preview_returns_full_draft_for_schema_org_recipe(self) -> None:
        fake = self._fake_fetch_html(load_fixture("schema_org_recipe.html"))
        with mock.patch("app.api.v1.recipe_import.fetch_html", side_effect=fake):
            response = self.client.post(
                "/api/v1/recipe-import/preview", json={"url": "https://blog.example.com/nalesniki"}
            )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["name"], "Naleśniki")
        self.assertNotIn("language", data)
        self.assertEqual(len(data["ingredients"]), 3)
        self.assertEqual(data["ingredients"][0]["quantity"], 2)
        self.assertEqual(data["ingredients"][0]["name"], "jajka")
        self.assertNotIn("servings", data)
        self.assertNotIn("prep_time", data)
        self.assertNotIn("cook_time", data)
        self.assertNotIn("total_time", data)
        self.assertNotIn("no_ingredients_found", data["warnings"])
        self.assertNotIn("no_instructions_found", data["warnings"])

    def test_preview_handles_at_graph_and_english_ingredients(self) -> None:
        fake = self._fake_fetch_html(load_fixture("graph_recipe.html"))
        with mock.patch("app.api.v1.recipe_import.fetch_html", side_effect=fake):
            response = self.client.post(
                "/api/v1/recipe-import/preview", json={"url": "https://example.com/graph-recipe"}
            )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["name"], "Graph Recipe")
        self.assertEqual([i["original_text"] for i in data["ingredients"]], ["1 cup flour", "2 eggs"])
        self.assertEqual(data["ingredients"][0]["unit"], "cup")

    def test_preview_handles_multiple_json_ld_blocks_with_one_invalid(self) -> None:
        fake = self._fake_fetch_html(load_fixture("multiple_ld_json.html"))
        with mock.patch("app.api.v1.recipe_import.fetch_html", side_effect=fake):
            response = self.client.post("/api/v1/recipe-import/preview", json={"url": "https://example.com/zupa"})

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["name"], "Zupa jarzynowa")
        self.assertEqual(len(data["ingredients"]), 3)

    def test_preview_falls_back_to_html_when_no_recipe_schema(self) -> None:
        fake = self._fake_fetch_html(load_fixture("no_recipe.html"))
        with mock.patch("app.api.v1.recipe_import.fetch_html", side_effect=fake):
            response = self.client.post("/api/v1/recipe-import/preview", json={"url": "https://example.com/post"})

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["name"], "Ten wpis nie jest przepisem")
        self.assertEqual(data["ingredients"], [])
        self.assertIn("no_structured_recipe_data", data["warnings"])
        self.assertIn("no_ingredients_found", data["warnings"])
        self.assertIn("no_instructions_found", data["warnings"])

    def test_preview_reports_low_confidence_ingredients_as_a_warning(self) -> None:
        html = """
        <html><head><script type="application/ld+json">
        {"@context":"https://schema.org","@type":"Recipe","name":"Test",
         "recipeIngredient":["something with no structure at all"]}
        </script></head></html>
        """
        fake = self._fake_fetch_html(html)
        with mock.patch("app.api.v1.recipe_import.fetch_html", side_effect=fake):
            response = self.client.post("/api/v1/recipe-import/preview", json={"url": "https://example.com/vague"})

        data = response.json()
        self.assertIn("some_ingredients_need_review", data["warnings"])
        self.assertTrue(data["ingredients"][0]["requires_review"])

    def test_preview_maps_blocked_host_to_400_with_error_code_and_no_leaked_detail(self) -> None:
        from app.services.recipe_import.errors import BlockedHostError

        async def fake_fetch(_url):
            raise BlockedHostError("Host resolves to a blocked address: evil.example -> 10.1.2.3")

        with mock.patch("app.api.v1.recipe_import.fetch_html", side_effect=fake_fetch):
            response = self.client.post("/api/v1/recipe-import/preview", json={"url": "http://evil.example/x"})

        self.assertEqual(response.status_code, 400)
        body = response.json()
        self.assertEqual(body["detail"]["error_code"], "blocked_host")
        # The internal detail (which leaked the resolved private IP) must
        # never reach the client - only a generic error_code does.
        self.assertNotIn("10.1.2.3", response.text)

    def test_preview_requires_authentication(self) -> None:
        self.main_module.app.dependency_overrides.clear()
        response = self.client.post("/api/v1/recipe-import/preview", json={"url": "https://example.com/x"})
        self.assertEqual(response.status_code, 401)

    def test_full_preview_edit_confirm_list_edit_delete_flow(self) -> None:
        """One local-database smoke reproduces the browser's critical path."""
        from app.db.models.recipe import Recipe
        from app.db.models.recipe_translation import RecipeTranslation

        fake = self._fake_fetch_html(load_fixture("schema_org_recipe.html"))
        with mock.patch("app.api.v1.recipe_import.fetch_html", side_effect=fake):
            preview = self.client.post(
                "/api/v1/recipe-import/preview", json={"url": "https://blog.example.com/nalesniki"}
            )
        self.assertEqual(preview.status_code, 200)
        self.assertEqual(self.db.query(Recipe).count(), 0)

        draft = preview.json()
        draft["name"] = "Edited imported pancakes"
        draft["description"] = "Edited after preview"
        draft.pop("warnings", None)
        draft["is_public"] = True
        draft["download_image"] = False
        draft["save_structured_ingredients"] = True

        confirmed = self.client.post("/api/v1/recipe-import/confirm", json=draft)
        self.assertEqual(confirmed.status_code, 200)
        recipe_id = confirmed.json()["recipe"]["id"]
        self.assertEqual(self.db.query(Recipe).count(), 1)
        self.assertEqual(self.db.query(RecipeTranslation).count(), 0)

        listed = self.client.get("/api/v1/recipes/")
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(listed.json()[0]["name"], "Edited imported pancakes")

        updated = self.client.put(
            f"/api/v1/recipes/{recipe_id}",
            json={
                "name": "Edited again",
                "description": "d",
                "ingredients": "1 egg",
                "instructions": "cook",
                "is_public": False,
            },
        )
        self.assertEqual(updated.status_code, 200)
        self.assertFalse(updated.json()["is_public"])

        deleted = self.client.delete(f"/api/v1/recipes/{recipe_id}")
        self.assertEqual(deleted.status_code, 204)
        self.assertEqual(self.db.query(Recipe).count(), 0)

    # ---- confirm ----

    def _confirm_payload(self, **overrides) -> dict:
        payload = {
            "source_url": "https://blog.example.com/nalesniki",
            "source_name": "blog.example.com",
            "name": "Naleśniki",
            "description": "Opis",
            "instructions": "Zrób to.",
            "is_public": False,
            "image_url": None,
            "download_image": False,
            "save_structured_ingredients": True,
            "ingredients": [
                {
                    "original_text": "2 jajka",
                    "quantity": 2,
                    "unit": None,
                    "name": "jajka",
                    "note": None,
                    "confidence": 0.85,
                    "requires_review": False,
                }
            ],
        }
        payload.update(overrides)
        return payload

    def test_confirm_persists_legacy_recipe_and_structured_ingredients(self) -> None:
        response = self.client.post("/api/v1/recipe-import/confirm", json=self._confirm_payload())
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["recipe"]["name"], "Naleśniki")
        self.assertEqual(data["warnings"], [])

        from app.db.models.recipe import Recipe
        from app.db.models.recipe_ingredient import RecipeIngredient
        recipe = self.db.query(Recipe).filter(Recipe.id == data["recipe"]["id"]).first()
        self.assertIsNotNone(recipe)
        self.assertEqual(recipe.source_url, "https://blog.example.com/nalesniki")
        self.assertIsNotNone(recipe.imported_at)

        ingredients = self.db.query(RecipeIngredient).filter(RecipeIngredient.recipe_id == recipe.id).all()
        self.assertEqual(len(ingredients), 1)
        self.assertEqual(ingredients[0].parsed_name, "jajka")
        self.assertEqual(ingredients[0].ingredient_id, None)  # never auto-mapped

    def test_confirm_preserves_edited_visibility(self) -> None:
        response = self.client.post(
            "/api/v1/recipe-import/confirm",
            json=self._confirm_payload(is_public=True, name="Edited imported recipe"),
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["recipe"]["is_public"])

    def test_untrusted_import_text_is_returned_as_data_not_markup(self) -> None:
        payload = self._confirm_payload(
            name='<img src=x onerror="window.__XSS=1">',
            description='<script>window.__XSS=2</script>',
            ingredients=[
                {
                    "original_text": '<svg onload="window.__XSS=3">',
                    "name": '<svg onload="window.__XSS=3">',
                }
            ],
        )
        response = self.client.post("/api/v1/recipe-import/confirm", json=payload)
        self.assertEqual(response.status_code, 200)
        recipe = response.json()["recipe"]
        self.assertIn("<img", recipe["name"])
        self.assertIn("<script>", recipe["description"])
        self.assertIn("<svg", recipe["ingredients"])

    def test_confirm_without_structured_ingredients_flag_skips_recipe_ingredient_rows(self) -> None:
        response = self.client.post(
            "/api/v1/recipe-import/confirm", json=self._confirm_payload(save_structured_ingredients=False)
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()

        from app.db.models.recipe_ingredient import RecipeIngredient

        count = self.db.query(RecipeIngredient).filter(RecipeIngredient.recipe_id == data["recipe"]["id"]).count()
        self.assertEqual(count, 0)
        # Legacy free-text field is still populated for backward compatibility.
        self.assertIn("2 jajka", data["recipe"]["ingredients"])

    def test_confirm_requires_authentication(self) -> None:
        self.main_module.app.dependency_overrides.clear()
        response = self.client.post("/api/v1/recipe-import/confirm", json=self._confirm_payload())
        self.assertEqual(response.status_code, 401)

    def test_confirm_rejects_invalid_draft_missing_title(self) -> None:
        payload = self._confirm_payload()
        payload["name"] = ""
        response = self.client.post("/api/v1/recipe-import/confirm", json=payload)
        self.assertEqual(response.status_code, 422)

    def test_confirm_rejects_non_http_source_url(self) -> None:
        response = self.client.post(
            "/api/v1/recipe-import/confirm", json=self._confirm_payload(source_url="ftp://example.com/x")
        )
        self.assertEqual(response.status_code, 422)

    def test_double_confirm_returns_existing_recipe_instead_of_duplicating(self) -> None:
        first = self.client.post("/api/v1/recipe-import/confirm", json=self._confirm_payload())
        second = self.client.post(
            "/api/v1/recipe-import/confirm", json=self._confirm_payload(name="Different title on retry")
        )

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(first.json()["recipe"]["id"], second.json()["recipe"]["id"])
        self.assertIn("duplicate_import_returned_existing", second.json()["warnings"])

        from app.db.models.recipe import Recipe

        count = self.db.query(Recipe).filter(Recipe.source_url == self._confirm_payload()["source_url"]).count()
        self.assertEqual(count, 1)

    def test_confirm_uses_owner_lock_before_duplicate_check(self) -> None:
        with mock.patch("app.api.v1.recipe_import.recipe_service.lock_user_for_import") as lock_mock:
            response = self.client.post("/api/v1/recipe-import/confirm", json=self._confirm_payload())

        self.assertEqual(response.status_code, 200)
        lock_mock.assert_called_once()
        self.assertEqual(lock_mock.call_args.args[1], self.user.id)

    def test_confirm_saves_without_image_when_download_not_requested(self) -> None:
        response = self.client.post(
            "/api/v1/recipe-import/confirm",
            json=self._confirm_payload(image_url="https://example.com/photo.jpg", download_image=False),
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["recipe"]["image"], "")

    def test_confirm_saves_without_optional_fields(self) -> None:
        response = self.client.post(
            "/api/v1/recipe-import/confirm",
            json={
                "source_url": "https://example.com/minimal",
                "name": "Minimal imported recipe",
            },
        )
        self.assertEqual(response.status_code, 200)
        recipe = response.json()["recipe"]
        self.assertEqual(recipe["name"], "Minimal imported recipe")
        self.assertEqual(recipe["ingredients"], "")

    def test_confirm_saves_recipe_without_image_when_download_fails(self) -> None:
        from app.services.recipe_import.errors import UpstreamFetchError

        async def failing_download(_url):
            raise UpstreamFetchError("boom")

        with mock.patch("app.api.v1.recipe_import.download_and_store_image", side_effect=failing_download):
            response = self.client.post(
                "/api/v1/recipe-import/confirm",
                json=self._confirm_payload(image_url="https://example.com/photo.jpg", download_image=True),
            )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["recipe"]["image"], "")
        self.assertIn("image_download_failed", data["warnings"])

        from app.db.models.recipe import Recipe

        recipe = self.db.query(Recipe).filter(Recipe.id == data["recipe"]["id"]).first()
        self.assertIsNotNone(recipe)  # the recipe itself must still be saved

    def test_confirm_deletes_downloaded_image_if_recipe_save_fails(self) -> None:
        async def fake_download(_url):
            return "/static/uploads/fake-during-test.jpg"

        with mock.patch("app.api.v1.recipe_import.download_and_store_image", side_effect=fake_download):
            with mock.patch("app.api.v1.recipe_import.delete_stored_image") as delete_mock:
                with mock.patch(
                    "app.services.recipe_service.create_recipe_from_import", side_effect=RuntimeError("db exploded")
                ):
                    with mock.patch("sqlalchemy.orm.Session.rollback") as rollback_mock:
                        with self.assertRaises(RuntimeError):
                            self.client.post(
                                "/api/v1/recipe-import/confirm",
                                json=self._confirm_payload(
                                    image_url="https://example.com/photo.jpg", download_image=True
                                ),
                            )
        rollback_mock.assert_called_once()
        delete_mock.assert_called_once_with("/static/uploads/fake-during-test.jpg")

    def test_old_recipe_crud_still_works_alongside_import(self) -> None:
        # Confirms importing a recipe doesn't interfere with the pre-existing
        # plain create/list flow.
        self.client.post("/api/v1/recipe-import/confirm", json=self._confirm_payload())

        create_response = self.client.post(
            "/api/v1/recipes/",
            json={"name": "Manually added", "description": "d", "ingredients": "a\nb", "instructions": "i"},
        )
        self.assertEqual(create_response.status_code, 200)

        list_response = self.client.get("/api/v1/recipes/")
        self.assertEqual(list_response.status_code, 200)
        names = {r["name"] for r in list_response.json()}
        self.assertIn("Naleśniki", names)
        self.assertIn("Manually added", names)


if __name__ == "__main__":
    unittest.main()
