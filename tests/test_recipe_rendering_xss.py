"""Ochrona przed stored XSS w renderowaniu treści przepisu.

Karta przepisu, lista składników, modal instrukcji i lista zakupów były sklejane
jako HTML i przypisywane do innerHTML, więc treść przepisu wykonywała się jako
kod. Przepis oznaczony jako publiczny jest serwowany innym użytkownikom, więc
podatność nie kończy się na autorze.

Projekt nie ma runnera JS (brak package.json, jsdom, Playwrighta), więc test
frontendu jest tu statyczny: pilnuje, żeby niebezpieczny wzorzec nie wrócił do
recipes.js. Dowód behawioralny (wstrzyknięty <img onerror> nie wykonuje się w
przeglądarce) należy do smoke'u opisanego w opisie PR-a.

Druga część to testy przez API: wroga i polska treść musi przechodzić przez
zapis i odczyt bez zmian. Escapowanie należy do warstwy renderowania - baza i
API mają oddawać dokładnie to, co dostały, żeby nie powstało podwójne
escapowanie ani ciche gubienie znaków.
"""
import os
import re
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

APP_DIR = Path(__file__).resolve().parent.parent / "app"
RECIPES_JS = (APP_DIR / "static" / "recipes.js").read_text(encoding="utf-8")


def purge_app_modules() -> None:
    for name in list(sys.modules):
        if name == "app" or name.startswith("app."):
            sys.modules.pop(name)


class RenderingSourceGuardTests(unittest.TestCase):
    """Strażnik wzorca: żadna ścieżka renderowania nie może sklejać HTML-a
    z danymi. Łapie regresję, w której ktoś dopisuje nową funkcję renderującą
    starym stylem."""

    def test_no_innerhtml_assignment_with_interpolation(self) -> None:
        # innerHTML = `...${cokolwiek}...` - dokładnie ten wzorzec wykonywał
        # <img src=x onerror=...> z nazwy przepisu.
        offenders = re.findall(r"\.innerHTML\s*=\s*`[^`]*\$\{[^`]*`", RECIPES_JS, re.DOTALL)
        self.assertEqual(offenders, [], f"innerHTML z interpolacją wrócił do recipes.js: {offenders}")

    def test_no_innerhtml_assignment_with_concatenation(self) -> None:
        offenders = re.findall(r"\.innerHTML\s*=\s*[^;`\n]*\+", RECIPES_JS)
        self.assertEqual(offenders, [], f"innerHTML sklejany stringiem: {offenders}")

    def test_no_other_html_parsing_sinks(self) -> None:
        for sink in ("insertAdjacentHTML", "outerHTML =", "document.write"):
            self.assertNotIn(sink, RECIPES_JS, f"Niebezpieczne API HTML w recipes.js: {sink}")

    def test_recipe_card_is_built_through_dom_api(self) -> None:
        self.assertIn("renderRecipeCard", RECIPES_JS)
        # Helper el() ustawia treść wyłącznie przez textContent.
        self.assertRegex(RECIPES_JS, r"function el\(tag, className, text\)")
        self.assertRegex(RECIPES_JS, r"node\.textContent = String\(text\)")

    def test_instructions_go_through_dataset_not_an_attribute_string(self) -> None:
        # data-instructions="${r.instructions}" pozwalało wyjść z atrybutu
        # cudzysłowem w treści instrukcji.
        self.assertNotIn('data-instructions="${', RECIPES_JS)
        self.assertIn("dataset.instructions", RECIPES_JS)

    def test_instructions_modal_does_not_join_html(self) -> None:
        self.assertNotIn('join("<br>")', RECIPES_JS)
        self.assertIn('createElement("br")', RECIPES_JS)

    def test_shopping_list_items_are_built_through_dom_api(self) -> None:
        # item.name to linia składnika przepisu - ta sama niezaufana treść.
        self.assertNotIn('<span class="item-name">${', RECIPES_JS)
        self.assertIn('el("span", "item-name", item.name)', RECIPES_JS)


class HostileContentRoundTripTests(unittest.TestCase):
    """Treść wroga i treść normalna muszą przejść przez API bez zmian."""

    HOSTILE = {
        "script_tag": "<script>window.__x=1</script>",
        "img_onerror": '<img src=x onerror="window.__x=1">',
        "svg_onload": "<svg/onload=alert(1)>",
        "attribute_breakout": '" onmouseover="window.__x=1',
        "closing_tag": "</h3><b>injected</b>",
    }

    POLISH = {
        "diacritics": "Żurek na zakwasie z jajkiem — pyszności",
        "apostrophes": "Kurczak 'po polsku' i sos \"chrzanowy\"",
        "ampersand": "Sól & pieprz < 5 g",
    }

    def setUp(self) -> None:
        # ignore_cleanup_errors: SQLite trzyma uchwyt do pliku na Windows nawet
        # po Session.close(), co inaczej wywala tearDown przed purge_app_modules.
        self._tmpdir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        db_path = Path(self._tmpdir.name) / "xss.db"
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
        self.user = User(username="xssuser", hashed_password="x", role="user")
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

    def _round_trip(self, payload: str) -> dict:
        created = self.client.post(
            "/api/v1/recipes/",
            json={
                "name": payload,
                "description": payload,
                "instructions": payload,
                "ingredients": f"{payload}\n1 cebula",
                "is_public": True,
            },
        )
        self.assertEqual(created.status_code, 200, created.text)
        recipe_id = created.json()["id"]

        fetched = self.client.get(f"/api/v1/recipes/{recipe_id}")
        self.assertEqual(fetched.status_code, 200, fetched.text)
        return fetched.json()

    def test_hostile_payloads_survive_round_trip_verbatim(self) -> None:
        for label, payload in self.HOSTILE.items():
            with self.subTest(payload=label):
                body = self._round_trip(payload)
                self.assertEqual(body["name"], payload)
                self.assertEqual(body["description"], payload)
                self.assertEqual(body["instructions"], payload)
                self.assertTrue(body["ingredients"].startswith(payload))

    def test_polish_text_survives_round_trip_verbatim(self) -> None:
        for label, payload in self.POLISH.items():
            with self.subTest(payload=label):
                body = self._round_trip(payload)
                self.assertEqual(body["name"], payload)
                self.assertEqual(body["description"], payload)

    def test_hostile_name_is_not_double_escaped_on_the_way_out(self) -> None:
        """Escapowanie należy do renderowania. Gdyby API zaczęło zwracać
        &lt;script&gt;, użytkownik zobaczyłby encje jako tekst w nazwie
        przepisu - to też jest błąd, tylko cichszy."""
        body = self._round_trip(self.HOSTILE["script_tag"])
        self.assertNotIn("&lt;", body["name"])
        self.assertNotIn("&amp;", body["name"])

    def test_hostile_content_survives_editing_too(self) -> None:
        created = self.client.post(
            "/api/v1/recipes/",
            json={
                "name": "Zwykła nazwa",
                "description": "opis",
                "instructions": "instrukcje",
                "ingredients": "a",
                "is_public": False,
            },
        )
        recipe_id = created.json()["id"]

        payload = self.HOSTILE["img_onerror"]
        updated = self.client.put(
            f"/api/v1/recipes/{recipe_id}",
            json={
                "name": payload,
                "description": payload,
                "instructions": payload,
                "ingredients": payload,
                "is_public": False,
            },
        )
        self.assertEqual(updated.status_code, 200, updated.text)
        self.assertEqual(updated.json()["name"], payload)


if __name__ == "__main__":
    unittest.main()
