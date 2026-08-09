import base64
import json
import time
import unittest

from app.services.recipe_import.preview_tokens import (
    PREVIEW_TOKEN_TTL_SECONDS,
    PreviewTokenError,
    PreviewTokenExpired,
    PreviewTokenOwnerMismatch,
    PreviewTokenSourceMismatch,
    issue_preview_token,
    verify_preview_token,
)


class PreviewTokenTests(unittest.TestCase):
    def test_token_verifies_for_same_user_and_canonical_source(self) -> None:
        token = issue_preview_token(7, "HTTPS://Example.com:443/recipe#ignored", now=100)
        verify_preview_token(token, 7, "https://example.com/recipe", now=100)

    def test_token_has_nonce_and_no_raw_source_url(self) -> None:
        token = issue_preview_token(7, "https://example.com/recipe", now=100)
        payload = token.split(".", 1)[0]
        claims = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
        self.assertEqual(claims["uid"], 7)
        self.assertEqual(claims["exp"] - claims["iat"], PREVIEW_TOKEN_TTL_SECONDS)
        self.assertTrue(claims["nonce"])
        self.assertNotIn("example.com", token)

    def test_modified_signature_is_rejected(self) -> None:
        token = issue_preview_token(7, "https://example.com/recipe", now=100)
        tampered = token[:-1] + ("A" if token[-1] != "A" else "B")
        with self.assertRaises(PreviewTokenError):
            verify_preview_token(tampered, 7, "https://example.com/recipe", now=100)

    def test_modified_claims_without_resigning_are_rejected(self) -> None:
        token = issue_preview_token(7, "https://example.com/recipe", now=100)
        encoded, signature = token.split(".", 1)
        claims = json.loads(base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4)))
        claims["uid"] = 8
        changed = base64.urlsafe_b64encode(
            json.dumps(claims, separators=(",", ":"), sort_keys=True).encode()
        ).rstrip(b"=").decode()
        with self.assertRaises(PreviewTokenError):
            verify_preview_token(f"{changed}.{signature}", 7, "https://example.com/recipe", now=100)

    def test_expired_token_is_rejected(self) -> None:
        token = issue_preview_token(7, "https://example.com/recipe", now=100)
        with self.assertRaises(PreviewTokenExpired):
            verify_preview_token(token, 7, "https://example.com/recipe", now=100 + PREVIEW_TOKEN_TTL_SECONDS)

    def test_other_user_is_rejected_without_disclosing_owner(self) -> None:
        token = issue_preview_token(7, "https://example.com/recipe", now=100)
        with self.assertRaises(PreviewTokenOwnerMismatch):
            verify_preview_token(token, 8, "https://example.com/recipe", now=100)

    def test_other_source_is_rejected(self) -> None:
        token = issue_preview_token(7, "https://example.com/recipe-a", now=100)
        with self.assertRaises(PreviewTokenSourceMismatch):
            verify_preview_token(token, 7, "https://example.com/recipe-b", now=100)


if __name__ == "__main__":
    unittest.main()
