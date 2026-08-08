"""Nowy schemat nie może zepsuć tego, co już działa na produkcji.

Ten PR dokłada kolumny do `recipes`, `users` i `ingredients` oraz cztery nowe
tabele, ale żadna funkcja produktowa z nich jeszcze nie korzysta. Warunek
wdrożenia jest więc prosty: istniejący CRUD przepisów, widoczność i
GET /ingredients/map muszą zachowywać się dokładnie tak, jak przed zmianą.

Testy idą przez prawdziwe API (TestClient) i przez modele, bo to dwie różne
drogi, którymi nowa kolumna może coś zepsuć: serializacja odpowiedzi i wstawianie
wiersza bez podania nowych pól.
"""
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


class SchemaCompatibilityTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        db_path = Path(self._tmpdir.name) / "compat.db"
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
        self.user = User(username="compatuser", hashed_password="x", role="user")
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


class ExistingRecipeCrudTests(SchemaCompatibilityTestCase):
    def _create(self, **overrides) -> dict:
        payload = {
            "name": "Naleśniki",
            "description": "Opis",
            "ingredients": "2 łyżki oliwy\n1 cebula",
            "instructions": "Wymieszaj",
            "is_public": False,
        }
        payload.update(overrides)
        response = self.client.post("/api/v1/recipes/", json=payload)
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def test_create_read_update_delete_still_works(self) -> None:
        created = self._create()
        recipe_id = created["id"]

        fetched = self.client.get(f"/api/v1/recipes/{recipe_id}")
        self.assertEqual(fetched.status_code, 200)
        self.assertEqual(fetched.json()["name"], "Naleśniki")

        updated = self.client.put(
            f"/api/v1/recipes/{recipe_id}",
            json={
                "name": "Naleśniki v2",
                "description": "Opis 2",
                "ingredients": "a",
                "instructions": "I2",
                "is_public": True,
            },
        )
        self.assertEqual(updated.status_code, 200, updated.text)
        self.assertEqual(updated.json()["name"], "Naleśniki v2")
        self.assertTrue(updated.json()["is_public"])

        deleted = self.client.delete(f"/api/v1/recipes/{recipe_id}")
        self.assertEqual(deleted.status_code, 204)
        self.assertEqual(self.client.get(f"/api/v1/recipes/{recipe_id}").status_code, 404)

    def test_visibility_endpoint_still_works(self) -> None:
        created = self._create(is_public=False)
        response = self.client.patch(
            f"/api/v1/recipes/{created['id']}/visibility", json={"is_public": True}
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertTrue(response.json()["is_public"])

    def test_recipe_list_response_shape_is_unchanged(self) -> None:
        """Nowe kolumny nie mogą wyciekać do odpowiedzi API. RecipeRead nie
        deklaruje source_url ani imported_at, więc kontrakt zostaje taki sam -
        gdyby wyciekły, klient dostałby pola, których nie umie zignorować."""
        self._create()
        response = self.client.get("/api/v1/recipes/")
        self.assertEqual(response.status_code, 200)

        body = response.json()
        self.assertEqual(len(body), 1)
        for leaked in ("source_url", "source_name", "source_author", "imported_at"):
            self.assertNotIn(leaked, body[0])

    def test_new_recipe_gets_null_source_columns(self) -> None:
        from app.db.models.recipe import Recipe

        created = self._create()
        recipe = self.db.query(Recipe).filter(Recipe.id == created["id"]).first()

        self.assertIsNone(recipe.source_url)
        self.assertIsNone(recipe.source_name)
        self.assertIsNone(recipe.source_author)
        self.assertIsNone(recipe.imported_at)


class LegacyRowCompatibilityTests(SchemaCompatibilityTestCase):
    def test_recipe_can_be_inserted_without_any_new_column(self) -> None:
        """Odwzorowanie 64 przepisów produkcyjnych: wiersz powstały przed tą
        zmianą nie zna nowych kolumn i musi dalej dać się odczytać."""
        from app.db.models.recipe import Recipe

        recipe = Recipe(
            name="Stary przepis",
            description="Opis",
            instructions="Instrukcje",
            ingredients="skladnik",
            user_id=self.user.id,
        )
        self.db.add(recipe)
        self.db.commit()
        self.db.refresh(recipe)

        response = self.client.get(f"/api/v1/recipes/{recipe.id}")
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["name"], "Stary przepis")

    def test_user_gets_default_language_without_being_asked(self) -> None:
        from app.db.models.user import User

        user = User(username="nowy", hashed_password="x", role="user")
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)

        self.assertEqual(user.language, "pl")

    def test_ingredient_map_endpoint_still_works_with_extended_table(self) -> None:
        """GET /ingredients/map czyta wyłącznie name/is_essential. Tabela dostała
        pięć nowych kolumn - stary wzorzec użycia musi działać bez podawania
        żadnej z nich."""
        from app.db.models.ingredient import Ingredient

        self.db.add(Ingredient(name="sol", is_essential=True))
        self.db.add(Ingredient(name="cukier", is_essential=False))
        self.db.commit()

        response = self.client.get("/ingredients/map")
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json(), {"sol": True, "cukier": False})

    def test_ingredient_new_columns_default_to_null(self) -> None:
        from app.db.models.ingredient import Ingredient

        self.db.add(Ingredient(name="bazylia", is_essential=True))
        self.db.commit()

        fetched = self.db.query(Ingredient).filter(Ingredient.name == "bazylia").first()
        self.assertIsNone(fetched.canonical_name_pl)
        self.assertIsNone(fetched.canonical_name_en)
        self.assertIsNone(fetched.default_store_section_id)
        # created_at/updated_at są NOT NULL, więc muszą wypełnić się same.
        self.assertIsNotNone(fetched.created_at)
        self.assertIsNotNone(fetched.updated_at)


