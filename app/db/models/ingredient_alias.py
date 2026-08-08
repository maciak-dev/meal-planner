from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base


class IngredientAlias(Base):
    """Alternatywna nazwa wskazująca na ten sam znormalizowany Ingredient
    (np. "pomidor"/"pomidory"/"tomato"/"tomatoes" -> jeden Ingredient).

    Tworzony wyłącznie przez jawną akcję użytkownika w UI mapowania składnika -
    nigdy automatycznym scalaniem niepewnych dopasowań.
    """

    __tablename__ = "ingredient_aliases"

    id = Column(Integer, primary_key=True, index=True)
    ingredient_id = Column(Integer, ForeignKey("ingredients.id", ondelete="CASCADE"), nullable=False, index=True)
    alias_text = Column(String, unique=True, nullable=False)
    language = Column(String(2), nullable=True)

    ingredient = relationship("Ingredient", backref="aliases")
