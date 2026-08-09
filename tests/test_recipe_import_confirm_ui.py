"""Regression checks for the browser-side preview -> confirm workflow.

The project does not ship a browser test runner, so these checks assert the
critical wiring in the actual template and JavaScript source. API-level tests
cover the server-side confirm behavior separately.
"""

import re
import unittest
from pathlib import Path


APP_DIR = Path(__file__).resolve().parent.parent / "app"
RECIPES_HTML = (APP_DIR / "templates" / "recipes.html").read_text(encoding="utf-8")
RECIPES_JS = (APP_DIR / "static" / "recipes.js").read_text(encoding="utf-8")
MAIN_CSS = (APP_DIR / "static" / "main.css").read_text(encoding="utf-8")


class RecipeImportConfirmUiTests(unittest.TestCase):
    def test_save_button_is_a_click_button_and_has_listener(self) -> None:
        self.assertIn('type="button" id="confirm-import-btn"', RECIPES_HTML)
        self.assertIn(
            'confirmImportBtn.addEventListener("click", confirmImportSave)',
            RECIPES_JS,
        )

    def test_payload_is_built_before_confirm_request(self) -> None:
        self.assertIn("function parseNumberOrNull(value)", RECIPES_JS)
        self.assertIn("preview_token: ImportState.previewToken", RECIPES_JS)
        self.assertIn("source_url: ImportState.sourceUrl", RECIPES_JS)
        payload_start = RECIPES_JS.index("payload = buildImportConfirmPayload()")
        request_start = RECIPES_JS.index(
            'Api.post("/api/v1/recipe-import/confirm", payload)'
        )
        self.assertLess(payload_start, request_start)

    def test_optional_ingredient_fields_are_serialized_without_blocking(self) -> None:
        self.assertIn('const normalized = String(value ?? "").trim()', RECIPES_JS)
        self.assertIn('if (!normalized) return null;', RECIPES_JS)
        self.assertIn('unit: item.unit || null', RECIPES_JS)
        self.assertIn('note: item.note || null', RECIPES_JS)

    def test_pre_request_failures_have_specific_messages(self) -> None:
        self.assertIn('importErrorMessage(importErrorCodeFromError(err))', RECIPES_JS)
        self.assertIn('return "invalid_quantity"', RECIPES_JS)
        self.assertIn('return "payload_invalid"', RECIPES_JS)
        self.assertIn('return "network_error"', RECIPES_JS)
        self.assertIn('return "api_error"', RECIPES_JS)

    def test_confirm_is_disabled_while_request_is_in_flight(self) -> None:
        body = re.search(
            r"async function confirmImportSave\(\)\s*\{(.*?)\n\}",
            RECIPES_JS,
            re.DOTALL,
        )
        self.assertIsNotNone(body)
        self.assertIn("if (ImportState.submitting) return;", body.group(1))
        self.assertIn("confirmBtn.disabled = true;", body.group(1))
        self.assertIn("ImportState.submitting = false;", body.group(1))

    def test_token_is_cleared_after_success_but_retained_for_retryable_errors(self) -> None:
        self.assertIn("closeImportDraftModal();", RECIPES_JS)
        self.assertIn('if (errorCode.startsWith("preview_token_")', RECIPES_JS)
        self.assertIn('ImportState.previewToken = "";', RECIPES_JS)

    def test_toast_layer_is_above_modal_without_capturing_clicks(self) -> None:
        self.assertIn("--z-modal: 100", MAIN_CSS)
        self.assertIn("--z-toast: 200", MAIN_CSS)
        self.assertIn("z-index: var(--z-modal)", MAIN_CSS)
        self.assertIn("z-index: var(--z-toast)", MAIN_CSS)
        self.assertIn("pointer-events: none", MAIN_CSS)


if __name__ == "__main__":
    unittest.main()
