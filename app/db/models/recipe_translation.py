from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.core.database import Base
from datetime import datetime


class RecipeTranslation(Base):
    """Tekst przepisu w jednym języku. Recipe zostaje kontenerem język-agnostycznym
    (własność, zdjęcie, składniki); ten model niesie name/description/instructions per language.
    """

    __tablename__ = "recipe_translations"
    __table_args__ = (
        UniqueConstraint("recipe_id", "language", name="uq_recipe_translations_recipe_language"),
    )

    id = Column(Integer, primary_key=True, index=True)
    recipe_id = Column(Integer, ForeignKey("recipes.id", ondelete="CASCADE"), nullable=False, index=True)
    language = Column(String(2), nullable=False)

    name = Column(String, nullable=False)
    description = Column(String, default="", nullable=False)
    instructions = Column(String, default="", nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    recipe = relationship("Recipe", backref="translations")
