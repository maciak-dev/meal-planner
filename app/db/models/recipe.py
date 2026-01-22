from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from app.core.database import Base
from datetime import datetime

class Recipe(Base):
    __tablename__ = "recipes"

    id = Column(Integer, primary_key=True, index=True)

    # Podstawowe dane przepisu
    name = Column(String, index=True)
    description = Column(String, nullable=True)
    instructions = Column(String, nullable=True)
    ingredients = Column(String, nullable=True)  # JSON/string

    # Metadane
    created_at = Column(DateTime, default=datetime.utcnow)
    is_public = Column(Boolean, default=False)
    image = Column(String, nullable=True)

    # Autor
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    author = relationship("User")
