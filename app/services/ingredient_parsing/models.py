from pydantic import BaseModel


class ParsedIngredientLine(BaseModel):
    """Wynik próby rozłożenia jednej linii składnika na ilość/jednostkę/nazwę/notatkę.

    original_text jest zawsze zachowany. confidence w [0, 1] - niska wartość
    oznacza needs_review=True, czyli że parsowanie wymaga ręcznego potwierdzenia
    (nigdy nie próbujemy być stuprocentowo skuteczni, patrz Etap 5 w specyfikacji).
    """

    original_text: str
    quantity: float | None = None
    unit: str | None = None
    name: str
    note: str | None = None
    confidence: float
    needs_review: bool
