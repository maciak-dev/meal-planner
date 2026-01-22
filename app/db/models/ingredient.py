from sqlalchemy import Column, Integer, String, Boolean
from app.core.database import Base

class Ingredient(Base):
    __tablename__ = "ingredients"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)

    # Czy składnik obowiązkowy w bazie
    is_essential = Column(Boolean, default=True)
