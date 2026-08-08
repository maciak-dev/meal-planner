from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from app.core.database import Base
from datetime import datetime

class Recipe(Base):
    __tablename__ = "recipes"

    id = Column(Integer, primary_key=True, index=True)

    # Podstawowe dane przepisu
    name = Column(String, nullable=False, index=True)
    description = Column(String, default="", nullable=False)
    instructions = Column(String, default="", nullable=False)
    ingredients = Column(String, default="", nullable=False)  # JSON/string

    # Metadane
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    is_public = Column(Boolean, default=False, nullable=False)
    image = Column(String, default="", nullable=False)

    # Pochodzenie przepisu - wypełniane wyłącznie dla przepisów zaimportowanych
    # z URL. Import jeszcze nie istnieje, więc dziś te kolumny są zawsze NULL;
    # schemat wchodzi wcześniej, żeby import nie musiał ruszać migracji.
    source_url = Column(String, nullable=True)
    source_name = Column(String, nullable=True)
    source_author = Column(String, nullable=True)
    imported_at = Column(DateTime, nullable=True)

    # Autor
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    author = relationship("User")
