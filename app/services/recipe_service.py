from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.db.models.recipe import Recipe
from app.schemas.recipe import RecipeCreate, RecipeVisibilityUpdate
from app.services.permissions_service import require_owner_or_admin


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