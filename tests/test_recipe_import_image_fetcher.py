import unittest
from unittest import mock

from app.services.recipe_import import fetcher
from app.services.recipe_import.errors import ResponseTooLargeError, UnsupportedContentTypeError

JPEG_MAGIC = b"\xff\xd8\xff\xe0" + b"\x00" * 32
PNG_MAGIC = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
WEBP_MAGIC = b"RIFF" + b"\x00\x00\x00\x00" + b"WEBP" + b"\x00" * 32


class FakeStreamResponse:
    def __init__(self, status_code=200, headers=None, chunks=None):
        self.status_code = status_code
        self.headers = headers or {}
        self._chunks = chunks or []

    async def aiter_bytes(self):
        for chunk in self._chunks:
            yield chunk


class FakeStreamCM:
    def __init__(self, response):
        self._response = response

    async def __aenter__(self):
        return self._response

    async def __aexit__(self, exc_type, exc, tb):
        return False


class FetchImageTests(unittest.IsolatedAsyncioTestCase):
    """fetch_image() reuses the exact same host guard as fetch_html - only
    the Content-Type allowlist, size limit, and body-vs-declared-type
    sniffing differ, both exercised here without any real network calls."""

    def setUp(self) -> None:
        self._host_guard_patch = mock.patch.object(
            fetcher, "_resolve_and_validate", return_value="93.184.216.34"
        )
        self._host_guard_patch.start()

    def tearDown(self) -> None:
        self._host_guard_patch.stop()

    async def test_accepts_jpeg(self) -> None:
        response = FakeStreamResponse(headers={"content-type": "image/jpeg"}, chunks=[JPEG_MAGIC])
        with mock.patch("httpx.AsyncClient.stream", return_value=FakeStreamCM(response)):
            image = await fetcher.fetch_image("https://example.com/photo.jpg")
        self.assertEqual(image.extension, "jpg")
        self.assertEqual(image.content_type, "image/jpeg")

    async def test_image_fetcher_disables_environment_proxies(self) -> None:
        captured = []

        class StubAsyncClient:
            def __init__(self, **kwargs):
                captured.append(kwargs)

            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                return None

            def stream(self, *args, **kwargs):
                return FakeStreamCM(FakeStreamResponse(
                    headers={"content-type": "image/jpeg"}, chunks=[JPEG_MAGIC]
                ))

        with mock.patch.object(fetcher.httpx, "AsyncClient", StubAsyncClient):
            await fetcher.fetch_image("https://example.com/photo.jpg")

        self.assertEqual(captured[0]["trust_env"], False)

    async def test_accepts_png(self) -> None:
        response = FakeStreamResponse(headers={"content-type": "image/png"}, chunks=[PNG_MAGIC])
        with mock.patch("httpx.AsyncClient.stream", return_value=FakeStreamCM(response)):
            image = await fetcher.fetch_image("https://example.com/photo.png")
        self.assertEqual(image.extension, "png")

    async def test_accepts_webp(self) -> None:
        response = FakeStreamResponse(headers={"content-type": "image/webp"}, chunks=[WEBP_MAGIC])
        with mock.patch("httpx.AsyncClient.stream", return_value=FakeStreamCM(response)):
            image = await fetcher.fetch_image("https://example.com/photo.webp")
        self.assertEqual(image.extension, "webp")

    async def test_rejects_svg_content_type(self) -> None:
        response = FakeStreamResponse(headers={"content-type": "image/svg+xml"}, chunks=[b"<svg></svg>"])
        with mock.patch("httpx.AsyncClient.stream", return_value=FakeStreamCM(response)):
            with self.assertRaises(UnsupportedContentTypeError):
                await fetcher.fetch_image("https://example.com/photo.svg")

    async def test_rejects_html_content_type(self) -> None:
        response = FakeStreamResponse(headers={"content-type": "text/html"}, chunks=[b"<html>error</html>"])
        with mock.patch("httpx.AsyncClient.stream", return_value=FakeStreamCM(response)):
            with self.assertRaises(UnsupportedContentTypeError):
                await fetcher.fetch_image("https://example.com/not-really-an-image.jpg")

    async def test_rejects_html_body_mislabeled_as_image(self) -> None:
        # Content-Type claims image/jpeg but the actual bytes are an HTML
        # error page - magic-byte sniffing must catch this, not just trust
        # the header. This is exactly "don't save an HTML page as an image".
        response = FakeStreamResponse(
            headers={"content-type": "image/jpeg"}, chunks=[b"<html><body>404 not found</body></html>"]
        )
        with mock.patch("httpx.AsyncClient.stream", return_value=FakeStreamCM(response)):
            with self.assertRaises(UnsupportedContentTypeError):
                await fetcher.fetch_image("https://example.com/fake.jpg")

    async def test_rejects_mismatched_magic_bytes(self) -> None:
        # Declares PNG but the body is actually a JPEG - still rejected, the
        # declared type and the sniffed type must agree.
        response = FakeStreamResponse(headers={"content-type": "image/png"}, chunks=[JPEG_MAGIC])
        with mock.patch("httpx.AsyncClient.stream", return_value=FakeStreamCM(response)):
            with self.assertRaises(UnsupportedContentTypeError):
                await fetcher.fetch_image("https://example.com/mismatch.png")

    async def test_rejects_oversized_image_via_content_length(self) -> None:
        response = FakeStreamResponse(
            headers={"content-type": "image/jpeg", "content-length": str(fetcher.MAX_IMAGE_BYTES + 1)}
        )
        with mock.patch("httpx.AsyncClient.stream", return_value=FakeStreamCM(response)):
            with self.assertRaises(ResponseTooLargeError):
                await fetcher.fetch_image("https://example.com/huge.jpg")

    async def test_rejects_oversized_image_via_streamed_chunks(self) -> None:
        big_chunk = JPEG_MAGIC + b"\x00" * fetcher.MAX_IMAGE_BYTES
        response = FakeStreamResponse(headers={"content-type": "image/jpeg"}, chunks=[big_chunk])
        with mock.patch("httpx.AsyncClient.stream", return_value=FakeStreamCM(response)):
            with self.assertRaises(ResponseTooLargeError):
                await fetcher.fetch_image("https://example.com/huge-stream.jpg")


if __name__ == "__main__":
    unittest.main()
