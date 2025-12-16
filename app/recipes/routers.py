from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Recipe
from app.schemas.recipe import RecipeCreate, RecipeRead

router = APIRouter(
    prefix="/recipes",
    tags=["recipes"]
)

# --- GET: lista przepisów ---
@router.get("/", response_model=list[RecipeRead])
def get_recipes_api(db: Session = Depends(get_db)):
    return db.query(Recipe).all()

# --- POST: dodaj przepis ---
@router.post("/", response_model=RecipeRead)
def add_recipe_api(
    recipe: RecipeCreate,
    db: Session = Depends(get_db)
):
    new_recipe = Recipe(
        name=recipe.name,
        description=recipe.description,
        ingredients=recipe.ingredients,
        instructions=recipe.instructions,
    )
    db.add(new_recipe)
    db.commit()
    db.refresh(new_recipe)
    return new_recipe

# --- GET by ID ---
@router.get("/{recipe_id}", response_model=RecipeRead)
def get_recipe(recipe_id: int, db: Session = Depends(get_db)):
    recipe = db.query(Recipe).filter(Recipe.id == recipe_id).first()
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")
    return recipe

# --- DELETE by ID ---
@router.delete("/{recipe_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_recipe(recipe_id: int, db: Session = Depends(get_db)):
    recipe = db.query(Recipe).filter(Recipe.id == recipe_id).first()
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")
    db.delete(recipe)
    db.commit()
    return None

# --- UPDATE by ID ---
@router.put("/{recipe_id}", response_model=RecipeRead)
def update_recipe(
    recipe_id: int,
    recipe: RecipeCreate,
    db: Session = Depends(get_db)
):
    db_recipe = db.query(Recipe).filter(Recipe.id == recipe_id).first()
    if not db_recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")

    db_recipe.name = recipe.name
    db_recipe.description = recipe.description
    db_recipe.ingredients = recipe.ingredients
    db_recipe.instructions = recipe.instructions

    db.commit()
    db.refresh(db_recipe)
    return db_recipe
