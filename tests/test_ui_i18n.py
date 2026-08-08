"""Tłumaczenia interfejsu PL/EN.

Zakres testów odpowiada zakresowi funkcji: sprawdzamy **interfejs**. Osobna
klasa pilnuje granicy — przełącznik języka nie może dotykać treści przepisów,
bo dwujęzyczność treści to inna, jeszcze niepodjęta decyzja produktowa.
"""
import json
import os
import re
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

APP_DIR = Path(__file__).resolve().parent.parent / "app"
PL_DICT = json.loads((APP_DIR / "i18n" / "pl.json").read_text(encoding="utf-8"))
EN_DICT = json.loads((APP_DIR / "i18n" / "en.json").read_text(encoding="utf-8"))
RECIPES_HTML = (APP_DIR / "templates" / "recipes.html").read_text(encoding="utf-8")
LOGIN_HTML = (APP_DIR / "templates" / "login.html").read_text(encoding="utf-8")
RECIPES_JS = (APP_DIR / "static" / "recipes.js").read_text(encoding="utf-8")


def purge_app_modules() -> None:
    for name in list(sys.modules):
        if name == "app" or name.startswith("app."):
            sys.modules.pop(name)


class DictionaryTests(unittest.TestCase):
    """Słowniki muszą być symetryczne, a każdy użyty klucz musi istnieć."""

    def test_dictionaries_have_identical_keys(self) -> None:
        self.assertEqual(set(PL_DICT), set(EN_DICT))
        self.assertGreater(len(PL_DICT), 50)  # próg zdrowia, łapie pusty plik

    def test_no_empty_translations(self) -> None:
        for lang, catalog in (("pl", PL_DICT), ("en", EN_DICT)):
            empty = sorted(k for k, v in catalog.items() if not str(v).strip())
            self.assertEqual(empty, [], f"puste tłumaczenia w {lang}: {empty}")

    def test_pl_and_en_actually_differ(self) -> None:
        """Gdyby ktoś skopiował plik PL na EN, testy kluczy nadal by przeszły,
        a użytkownik EN dostałby polski interfejs."""
        identical = [k for k in PL_DICT if PL_DICT[k] == EN_DICT[k]]
        # Część wartości słusznie jest identyczna (np. "PL", "EN").
        self.assertLess(len(identical), len(PL_DICT) * 0.3, f"podejrzanie wiele identycznych: {identical}")

    def _used_keys(self) -> set[str]:
        template_keys = set(re.findall(r"t\('([\w.]+)'", RECIPES_HTML)) | set(
            re.findall(r"t\('([\w.]+)'", LOGIN_HTML)
        )
        # Negative lookbehind odsiewa fałszywe trafienia typu createElement("...")
        js_keys = set(re.findall(r'(?<![A-Za-z])t\("([\w.]+)"', RECIPES_JS))
        # Ten sam negative lookbehind co dla JS - bez niego regex łapie np.
        # request.headers.get("referer") jako wywołanie t().
        python_keys = set(
            re.findall(r'(?<![A-Za-z])t\("([\w.]+)"', (APP_DIR / "main.py").read_text(encoding="utf-8"))
        )
        return template_keys | js_keys | python_keys

    def test_every_used_key_exists_in_both_dictionaries(self) -> None:
        used = self._used_keys()
        self.assertGreater(len(used), 30)
        self.assertEqual(sorted(k for k in used if k not in PL_DICT), [])
        self.assertEqual(sorted(k for k in used if k not in EN_DICT), [])

    def test_no_import_or_content_translation_keys_leaked(self) -> None:
        """Klucze importu z URL należą do innego pakietu; klucz martwej pozycji
        menu został usunięty w PR #15 i nie może wrócić."""
        for key in PL_DICT:
            self.assertFalse(key.startswith("import."), f"klucz importu w słowniku: {key}")
        self.assertNotIn("burger.ingredients", PL_DICT)
        self.assertNotIn("toast.ingredients_coming_soon", PL_DICT)


