import re

from app.services.recipe_import.models import RecipeImportDraft

_ISO_DURATION_RE = re.compile(
    r"^P(?:\d+D)?T?(?:(?P<hours>\d+)H)?(?:(?P<minutes>\d+)M)?(?:(?P<seconds>\d+)S)?$"
)


def _parse_iso_duration_minutes(value) -> int | None:
    """Zamienia ISO8601 duration (np. "PT1H30M") na liczbę minut. None jeśli
    format nierozpoznany - liczba porcji/czasy są opcjonalne, nie zgadujemy.
    """
    if not isinstance(value, str):
        return None

    match = _ISO_DURATION_RE.match(value.strip())
    if not match:
        return None

    hours = int(match.group("hours") or 0)
    minutes = int(match.group("minutes") or 0)
    seconds = int(match.group("seconds") or 0)

    total_minutes = hours * 60 + minutes + (1 if seconds else 0)
    return total_minutes or None


def _first_str(value) -> str | None:
    if isinstance(value, str):
        return value.strip() or None
    if isinstance(value, list) and value:
        return _first_str(value[0])
    if isinstance(value, dict):
        return _first_str(value.get("name") or value.get("url") or value.get("text"))
    return None


def _extract_ingredients(value) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        return [line.strip() for line in value.splitlines() if line.strip()]
    return []


def _extract_instructions(value) -> str | None:
    """recipeInstructions bywa: tekstem, listą kroków (str) albo listą
    HowToStep/HowToSection - zawsze spłaszczamy do jednego tekstu z krokami
    po linii, zgodnie z tym jak dziś działa Recipe.instructions (wolny tekst).
    """
    if value is None:
        return None

    if isinstance(value, str):
        return value.strip() or None

    if isinstance(value, list):
        steps: list[str] = []
        for item in value:
            if isinstance(item, str):
                text = item.strip()
            elif isinstance(item, dict):
                if item.get("@type") == "HowToSection" and "itemListElement" in item:
                    nested = _extract_instructions(item["itemListElement"])
                    if nested:
                        steps.append(nested)
                    continue
                text = str(item.get("text") or item.get("name") or "").strip()
            else:
                text = ""

            if text:
                steps.append(text)

        return "\n".join(steps) if steps else None

    return None


def _extract_image_url(value) -> str | None:
    if isinstance(value, str):
        return value.strip() or None
    if isinstance(value, list) and value:
        return _extract_image_url(value[0])
    if isinstance(value, dict):
        return _extract_image_url(value.get("url"))
    return None


def normalize_schema_org_recipe(recipe: dict, source_url: str, source_name: str | None) -> RecipeImportDraft:
    return RecipeImportDraft(
        title=_first_str(recipe.get("name")),
        description=_first_str(recipe.get("description")),
        language=_first_str(recipe.get("inLanguage")),
        ingredients=_extract_ingredients(recipe.get("recipeIngredient") or recipe.get("ingredients")),
        instructions=_extract_instructions(recipe.get("recipeInstructions")),
        servings=_first_str(recipe.get("recipeYield")),
        prep_time_minutes=_parse_iso_duration_minutes(recipe.get("prepTime")),
        cook_time_minutes=_parse_iso_duration_minutes(recipe.get("cookTime")),
        total_time_minutes=_parse_iso_duration_minutes(recipe.get("totalTime")),
        categories=_extract_ingredients(recipe.get("recipeCategory")),
        image_url=_extract_image_url(recipe.get("image")),
        author=_first_str(recipe.get("author")),
        source_url=source_url,
        source_name=source_name,
        used_fallback_parser=False,
    )


def normalize_fallback_html(fallback: dict, source_url: str, source_name: str | None) -> RecipeImportDraft:
    """Buduje draft z ograniczonego fallbacku HTML (Etap 3, krok 6) - używane
    tylko gdy strona nie ma danych schema.org/Recipe. Zawsze jawnie oznaczone
    used_fallback_parser=True, żeby UI mogło ostrzec użytkownika o niskiej pewności.
    """
    return RecipeImportDraft(
        title=fallback.get("title"),
        description=fallback.get("description"),
        image_url=fallback.get("image_url"),
        ingredients=[],
        instructions=None,
        source_url=source_url,
        source_name=source_name,
        used_fallback_parser=True,
    )
