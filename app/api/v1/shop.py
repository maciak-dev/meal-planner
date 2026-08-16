from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.db.models.ingredient import Ingredient
from app.db.models.store import Store
from app.db.models.ingredient_store_placement import IngredientStorePlacement
from app.db.models.store_section import StoreSection
from app.services.ingredient_parsing.parser import parse_ingredient_line
from app.schemas.shop import (
    IngredientCreate,
    IngredientRead,
    IngredientStoreUpdate,
    IngredientStorePlacementCreate,
    IngredientStorePlacementRead,
    IngredientStorePlacementUpdate,
    ShoppingRouteRequest,
    ShoppingRouteResponse,
    StoreLayoutRead,
    StoreSectionCreate,
    StoreSectionRead,
    StoreSectionUpdate,
    StoreCreate,
    StoreRead,
    StoreUpdate,
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


@router.patch("/stores/{store_id}", response_model=StoreRead)
def update_store(
    store_id: int,
    data: StoreUpdate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    require_catalog_editor(user)
    store = db.get(Store, store_id)
    if store is None:
        raise HTTPException(status_code=404, detail="Store not found")
    duplicate = db.query(Store).filter(
        Store.id != store_id, func.lower(Store.name) == data.name.lower()
    ).first()
    if duplicate:
        raise HTTPException(status_code=409, detail="A store with this name already exists")
    store.name = data.name
    db.commit()
    db.refresh(store)
    return store


def _store_layout(db: Session, store: Store) -> StoreLayoutRead:
    sections = sorted(store.sections, key=lambda item: (item.sort_order, item.id))
    return StoreLayoutRead(
        id=store.id,
        name=store.name,
        sections=[
            StoreSectionRead(
                id=section.id,
                store_id=section.store_id,
                name=section.name_pl,
                position=section.sort_order,
            )
            for section in sections
        ],
        placements=[
            IngredientStorePlacementRead(
                id=placement.id,
                store_id=placement.store_id,
                ingredient_id=placement.ingredient_id,
                store_section_id=placement.store_section_id,
                position=placement.position,
            )
            for placement in sorted(store.placements, key=lambda item: item.id)
        ],
    )


@router.get("/stores/{store_id}/layout", response_model=StoreLayoutRead)
def get_store_layout(store_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    store = db.get(Store, store_id)
    if store is None:
        raise HTTPException(status_code=404, detail="Store not found")
    return _store_layout(db, store)


@router.post("/stores/{store_id}/sections", response_model=StoreSectionRead, status_code=status.HTTP_201_CREATED)
def create_store_section(
    store_id: int,
    data: StoreSectionCreate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    require_catalog_editor(user)
    store = db.get(Store, store_id)
    if store is None:
        raise HTTPException(status_code=404, detail="Store not found")
    position = data.position
    if position is None:
        position = max((section.sort_order for section in store.sections), default=-1) + 1
    section = StoreSection(
        store_id=store_id,
        name_pl=data.name,
        name_en=data.name,
        sort_order=position,
    )
    db.add(section)
    db.commit()
    db.refresh(section)
    return StoreSectionRead(id=section.id, store_id=store_id, name=section.name_pl, position=section.sort_order)


def _owned_section(db: Session, store_id: int, section_id: int) -> StoreSection:
    section = db.query(StoreSection).filter(
        StoreSection.id == section_id, StoreSection.store_id == store_id
    ).first()
    if section is None:
        raise HTTPException(status_code=404, detail="Store section not found")
    return section


@router.patch("/stores/{store_id}/sections/{section_id}", response_model=StoreSectionRead)
def update_store_section(
    store_id: int,
    section_id: int,
    data: StoreSectionUpdate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    require_catalog_editor(user)
    section = _owned_section(db, store_id, section_id)
    section.name_pl = data.name
    section.name_en = data.name
    if data.position is not None:
        section.sort_order = data.position
    db.commit()
    db.refresh(section)
    return StoreSectionRead(id=section.id, store_id=store_id, name=section.name_pl, position=section.sort_order)


@router.delete("/stores/{store_id}/sections/{section_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_store_section(
    store_id: int,
    section_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    require_catalog_editor(user)
    section = _owned_section(db, store_id, section_id)
    db.delete(section)
    db.commit()


@router.post("/stores/{store_id}/placements", response_model=IngredientStorePlacementRead, status_code=status.HTTP_201_CREATED)
def create_ingredient_placement(
    store_id: int,
    data: IngredientStorePlacementCreate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    require_catalog_editor(user)
    if db.get(Store, store_id) is None:
        raise HTTPException(status_code=404, detail="Store not found")
    _owned_section(db, store_id, data.store_section_id)
    if db.get(Ingredient, data.ingredient_id) is None:
        raise HTTPException(status_code=404, detail="Ingredient not found")
    if db.query(IngredientStorePlacement).filter_by(store_id=store_id, ingredient_id=data.ingredient_id).first():
        raise HTTPException(status_code=409, detail="Ingredient already has a placement in this store")
    placement = IngredientStorePlacement(
        store_id=store_id,
        ingredient_id=data.ingredient_id,
        store_section_id=data.store_section_id,
        position=data.position,
    )
    db.add(placement)
    db.commit()
    db.refresh(placement)
    return placement


@router.patch("/stores/{store_id}/placements/{placement_id}", response_model=IngredientStorePlacementRead)
def update_ingredient_placement(
    store_id: int,
    placement_id: int,
    data: IngredientStorePlacementUpdate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    require_catalog_editor(user)
    placement = db.query(IngredientStorePlacement).filter_by(id=placement_id, store_id=store_id).first()
    if placement is None:
        raise HTTPException(status_code=404, detail="Placement not found")
    if data.store_section_id is not None:
        _owned_section(db, store_id, data.store_section_id)
        placement.store_section_id = data.store_section_id
    placement.position = data.position
    db.commit()
    db.refresh(placement)
    return placement


@router.delete("/stores/{store_id}/placements/{placement_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_ingredient_placement(
    store_id: int,
    placement_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    require_catalog_editor(user)
    placement = db.query(IngredientStorePlacement).filter_by(id=placement_id, store_id=store_id).first()
    if placement is None:
        raise HTTPException(status_code=404, detail="Placement not found")
    db.delete(placement)
    db.commit()


def _norm(value: str) -> str:
    return " ".join(value.casefold().split())


@router.post("/stores/{store_id}/sort-items", response_model=ShoppingRouteResponse)
def sort_shopping_items(
    store_id: int,
    data: ShoppingRouteRequest,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    store = db.get(Store, store_id)
    if store is None:
        raise HTTPException(status_code=404, detail="Store not found")
    section_order = {section.id: (section.sort_order, section.id) for section in store.sections}
    placements = {
        placement.ingredient_id: placement
        for placement in store.placements
        if placement.store_section_id in section_order
    }
    names: dict[str, int] = {}
    for ingredient in db.query(Ingredient).all():
        for value in (ingredient.name, ingredient.canonical_name_pl, ingredient.canonical_name_en):
            if value:
                names[_norm(value)] = ingredient.id
        for alias in ingredient.aliases:
            names[_norm(alias.alias_text)] = ingredient.id

    ranked = []
    unassigned = 0
    for index, item in enumerate(data.items):
        parsed = parse_ingredient_line(item.name)
        ingredient_id = names.get(_norm(parsed.name)) or names.get(_norm(item.name))
        placement = placements.get(ingredient_id)
        if placement is None:
            rank = (1, 0, 0, index)
            unassigned += 1
        else:
            section_rank = section_order[placement.store_section_id]
            position_rank = placement.position if placement.position is not None else 10**9
            rank = (0, section_rank[0], position_rank, index)
        ranked.append((item.done, rank, item))
    ranked.sort(key=lambda entry: (entry[0], *entry[1]))
    return ShoppingRouteResponse(items=[entry[2] for entry in ranked], unassigned_count=unassigned)


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
