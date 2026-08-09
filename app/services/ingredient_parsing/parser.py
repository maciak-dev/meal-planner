import re

from app.services.ingredient_parsing.models import ParsedIngredientLine

NEEDS_REVIEW_THRESHOLD = 0.75

_UNICODE_FRACTIONS = {
    "½": 0.5, "¼": 0.25, "¾": 0.75,
    "⅓": 1 / 3, "⅔": 2 / 3,
    "⅕": 0.2, "⅖": 0.4, "⅗": 0.6, "⅘": 0.8,
    "⅙": 1 / 6, "⅚": 5 / 6,
    "⅛": 0.125, "⅜": 0.375, "⅝": 0.625, "⅞": 0.875,
}

# surface form (lowercase) -> canonical unit
_UNITS = {
    # metric, shared PL/EN spelling for abbreviations
    "g": "g", "gram": "g", "gramy": "g", "gramów": "g", "grams": "g",
    "kg": "kg", "kilogram": "kg", "kilogramy": "kg", "kilogramów": "kg", "kilograms": "kg",
    "ml": "ml", "mililitr": "ml", "mililitry": "ml", "mililitrów": "ml",
    "milliliter": "ml", "milliliters": "ml", "millilitre": "ml", "millilitres": "ml",
    "l": "l", "litr": "l", "litry": "l", "litrów": "l", "liter": "l", "liters": "l", "litre": "l", "litres": "l",
    # PL kitchen units
    "szklanka": "szklanka", "szklanki": "szklanka", "szklanek": "szklanka",
    "łyżka": "łyżka", "łyżki": "łyżka", "łyżek": "łyżka",
    "łyżeczka": "łyżeczka", "łyżeczki": "łyżeczka", "łyżeczek": "łyżeczka",
    "ząbek": "ząbek", "ząbki": "ząbek", "ząbków": "ząbek",
    "sztuka": "sztuka", "sztuki": "sztuka", "sztuk": "sztuka",
    "pęczek": "pęczek", "pęczki": "pęczek", "pęczków": "pęczek",
    "opakowanie": "opakowanie", "opakowania": "opakowanie", "opakowań": "opakowanie",
    "plaster": "plaster", "plastry": "plaster", "plastrów": "plaster",
    "szczypta": "szczypta", "szczypty": "szczypta", "szczypt": "szczypta",
    # EN kitchen units
    "cup": "cup", "cups": "cup",
    "tbsp": "tbsp", "tablespoon": "tbsp", "tablespoons": "tbsp",
    "tsp": "tsp", "teaspoon": "tsp", "teaspoons": "tsp",
    "clove": "clove", "cloves": "clove",
    "piece": "piece", "pieces": "piece",
    "slice": "slice", "slices": "slice",
    "pinch": "pinch", "pinches": "pinch",
    "can": "can", "cans": "can",
    "pack": "package", "packs": "package", "package": "package", "packages": "package",
}

# words describing quality/size, extracted into `note` rather than left in `name`
_NOTE_WORDS = {
    "duży", "duże", "duża", "dużych", "duzy", "duza",
    "mały", "małe", "mała", "małych", "maly", "mala",
    "świeży", "świeże", "świeża", "swiezy", "swieze", "swieza",
    "starty", "starta", "starte",
    "posiekany", "posiekana", "posiekane",
    "drobno",
    "large", "small", "fresh", "chopped", "diced", "minced", "grated", "ground", "ripe",
}

_TO_TASTE_RE = re.compile(r"\b(do smaku|to taste)\b", re.IGNORECASE)
_FILLER_AFTER_UNIT = {"of", "z"}

_MIXED_NUMBER_RE = re.compile(r"^(\d+)\s+(\d+)/(\d+)\s*")
_SIMPLE_FRACTION_RE = re.compile(r"^(\d+)/(\d+)\s*")
_UNICODE_FRACTION_RE = re.compile(r"^(\d+)?\s*([" + "".join(_UNICODE_FRACTIONS) + r"])\s*")
_DECIMAL_RE = re.compile(r"^(\d+[.,]\d+)\s*")
_INTEGER_RE = re.compile(r"^(\d+)\s*")