class NoProductFeatureLeakedTests(unittest.TestCase):
    """Strażnik zakresu: schemat z migracji nie może być aktywowany po cichu.

    Pierwotnie ten strażnik pilnował też nieobecności i18n interfejsu — słusznie,
    bo pakiet migracji nie miał prawa go wnosić. i18n UI weszło własnym,
    osobnym pakietem, więc ta część asercji została **świadomie zdjęta**;
    granica przesunęła się, nie zniknęła.

    Nadal poza zakresem i nadal pilnowane: import przepisu z URL oraz warstwa
    tłumaczeń TREŚCI przepisu (`recipe_translations` jako funkcja produktowa).
    Schemat ma te tabele gotowe od PR #16 — to nie znaczy, że wolno je włączyć
    przy okazji."""

    REPO_ROOT = Path(__file__).resolve().parents[1]

    def _assert_no_sources_under(self, relative_path: str) -> None:
        """Sprawdza nieobecność KODU, nie katalogu.

        Sam katalog może zostać po przełączeniu brancha, jeśli w środku siedzi
        osierocony __pycache__ - to lokalny śmieć, nie wyciek zakresu, i nie
        powinien wywalać testu.
        """
        target = self.REPO_ROOT / relative_path
        if target.suffix == ".py":
            self.assertFalse(target.is_file(), f"{relative_path} nie należy do tego PR-a")
            return

        leaked = sorted(str(p.relative_to(self.REPO_ROOT)) for p in target.glob("**/*.py"))
        self.assertEqual(leaked, [], f"Kod z innego PR-a w {relative_path}: {leaked}")

    def test_import_feature_is_absent(self) -> None:
        for path in (
            "app/services/recipe_import",
            "app/api/v1/recipe_import.py",
            "app/schemas/recipe_import.py",
            "app/services/ingredient_parsing",
        ):
            with self.subTest(path=path):
                self._assert_no_sources_under(path)

    def test_recipe_content_translation_service_is_absent(self) -> None:
        """i18n INTERFEJSU jest dozwolone. Tłumaczenie TREŚCI przepisu - nie."""
        self._assert_no_sources_under("app/services/recipe_translation_service.py")

    def test_no_router_references_import_endpoints(self) -> None:
        router = (self.REPO_ROOT / "app/api/v1/router.py").read_text(encoding="utf-8")
        self.assertNotIn("recipe_import", router)

    def test_frontend_has_no_import_or_content_language_controls(self) -> None:
        template = (self.REPO_ROOT / "app/templates/recipes.html").read_text(encoding="utf-8")
        # `set-lang` świadomie NIE jest tu wymieniony - przełącznik języka
        # interfejsu jest dozwolony. `add-content-language` to selektor języka
        # TREŚCI przepisu i nadal nie należy do żadnego wdrożonego pakietu.
        for marker in (
            "import-url-modal",
            "import-draft-modal",
            "add-content-language",
            "edit-content-language",
        ):
            self.assertNotIn(marker, template, f"{marker} nie należy do tego pakietu")

    def test_recipe_schema_has_no_content_language_field(self) -> None:
        """RecipeCreate/RecipeRead bez pola `language` - inaczej tłumaczenie
        treści weszłoby tylnymi drzwiami przez API."""
        schema = (self.REPO_ROOT / "app/schemas/recipe.py").read_text(encoding="utf-8")
        self.assertNotIn("language", schema)


if __name__ == "__main__":
    unittest.main()
