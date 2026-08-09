from urllib.parse import urlsplit

from bs4 import BeautifulSoup

from app.services.recipe_import.models import RecipeImportDraft
from app.services.recipe_import.normalizer import normalize_fallback_html, normalize_schema_org_recipe
from app.services.recipe_import.schema_org import extract_schema_org_recipe


def _source_name_from_url(url: str) -> str:
    return urlsplit(url).hostname or url


def _fallback_html_parse(html: str) -> dict:
    """Bardzo ograniczona analiza HTML gdy nie ma danych schema.org/Recipe:
    tytuł z <h1> (albo <title>), opis i zdjęcie z meta og:*. Nie próbujemy
    zgadywać składników/instrukcji z gołego HTML - zbyt niepewne bez struktury.
    """
    soup = BeautifulSoup(html, "html.parser")

    h1 = soup.find("h1")
    title = h1.get_text(strip=True) if h1 else None
    if not title and soup.title:
        title = soup.title.get_text(strip=True)

    def meta_content(prop: str) -> str | None:
        tag = soup.find("meta", attrs={"property": prop}) or soup.find("meta", attrs={"name": prop})
        return tag.get("content", "").strip() if tag and tag.get("content") else None

    return {
        "title": title,
        "description": meta_content("og:description") or meta_content("description"),
        "image_url": meta_content("og:image"),
    }


def parse_page(html: str, source_url: str) -> RecipeImportDraft:
    """Kolejność ekstrakcji: schema.org/Recipe (JSON-LD) -> fallback HTML.
    Nigdy nie zakłada kompletnych danych - brakujące pola zostają None/[],
    użytkownik uzupełnia je w formularzu podglądu przed zapisem.
    """
    source_name = _source_name_from_url(source_url)

    schema_recipe = extract_schema_org_recipe(html)
    if schema_recipe is not None:
        return normalize_schema_org_recipe(schema_recipe, source_url, source_name)

    fallback = _fallback_html_parse(html)
    return normalize_fallback_html(fallback, source_url, source_name)
