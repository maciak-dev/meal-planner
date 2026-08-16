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


def _decode_base64url(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def _tamper_signature(token: str) -> str:
    encoded_claims, encoded_signature = token.split(".", 1)
    signature = bytearray(_decode_base64url(encoded_signature))
    signature[0] ^= 0x01
    tampered_signature = base64.urlsafe_b64encode(signature).rstrip(b"=").decode("ascii")
    return f"{encoded_claims}.{tampered_signature}"


class PreviewTokenTests(unittest.TestCase):
    def test_token_verifies_for_same_user_and_canonical_source(self) -> None:
        token = issue_preview_token(7, "HTTPS://Example.com:443/recipe#ignored", now=100)
        verify_preview_token(token, 7, "https://example.com/recipe", now=100)

    def test_token_has_nonce_and_no_raw_source_url(self) -> None:
        token = issue_preview_token(7, "https://example.com/recipe", now=100)
        payload = token.split(".", 1)[0]
        claims = json.loads(_decode_base64url(payload))
        self.assertEqual(claims["uid"], 7)
        self.assertEqual(claims["exp"] - claims["iat"], PREVIEW_TOKEN_TTL_SECONDS)
        self.assertTrue(claims["nonce"])
        self.assertNotIn("example.com", token)

    def test_modified_signature_is_rejected(self) -> None:
        for iteration in range(100):
            with self.subTest(iteration=iteration):
                token = issue_preview_token(7, "https://example.com/recipe", now=100)
                verify_preview_token(token, 7, "https://example.com/recipe", now=100)

                tampered = _tamper_signature(token)
                original_signature = token.split(".", 1)[1]
                tampered_signature = tampered.split(".", 1)[1]
                self.assertNotEqual(
                    _decode_base64url(original_signature),
                    _decode_base64url(tampered_signature),
                )
                with self.assertRaises(PreviewTokenError):
                    verify_preview_token(tampered, 7, "https://example.com/recipe", now=100)

    def test_modified_claims_without_resigning_are_rejected(self) -> None:
        token = issue_preview_token(7, "https://example.com/recipe", now=100)
        encoded, signature = token.split(".", 1)
        claims = json.loads(_decode_base64url(encoded))
        claims["uid"] = 8
        changed = base64.urlsafe_b64encode(
            json.dumps(claims, separators=(",", ":"), sort_keys=True).encode()
        ).rstrip(b"=").decode()
        with self.assertRaises(PreviewTokenError):
            verify_preview_token(f"{changed}.{signature}", 7, "https://example.com/recipe", now=100)

    def test_malformed_tokens_are_rejected(self) -> None:
        for token in ("", "not-a-token", "payload.signature.extra", "payload.%"):
            with self.subTest(token=token):
                with self.assertRaises(PreviewTokenError):
                    verify_preview_token(token, 7, "https://example.com/recipe", now=100)

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
