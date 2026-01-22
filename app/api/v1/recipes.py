import uuid, os

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.recipe import RecipeCreate, RecipeRead, RecipeVisibilityUpdate
from app.services import recipe_service
from app.core.security import get_current_user
from app.utils.file_utils import save_image, delete_image

UPLOAD_DIR = "app/static/uploads"

router = APIRouter()


# =========================
# LIST
# =========================

@router.get("/", response_model=list[RecipeRead])
def list_recipes(
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    recipes = recipe_service.get_visible_recipes(db, user)

    return [
        RecipeRead(
            **r.__dict__,
            is_owner=(r.user_id == user.id)
        )
        for r in recipes
    ]


# =========================
# CREATE
# =========================

@router.post("/", response_model=RecipeRead)
def create_recipe(
    data: RecipeCreate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    return recipe_service.create_recipe(db, data, user.id)


# =========================
# GET BY ID
# =========================

@router.get("/{recipe_id}", response_model=RecipeRead)
def get_recipe(
    recipe_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    recipe = recipe_service.get_recipe_by_id(db, recipe_id)

    if not recipe:
        raise HTTPException(404)

    if recipe.is_public or recipe.user_id == user.id or user.role in ("admin", "super_admin"):
        return recipe

    raise HTTPException(status_code=403)


# =========================
# UPDATE
# =========================



@router.put("/{recipe_id}", response_model=RecipeRead)
def update_recipe(
    recipe_id: int,
    data: RecipeCreate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    recipe = recipe_service.get_recipe_by_id(db, recipe_id)
    if not recipe:
        raise HTTPException(404)

    return recipe_service.update_recipe(db, recipe, data, user)

# =========================
# DELETE
# =========================

@router.delete("/{recipe_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_recipe(
    recipe_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    recipe = recipe_service.get_recipe_by_id(db, recipe_id)
    if not recipe:
        raise HTTPException(404)

    recipe_service.delete_recipe(db, recipe, user)
    return None


# =========================
# VISIBILITY
# =========================

@router.patch("/{recipe_id}/visibility", response_model=RecipeRead)
def update_visibility(
    recipe_id: int,
    payload: RecipeVisibilityUpdate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    recipe = recipe_service.get_recipe_by_id(db, recipe_id)
    if not recipe:
        raise HTTPException(404)

    return recipe_service.update_visibility(db, recipe, payload, user)


@router.put("/{recipe_id}/image")
def set_recipe_image(
    recipe_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    recipe = recipe_service.get_recipe_by_id(db, recipe_id)
    if not recipe:
        raise HTTPException(404)

    if recipe.user_id != user.id:
        raise HTTPException(403)

    delete_image(recipe.image)

    try:
        image_url, _ = save_image(file)
    except ValueError:
        raise HTTPException(400, "Invalid image type")

    recipe.image = image_url
    db.commit()
    db.refresh(recipe)

    return {"image": recipe.image}


@router.delete("/{recipe_id}/image")
def delete_recipe_image(
    recipe_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    recipe = recipe_service.get_recipe_by_id(db, recipe_id)
    if not recipe:
        raise HTTPException(404)

    if recipe.user_id != user.id:
        raise HTTPException(403)

    delete_image(recipe.image)

    recipe.image = None
    db.commit()
    db.refresh(recipe)

    return {"detail": "Image deleted"}



