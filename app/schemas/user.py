from pydantic import BaseModel

# Tworzenie użytkownika
class UserCreate(BaseModel):
    username: str
    password: str
    role: str = "user"  # domyślna rola


# Odczyt użytkownika
class UserRead(BaseModel):
    id: int
    username: str
    role: str

    model_config = {
        "from_attributes": True
    }
