"""Kontrolki, które obiecywały coś, czego nie robiły.

Statyczne sprawdzenia nad źródłem - projekt nie ma runnera JS. Każdy test
odpowiada jednemu znalezisku audytu produktowego i ma pilnować, żeby kontrolka
nie zaczęła znowu kłamać.
"""
import os
import re
import sys
import tempfile
import unittest
from collections import Counter
from pathlib import Path
from unittest import mock

APP_DIR = Path(__file__).resolve().parent.parent / "app"
RECIPES_HTML = (APP_DIR / "templates" / "recipes.html").read_text(encoding="utf-8")
RECIPES_JS_RAW = (APP_DIR / "static" / "recipes.js").read_text(encoding="utf-8")


def _strip_js_comments(source: str) -> str:
    """Usuwa komentarze przed skanowaniem źródła.

    Bez tego komentarz opisujący naprawiony błąd (np. wzmianka o dawnym
    wywołaniu) wygląda dla testu jak żywy kod i zapala fałszywy alarm.
    """
    without_block = re.sub(r"/\*.*?\*/", "", source, flags=re.DOTALL)
    return re.sub(r"(?m)^\s*//.*$|(?<=[;,)\s])//[^\n]*$", "", without_block)


RECIPES_JS = _strip_js_comments(RECIPES_JS_RAW)


def purge_app_modules() -> None:
    for name in list(sys.modules):
        if name == "app" or name.startswith("app."):
            sys.modules.pop(name)


def _payload_body(function_source_marker: str) -> str:
    """Ciało literału obiektu wysyłanego przez daną akcję (`const recipe = {...}`)."""
    match = re.search(
        function_source_marker + r".*?\bconst recipe = \{(.*?)\n\s*\};",
        RECIPES_JS,
        re.DOTALL,
    )
    if match is None:
        raise AssertionError(f"Nie znaleziono payloadu dla: {function_source_marker}")
    return match.group(1)


class DuplicateIdTests(unittest.TestCase):
    """P-2: id="edit-is-public" występowało dwa razy - w formularzu dodawania i
    w modalu edycji. getElementById zwraca pierwszy, więc przełącznik w modalu
    edycji czytał i zapisywał cudzy element."""

    def test_no_duplicate_ids_in_template(self) -> None:
        ids = re.findall(r'id="([^"]+)"', RECIPES_HTML)
        duplicates = {id_ for id_, count in Counter(ids).items() if count > 1}
        self.assertEqual(duplicates, set(), f"Zduplikowane id: {duplicates}")

    def test_add_and_edit_forms_have_separate_visibility_checkboxes(self) -> None:
        self.assertIn('id="add-is-public"', RECIPES_HTML)
        self.assertIn('id="edit-is-public"', RECIPES_HTML)


class VisibilitySwitchTests(unittest.TestCase):
    """P-1: przełącznik PRIVATE/PUBLIC w formularzu dodawania był renderowany,
    ale create() nie czytało jego wartości - każdy nowy przepis wychodził
    prywatny niezależnie od ustawienia."""

    def test_create_payload_sends_is_public(self) -> None:
        self.assertIn("is_public:", _payload_body(r"create\(\)\s*\{"))

    def test_update_payload_still_sends_is_public(self) -> None:
        self.assertIn("is_public:", _payload_body(r"async update\(\)\s*\{"))

    def test_each_form_reads_its_own_checkbox(self) -> None:
        self.assertRegex(RECIPES_JS, r'isPublic: \(\) => document\.getElementById\("add-is-public"\)')
        self.assertRegex(RECIPES_JS, r'isPublic: \(\) => document\.getElementById\("edit-is-public"\)')
        # Żadna ścieżka nie może już sięgać po element po surowym id z pominięciem
        # akcesora - to właśnie tak formularz dodawania trafiał w pole edycji.
        self.assertNotIn('document.getElementById("edit-is-public")', _payload_body(r"create\(\)\s*\{"))

    def test_clear_form_unchecks_checkboxes_instead_of_clearing_value(self) -> None:
        # el.value = "" na checkboxie nic nie odznacza, więc przełącznik
        # zostawał włączony dla kolejnego dodawanego przepisu.
        self.assertIn('el.type === "checkbox"', RECIPES_JS)
        self.assertIn("el.checked = false", RECIPES_JS)


