import socket
import unittest
from unittest import mock

import httpx

from app.services.recipe_import import fetcher
from app.services.recipe_import.errors import (
    BlockedHostError,
    FetchTimeoutError,
    InvalidUrlError,
    ResponseTooLargeError,
    TooManyRedirectsError,
    UnsupportedContentTypeError,
    UpstreamFetchError,
)
from app.services.recipe_import.fetcher import _resolve_and_validate, _validate_url


class ValidateUrlTests(unittest.TestCase):
    def test_http_and_https_use_their_standard_default_ports(self) -> None:
        scheme, host, port, path, query, fragment = _validate_url("http://example.com/recipe")
        self.assertEqual((scheme, host, port, path), ("http", "example.com", 80, "/recipe"))

        scheme, host, port, path, query, fragment = _validate_url("https://example.com/recipe")
        self.assertEqual((scheme, host, port, path), ("https", "example.com", 443, "/recipe"))

    def test_explicit_standard_port_is_allowed(self) -> None:
        _, _, port, _, _, _ = _validate_url("https://example.com:443/recipe")
        self.assertEqual(port, 443)

    def test_non_standard_port_is_rejected(self) -> None:
        for url in ("http://example.com:8080/recipe", "https://example.com:8443/recipe", "http://example.com:22/x"):
            with self.assertRaises(InvalidUrlError):
                _validate_url(url)

    def test_ftp_scheme_is_rejected(self) -> None:
        with self.assertRaises(InvalidUrlError):
            _validate_url("ftp://example.com/recipe")

    def test_file_scheme_is_rejected(self) -> None:
        with self.assertRaises(InvalidUrlError):
            _validate_url("file:///etc/passwd")

    def test_missing_host_is_rejected(self) -> None:
        with self.assertRaises(InvalidUrlError):
            _validate_url("http:///no-host")

    def test_userinfo_with_password_is_rejected(self) -> None:
        with self.assertRaises(InvalidUrlError):
            _validate_url("https://user:password@example.com/recipe")

    def test_userinfo_username_only_is_rejected(self) -> None:
        # "https://example.com@127.0.0.1" parses as username="example.com",
        # host="127.0.0.1" - a classic userinfo trick to smuggle a trusted-
        # looking name in front of the real (attacker-controlled) target.
        # Rejected outright, never reinterpreted as "the real host is X".
        with self.assertRaises(InvalidUrlError):
            _validate_url("https://example.com@127.0.0.1/recipe")


class ResolveAndValidateTests(unittest.TestCase):
    """No real network calls: literal IPs and 'localhost' resolve without DNS,
    and everything else is mocked via socket.getaddrinfo."""

    def test_blocks_localhost(self) -> None:
        with self.assertRaises(BlockedHostError):
            _resolve_and_validate("localhost")

    def test_blocks_loopback_ipv4(self) -> None:
        with self.assertRaises(BlockedHostError):
            _resolve_and_validate("127.0.0.1")

    def test_blocks_loopback_ipv6(self) -> None:
        with self.assertRaises(BlockedHostError):
            _resolve_and_validate("::1")

    def test_blocks_cloud_metadata_address(self) -> None:
        with self.assertRaises(BlockedHostError):
            _resolve_and_validate("169.254.169.254")

    def test_blocks_private_ipv4_ranges(self) -> None:
        for ip in ("10.0.0.5", "172.16.0.5", "192.168.1.5"):
            with self.assertRaises(BlockedHostError):
                _resolve_and_validate(ip)

    def test_blocks_ipv6_unique_local_and_link_local(self) -> None:
        for ip in ("fd00::1", "fe80::1"):
            with self.assertRaises(BlockedHostError):
                _resolve_and_validate(ip)

    def test_blocks_ipv6_mapped_loopback_and_unspecified(self) -> None:
        for ip in ("::1", "::"):
            with self.assertRaises(BlockedHostError):
                _resolve_and_validate(ip)

    def test_blocks_shared_address_space(self) -> None:
        with self.assertRaises(BlockedHostError):
            _resolve_and_validate("100.64.0.1")

    def test_dns_resolution_failure_is_blocked_not_crashed(self) -> None:
        with mock.patch("socket.getaddrinfo", side_effect=socket.gaierror("no such host")):
            with self.assertRaises(BlockedHostError):
                _resolve_and_validate("this-domain-does-not-resolve.invalid")

    def test_allows_and_returns_a_hostname_resolving_to_a_public_address(self) -> None:
        fake_addrinfo = [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 0)),
        ]
        with mock.patch("socket.getaddrinfo", return_value=fake_addrinfo):
            resolved = _resolve_and_validate("recipes.example.com")
        self.assertEqual(resolved, "93.184.216.34")

    def test_blocks_hostname_when_any_resolved_address_is_private(self) -> None:
        # Defense against multi-A-record bypass: one public + one private IP
        # must still be blocked, not just the first one checked.
        fake_addrinfo = [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 0)),
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("10.0.0.1", 0)),
        ]
        with mock.patch("socket.getaddrinfo", return_value=fake_addrinfo):
            with self.assertRaises(BlockedHostError):
                _resolve_and_validate("sneaky.example.com")

    def test_blocks_hostname_when_private_address_comes_first(self) -> None:
        fake_addrinfo = [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("10.0.0.1", 0)),
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 0)),
        ]
        with mock.patch("socket.getaddrinfo", return_value=fake_addrinfo):
            with self.assertRaises(BlockedHostError):
                _resolve_and_validate("sneaky2.example.com")

    def test_blocks_ipv6_private_address_mixed_with_public_ipv4(self) -> None:
        fake_addrinfo = [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 0)),
            (socket.AF_INET6, socket.SOCK_STREAM, 6, "", ("fd00::1", 0, 0, 0)),
        ]
        with mock.patch("socket.getaddrinfo", return_value=fake_addrinfo):
            with self.assertRaises(BlockedHostError):
                _resolve_and_validate("dual-stack-sneaky.example.com")


