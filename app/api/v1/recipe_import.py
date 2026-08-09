from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.i18n import resolve_language
from app.core.security import get_current_user
from app.schemas.recipe_import import (
    ImportedIngredientOut,
    RecipeImportConfirmRequest,
    RecipeImportConfirmResponse,
    RecipeImportPreviewRequest,
    RecipeImportPreviewResponse,
)
from app.services import recipe_service
from app.services.ingredient_parsing.parser import parse_ingredient_line
from app.services.recipe_import import parser as recipe_parser
from app.services.recipe_import.errors import (
    BlockedHostError,
    FetchTimeoutError,
    InvalidUrlError,
    NoRecipeFoundError,
    RecipeImportError,
    ResponseTooLargeError,
    TooManyRedirectsError,
    UnsupportedContentTypeError,
    UpstreamFetchError,
)
from app.services.recipe_import.fetcher import fetch_html
from app.services.recipe_import.image_storage import delete_stored_image, download_and_store_image

router = APIRouter()

# Ordered most-specific-first: RecipeImportError subclasses are checked with
# isinstance, so a subclass listed after its parent would never be reached.
_ERROR_CODES: list[tuple[type[RecipeImportError], str]] = [
    (InvalidUrlError, "invalid_url"),
    (BlockedHostError, "blocked_host"),
    (TooManyRedirectsError, "too_many_redirects"),
    (FetchTimeoutError, "timeout"),
    (ResponseTooLargeError, "too_large"),
    (UnsupportedContentTypeError, "unsupported_content_type"),
    (NoRecipeFoundError, "no_recipe_found"),
    (UpstreamFetchError, "upstream_error"),
]


def _error_code_for(exc: RecipeImportError) -> str:
    for exc_type, code in _ERROR_CODES:
        if isinstance(exc, exc_type):
            return code
    return "import_failed"


def _raise_as_http_error(exc: RecipeImportError) -> None:
    """Konwertuje błąd importu na HTTPException z kodem błędu, ale BEZ treści
    wyjątku (która może zawierać rozwiązany adres IP / szczegóły hosta -
    "czytelne, nieprzeciekające błędy"). Pełny szczegół zostaje tylko w
    logach serwera przez oryginalny wyjątek (widoczny w tracebacku FastAPI
    w trybie dev; w prod niezalogowany tu świadomie, żeby nie rozdymać
    zakresu tej zmiany o nowy logger).
    """
    raise HTTPException(status_code=400, detail={"error_code": _error_code_for(exc)}) from exc


@router.post("/preview", response_model=RecipeImportPreviewResponse)
async def preview_recipe_import(
    payload: RecipeImportPreviewRequest,
    user=Depends(get_current_user),
):
    """Pobiera i parsuje przepis pod danym URL. Nic nie zapisuje do bazy."""
    try:
        page = await fetch_html(payload.url)
    except RecipeImportError as e:
        _raise_as_http_error(e)

    draft = recipe_parser.parse_page(page.html, page.url)
    parsed_ingredients = [parse_ingredient_line(line) for line in draft.ingredients]

    warnings: list[str] = []
    if draft.used_fallback_parser:
        warnings.append("no_structured_recipe_data")
    if not draft.ingredients:
        warnings.append("no_ingredients_found")
    if not draft.instructions:
        warnings.append("no_instructions_found")
    if not draft.image_url:
        warnings.append("no_image_found")
    if any(p.needs_review for p in parsed_ingredients):
        warnings.append("some_ingredients_need_review")

    return RecipeImportPreviewResponse(
        source_url=draft.source_url,
        source_name=draft.source_name,
        source_author=draft.author,
        language=draft.language,
        name=draft.title,
        description=draft.description,
        instructions=draft.instructions,
        servings=draft.servings,
        prep_time=draft.prep_time_minutes,
        cook_time=draft.cook_time_minutes,
        total_time=draft.total_time_minutes,
        image_url=draft.image_url,
        ingredients=[
            ImportedIngredientOut(
                original_text=p.original_text,
                quantity=p.quantity,
                unit=p.unit,
                name=p.name,
                note=p.note,
                confidence=p.confidence,
                requires_review=p.needs_review,
            )
            for p in parsed_ingredients
        ],
        warnings=warnings,
    )


@router.post("/confirm", response_model=RecipeImportConfirmResponse)
async def confirm_recipe_import(
    payload: RecipeImportConfirmRequest,
    request: Request,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Zapisuje wyłącznie dane zatwierdzone przez użytkownika. Nigdy nie
    pobiera strony ponownie - jedyny opcjonalny network call tutaj jest do
    zdjęcia, i tylko jeśli payload.download_image=True.
    """
    lang = resolve_language(request, user)

    existing = recipe_service.find_recent_import(db, user.id, payload.source_url)
    if existing is not None:
        return RecipeImportConfirmResponse(
            recipe=recipe_service.to_recipe_read(
                db, existing, lang, is_owner=True, author_username=user.username
            ),
            warnings=["duplicate_import_returned_existing"],
        )

    warnings: list[str] = []
    image_path: str | None = None
    if payload.download_image and payload.image_url:
        try:
            image_path = await download_and_store_image(payload.image_url)
        except RecipeImportError:
            warnings.append("image_download_failed")

    try:
        recipe = recipe_service.create_recipe_from_import(db, payload, user.id, image_path=image_path)
    except Exception:
        if image_path:
            delete_stored_image(image_path)
        raise

    return RecipeImportConfirmResponse(
        recipe=recipe_service.to_recipe_read(db, recipe, lang, is_owner=True, author_username=user.username),
        warnings=warnings,
    )
