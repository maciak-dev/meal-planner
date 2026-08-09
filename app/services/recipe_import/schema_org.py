import json

from bs4 import BeautifulSoup


def _type_matches_recipe(node: dict) -> bool:
    node_type = node.get("@type")
    if isinstance(node_type, str):
        return "Recipe" in node_type
    if isinstance(node_type, list):
        return any("Recipe" in str(t) for t in node_type)
    return False


def _walk_for_recipe(data) -> dict | None:
    """Przechodzi dowolnie zagnieżdżoną strukturę JSON-LD (dict/list, w tym
    @graph) i zwraca pierwszy węzeł, którego @type zawiera "Recipe"."""
    if isinstance(data, dict):
        if _type_matches_recipe(data):
            return data
        if "@graph" in data:
            found = _walk_for_recipe(data["@graph"])
            if found is not None:
                return found
        return None

    if isinstance(data, list):
        for item in data:
            found = _walk_for_recipe(item)
            if found is not None:
                return found
        return None

    return None


def extract_schema_org_recipe(html: str) -> dict | None:
    """Szuka application/ld+json blokow ze schema.org/Recipe.

    Strona może mieć kilka bloków JSON-LD (dla różnych typów: Organization,
    BreadcrumbList, Recipe...) - sprawdzamy każdy, tolerancyjnie na błędny JSON
    w pojedynczym bloku (jeden zepsuty blok nie blokuje odczytu innych).
    """
    soup = BeautifulSoup(html, "html.parser")

    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        raw = script.string or script.get_text()
        if not raw or not raw.strip():
            continue

        try:
            data = json.loads(raw)
        except (json.JSONDecodeError, ValueError):
            continue

        recipe = _walk_for_recipe(data)
        if recipe is not None:
            return recipe

    return None
