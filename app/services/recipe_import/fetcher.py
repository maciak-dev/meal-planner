import ipaddress
import socket
from dataclasses import dataclass
from urllib.parse import urlsplit, urlunsplit

import httpx

from app.services.recipe_import.errors import (
    BlockedHostError,
    FetchTimeoutError,
    InvalidUrlError,
    ResponseTooLargeError,
    TooManyRedirectsError,
    UnsupportedContentTypeError,
    UpstreamFetchError,
)

ALLOWED_SCHEMES = {"http", "https"}
DEFAULT_PORT_FOR_SCHEME = {"http": 80, "https": 443}
# Only the standard ports are allowed. Anything else needs a deliberate,
# separately-configured allowlist - there is no such config today, so no
# other port is accepted.
ALLOWED_PORTS = {80, 443}
MAX_REDIRECTS = 3
MAX_RESPONSE_BYTES = 3 * 1024 * 1024  # 3 MB, enforced on the DECOMPRESSED stream
MAX_IMAGE_BYTES = 5 * 1024 * 1024  # 5 MB
TIMEOUT_SECONDS = 10.0
ALLOWED_CONTENT_TYPE_PREFIXES = ("text/html", "application/xhtml+xml")
# SVG is deliberately excluded even though browsers treat it as an "image" -
# it can carry <script>/event-handler content. HTML is excluded outright:
# an image URL that actually serves an HTML error page must never be saved.
ALLOWED_IMAGE_CONTENT_TYPES = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
}
USER_AGENT = "MealPlannerRecipeImporter/1.0 (+https://github.com/maciak-dev/meal-planner)"


@dataclass
class FetchedPage:
    url: str
    html: str
    content_type: str


@dataclass
class FetchedImage:
    content: bytes
    content_type: str
    extension: str


