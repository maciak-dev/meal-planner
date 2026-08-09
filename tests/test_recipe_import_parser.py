import unittest
from pathlib import Path

from app.services.recipe_import.parser import parse_page
from app.services.recipe_import.schema_org import extract_schema_org_recipe

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures" / "recipe_import"


def load_fixture(name: str) -> str:
    return (FIXTURES_DIR / name).read_text(encoding="utf-8")


class SchemaOrgExtractionTests(unittest.TestCase):
    def test_extracts_recipe_from_single_ld_json_block(self) -> None:
        html = load_fixture("schema_org_recipe.html")
        recipe = extract_schema_org_recipe(html)
        self.assertIsNotNone(recipe)
        self.assertEqual(recipe["name"], "Naleśniki")

    def test_returns_none_when_no_recipe_present(self) -> None:
        html = load_fixture("no_recipe.html")
        self.assertIsNone(extract_schema_org_recipe(html))

    def test_skips_invalid_json_block_and_finds_recipe_in_a_later_block(self) -> None:
        html = load_fixture("multiple_ld_json.html")
        recipe = extract_schema_org_recipe(html)
        self.assertIsNotNone(recipe)
        self.assertEqual(recipe["name"], "Zupa jarzynowa")

    def test_finds_recipe_nested_inside_at_graph(self) -> None:
        html = load_fixture("graph_recipe.html")
        recipe = extract_schema_org_recipe(html)
        self.assertIsNotNone(recipe)
        self.assertEqual(recipe["name"], "Graph Recipe")


class ParsePageTests(unittest.TestCase):
    def test_full_schema_org_recipe_is_normalized_completely(self) -> None:
        html = load_fixture("schema_org_recipe.html")
        draft = parse_page(html, "https://blog.example.com/nalesniki")

        self.assertFalse(draft.used_fallback_parser)
        self.assertEqual(draft.title, "Naleśniki")
        self.assertEqual(draft.description, "Proste naleśniki na słodko")
        self.assertEqual(draft.language, "pl")
        self.assertEqual(draft.ingredients, ["2 jajka", "1 szklanka mleka", "200 g mąki"])
        self.assertIn("Wymieszaj składniki", draft.instructions)
        self.assertIn("Usmaż na patelni", draft.instructions)
        self.assertEqual(draft.prep_time_minutes, 10)
        self.assertEqual(draft.cook_time_minutes, 20)
        self.assertEqual(draft.total_time_minutes, 30)
        self.assertEqual(draft.servings, "4 porcje")
        self.assertEqual(draft.image_url, "https://example.com/img/nalesniki.jpg")
        self.assertEqual(draft.author, "Jan Kowalski")
        self.assertEqual(draft.source_url, "https://blog.example.com/nalesniki")
        self.assertEqual(draft.source_name, "blog.example.com")

    def test_page_without_recipe_falls_back_to_limited_html_parsing(self) -> None:
        html = load_fixture("no_recipe.html")
        draft = parse_page(html, "https://example.com/post")

        self.assertTrue(draft.used_fallback_parser)
        self.assertEqual(draft.title, "Ten wpis nie jest przepisem")
        self.assertEqual(draft.description, "A post about something unrelated to cooking")
        self.assertEqual(draft.image_url, "https://example.com/img/post.jpg")
        self.assertEqual(draft.ingredients, [])
        self.assertIsNone(draft.instructions)

    def test_instructions_as_plain_string_with_newlines(self) -> None:
        html = load_fixture("multiple_ld_json.html")
        draft = parse_page(html, "https://example.com/zupa")

        self.assertEqual(draft.title, "Zupa jarzynowa")
        self.assertEqual(draft.ingredients, ["woda", "warzywa", "sol do smaku"])
        self.assertIn("Ugotuj warzywa", draft.instructions)
        self.assertIn("Dopraw solą", draft.instructions)

    def test_recipe_nested_in_at_graph_is_normalized(self) -> None:
        html = load_fixture("graph_recipe.html")
        draft = parse_page(html, "https://example.com/graph-recipe")

        self.assertFalse(draft.used_fallback_parser)
        self.assertEqual(draft.title, "Graph Recipe")
        self.assertEqual(draft.ingredients, ["1 cup flour", "2 eggs"])
        self.assertEqual(draft.instructions, "Mix and bake.")


if __name__ == "__main__":
    unittest.main()
