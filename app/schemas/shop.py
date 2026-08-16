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