def _extract_quantity(text: str) -> tuple[float | None, str]:
    """Próbuje zdjąć ilość z początku linii. Zwraca (quantity, reszta_tekstu)."""
    m = _MIXED_NUMBER_RE.match(text)
    if m:
        whole, num, den = m.groups()
        return float(whole) + float(num) / float(den), text[m.end():]

    m = _SIMPLE_FRACTION_RE.match(text)
    if m:
        num, den = m.groups()
        return float(num) / float(den), text[m.end():]

    m = _UNICODE_FRACTION_RE.match(text)
    if m:
        whole, frac_char = m.groups()
        value = _UNICODE_FRACTIONS[frac_char]
        if whole:
            value += float(whole)
        return value, text[m.end():]

    m = _DECIMAL_RE.match(text)
    if m:
        return float(m.group(1).replace(",", ".")), text[m.end():]

    m = _INTEGER_RE.match(text)
    if m:
        return float(m.group(1)), text[m.end():]

    return None, text


def _extract_unit(text: str) -> tuple[str | None, str]:
    """Próbuje zdjąć jednostkę z początku (już bez ilości) tekstu, pomijając
    słowo-wypełniacz typu "of"/"z" po jednostce (np. "cloves of garlic")."""
    match = re.match(r"^([^\s]+)\s*", text)
    if not match:
        return None, text

    token = match.group(1).strip(".,").lower()
    canonical = _UNITS.get(token)
    if canonical is None:
        return None, text

    rest = text[match.end():]
    filler_match = re.match(r"^(\w+)\s+", rest)
    if filler_match and filler_match.group(1).lower() in _FILLER_AFTER_UNIT:
        rest = rest[filler_match.end():]

    return canonical, rest


def _extract_note(text: str) -> tuple[str | None, str]:
    """Wyszukuje pierwsze słowo opisujące jakość/rozmiar (np. "duże", "fresh")
    gdziekolwiek w tekście i wyjmuje je do `note`, żeby nie zaśmiecało `name`."""
    words = text.split()
    for i, word in enumerate(words):
        normalized = word.strip(".,").lower()
        if normalized in _NOTE_WORDS:
            remaining = words[:i] + words[i + 1:]
            return word.strip(".,"), " ".join(remaining)
    return None, text


def parse_ingredient_line(original_text: str) -> ParsedIngredientLine:
    """Rozkłada tekst linii składnika na ilość/jednostkę/nazwę/notatkę.

    Nie oczekuje stuprocentowej skuteczności (patrz Etap 5) - zawsze zwraca
    original_text w całości i confidence, żeby UI mogło pokazać, które linie
    wymagają ręcznej poprawy (needs_review).
    """
    text = original_text.strip()

    to_taste_match = _TO_TASTE_RE.search(text)
    to_taste_note = None
    if to_taste_match:
        to_taste_note = to_taste_match.group(0)
        text = _TO_TASTE_RE.sub("", text).strip()

    quantity, rest = _extract_quantity(text)
    rest = rest.strip()

    # Note words (np. "duże") są zdejmowane PRZED próbą rozpoznania jednostki,
    # bo w PL zwykle stoją między ilością a jednostką: "2 duże ząbki czosnku".
    note, rest = _extract_note(rest)
    rest = rest.strip()
    if to_taste_note:
        note = f"{note}, {to_taste_note}" if note else to_taste_note

    unit = None
    if quantity is not None:
        unit, rest = _extract_unit(rest)
        rest = rest.strip()

    name = rest.strip() or original_text.strip()

    if quantity is not None and unit is not None:
        confidence = 0.9
    elif quantity is not None and unit is None:
        confidence = 0.85
    elif to_taste_note is not None:
        confidence = 0.8
    elif quantity is None and unit is None:
        confidence = 0.5
    else:
        confidence = 0.6

    return ParsedIngredientLine(
        original_text=original_text,
        quantity=quantity,
        unit=unit,
        name=name,
        note=note,
        confidence=confidence,
        needs_review=confidence < NEEDS_REVIEW_THRESHOLD,
    )


def parse_ingredient_lines(text: str) -> list[ParsedIngredientLine]:
    """Parsuje wieloliniowy tekst składników (jeden składnik na linię)."""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return [parse_ingredient_line(line) for line in lines]
