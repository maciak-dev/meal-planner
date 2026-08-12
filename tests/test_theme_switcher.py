"""Motywy interfejsu (cyber / scandi / map).

Testy statyczne w stylu test_ui_i18n.py: czytają pliki frontendu i pilnują
kontraktu systemu motywów — jednej listy motywów, jednego klucza
localStorage i kompletu bloków w themes.css. Chronią przed regresją przy
dodawaniu kolejnego motywu (np. dopisanie motywu w JS bez bloku CSS).
"""
import re
import unittest
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent.parent / "app"
THEMES_CSS = (APP_DIR / "static" / "themes.css").read_text(encoding="utf-8")
MAIN_CSS = (APP_DIR / "static" / "main.css").read_text(encoding="utf-8")
RECIPES_JS = (APP_DIR / "static" / "recipes.js").read_text(encoding="utf-8")
RECIPES_HTML = (APP_DIR / "templates" / "recipes.html").read_text(encoding="utf-8")
LOGIN_HTML = (APP_DIR / "templates" / "login.html").read_text(encoding="utf-8")

EXPECTED_THEMES = ["theme-cyber", "theme-scandi", "theme-map"]


def js_theme_list(source: str) -> list[str]:
    match = re.search(r"THEMES\s*[:=]\s*\[([^\]]+)\]", source)
    assert match, "brak listy THEMES"
    return re.findall(r'"(theme-[\w-]+)"', match.group(1))


class ThemeContractTests(unittest.TestCase):
    def test_recipes_js_knows_all_three_themes(self) -> None:
        self.assertEqual(js_theme_list(RECIPES_JS), EXPECTED_THEMES)

    def test_login_uses_the_same_theme_list(self) -> None:
        self.assertEqual(js_theme_list(LOGIN_HTML), EXPECTED_THEMES)

    def test_persistence_key_is_unchanged(self) -> None:
        """Preferencja motywu zapisywana dokładnie tak jak przed zmianą."""
        self.assertIn('localStorage.setItem("theme", theme)', RECIPES_JS)
        self.assertIn('localStorage.setItem("theme", theme)', LOGIN_HTML)
        self.assertIn('localStorage.getItem("theme")', RECIPES_JS)
        self.assertIn('localStorage.getItem("theme")', LOGIN_HTML)

    def test_default_theme_is_cyber(self) -> None:
        self.assertRegex(RECIPES_JS, r'localStorage\.getItem\("theme"\)\s*\|\|\s*this\.THEMES\[0\]')
        self.assertEqual(js_theme_list(RECIPES_JS)[0], "theme-cyber")

    def test_css_has_a_block_for_every_switchable_theme(self) -> None:
        """cyber jest motywem bazowym (:root w main.css); scandi i map
        muszą mieć własne bloki w themes.css."""
        self.assertIn("body.theme-scandi", THEMES_CSS)
        self.assertIn("body.theme-map", THEMES_CSS)
        self.assertIn("body.theme-cyber", MAIN_CSS)

    def test_switcher_offers_every_theme(self) -> None:
        for theme in EXPECTED_THEMES:
            self.assertIn(f'data-theme-option="{theme}"', RECIPES_HTML)

    def test_map_theme_visual_foundation(self) -> None:
        """Kontrakt motywu map: tokeny prywatnego MAP, bez glow i gradientów."""
        map_block = THEMES_CSS[THEMES_CSS.index("body.theme-map") :]
        for token in ("#171614", "#1C1B18", "#3AA99F", "#E9E6DF", "#E05252"):
            self.assertIn(token, map_block)
        self.assertIn("'Space Grotesk'", map_block)
        self.assertIn("'JetBrains Mono'", map_block)
        # bez cyberowych efektów w bloku map
        self.assertNotIn("text-shadow: 0 0", map_block)
        self.assertNotIn("linear-gradient", map_block)


if __name__ == "__main__":
    unittest.main()
