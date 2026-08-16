from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from app.core.database import Base


class StoreSection(Base):
    """Sekcja/dział sklepu (np. Warzywa i owoce, Nabiał) używana do sortowania listy zakupów.

    A section belongs to a store in the route-preset model. Nullable store_id keeps
    old global catalogue rows readable during the additive migration.
    """

    __tablename__ = "store_sections"

    id = Column(Integer, primary_key=True, index=True)
    # Nullable for compatibility with the original global section seed. New
    # route sections always belong to one store.
    store_id = Column(Integer, ForeignKey("stores.id"), nullable=True, index=True)
    name_pl = Column(String, nullable=False)
    name_en = Column(String, nullable=False)
    sort_order = Column(Integer, default=0, nullable=False)

    store = relationship("Store", back_populates="sections")
