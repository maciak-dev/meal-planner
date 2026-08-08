"""Tłumaczenia interfejsu użytkownika.

Zakres: **wyłącznie interfejs** — etykiety, przyciski, komunikaty. Treść
przepisów (nazwa, opis, składniki, instrukcje) zostaje w języku, w którym
została zapisana, i ten moduł jej nie dotyka. Schemat bazy ma tabelę
`recipe_translations` przygotowaną pod dwujęzyczność treści, ale jej
uruchomienie to osobna decyzja produktowa — patrz docs/modules/i18n.md.
"""
import json
from functools import lru_cache
from pathlib import Path

from fastapi import Request

SUPPORTED_LANGUAGES = ("pl", "en")
DEFAULT_LANGUAGE = "pl"
LANG_COOKIE_NAME = "lang"

_I18N_DIR = Path(__file__).resolve().parent.parent / "i18n"


@lru_cache(maxsize=None)
def load_translations() -> dict[str, dict[str, str]]:
    """Wczytuje słowniki raz na proces.

    Cache oznacza, że zmiana pliku JSON wymaga restartu aplikacji. To świadomy
    wybór: słowniki zmieniają się przy wdrożeniu, a nie w trakcie działania,
    więc czytanie ich z dysku przy każdym żądaniu byłoby kosztem bez powodu.
    """
    catalogs: dict[str, dict[str, str]] = {}
    for lang in SUPPORTED_LANGUAGES:
        path = _I18N_DIR / f"{lang}.json"
        with path.open("r", encoding="utf-8") as f:
            catalogs[lang] = json.load(f)
    return catalogs


def t(key: str, lang: str, **kwargs) -> str:
    """Tłumaczy klucz z fallbackiem: `lang` → `pl` → sam klucz.

    Brakujący klucz **nigdy nie wywala żądania** — w najgorszym razie użytkownik
    zobaczy surowy klucz. Widoczny klucz jest brzydki, ale jest to defekt
    kosmetyczny; wyjątek w środku renderowania szablonu byłby błędem 500 na
    stronie, która poza tym działa.

    Interpolacja `{name}` też jest fail-safe: brakujący albo nadmiarowy
    parametr zwraca tekst nieprzetworzony zamiast rzucać.
    """
    catalogs = load_translations()

    text = catalogs.get(lang, {}).get(key)
    if text is None:
        text = catalogs.get(DEFAULT_LANGUAGE, {}).get(key)
    if text is None:
        text = key

    if kwargs:
        try:
            text = text.format(**kwargs)
        except (KeyError, IndexError, ValueError):
            pass
    return text


def js_translations(lang: str) -> dict[str, str]:
    """Słownik do wstrzyknięcia jako `window.I18N`.

    Front i backend korzystają z tego samego pliku źródłowego, więc string
    istnieje w repozytorium dokładnie raz, niezależnie od tego, czy renderuje
    go Jinja czy JavaScript.
    """
    catalogs = load_translations()
    return catalogs.get(lang, catalogs[DEFAULT_LANGUAGE])


def resolve_language(request: Request, user=None) -> str:
    """Priorytet: cookie `lang` → `User.language` → `Accept-Language` → `pl`.

    Cookie jest pierwsze celowo: to ostatni jawny wybór użytkownika i działa
    również dla osoby niezalogowanej (ekran logowania). `User.language` niesie
    ten wybór między urządzeniami i przeglądarkami po zalogowaniu.
    `Accept-Language` jest tylko zgadywaniem pierwszego wrażenia.
    """
    cookie_lang = request.cookies.get(LANG_COOKIE_NAME)
    if cookie_lang in SUPPORTED_LANGUAGES:
        return cookie_lang

    user_lang = getattr(user, "language", None)
    if user_lang in SUPPORTED_LANGUAGES:
        return user_lang

    accept_language = request.headers.get("accept-language", "")
    for part in accept_language.split(","):
        code = part.split(";")[0].strip().lower()[:2]
        if code in SUPPORTED_LANGUAGES:
            return code

    return DEFAULT_LANGUAGE
