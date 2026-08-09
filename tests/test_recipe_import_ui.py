"""Lightweight UI checks for the recipe-import feature.

The project has no browser/JS test runner (no Selenium/Playwright/Jest), so
these are static checks over the actual template/JS source - not a
replacement for the interactive browser verification already done manually
(login, PL/EN switch, opening both modals, editing/removing an ingredient
row, a live SSRF block against the real endpoint, and a real confirm save
against a local test DB - see docs/handoffs/i18n-recipe-import-ingredients.md).
"""
import json
import re
import unittest
from collections import Counter
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent.parent / "app"
RECIPES_HTML = (APP_DIR / "templates" / "recipes.html").read_text(encoding="utf-8")
LOGIN_HTML = (APP_DIR / "templates" / "login.html").read_text(encoding="utf-8")
RECIPES_JS = (APP_DIR / "static" / "recipes.js").read_text(encoding="utf-8")
PL_DICT = json.loads((APP_DIR / "i18n" / "pl.json").read_text(encoding="utf-8"))
EN_DICT = json.loads((APP_DIR / "i18n" / "en.json").read_text(encoding="utf-8"))


class ImportButtonPresenceTests(unittest.TestCase):
    def test_import_button_exists_in_recipes_template(self) -> None:
        self.assertIn('id="open-import-url-btn"', RECIPES_HTML)
        self.assertIn("import.button", RECIPES_HTML)

    def test_both_import_modals_exist(self) -> None:
        self.assertIn('id="import-url-modal"', RECIPES_HTML)
        self.assertIn('id="import-draft-modal"', RECIPES_HTML)

    def test_ingredient_review_table_exists(self) -> None:
        self.assertIn('id="import-ingredients-body"', RECIPES_HTML)
        self.assertIn('id="import-add-ingredient-btn"', RECIPES_HTML)


class I18nKeyCoverageTests(unittest.TestCase):
    """Every t('...')/t("...") key actually used in the template or JS must
    resolve in BOTH dictionaries, and the dictionaries must stay symmetric."""

    def test_pl_and_en_dictionaries_have_identical_keys(self) -> None:
        self.assertEqual(set(PL_DICT.keys()), set(EN_DICT.keys()))
        self.assertGreater(len(PL_DICT), 100)  # sanity floor, catches an accidental near-empty file

    def _used_template_keys(self) -> set[str]:
        return set(re.findall(r"t\('([\w.]+)'", RECIPES_HTML)) | set(re.findall(r"t\('([\w.]+)'", LOGIN_HTML))

    def _used_js_keys(self) -> set[str]:
        # Negative lookbehind excludes false positives like createElement("button")
        # or getElementById("text-input"), which also match a bare `t\("..."\)`
        # substring but aren't calls to the t() translation helper.
        return set(re.findall(r'(?<![A-Za-z])t\("([\w.]+)"', RECIPES_JS))

    def test_all_used_keys_resolve_in_both_dictionaries(self) -> None:
        used = self._used_template_keys() | self._used_js_keys()
        self.assertGreater(len(used), 0)
        missing_pl = sorted(k for k in used if k not in PL_DICT)
        missing_en = sorted(k for k in used if k not in EN_DICT)
        self.assertEqual(missing_pl, [])
        self.assertEqual(missing_en, [])

    def test_import_error_and_warning_code_lookup_tables_are_fully_translated(self) -> None:
        # These two JS objects map API error_code/warning values to i18n keys
        # via a variable lookup, so the static t("...") scan above can't see
        # them - check their literal values directly instead.
        error_map = dict(re.findall(r'(\w+):\s*"(import\.error\.[\w.]+)"', RECIPES_JS))
        warning_map = dict(re.findall(r'(\w+):\s*"(import\.warning\.[\w.]+)"', RECIPES_JS))
        self.assertGreater(len(error_map), 0)
        self.assertGreater(len(warning_map), 0)
        for key in {**error_map, **warning_map}.values():
            self.assertIn(key, PL_DICT, msg=f"{key} missing from pl.json")
            self.assertIn(key, EN_DICT, msg=f"{key} missing from en.json")


class DuplicateIdTests(unittest.TestCase):
    def test_no_duplicate_ids(self) -> None:
        ids = re.findall(r'id="([^"]+)"', RECIPES_HTML)
        counts = Counter(ids)
        duplicates = {id_ for id_, count in counts.items() if count > 1}
        self.assertEqual(duplicates, set(), f"Duplicate id(s): {duplicates}")

    def test_all_new_import_ids_are_unique(self) -> None:
        ids = re.findall(r'id="(import-[^"]+)"', RECIPES_HTML)
        self.assertEqual(len(ids), len(set(ids)))
        self.assertGreater(len(ids), 5)


