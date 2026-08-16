from sqlalchemy import Column, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import relationship

from app.core.database import Base


class IngredientStorePlacement(Base):
    """Optional location of one ingredient in one store's route preset."""

    __tablename__ = "ingredient_store_placements"
    __table_args__ = (UniqueConstraint("store_id", "ingredient_id", name="uq_store_ingredient"),)

    id = Column(Integer, primary_key=True, index=True)
    store_id = Column(Integer, ForeignKey("stores.id", ondelete="CASCADE"), nullable=False, index=True)
    ingredient_id = Column(Integer, ForeignKey("ingredients.id", ondelete="CASCADE"), nullable=False, index=True)
    store_section_id = Column(Integer, ForeignKey("store_sections.id", ondelete="CASCADE"), nullable=False, index=True)
    position = Column(Integer, nullable=True)

    store = relationship("Store", back_populates="placements")
    ingredient = relationship("Ingredient")
    section = relationship("StoreSection")
