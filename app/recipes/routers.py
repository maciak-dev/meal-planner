from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.database import get_db
from app.models import Recipe
from app.schemas.recipe import RecipeCreate, RecipeRead, RecipeVisibilityUpdate
from app.core.security import get_current_user,  require_admin, require_owner_or_admin, is_super_admin
router = APIRouter(
    prefix="/recipes",
    tags=["recipes"],
)

# --- GET: lista przepisów ---
@router.get("/", response_model=list[RecipeRead])
def get_recipes_api(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    recipes = (
        db.query(Recipe)
        .filter(
            or_(
                Recipe.user_id == current_user.id,   # 👈 moje (private + public)
                Recipe.is_public == True              # 👈 cudze publiczne
            )
        )
        .order_by(Recipe.created_at.desc())
        .all()
    )

    return [
    RecipeRead(
        **r.__dict__,
        is_owner=(r.user_id == current_user.id)
    )
    for r in recipes
]

# --- POST: dodaj przepis ---
@router.post("/",
    response_model=RecipeRead)
def add_recipe_api(
    recipe: RecipeCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    new_recipe = Recipe(
        name=recipe.name,
        description=recipe.description,
        ingredients=recipe.ingredients,
        instructions=recipe.instructions,
        user_id=current_user.id,   # 👈 TO JEST KLUCZ
        is_public=recipe.is_public # jeśli już dodałeś
    )
    db.add(new_recipe)
    db.commit()
    db.refresh(new_recipe)
    return new_recipe

# --- GET by ID ---
@router.get("/{recipe_id}", response_model=RecipeRead)
def get_recipe(
    recipe_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    recipe = db.query(Recipe).filter(Recipe.id == recipe_id).first()
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")

    if recipe.is_public:
        return recipe

    if recipe.user_id == current_user.id:
        return recipe

    if is_super_admin(current_user):
        return recipe

    raise HTTPException(status_code=403, detail="Not authorized")


# --- DELETE by ID ---
@router.delete("/{recipe_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_recipe(
    recipe_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    recipe = db.query(Recipe).filter(Recipe.id == recipe_id).first()
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")

    require_owner_or_admin(recipe, current_user)

    db.delete(recipe)
    db.commit()
    return None

# --- UPDATE by ID ---
@router.put("/{recipe_id}", response_model=RecipeRead)
def update_recipe(
    recipe_id: int,
    recipe: RecipeCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    db_recipe = db.query(Recipe).filter(Recipe.id == recipe_id).first()
    if not db_recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")

    require_owner_or_admin(db_recipe, current_user)

    db_recipe.name = recipe.name
    db_recipe.description = recipe.description
    db_recipe.ingredients = recipe.ingredients
    db_recipe.instructions = recipe.instructions

    db.commit()
    db.refresh(db_recipe)
    return db_recipe

@router.patch("/{recipe_id}/visibility", response_model=RecipeRead)
def toggle_recipe_visibility(
    recipe_id: int,
    payload: RecipeVisibilityUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    recipe = db.query(Recipe).filter(Recipe.id == recipe_id).first()
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")

    require_owner_or_admin(recipe, current_user)

    recipe.is_public = payload.is_public
    db.commit()
    db.refresh(recipe)
    return recipe
