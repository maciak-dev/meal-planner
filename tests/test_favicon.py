from pathlib import Path
from xml.etree import ElementTree


ROOT = Path(__file__).resolve().parents[1]
FAVICON_HREF = "/static/meal-favicon-dark.svg"
TEMPLATES = ("login.html", "recipes.html", "admin_panel.html")


def test_meal_templates_use_the_accepted_domain_favicon():
    for template_name in TEMPLATES:
        template = (ROOT / "app" / "templates" / template_name).read_text(
            encoding="utf-8"
        )
        assert template.count(FAVICON_HREF) == 1


def test_meal_favicon_is_valid_svg():
    favicon = ROOT / "app" / "static" / Path(FAVICON_HREF).name
    root = ElementTree.parse(favicon).getroot()

    assert root.tag == "{http://www.w3.org/2000/svg}svg"
    assert root.attrib["viewBox"] == "0 0 512 512"
