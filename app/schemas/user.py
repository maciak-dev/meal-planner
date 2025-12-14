from pydantic import BaseModel

class UserCreate(BaseModel):
    username: str
    password: str

    model_config = {
        "from_attributes": True
    }
