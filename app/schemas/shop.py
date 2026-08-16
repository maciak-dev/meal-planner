from pydantic import BaseModel, Field, field_validator


class StoreCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)

    @field_validator("name")
    @classmethod
    def trim_name(cls, value: str) -> str:
        value = " ".join(value.split())
        if not value:
            raise ValueError("Store name cannot be empty")
        return value


class StoreRead(BaseModel):
    id: int
    name: str

    model_config = {"from_attributes": True}


class StoreUpdate(StoreCreate):
    pass


class StoreSectionCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    position: int | None = Field(default=None, ge=0)

    @field_validator("name")
    @classmethod
    def trim_name(cls, value: str) -> str:
        value = " ".join(value.split())
        if not value:
            raise ValueError("Section name cannot be empty")
        return value


class StoreSectionUpdate(StoreSectionCreate):
    pass


class StoreSectionRead(BaseModel):
    id: int
    store_id: int | None
    name: str
    position: int


class IngredientStorePlacementCreate(BaseModel):
    ingredient_id: int
    store_section_id: int
    position: int | None = Field(default=None, ge=0)


class IngredientStorePlacementUpdate(BaseModel):
    store_section_id: int | None = None
    position: int | None = Field(default=None, ge=0)


class IngredientStorePlacementRead(BaseModel):
    id: int
    store_id: int
    ingredient_id: int
    store_section_id: int
    position: int | None


class StoreLayoutRead(BaseModel):
    id: int
    name: str
    sections: list[StoreSectionRead]
    placements: list[IngredientStorePlacementRead]


class IngredientCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    canonical_name_pl: str | None = Field(default=None, max_length=160)
    canonical_name_en: str | None = Field(default=None, max_length=160)

    @field_validator("name", "canonical_name_pl", "canonical_name_en")
    @classmethod
    def trim_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = " ".join(value.split())
        return value or None


class IngredientStoreUpdate(BaseModel):
    preferred_store_id: int | None = None


class IngredientRead(BaseModel):
    id: int
    name: str
    canonical_name_pl: str | None = None
    canonical_name_en: str | None = None
    preferred_store_id: int | None = None
    preferred_store: StoreRead | None = None

    model_config = {"from_attributes": True}


class ShoppingRouteItem(BaseModel):
    id: str
    name: str
    qty: int | float = 1
    done: bool = False


class ShoppingRouteRequest(BaseModel):
    items: list[ShoppingRouteItem] = Field(max_length=500)


class ShoppingRouteResponse(BaseModel):
    items: list[ShoppingRouteItem]
    unassigned_count: int
