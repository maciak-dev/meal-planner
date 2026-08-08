from sqlalchemy import Column, Integer, String, Numeric, Boolean, ForeignKey
from sqlalchemy.orm import backref, relationship
from app.core.database import Base


class RecipeIngredient(Base):
    """Jedna pozycja składnika przypisana do przepisu - most między wolnym tekstem
    linii składnika a znormalizowanym Ingredient.

    original_text jest zawsze zachowywany (np. "2 duże ząbki czosnku"); quantity/unit/note
    to wynik parsera (Etap 5) ALBO ręczna korekta użytkownika w draftcie importu.
    parsed_name to nazwa składnika tak, jak ją zaakceptował/poprawił użytkownik - to
    wciąż wolny tekst, NIE mapowanie na Ingredient (to robi ingredient_id, ustawiane
    tylko przez Fazę C). needs_review=True dopóki człowiek nie potwierdzi.
    """

    __tablename__ = "recipe_ingredients"

    id = Column(Integer, primary_key=True, index=True)
    recipe_id = Column(Integer, ForeignKey("recipes.id", ondelete="CASCADE"), nullable=False, index=True)
    ingredient_id = Column(Integer, ForeignKey("ingredients.id"), nullable=True, index=True)

    original_text = Column(String, nullable=False)
    parsed_name = Column(String, nullable=True)
    quantity = Column(Numeric(10, 3), nullable=True)
    unit = Column(String, nullable=True)
    note = Column(String, nullable=True)
    sort_order = Column(Integer, default=0, nullable=False)
    needs_review = Column(Boolean, default=True, nullable=False)

    # patrz recipe_translation.py - to samo NOT NULL recipe_id i ten sam powód;
    # sprzątanie po stronie bazy pochodzi z ON DELETE CASCADE w migracji 539387eab2be.
    recipe = relationship(
        "Recipe",
        backref=backref(
            "structured_ingredients",
            cascade="all, delete-orphan",
            passive_deletes=True,
        ),
    )
    # ingredient_id jest nullable i celowo BEZ kaskady: usunięcie znormalizowanego
    # składnika nie może kasować pozycji przepisów, które go używały.
    ingredient = relationship("Ingredient")
