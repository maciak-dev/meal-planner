from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.orm import relationship

from app.core.database import Base


class Store(Base):
    """A user-managed store preference target for the ingredient catalogue."""

    __tablename__ = "stores"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    sections = relationship(
        "StoreSection", back_populates="store", cascade="all, delete-orphan"
    )
    placements = relationship(
        "IngredientStorePlacement", back_populates="store", cascade="all, delete-orphan"
    )
