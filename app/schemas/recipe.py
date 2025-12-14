from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class RecipeBase(BaseModel):
    name: str
    description: Optional[str] = None
    ingredients: Optional[str] = None
    instructions: Optional[str] = None

class RecipeCreate(RecipeBase):
    pass

class RecipeRead(RecipeBase):
    id: int
    created_at: datetime

    model_config = {
        "from_attributes": True
    }