class DraftSerializationStructureTests(unittest.TestCase):
    """buildImportConfirmPayload() has no JS test runner available (the
    script assumes a live DOM) - this checks its source builds an object
    with every field the confirm schema requires. Actual end-to-end
    serialization (edit -> submit -> DB row) was verified interactively,
    see the module docstring."""

    def test_build_payload_function_exists(self) -> None:
        self.assertIn("function buildImportConfirmPayload()", RECIPES_JS)

    def test_build_payload_includes_all_required_confirm_fields(self) -> None:
        match = re.search(
            r"function buildImportConfirmPayload\(\).*?\breturn\s*\{(.*?)\};",
            RECIPES_JS,
            re.DOTALL,
        )
        self.assertIsNotNone(match)
        body = match.group(1)
        for field in (
            "source_url", "source_name", "source_author", "name",
            "description", "instructions",
            "is_public", "image_url", "download_image", "save_structured_ingredients", "ingredients",
        ):
            self.assertIn(f"{field}:", body, msg=f"buildImportConfirmPayload is missing '{field}'")

    def test_payload_does_not_send_unsupported_recipe_metadata(self) -> None:
        match = re.search(
            r"function buildImportConfirmPayload\(\).*?\breturn\s*\{(.*?)\};",
            RECIPES_JS,
            re.DOTALL,
        )
        body = match.group(1)
        for field in ("servings", "prep_time", "cook_time", "total_time"):
            self.assertNotIn(f"{field}:", body)

    def test_import_ui_has_accessible_language_switch_and_basic_sections(self) -> None:
        for source in (RECIPES_HTML, LOGIN_HTML):
            self.assertIn('aria-current="true"', source)
            self.assertIn('class="lang-option', source)
        self.assertIn("import.basic_section", RECIPES_HTML)
        self.assertIn("import.source_section", RECIPES_HTML)
        self.assertNotIn('id="import-draft-prep-time"', RECIPES_HTML)
        self.assertNotIn('id="import-draft-cook-time"', RECIPES_HTML)

    def test_ingredient_rows_serialize_all_editable_fields(self) -> None:
        match = re.search(r"ingredients:\s*ImportState\.ingredients\.map\(item\s*=>\s*\(\{(.*?)\}\)\)", RECIPES_JS, re.DOTALL)
        self.assertIsNotNone(match)
        body = match.group(1)
        for field in ("original_text", "quantity", "unit", "name", "note", "confidence", "requires_review"):
            self.assertIn(f"{field}:", body)

    def test_import_rendering_does_not_interpolate_recipe_text_as_html(self) -> None:
        self.assertIn("originalCell.textContent = item.original_text", RECIPES_JS)
        self.assertIn("item.textContent = t(key)", RECIPES_JS)
        self.assertNotIn("innerHTML = item", RECIPES_JS)


class DoubleSubmitGuardTests(unittest.TestCase):
    """Real duplicate-confirm protection is tested at the API level in
    tests/test_recipe_import_endpoints.py (server-side, source_url + time
    window). This checks the client ALSO refuses to fire a second request
    while one is in flight, per Etap 6's "blokada podwójnego kliknięcia"."""

    def test_confirm_handler_checks_a_submitting_flag_before_sending(self) -> None:
        match = re.search(r"async function confirmImportSave\(\)\s*\{(.*?)\n\}", RECIPES_JS, re.DOTALL)
        self.assertIsNotNone(match)
        body = match.group(1)
        self.assertIn("if (ImportState.submitting) return;", body)
        self.assertIn("ImportState.submitting = true;", body)
        self.assertIn("confirmBtn.disabled = true;", body)

    def test_submitting_flag_is_reset_in_a_finally_block(self) -> None:
        match = re.search(r"async function confirmImportSave\(\).*?finally\s*\{(.*?)\}\s*\}", RECIPES_JS, re.DOTALL)
        self.assertIsNotNone(match)
        self.assertIn("ImportState.submitting = false;", match.group(1))

    def test_confirm_validates_new_empty_ingredient_rows(self) -> None:
        self.assertIn("function validateImportIngredients()", RECIPES_JS)
        self.assertIn('t("import.error.ingredient_required")', RECIPES_JS)


if __name__ == "__main__":
    unittest.main()