def _is_blocked_ip(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    return (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    )


def _validate_url(url: str) -> tuple[str, str, int, str, str, str]:
    """Walidacja składniowa: schemat, brak userinfo, host obowiązkowy, jawna
    polityka portów. Zwraca (scheme, hostname, port, path, query, fragment).
    """
    parts = urlsplit(url)

    if parts.scheme not in ALLOWED_SCHEMES:
        raise InvalidUrlError(f"Unsupported URL scheme: {parts.scheme or '(none)'}")

    # Userinfo (https://user:pass@host or https://host@otherhost) is rejected
    # outright - never reinterpreted, never used to guess "the real" target.
    if parts.username is not None or parts.password is not None:
        raise InvalidUrlError("URLs with embedded credentials (userinfo) are not allowed")

    if not parts.hostname:
        raise InvalidUrlError("URL is missing a host")

    default_port = DEFAULT_PORT_FOR_SCHEME[parts.scheme]
    port = parts.port if parts.port is not None else default_port
    if port not in ALLOWED_PORTS:
        raise InvalidUrlError(f"Port {port} is not allowed (only 80/443 are permitted)")

    return parts.scheme, parts.hostname, port, (parts.path or "/"), parts.query, parts.fragment


def _resolve_and_validate(hostname: str) -> str:
    """Rozwiązuje hostname i sprawdza KAŻDY zwrócony adres (obrona przed
    hostami z mieszanymi rekordami A: jeden publiczny + jeden prywatny musi
    nadal zostać zablokowany). Zwraca jeden zwalidowany adres IP, do którego
    zostanie PRZYPIĘTE faktyczne połączenie TCP - nie ufamy samemu hostname'owi
    ponownie przy connect().
    """
    try:
        addr_infos = socket.getaddrinfo(hostname, None)
    except socket.gaierror as e:
        raise BlockedHostError(f"Could not resolve host: {hostname}") from e

    if not addr_infos:
        raise BlockedHostError(f"Could not resolve host: {hostname}")

    validated_ips: list[str] = []
    for _family, _type, _proto, _canon, sockaddr in addr_infos:
        ip_str = sockaddr[0]
        ip = ipaddress.ip_address(ip_str)
        if _is_blocked_ip(ip):
            raise BlockedHostError(f"Host resolves to a blocked address: {hostname} -> {ip_str}")
        validated_ips.append(ip_str)

    return validated_ips[0]


def _build_pinned_url(scheme: str, resolved_ip: str, port: int, path: str, query: str, fragment: str) -> str:
    """Zamienia hostname w URL na zwalidowany, dosłowny adres IP - to jest
    faktyczny target połączenia TCP (bez ponownej rezolucji DNS przez httpx).
    """
    ip_obj = ipaddress.ip_address(resolved_ip)
    host_literal = f"[{resolved_ip}]" if ip_obj.version == 6 else resolved_ip
    netloc = f"{host_literal}:{port}"
    return urlunsplit((scheme, netloc, path, query, fragment))


async def fetch_html(url: str) -> FetchedPage:
    """Bezpiecznie pobiera stronę HTML pod importowanym URL-em.

    Na każdą próbę (włącznie z każdym przekierowaniem): walidacja składniowa
    (schemat/userinfo/port) -> rezolucja + walidacja KAŻDEGO adresu IP ->
    połączenie PINOWANE do zwalidowanego adresu (Host i SNI zostają oryginalne,
    więc TLS wciąż weryfikuje właściwy certyfikat) -> limity rozmiaru/timeout/
    Content-Type. Przypięcie połączenia do zwalidowanego IP (przez
    `sni_hostname` extension httpx/httpcore + dosłowny IP w URL + jawny nagłówek
    Host) domyka DNS rebinding - httpx nie wykonuje żadnej własnej rezolucji
    DNS na już-dosłownym adresie IP, więc adres nie może się zmienić między
    walidacją a faktycznym connect(). Nigdy nie wykonuje JS strony (httpx tylko
    pobiera bajty, nie renderuje).
    """
    current_url = url
    redirects_followed = 0

    async with httpx.AsyncClient(follow_redirects=False, timeout=TIMEOUT_SECONDS) as client:
        while True:
            scheme, hostname, port, path, query, fragment = _validate_url(current_url)
            resolved_ip = _resolve_and_validate(hostname)
            pinned_url = _build_pinned_url(scheme, resolved_ip, port, path, query, fragment)

            headers = {
                "Host": hostname,
                "User-Agent": USER_AGENT,
                "Accept": "text/html,application/xhtml+xml",
            }
            extensions = {"sni_hostname": hostname} if scheme == "https" else {}

            try:
                async with client.stream("GET", pinned_url, headers=headers, extensions=extensions) as response:
                    if response.status_code in (301, 302, 303, 307, 308):
                        location = response.headers.get("location")
                        if not location:
                            raise UpstreamFetchError(f"Redirect without Location header from {current_url}")

                        redirects_followed += 1
                        if redirects_followed > MAX_REDIRECTS:
                            raise TooManyRedirectsError(f"Too many redirects while fetching {url}")

                        # Resolve the redirect against the ORIGINAL (hostname-based)
                        # URL, not the IP-pinned one, so relative Location headers
                        # and the next loop iteration's validation see a normal URL.
                        origin_url = urlunsplit((scheme, f"{hostname}:{port}", path, query, fragment))
                        current_url = str(httpx.URL(origin_url).join(location))
                        continue

                    if response.status_code != 200:
                        raise UpstreamFetchError(f"Upstream returned HTTP {response.status_code} for {current_url}")

                    content_type = response.headers.get("content-type", "")
                    if not any(content_type.lower().startswith(p) for p in ALLOWED_CONTENT_TYPE_PREFIXES):
                        raise UnsupportedContentTypeError(f"Unsupported Content-Type: {content_type or '(none)'}")

                    content_length = response.headers.get("content-length")
                    if content_length is not None and int(content_length) > MAX_RESPONSE_BYTES:
                        raise ResponseTooLargeError(
                            f"Response too large ({content_length} bytes, limit {MAX_RESPONSE_BYTES})"
                        )

                    # aiter_bytes() yields already-decompressed bytes (httpx
                    # decodes gzip/deflate/br transparently) - this cap is
                    # therefore enforced on the DECOMPRESSED size, which is
                    # what guards against a "gzip bomb" (small Content-Length,
                    # huge decoded payload): the loop aborts as soon as the
                    # decoded total crosses the limit, regardless of what the
                    # compressed Content-Length claimed.
                    chunks: list[bytes] = []
                    total = 0
                    async for chunk in response.aiter_bytes():
                        total += len(chunk)
                        if total > MAX_RESPONSE_BYTES:
                            raise ResponseTooLargeError(
                                f"Response exceeded {MAX_RESPONSE_BYTES} bytes while streaming"
                            )
                        chunks.append(chunk)

                    html = b"".join(chunks).decode(response.encoding or "utf-8", errors="replace")
                    return FetchedPage(url=current_url, html=html, content_type=content_type)

            except httpx.TimeoutException as e:
                raise FetchTimeoutError(f"Timed out fetching {current_url}") from e
            except httpx.RequestError as e:
                raise UpstreamFetchError(f"Failed to fetch {current_url}: {e}") from e


def _sniff_image_type(data: bytes) -> str | None:
    """Magic-byte check on the actual body - never trust a declared
    Content-Type alone. Catches a server that mislabels an HTML error page
    (or anything else) as image/jpeg."""
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if len(data) >= 12 and data[0:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return None


async def fetch_image(url: str) -> FetchedImage:
    """Bezpiecznie pobiera obraz przepisu PO zatwierdzeniu importu przez
    użytkownika. Ten sam SSRF guard co fetch_html (walidacja URL, pinowanie
    IP, limit przekierowań/timeout), inny whitelist Content-Type (tylko
    JPEG/PNG/WebP - świadomie bez SVG, może nosić aktywną zawartość) i inny
    limit rozmiaru. Treść jest dodatkowo sprawdzana po magic bytes, żeby
    złapać serwer, który zwraca coś innego niż deklaruje w Content-Type
    (np. stronę błędu HTML podpisaną jako image/jpeg).
    """
    current_url = url
    redirects_followed = 0

    async with httpx.AsyncClient(follow_redirects=False, timeout=TIMEOUT_SECONDS) as client:
        while True:
            scheme, hostname, port, path, query, fragment = _validate_url(current_url)
            resolved_ip = _resolve_and_validate(hostname)
            pinned_url = _build_pinned_url(scheme, resolved_ip, port, path, query, fragment)

            headers = {
                "Host": hostname,
                "User-Agent": USER_AGENT,
                "Accept": "image/jpeg,image/png,image/webp",
            }
            extensions = {"sni_hostname": hostname} if scheme == "https" else {}

            try:
                async with client.stream("GET", pinned_url, headers=headers, extensions=extensions) as response:
                    if response.status_code in (301, 302, 303, 307, 308):
                        location = response.headers.get("location")
                        if not location:
                            raise UpstreamFetchError(f"Redirect without Location header from {current_url}")

                        redirects_followed += 1
                        if redirects_followed > MAX_REDIRECTS:
                            raise TooManyRedirectsError(f"Too many redirects while fetching {url}")

                        origin_url = urlunsplit((scheme, f"{hostname}:{port}", path, query, fragment))
                        current_url = str(httpx.URL(origin_url).join(location))
                        continue

                    if response.status_code != 200:
                        raise UpstreamFetchError(f"Upstream returned HTTP {response.status_code} for {current_url}")

                    content_type = response.headers.get("content-type", "").split(";")[0].strip().lower()
                    if content_type not in ALLOWED_IMAGE_CONTENT_TYPES:
                        raise UnsupportedContentTypeError(f"Unsupported image Content-Type: {content_type or '(none)'}")

                    content_length = response.headers.get("content-length")
                    if content_length is not None and int(content_length) > MAX_IMAGE_BYTES:
                        raise ResponseTooLargeError(
                            f"Image too large ({content_length} bytes, limit {MAX_IMAGE_BYTES})"
                        )

                    chunks: list[bytes] = []
                    total = 0
                    async for chunk in response.aiter_bytes():
                        total += len(chunk)
                        if total > MAX_IMAGE_BYTES:
                            raise ResponseTooLargeError(f"Image exceeded {MAX_IMAGE_BYTES} bytes while streaming")
                        chunks.append(chunk)

                    data = b"".join(chunks)
                    sniffed = _sniff_image_type(data)
                    if sniffed is None or sniffed != content_type:
                        raise UnsupportedContentTypeError(
                            "Response body does not match the declared image Content-Type"
                        )

                    return FetchedImage(
                        content=data,
                        content_type=content_type,
                        extension=ALLOWED_IMAGE_CONTENT_TYPES[content_type],
                    )

            except httpx.TimeoutException as e:
                raise FetchTimeoutError(f"Timed out fetching image {current_url}") from e
            except httpx.RequestError as e:
                raise UpstreamFetchError(f"Failed to fetch image {current_url}: {e}") from e