class TranslationHelperTests(unittest.TestCase):
    def setUp(self) -> None:
        self._env_patch = mock.patch.dict(
            os.environ,
            {
                "ENV": "dev",
                "APP_INSTANCE": "dev",
                "SECRET_KEY": "dev-secret",
                "DATABASE_URL": "sqlite:///:memory:",
                "MEAL_PLANNER_LOAD_ENV_FILE": "0",
            },
            clear=True,
        )
        self._env_patch.start()

    def tearDown(self) -> None:
        self._env_patch.stop()
        purge_app_modules()

    def test_translates_into_both_languages(self) -> None:
        from app.core.i18n import t

        self.assertEqual(t("common.logout", "pl"), PL_DICT["common.logout"])
        self.assertEqual(t("common.logout", "en"), EN_DICT["common.logout"])
        self.assertNotEqual(t("common.logout", "pl"), t("common.logout", "en"))

    def test_missing_key_returns_the_key_and_never_raises(self) -> None:
        """Brakujący klucz nie może wywalić żądania - w najgorszym razie
        użytkownik zobaczy surowy klucz zamiast pustej strony 500."""
        from app.core.i18n import t

        self.assertEqual(t("nie.ma.takiego.klucza", "pl"), "nie.ma.takiego.klucza")
        self.assertEqual(t("nie.ma.takiego.klucza", "en"), "nie.ma.takiego.klucza")

    def test_unknown_language_falls_back_to_polish(self) -> None:
        from app.core.i18n import t

        self.assertEqual(t("common.logout", "de"), PL_DICT["common.logout"])
        self.assertEqual(t("common.logout", ""), PL_DICT["common.logout"])

    def test_interpolation_works_and_is_fail_safe(self) -> None:
        from app.core.i18n import t

        rendered = t("toast.item_removed", "pl", name="mleko")
        self.assertIn("mleko", rendered)
        self.assertNotIn("{name}", rendered)

        # Brakujący parametr nie może rzucić - zwraca tekst nieprzetworzony.
        self.assertIn("{name}", t("toast.item_removed", "pl"))

    def test_js_translations_returns_a_full_catalog(self) -> None:
        from app.core.i18n import js_translations

        self.assertEqual(set(js_translations("pl")), set(PL_DICT))
        self.assertEqual(set(js_translations("en")), set(EN_DICT))
        # Nieznany język dostaje katalog domyślny, a nie pusty słownik.
        self.assertEqual(set(js_translations("de")), set(PL_DICT))


class LanguageResolutionTests(unittest.TestCase):
    """Priorytet: cookie -> User.language -> Accept-Language -> pl."""

    def setUp(self) -> None:
        self._env_patch = mock.patch.dict(
            os.environ,
            {
                "ENV": "dev",
                "APP_INSTANCE": "dev",
                "SECRET_KEY": "dev-secret",
                "DATABASE_URL": "sqlite:///:memory:",
                "MEAL_PLANNER_LOAD_ENV_FILE": "0",
            },
            clear=True,
        )
        self._env_patch.start()

    def tearDown(self) -> None:
        self._env_patch.stop()
        purge_app_modules()

    def _request(self, cookies=None, headers=None):
        from starlette.datastructures import Headers
        from starlette.requests import Request

        raw_headers = []
        for key, value in (headers or {}).items():
            raw_headers.append((key.lower().encode(), value.encode()))
        if cookies:
            cookie_header = "; ".join(f"{k}={v}" for k, v in cookies.items())
            raw_headers.append((b"cookie", cookie_header.encode()))

        scope = {
            "type": "http",
            "method": "GET",
            "path": "/",
            "headers": raw_headers,
            "query_string": b"",
        }
        request = Request(scope)
        assert isinstance(request.headers, Headers)
        return request

    def test_default_is_polish(self) -> None:
        from app.core.i18n import resolve_language

        self.assertEqual(resolve_language(self._request()), "pl")

    def test_cookie_wins(self) -> None:
        from app.core.i18n import resolve_language

        self.assertEqual(resolve_language(self._request(cookies={"lang": "en"})), "en")

    def test_cookie_beats_user_preference(self) -> None:
        """Cookie to ostatni jawny wybór na tym urządzeniu."""
        from app.core.i18n import resolve_language

        user = mock.Mock(language="pl")
        self.assertEqual(resolve_language(self._request(cookies={"lang": "en"}), user), "en")

    def test_user_preference_used_when_no_cookie(self) -> None:
        from app.core.i18n import resolve_language

        user = mock.Mock(language="en")
        self.assertEqual(resolve_language(self._request(), user), "en")

    def test_accept_language_header_used_as_last_guess(self) -> None:
        from app.core.i18n import resolve_language

        request = self._request(headers={"accept-language": "en-US,en;q=0.9"})
        self.assertEqual(resolve_language(request), "en")

    def test_unsupported_values_are_ignored(self) -> None:
        from app.core.i18n import resolve_language

        user = mock.Mock(language="de")
        request = self._request(cookies={"lang": "xx"}, headers={"accept-language": "fr-FR,fr"})
        self.assertEqual(resolve_language(request, user), "pl")


class SetLanguageEndpointTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        db_path = Path(self._tmpdir.name) / "i18n.db"
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
        from passlib.hash import bcrypt

        from app.core.database import SessionLocal
        from app.db.models.user import User

        self.main_module = main_module
        self.db = SessionLocal()
        self.user = User(
            username="langowiec",
            hashed_password=bcrypt.hash("tajne-haslo"),
            role="user",
        )
        self.db.add(self.user)
        self.db.commit()
        self.db.refresh(self.user)

        self.client = TestClient(main_module.app, follow_redirects=False)
        # Prawdziwe logowanie zamiast nadpisania zależności: endpoint zapisuje
        # users.language przez sesję z get_db, więc podstawienie obiektu User z
        # innej sesji dawałoby fałszywy wynik - commit nie dotyczyłby tego
        # obiektu i test przechodziłby lub padał z niewłaściwego powodu.
        login = self.client.post(
            "/login", data={"username": "langowiec", "password": "tajne-haslo"}
        )
        self.assertEqual(login.status_code, 302, login.text)

    def tearDown(self) -> None:
        self.main_module.app.dependency_overrides.clear()
        self.db.close()
        from app.core.database import engine

        engine.dispose()
        self._env_patch.stop()
        self._tmpdir.cleanup()
        purge_app_modules()

    def _reload_user(self):
        """Świeży odczyt z bazy - obiekt z self.db nie widzi commitu wykonanego
        w sesji żądania."""
        from app.db.models.user import User

        self.db.expire_all()
        return self.db.query(User).filter(User.username == "langowiec").first()

    def _set_lang(self, code: str, referer: str | None = None):
        headers = {"referer": referer} if referer else {}
        return self.client.post("/set-lang", data={"code": code}, headers=headers)

    def test_switching_to_english_persists_on_the_account(self) -> None:
        response = self._set_lang("en")

        self.assertEqual(response.status_code, 303)
        self.assertEqual(self._reload_user().language, "en")

    def test_switching_back_to_polish_persists(self) -> None:
        self._set_lang("en")
        self._set_lang("pl")

        self.assertEqual(self._reload_user().language, "pl")

    def test_language_cookie_is_set(self) -> None:
        response = self._set_lang("en")

        self.assertEqual(response.cookies.get("lang"), "en")

    def test_choice_survives_the_next_request(self) -> None:
        """Cookie niesie wybór w tej przeglądarce."""
        self._set_lang("en")

        page = self.client.get("/login")
        self.assertEqual(page.status_code, 200)
        self.assertIn(EN_DICT["login.button"], page.text)

    def test_choice_survives_a_fresh_session_via_user_language(self) -> None:
        """Nowa przeglądarka: sesja jest, cookie `lang` nie ma. Język musi
        przyjść z konta - to jest jedyny powód, dla którego preferencja w ogóle
        siedzi w users.language, a nie tylko w cookie."""
        self._set_lang("en")
        self.client.cookies.delete("lang")  # zostaje access_token, znika lang

        page = self.client.get("/recipes-ui")
        self.assertEqual(page.status_code, 200, page.text)
        self.assertIn(EN_DICT["topbar.recipes_tab"], page.text)

    def test_unsupported_language_is_rejected(self) -> None:
        response = self._set_lang("de")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(self._reload_user().language, "pl")

    def test_endpoint_is_post_only(self) -> None:
        """GET mutujący stan dałby się wywołać linkiem z obcej strony -
        SameSite=Lax wysyła cookie sesji przy nawigacji GET."""
        self.assertEqual(self.client.get("/set-lang/en").status_code, 404)
        self.assertEqual(self.client.get("/set-lang").status_code, 405)

    def test_redirect_returns_to_a_safe_local_path(self) -> None:
        response = self._set_lang("en", referer="http://testserver/recipes-ui?x=1")
        self.assertEqual(response.headers["location"], "/recipes-ui?x=1")

    def test_foreign_referer_cannot_redirect_off_site(self) -> None:
        response = self._set_lang("en", referer="https://evil.example/phish")
        self.assertEqual(response.headers["location"], "/recipes-ui")

    def test_anonymous_user_can_switch_language(self) -> None:
        """Ekran logowania musi dać się przełączyć przed zalogowaniem."""
        self.client.cookies.clear()  # wylogowanie: znika access_token

        response = self._set_lang("en")
        self.assertEqual(response.status_code, 303)
        self.assertEqual(response.cookies.get("lang"), "en")
        # Bez sesji nie ma czego zapisać na koncie - zostaje samo cookie.
        self.assertEqual(self._reload_user().language, "pl")