class FakeStreamResponse:
    """Stand-in for an httpx streaming response - avoids any real network I/O."""

    def __init__(self, status_code=200, headers=None, chunks=None, encoding="utf-8"):
        self.status_code = status_code
        self.headers = headers or {}
        self._chunks = chunks or []
        self.encoding = encoding

    async def aiter_bytes(self):
        for chunk in self._chunks:
            yield chunk


class FakeStreamCM:
    """httpx's client.stream(...) returns an async context manager directly
    (it is not itself a coroutine) - this mirrors that shape for mocking."""

    def __init__(self, response):
        self._response = response

    async def __aenter__(self):
        return self._response

    async def __aexit__(self, exc_type, exc, tb):
        return False


class FetchHtmlBehaviorTests(unittest.IsolatedAsyncioTestCase):
    """Exercises fetch_html's redirect/size/timeout/content-type handling with
    a mocked httpx transport - no real network calls, per the project's testing
    guidance for the import feature. The host guard is mocked to a fixed public
    IP here; ResolveAndValidateTests above already covers the guard itself."""

    def setUp(self) -> None:
        self._host_guard_patch = mock.patch.object(
            fetcher, "_resolve_and_validate", return_value="93.184.216.34"
        )
        self._host_guard_patch.start()

    def tearDown(self) -> None:
        self._host_guard_patch.stop()

    async def test_successful_fetch_returns_html(self) -> None:
        response = FakeStreamResponse(
            status_code=200,
            headers={"content-type": "text/html; charset=utf-8"},
            chunks=[b"<html>", b"<body>ok</body></html>"],
        )
        with mock.patch("httpx.AsyncClient.stream", return_value=FakeStreamCM(response)):
            page = await fetcher.fetch_html("https://example.com/recipe")
        self.assertIn("ok", page.html)
        self.assertEqual(page.url, "https://example.com/recipe")

    async def test_fetcher_disables_environment_proxies(self) -> None:
        captured = []

        class StubAsyncClient:
            def __init__(self, **kwargs):
                captured.append(kwargs)

            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                return None

            def stream(self, *args, **kwargs):
                response = FakeStreamResponse(
                    status_code=200,
                    headers={"content-type": "text/html"},
                    chunks=[b"<html>ok</html>"],
                )
                return FakeStreamCM(response)

        with mock.patch.object(fetcher.httpx, "AsyncClient", StubAsyncClient):
            await fetcher.fetch_html("https://example.com/recipe")

        self.assertEqual(captured[0]["trust_env"], False)
        self.assertFalse(captured[0]["follow_redirects"])
        self.assertEqual(captured[0]["timeout"], fetcher.TIMEOUT_SECONDS)

    async def test_pinned_request_preserves_original_host_header(self) -> None:
        captured = {}

        def fake_stream(method, url, *, headers=None, extensions=None, **kwargs):
            captured["url"] = str(url)
            captured["headers"] = dict(headers or {})
            captured["extensions"] = dict(extensions or {})
            response = FakeStreamResponse(
                status_code=200, headers={"content-type": "text/html"}, chunks=[b"<html>ok</html>"]
            )
            return FakeStreamCM(response)

        with mock.patch("httpx.AsyncClient.stream", side_effect=fake_stream):
            await fetcher.fetch_html("https://example.com/recipe")

        # The wire-level request targets the pinned IP directly (no second DNS
        # resolution can happen at connect time), while the Host header and
        # TLS SNI extension stay on the real hostname so the certificate is
        # still verified against the correct name.
        self.assertIn("93.184.216.34", captured["url"])
        self.assertEqual(captured["headers"]["Host"], "example.com")
        self.assertEqual(captured["extensions"]["sni_hostname"], "example.com")

    async def test_follows_redirect_and_re_validates_target(self) -> None:
        redirect = FakeStreamResponse(status_code=302, headers={"location": "https://example.com/final"})
        final = FakeStreamResponse(
            status_code=200, headers={"content-type": "text/html"}, chunks=[b"<html>final</html>"]
        )
        with mock.patch("httpx.AsyncClient.stream", side_effect=[FakeStreamCM(redirect), FakeStreamCM(final)]):
            page = await fetcher.fetch_html("https://example.com/start")
        self.assertIn("final", page.html)
        self.assertEqual(page.url, "https://example.com/final")

    async def test_redirect_target_goes_through_the_same_host_guard(self) -> None:
        # A redirect to a blocked address must be rejected, not silently
        # followed - the guard mock here simulates that re-validation.
        redirect = FakeStreamResponse(status_code=302, headers={"location": "http://169.254.169.254/latest"})
        with mock.patch("httpx.AsyncClient.stream", return_value=FakeStreamCM(redirect)):
            with mock.patch.object(
                fetcher, "_resolve_and_validate", side_effect=[
                    "93.184.216.34",
                    BlockedHostError("blocked"),
                ]
            ):
                with self.assertRaises(BlockedHostError):
                    await fetcher.fetch_html("https://example.com/start")

    async def test_too_many_redirects_raises(self) -> None:
        redirect = FakeStreamResponse(status_code=302, headers={"location": "https://example.com/next"})
        with mock.patch("httpx.AsyncClient.stream", return_value=FakeStreamCM(redirect)):
            with self.assertRaises(TooManyRedirectsError):
                await fetcher.fetch_html("https://example.com/start")

    async def test_unsupported_content_type_rejected(self) -> None:
        response = FakeStreamResponse(status_code=200, headers={"content-type": "application/pdf"})
        with mock.patch("httpx.AsyncClient.stream", return_value=FakeStreamCM(response)):
            with self.assertRaises(UnsupportedContentTypeError):
                await fetcher.fetch_html("https://example.com/file.pdf")

    async def test_html_content_type_must_be_an_exact_media_type(self) -> None:
        response = FakeStreamResponse(status_code=200, headers={"content-type": "text/html-malicious"})
        with mock.patch("httpx.AsyncClient.stream", return_value=FakeStreamCM(response)):
            with self.assertRaises(UnsupportedContentTypeError):
                await fetcher.fetch_html("https://example.com/file")

    async def test_response_too_large_via_content_length_header(self) -> None:
        response = FakeStreamResponse(
            status_code=200,
            headers={"content-type": "text/html", "content-length": str(fetcher.MAX_RESPONSE_BYTES + 1)},
        )
        with mock.patch("httpx.AsyncClient.stream", return_value=FakeStreamCM(response)):
            with self.assertRaises(ResponseTooLargeError):
                await fetcher.fetch_html("https://example.com/huge")

    async def test_response_too_large_via_streamed_chunks(self) -> None:
        big_chunk = b"x" * (fetcher.MAX_RESPONSE_BYTES + 1)
        response = FakeStreamResponse(status_code=200, headers={"content-type": "text/html"}, chunks=[big_chunk])
        with mock.patch("httpx.AsyncClient.stream", return_value=FakeStreamCM(response)):
            with self.assertRaises(ResponseTooLargeError):
                await fetcher.fetch_html("https://example.com/huge-stream")

    async def test_invalid_content_length_is_rejected(self) -> None:
        response = FakeStreamResponse(
            status_code=200,
            headers={"content-type": "text/html", "content-length": "not-a-number"},
        )
        with mock.patch("httpx.AsyncClient.stream", return_value=FakeStreamCM(response)):
            with self.assertRaises(UpstreamFetchError):
                await fetcher.fetch_html("https://example.com/invalid-length")

    async def test_gzip_bomb_is_caught_on_decompressed_size_not_declared_length(self) -> None:
        # httpx's aiter_bytes() yields already-decompressed bytes, so a small
        # declared Content-Length with a huge decoded payload (a "gzip bomb")
        # is still caught by the streaming cap below - it never trusts the
        # compressed Content-Length header as the true size.
        decompressed_bomb_chunk = b"x" * (fetcher.MAX_RESPONSE_BYTES + 1)
        response = FakeStreamResponse(
            status_code=200,
            headers={"content-type": "text/html", "content-length": "512"},  # tiny compressed size
            chunks=[decompressed_bomb_chunk],
        )
        with mock.patch("httpx.AsyncClient.stream", return_value=FakeStreamCM(response)):
            with self.assertRaises(ResponseTooLargeError):
                await fetcher.fetch_html("https://example.com/bomb.gz")

    async def test_timeout_is_translated_to_fetch_timeout_error(self) -> None:
        with mock.patch("httpx.AsyncClient.stream", side_effect=httpx.TimeoutException("timed out")):
            with self.assertRaises(FetchTimeoutError):
                await fetcher.fetch_html("https://example.com/slow")

    async def test_non_200_status_raises_upstream_error(self) -> None:
        response = FakeStreamResponse(status_code=500, headers={"content-type": "text/html"})
        with mock.patch("httpx.AsyncClient.stream", return_value=FakeStreamCM(response)):
            with self.assertRaises(UpstreamFetchError):
                await fetcher.fetch_html("https://example.com/broken")


