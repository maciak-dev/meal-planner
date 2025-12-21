from pydantic import BaseModel
class UserCreate(BaseModel):
    username: str
    password: str
    role: str = "user"  # domyślnie user

class UserRead(BaseModel):
    id: int
    username: str
    role: str

    model_config = {
        "from_attributes": True
    }