class TranslatedScreensTests(unittest.TestCase):
    """Najważniejsze kontrolki muszą istnieć w obu językach."""

    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        db_path = Path(self._tmpdir.name) / "screens.db"
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
        from app.core.security import get_current_user_optional
        from app.db.models.user import User

        self.main_module = main_module
        self.db = SessionLocal()
        self.user = User(username="ekranowiec", hashed_password="x", role="user")
        self.db.add(self.user)
        self.db.commit()
        self.db.refresh(self.user)

        main_module.app.dependency_overrides[get_current_user_optional] = lambda: self.user
        self.client = TestClient(main_module.app)

    def tearDown(self) -> None:
        self.main_module.app.dependency_overrides.clear()
        self.db.close()
        from app.core.database import engine

        engine.dispose()
        self._env_patch.stop()
        self._tmpdir.cleanup()
        purge_app_modules()

    def _page(self, path: str, lang: str) -> str:
        self.client.cookies.set("lang", lang)
        response = self.client.get(path)
        self.assertEqual(response.status_code, 200, response.text)
        return response.text

    def test_login_screen_in_both_languages(self) -> None:
        for lang, catalog in (("pl", PL_DICT), ("en", EN_DICT)):
            with self.subTest(lang=lang):
                page = self._page("/login", lang)
                for key in ("login.button", "login.username_placeholder", "login.password_placeholder"):
                    self.assertIn(catalog[key], page)
                self.assertIn(f'<html lang="{lang}"', page)

    def test_recipes_screen_in_both_languages(self) -> None:
        for lang, catalog in (("pl", PL_DICT), ("en", EN_DICT)):
            with self.subTest(lang=lang):
                page = self._page("/recipes-ui", lang)
                for key in (
                    "topbar.recipes_tab",
                    "topbar.shopping_tab",
                    "recipes.add_button",
                    "recipes.search_placeholder",
                    "common.logout",
                ):
                    self.assertIn(catalog[key], page)

    def test_language_switch_is_present_and_marks_the_active_language(self) -> None:
        for lang in ("pl", "en"):
            with self.subTest(lang=lang):
                page = self._page("/recipes-ui", lang)
                self.assertIn('action="/set-lang"', page)
                self.assertIn('method="post"', page)
                self.assertRegex(page, rf'value="{lang}"[^>]*class="lang-option active"')

    def test_switch_explains_it_only_covers_the_interface(self) -> None:
        """Przełącznik nie może udawać, że tłumaczy przepisy."""
        for lang, catalog in (("pl", PL_DICT), ("en", EN_DICT)):
            with self.subTest(lang=lang):
                self.assertIn(catalog["lang.scope_note"], self._page("/login", lang))

    def test_js_dictionary_is_injected_for_the_active_language(self) -> None:
        page = self._page("/recipes-ui", "en")
        self.assertIn("window.I18N", page)
        self.assertIn(EN_DICT["toast.recipe_saved"], page)

    def test_anonymous_visitor_still_gets_a_working_login_page(self) -> None:
        """Brak regresji dla niezalogowanego - najczęstszy wypadek przy
        dodawaniu zależności od użytkownika w rozwiązywaniu języka."""
        from app.core.security import get_current_user_optional

        self.main_module.app.dependency_overrides[get_current_user_optional] = lambda: None
        response = self.client.get("/login")

        self.assertEqual(response.status_code, 200)
        self.assertIn(PL_DICT["login.button"], response.text)


