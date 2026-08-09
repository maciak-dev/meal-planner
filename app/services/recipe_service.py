from datetime import datetime, timedelta

from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.db.models.recipe import Recipe
from app.db.models.recipe_ingredient import RecipeIngredient
from app.db.models.user import User
from app.schemas.recipe import RecipeCreate, RecipeVisibilityUpdate
from app.schemas.recipe import RecipeRead
from app.services.ingredient_parsing.parser import NEEDS_REVIEW_THRESHOLD
from app.services.permissions_service import require_owner_or_admin

DUPLICATE_IMPORT_WINDOW_SECONDS = 120


def to_recipe_read(db: Session, recipe: Recipe, language: str, **extra) -> RecipeRead:
    """Build the regular legacy recipe response without translating content."""
    return RecipeRead(**{**recipe.__dict__, **extra})


# =========================
# CREATE
# =========================

def create_recipe(db: Session, data: RecipeCreate, user_id: int) -> Recipe:
    """Tworzy nowy przepis przypisany do użytkownika."""
    recipe = Recipe(
        name=data.name,
        description=data.description,
        ingredients=data.ingredients,
        instructions=data.instructions,
        is_public=data.is_public,
        user_id=user_id
    )

    db.add(recipe)
    db.commit()
    db.refresh(recipe)
    return recipe


def find_recent_import(
    db: Session,
    user_id: int,
    source_url: str,
    within_seconds: int = DUPLICATE_IMPORT_WINDOW_SECONDS,
) -> Recipe | None:
    """Return a recent identical import to make a double submit idempotent."""
    cutoff = datetime.utcnow() - timedelta(seconds=within_seconds)
    return (
        db.query(Recipe)
        .filter(
            Recipe.user_id == user_id,
            Recipe.source_url == source_url,
            Recipe.imported_at.isnot(None),
            Recipe.imported_at >= cutoff,
        )
        .order_by(Recipe.imported_at.desc())
        .first()
    )


def lock_user_for_import(db: Session, user_id: int) -> None:
    """Serialize imports for one owner before the duplicate check.

    PostgreSQL's row lock closes the race where two simultaneous confirms both
    observe no recent import and then create duplicate recipes. SQLite ignores
    FOR UPDATE, but production uses PostgreSQL and the existing duplicate
    window remains a best-effort fallback for that development backend.
    """
    db.query(User.id).filter(User.id == user_id).with_for_update().one()


def create_recipe_from_import(db: Session, payload, user_id: int, image_path: str | None = None) -> Recipe:
    """Persist only the edited confirm payload; preview never writes data."""
    ingredients_text = "\n".join(item.original_text for item in payload.ingredients)
    recipe = Recipe(
        name=payload.name,
        description=payload.description or "",
        ingredients=ingredients_text,
        instructions=payload.instructions or "",
        is_public=payload.is_public,
        image=image_path or "",
        user_id=user_id,
        source_url=payload.source_url,
        source_name=payload.source_name,
        source_author=payload.source_author,
        imported_at=datetime.utcnow(),
    )
    db.add(recipe)
    db.flush()

    if payload.save_structured_ingredients:
        for index, item in enumerate(payload.ingredients):
            confidence = item.confidence if item.confidence is not None else 0.0
            db.add(
                RecipeIngredient(
                    recipe_id=recipe.id,
                    ingredient_id=None,
                    original_text=item.original_text,
                    parsed_name=item.name,
                    quantity=item.quantity,
                    unit=item.unit,
                    note=item.note,
                    sort_order=index,
                    needs_review=item.requires_review or confidence < NEEDS_REVIEW_THRESHOLD,
                )
            )

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(recipe)
    return recipe


# =========================
# READ
# =========================

def get_recipe_by_id(db: Session, recipe_id: int) -> Recipe | None:
    """Pobiera przepis po ID."""
    return db.query(Recipe).filter(Recipe.id == recipe_id).first()


def get_user_recipes(db: Session, user_id: int):
    """Zwraca wszystkie przepisy użytkownika."""
    return (
        db.query(Recipe)
        .filter(Recipe.user_id == user_id)
        .order_by(Recipe.created_at.desc())
        .all()
    )


def get_visible_recipes(db: Session, user):
    """Zwraca przepisy widoczne dla użytkownika."""
    from sqlalchemy import or_

    return (
        db.query(Recipe)
        .filter(
            or_(
                Recipe.user_id == user.id,
                Recipe.is_public == True
            )
        )
        .order_by(Recipe.created_at.desc())
        .all()
    )


# =========================
# UPDATE
# =========================

def update_recipe(db: Session, recipe: Recipe, data: RecipeCreate, user):
    if recipe.user_id != user.id and user.role not in ("admin", "super_admin"):
        raise HTTPException(status_code=403, detail="Not allowed")

    recipe.name = data.name
    recipe.description = data.description
    recipe.ingredients = data.ingredients
    recipe.instructions = data.instructions
    recipe.is_public = data.is_public

    db.commit()
    db.refresh(recipe)
    return recipe


def update_visibility(db: Session, recipe: Recipe, payload: RecipeVisibilityUpdate, user):
    """Zmienia widoczność przepisu."""
    require_owner_or_admin(recipe, user)

    recipe.is_public = payload.is_public
    db.commit()
    db.refresh(recipe)
    return recipe


# =========================
# DELETE
# =========================

def delete_recipe(db: Session, recipe: Recipe, user):
    """Usuwa przepis po autoryzacji."""
    require_owner_or_admin(recipe, user)

    db.delete(recipe)
    db.commit()