class ShoppingEnterKeyTests(unittest.TestCase):
    """Enter w polu listy zakupów wołał Shopping.addItem(), którego nigdy nie
    było - rzucał TypeError i pozycja nie trafiała na listę."""

    def test_enter_handler_calls_an_existing_function(self) -> None:
        self.assertNotIn("Shopping.addItem()", RECIPES_JS)
        self.assertIn("function addShoppingItem()", RECIPES_JS)

        handler = re.search(
            r'shoppingInput\.addEventListener\("keydown".*?\}\);',
            RECIPES_JS,
            re.DOTALL,
        )
        self.assertIsNotNone(handler)
        self.assertIn("addShoppingItem()", handler.group(0))

    def test_every_shopping_method_called_on_the_object_actually_exists(self) -> None:
        """Ogólniejszy strażnik: żadne Shopping.foo() w kodzie nie może
        wskazywać na metodę, której obiekt nie definiuje."""
        called = set(re.findall(r"\bShopping\.(\w+)\(", RECIPES_JS))
        shopping_block = re.search(r"const Shopping = \{(.*?)\n\};", RECIPES_JS, re.DOTALL)
        self.assertIsNotNone(shopping_block)
        defined = set(re.findall(r"^\s{4}(?:async\s+)?(\w+)[\(:]", shopping_block.group(1), re.MULTILINE))

        missing = sorted(name for name in called if name not in defined)
        self.assertEqual(missing, [], f"Shopping.{missing} wywoływane, ale niezdefiniowane")


class DeadIngredientsMenuTests(unittest.TestCase):
    """P-5: pozycja menu 'Ingredients' prowadziła wyłącznie do toastu
    'feature coming soon'."""

    def test_menu_entry_is_gone(self) -> None:
        self.assertNotIn("openIngredientsModal", RECIPES_HTML)

    def test_dead_handler_and_its_toast_are_gone(self) -> None:
        self.assertNotIn("function openIngredientsModal", RECIPES_JS)
        self.assertNotIn("Ingredients feature coming soon", RECIPES_JS)


class VisibilityPersistenceTests(unittest.TestCase):
    """Behawioralne potwierdzenie P-1 po stronie API: is_public wysłane w
    payloadzie faktycznie ląduje w bazie i wraca przy odczycie."""

    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        db_path = Path(self._tmpdir.name) / "controls.db"
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
        self.user = User(username="controlsuser", hashed_password="x", role="user")
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

    def _create(self, is_public: bool) -> dict:
        response = self.client.post(
            "/api/v1/recipes/",
            json={
                "name": "Widoczność",
                "description": "D",
                "ingredients": "a",
                "instructions": "I",
                "is_public": is_public,
            },
        )
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def test_public_recipe_stays_public(self) -> None:
        created = self._create(True)
        self.assertTrue(created["is_public"])
        self.assertTrue(self.client.get(f"/api/v1/recipes/{created['id']}").json()["is_public"])

    def test_private_recipe_stays_private(self) -> None:
        created = self._create(False)
        self.assertFalse(created["is_public"])
        self.assertFalse(self.client.get(f"/api/v1/recipes/{created['id']}").json()["is_public"])

    def test_visibility_can_be_flipped_by_edit(self) -> None:
        created = self._create(False)
        updated = self.client.put(
            f"/api/v1/recipes/{created['id']}",
            json={
                "name": "Widoczność",
                "description": "D",
                "ingredients": "a",
                "instructions": "I",
                "is_public": True,
            },
        )
        self.assertEqual(updated.status_code, 200, updated.text)
        self.assertTrue(updated.json()["is_public"])


if __name__ == "__main__":
    unittest.main()
