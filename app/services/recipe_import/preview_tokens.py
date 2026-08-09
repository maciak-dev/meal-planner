"""Short-lived, user-bound capabilities for recipe import confirmation."""

import base64
import hashlib
import hmac
import json
import secrets
import time
from urllib.parse import urlsplit, urlunsplit

from app.core.config import SECRET_KEY

PREVIEW_TOKEN_TTL_SECONDS = 10 * 60
TOKEN_VERSION = 1
_TOKEN_SEPARATOR = "."


class PreviewTokenError(ValueError):
    """Base class for safe, client-facing preview token failures."""


class PreviewTokenOwnerMismatch(PreviewTokenError):
    pass


class PreviewTokenExpired(PreviewTokenError):
    pass


class PreviewTokenSourceMismatch(PreviewTokenError):
    pass


def canonical_source_url(url: str) -> str:
    """Return a stable, non-fetching representation used only for binding."""
    parts = urlsplit(url)
    if parts.scheme not in {"http", "https"} or not parts.hostname:
        raise PreviewTokenSourceMismatch("Source URL is not bindable")
    if parts.username is not None or parts.password is not None:
        raise PreviewTokenSourceMismatch("Source URL is not bindable")

    try:
        port = parts.port
    except ValueError as exc:
        raise PreviewTokenSourceMismatch("Source URL is not bindable") from exc

    hostname = parts.hostname.lower().rstrip(".")
    host_literal = f"[{hostname}]" if ":" in hostname else hostname
    default_port = 80 if parts.scheme == "http" else 443
    netloc = host_literal if port in (None, default_port) else f"{host_literal}:{port}"
    return urlunsplit((parts.scheme.lower(), netloc, parts.path or "/", parts.query, ""))


def _source_fingerprint(url: str) -> str:
    return hashlib.sha256(canonical_source_url(url).encode("utf-8")).hexdigest()


def _b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _b64decode(value: str) -> bytes:
    if not value or len(value) > 4096:
        raise PreviewTokenError("Invalid preview token")
    try:
        return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
    except (ValueError, UnicodeError) as exc:
        raise PreviewTokenError("Invalid preview token") from exc


def issue_preview_token(user_id: int, source_url: str, *, now: int | None = None) -> str:
    issued_at = int(time.time() if now is None else now)
    claims = {
        "v": TOKEN_VERSION,
        "uid": int(user_id),
        "src": _source_fingerprint(source_url),
        "iat": issued_at,
        "exp": issued_at + PREVIEW_TOKEN_TTL_SECONDS,
        "nonce": secrets.token_urlsafe(16),
    }
    payload = _b64encode(json.dumps(claims, separators=(",", ":"), sort_keys=True).encode("utf-8"))
    signature = hmac.new(SECRET_KEY.encode("utf-8"), payload.encode("ascii"), hashlib.sha256).digest()
    return f"{payload}{_TOKEN_SEPARATOR}{_b64encode(signature)}"


def verify_preview_token(token: str, user_id: int, source_url: str, *, now: int | None = None) -> None:
    if not isinstance(token, str) or token.count(_TOKEN_SEPARATOR) != 1:
        raise PreviewTokenError("Invalid preview token")

    encoded_claims, encoded_signature = token.split(_TOKEN_SEPARATOR, 1)
    expected_signature = hmac.new(
        SECRET_KEY.encode("utf-8"), encoded_claims.encode("ascii"), hashlib.sha256
    ).digest()
    actual_signature = _b64decode(encoded_signature)
    if not hmac.compare_digest(actual_signature, expected_signature):
        raise PreviewTokenError("Invalid preview token")

    try:
        claims = json.loads(_b64decode(encoded_claims).decode("utf-8"))
        valid_shape = (
            claims.get("v") == TOKEN_VERSION
            and isinstance(claims.get("uid"), int)
            and isinstance(claims.get("src"), str)
            and isinstance(claims.get("iat"), int)
            and isinstance(claims.get("exp"), int)
            and isinstance(claims.get("nonce"), str)
            and bool(claims["nonce"])
        )
    except (AttributeError, KeyError, TypeError, ValueError, UnicodeError, json.JSONDecodeError) as exc:
        raise PreviewTokenError("Invalid preview token") from exc

    if not valid_shape:
        raise PreviewTokenError("Invalid preview token")
    if claims["uid"] != int(user_id):
        raise PreviewTokenOwnerMismatch("Preview token belongs to another user")
    if int(time.time() if now is None else now) >= claims["exp"]:
        raise PreviewTokenExpired("Preview token has expired")
    if not hmac.compare_digest(claims["src"], _source_fingerprint(source_url)):
        raise PreviewTokenSourceMismatch("Preview token source does not match")