class DnsRebindingMitigationTests(unittest.IsolatedAsyncioTestCase):
    """Confirms the actual anti-rebinding mechanism: DNS is resolved exactly
    once per fetch attempt and the connection is pinned to that address - a
    DNS record that changes to a private IP *after* validation cannot affect
    an in-flight fetch, because nothing re-resolves the hostname at connect
    time (httpx connects to the literal IP already baked into the URL)."""

    async def test_getaddrinfo_is_called_exactly_once_per_attempt(self) -> None:
        call_count = {"n": 0}
        real_getaddrinfo = socket.getaddrinfo

        def counting_getaddrinfo(host, *args, **kwargs):
            if host == "rebinding-target.example.com":
                call_count["n"] += 1
                # Always returns the SAME public address regardless of how
                # many times it's called in this test - if fetch_html ever
                # re-resolved mid-flight, this fake would still look "safe",
                # so the real assertion is the call *count*, proving there is
                # no second resolution window for a rebind to exploit.
                return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 0))]
            return real_getaddrinfo(host, *args, **kwargs)

        response = FakeStreamResponse(
            status_code=200, headers={"content-type": "text/html"}, chunks=[b"<html>ok</html>"]
        )
        with mock.patch("socket.getaddrinfo", side_effect=counting_getaddrinfo):
            with mock.patch("httpx.AsyncClient.stream", return_value=FakeStreamCM(response)):
                await fetcher.fetch_html("https://rebinding-target.example.com/recipe")

        self.assertEqual(call_count["n"], 1)

    async def test_connection_targets_the_validated_ip_not_a_re_resolved_one(self) -> None:
        # Even if the DNS record "changes" between validation and the actual
        # request (simulated here by a resolver that would return a private
        # IP on any call after the first), the wire-level URL httpx is asked
        # to fetch already has the first, validated IP baked in - a second
        # lookup is never performed to pick up the change.
        calls = []

        def flaky_getaddrinfo(host, *args, **kwargs):
            calls.append(host)
            if len(calls) == 1:
                return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 0))]
            return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("10.0.0.1", 0))]

        captured_url = {}

        def fake_stream(method, url, *, headers=None, extensions=None, **kwargs):
            captured_url["value"] = str(url)
            response = FakeStreamResponse(
                status_code=200, headers={"content-type": "text/html"}, chunks=[b"<html>ok</html>"]
            )
            return FakeStreamCM(response)

        with mock.patch("socket.getaddrinfo", side_effect=flaky_getaddrinfo):
            with mock.patch("httpx.AsyncClient.stream", side_effect=fake_stream):
                await fetcher.fetch_html("https://rebind-race.example.com/recipe")

        self.assertIn("93.184.216.34", captured_url["value"])
        self.assertNotIn("10.0.0.1", captured_url["value"])


if __name__ == "__main__":
    unittest.main()