class RecipeContentIsNotTranslatedTests(unittest.TestCase):
    """Granica pakietu: język interfejsu ≠ język treści przepisu.

    Ten pakiet celowo NIE aktywuje recipe_translations. Gdyby ktoś to zmienił,
    te testy zapalą się jako pierwsze."""

    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        db_path = Path(self._tmpdir.name) / "content.db"
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
        from app.core.security import get_current_user, get_current_user_optional
        from app.db.models.user import User

        self.main_module = main_module
        self.db = SessionLocal()
        self.user = User(username="tresciowiec", hashed_password="x", role="user")
        self.db.add(self.user)
        self.db.commit()
        self.db.refresh(self.user)

        main_module.app.dependency_overrides[get_current_user] = lambda: self.user
        main_module.app.dependency_overrides[get_current_user_optional] = lambda: self.user
        self.client = TestClient(main_module.app)

    def tearDown(self) -> None:
        self.main_module.app.dependency_overrides.clear()
        self.db.close()
        from app.core.database import engine

        engine.dispose()
        self._env_patch.stop()
        self._tmpdir.cleanup()
        purge_app_modules()

    def test_recipe_content_is_identical_in_both_ui_languages(self) -> None:
        created = self.client.post(
            "/api/v1/recipes/",
            json={
                "name": "Żurek na zakwasie",
                "description": "Opis po polsku",
                "ingredients": "2 łyżki oliwy\n1 cebula",
                "instructions": "Wymieszaj i podawaj",
                "is_public": True,
            },
        )
        self.assertEqual(created.status_code, 200, created.text)
        recipe_id = created.json()["id"]

        self.client.cookies.set("lang", "pl")
        pl_body = self.client.get(f"/api/v1/recipes/{recipe_id}").json()
        self.client.cookies.set("lang", "en")
        en_body = self.client.get(f"/api/v1/recipes/{recipe_id}").json()

        for field in ("name", "description", "ingredients", "instructions"):
            self.assertEqual(pl_body[field], en_body[field], f"pole {field} zmienia się z językiem UI")
        self.assertEqual(en_body["name"], "Żurek na zakwasie")

    def test_recipe_api_response_has_no_language_field(self) -> None:
        """RecipeRead nie dostaje pola language - dwujęzyczność treści to
        osobna decyzja i osobny pakiet."""
        created = self.client.post(
            "/api/v1/recipes/",
            json={
                "name": "Test",
                "description": "D",
                "ingredients": "a",
                "instructions": "I",
                "is_public": False,
            },
        )
        self.assertNotIn("language", created.json())

    def test_recipe_translations_table_stays_empty(self) -> None:
        from app.db.models.recipe_translation import RecipeTranslation

        self.client.post(
            "/api/v1/recipes/",
            json={
                "name": "Test",
                "description": "D",
                "ingredients": "a",
                "instructions": "I",
                "is_public": False,
            },
        )
        self.assertEqual(self.db.query(RecipeTranslation).count(), 0)

    def test_no_translation_service_was_introduced(self) -> None:
        self.assertFalse((APP_DIR / "services" / "recipe_translation_service.py").is_file())


if __name__ == "__main__":
    unittest.main()
