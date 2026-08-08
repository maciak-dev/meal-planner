from urllib.parse import urlsplit


DEFAULT_RETURN_PATH = "/recipes-ui"


def safe_local_return_path(
    referer: str | None,
    allowed_netloc: str | None = None,
    default: str = DEFAULT_RETURN_PATH,
) -> str:
    """Zwraca wyłącznie ścieżkę same-origin (plus query) z nagłówka Referer.

    Używane przy przełączaniu języka: po zmianie wracamy tam, skąd użytkownik
    przyszedł. Referer jest sterowany przez klienta, więc bez tej walidacji
    `/set-lang` stałby się otwartym przekierowaniem — wystarczyłoby podać
    `Referer: https://obcy.example`, żeby wysłać tam użytkownika.

    Odrzucane: obcy `netloc`, schemat bez netloc (`javascript:`), ścieżka nie
    zaczynająca się od `/`, protocol-relative `//evil.example` oraz backslash
    (część przeglądarek traktuje go jak `/`).
    """
    if not referer:
        return default

    parsed = urlsplit(referer)
    if parsed.netloc and parsed.netloc != allowed_netloc:
        return default
    if parsed.scheme and not parsed.netloc:
        return default
    if not parsed.path.startswith("/") or parsed.path.startswith("//") or "\\" in parsed.path:
        return default

    return parsed.path + (f"?{parsed.query}" if parsed.query else "")
