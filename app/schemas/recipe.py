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
    is_public: bool
    is_owner: bool = False
    model_config = {
        "from_attributes": True
    }

class RecipeVisibilityUpdate(BaseModel):
    is_public: bool


