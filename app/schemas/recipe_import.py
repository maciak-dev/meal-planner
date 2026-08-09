from pydantic import BaseModel, Field, field_validator

from app.core.i18n import SUPPORTED_LANGUAGES
from app.schemas.recipe import RecipeRead

MAX_URL_LENGTH = 2000
MAX_TITLE_LENGTH = 300
MAX_DESCRIPTION_LENGTH = 5000
MAX_INSTRUCTIONS_LENGTH = 20000
MAX_SHORT_FIELD_LENGTH = 300
MAX_INGREDIENT_TEXT_LENGTH = 500
MAX_INGREDIENTS = 200


class RecipeImportPreviewRequest(BaseModel):
    url: str = Field(min_length=1, max_length=MAX_URL_LENGTH)


class ImportedIngredientOut(BaseModel):
    """Jedna linia składnika w draftcie zwracanym przez /preview."""

    original_text: str
    quantity: float | None = None
    unit: str | None = None
    name: str
    note: str | None = None
    confidence: float
    requires_review: bool


class RecipeImportPreviewResponse(BaseModel):
    source_url: str
    source_name: str | None = None
    source_author: str | None = None
    language: str | None = None
    name: str | None = None
    description: str | None = None
    instructions: str | None = None
    servings: str | None = None
    prep_time: int | None = None
    cook_time: int | None = None
    total_time: int | None = None
    image_url: str | None = None
    ingredients: list[ImportedIngredientOut] = []
    warnings: list[str] = []


class ImportedIngredientIn(BaseModel):
    """Jedna linia składnika tak, jak wraca z klienta po korekcie użytkownika."""

    original_text: str = Field(min_length=1, max_length=MAX_INGREDIENT_TEXT_LENGTH)
    quantity: float | None = Field(default=None, ge=0)
    unit: str | None = Field(default=None, max_length=50)
    name: str = Field(min_length=1, max_length=MAX_INGREDIENT_TEXT_LENGTH)
    note: str | None = Field(default=None, max_length=MAX_INGREDIENT_TEXT_LENGTH)
    confidence: float | None = Field(default=None, ge=0, le=1)
    requires_review: bool = False


class RecipeImportConfirmRequest(BaseModel):
    """Wyłącznie dane zatwierdzone przez użytkownika - confirm nigdy nie
    pobiera strony ponownie (poza opcjonalnym zdjęciem, patrz download_image)
    i nigdy nie zapisuje niczego, co nie przyszło w tym payloadzie.
    """

    source_url: str = Field(min_length=1, max_length=MAX_URL_LENGTH)
    source_name: str | None = Field(default=None, max_length=MAX_SHORT_FIELD_LENGTH)
    source_author: str | None = Field(default=None, max_length=MAX_SHORT_FIELD_LENGTH)
    language: str = "pl"

    name: str = Field(min_length=1, max_length=MAX_TITLE_LENGTH)
    description: str | None = Field(default=None, max_length=MAX_DESCRIPTION_LENGTH)
    instructions: str | None = Field(default=None, max_length=MAX_INSTRUCTIONS_LENGTH)
    servings: str | None = Field(default=None, max_length=MAX_SHORT_FIELD_LENGTH)
    prep_time: int | None = Field(default=None, ge=0, le=100_000)
    cook_time: int | None = Field(default=None, ge=0, le=100_000)
    total_time: int | None = Field(default=None, ge=0, le=100_000)

    image_url: str | None = Field(default=None, max_length=MAX_URL_LENGTH)
    download_image: bool = False

    ingredients: list[ImportedIngredientIn] = Field(default_factory=list, max_length=MAX_INGREDIENTS)
    save_structured_ingredients: bool = False

    @field_validator("language")
    @classmethod
    def _language_must_be_supported(cls, value: str) -> str:
        if value not in SUPPORTED_LANGUAGES:
            raise ValueError(f"Unsupported language: {value!r}")
        return value

    @field_validator("source_url", "image_url")
    @classmethod
    def _url_must_look_like_http_url(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not (value.startswith("http://") or value.startswith("https://")):
            raise ValueError("Only http/https URLs are allowed")
        return value

    @field_validator("name")
    @classmethod
    def _name_must_not_be_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Recipe title cannot be blank")
        return stripped


class RecipeImportConfirmResponse(BaseModel):
    recipe: RecipeRead
    warnings: list[str] = []
