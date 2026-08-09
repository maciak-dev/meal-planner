from pydantic import BaseModel


class RecipeImportDraft(BaseModel):
    """Wynik importu przepisu z URL, zanim użytkownik go zatwierdzi.

    Nic w tym module nie zapisuje się do bazy - to czysty, ubijalny w JSON
    obiekt, który wraca do klienta z /recipe-import/preview i przychodzi
    z powrotem (po korektach użytkownika) do /recipe-import/confirm.
    """

    title: str | None = None
    description: str | None = None
    language: str | None = None

    ingredients: list[str] = []
    instructions: str | None = None

    servings: str | None = None
    prep_time_minutes: int | None = None
    cook_time_minutes: int | None = None
    total_time_minutes: int | None = None

    categories: list[str] = []
    image_url: str | None = None
    author: str | None = None

    source_url: str
    source_name: str | None = None

    # True gdy nie znaleziono danych schema.org/Recipe i draft pochodzi
    # tylko z ograniczonego fallbacku HTML (<h1>, meta og:*).
    used_fallback_parser: bool = False
