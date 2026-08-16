from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.db.models.ingredient import Ingredient
from app.db.models.store import Store
from app.schemas.shop import (
    IngredientCreate,
    IngredientRead,
    IngredientStoreUpdate,
    StoreCreate,
    StoreRead,
)

router = APIRouter()


def require_catalog_editor(user):
    if user.role not in ("admin", "super_admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required")
    return user


@router.get("/stores", response_model=list[StoreRead])
def list_stores(db: Session = Depends(get_db), user=Depends(get_current_user)):
    return db.query(Store).order_by(func.lower(Store.name), Store.id).all()


@router.post("/stores", response_model=StoreRead, status_code=status.HTTP_201_CREATED)
def create_store(
    data: StoreCreate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    require_catalog_editor(user)
    existing = db.query(Store).filter(func.lower(Store.name) == data.name.lower()).first()
    if existing:
        raise HTTPException(status_code=409, detail="A store with this name already exists")
    store = Store(name=data.name)
    db.add(store)
    db.commit()
    db.refresh(store)
    return store


@router.get("/ingredients", response_model=list[IngredientRead])
def list_ingredients(db: Session = Depends(get_db), user=Depends(get_current_user)):
    return db.query(Ingredient).order_by(func.lower(Ingredient.name), Ingredient.id).all()


@router.post("/ingredients", response_model=IngredientRead, status_code=status.HTTP_201_CREATED)
def create_ingredient(
    data: IngredientCreate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    require_catalog_editor(user)
    existing = db.query(Ingredient).filter(func.lower(Ingredient.name) == data.name.lower()).first()
    if existing:
        raise HTTPException(status_code=409, detail="An ingredient with this name already exists")
    ingredient = Ingredient(
        name=data.name,
        canonical_name_pl=data.canonical_name_pl,
        canonical_name_en=data.canonical_name_en,
    )
    db.add(ingredient)
    db.commit()
    db.refresh(ingredient)
    return ingredient


@router.patch("/ingredients/{ingredient_id}/store", response_model=IngredientRead)
def set_ingredient_store(
    ingredient_id: int,
    data: IngredientStoreUpdate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    require_catalog_editor(user)
    ingredient = db.get(Ingredient, ingredient_id)
    if ingredient is None:
        raise HTTPException(status_code=404, detail="Ingredient not found")
    if data.preferred_store_id is not None and db.get(Store, data.preferred_store_id) is None:
        raise HTTPException(status_code=422, detail="Store not found")
    ingredient.preferred_store_id = data.preferred_store_id
    db.commit()
    db.refresh(ingredient)
    return ingredient
