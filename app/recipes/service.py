from sqlalchemy.orm import Session
from .. import models, schemas

# --- CRUD dla Recipe ---

def create_recipe(db: Session, recipe: schemas.RecipeCreate):
    db_recipe = models.Recipe(
        name=recipe.name,
        description=recipe.description,
        ingredients=recipe.ingredients,
        instructions=recipe.instructions
    )
    db.add(db_recipe)
    db.commit()
    db.refresh(db_recipe)
    return db_recipe

def get_recipe(db: Session, recipe_id: int):
    return db.query(models.Recipe).filter(models.Recipe.id == recipe_id).first()

def get_recipes(db: Session, limit: int = 100):
    return db.query(models.Recipe).order_by(models.Recipe.created_at.desc()).limit(limit).all()

def delete_recipe(db: Session, recipe_id: int):
    recipe = db.query(models.Recipe).filter(models.Recipe.id == recipe_id).first()
    if recipe:
        db.delete(recipe)
        db.commit()
    return recipe
