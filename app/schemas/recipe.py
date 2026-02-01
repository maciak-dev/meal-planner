from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class RecipeBase(BaseModel):
    name: str
    description: Optional[str] = None
    ingredients: Optional[str] = None
    instructions: Optional[str] = None
    is_public: bool = False


class RecipeCreate(RecipeBase):
    pass


class RecipeRead(RecipeBase):
    id: int
    created_at: datetime
    user_id: int
    image: Optional[str] = None   # 👈 tylko ścieżka, nie plik
    is_owner: bool = False
    author_username: Optional[str] = None
    model_config = {
        "from_attributes": True
    }


class RecipeVisibilityUpdate(BaseModel):
    is_public: bool
