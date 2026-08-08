from sqlalchemy import Column, Integer, String
from app.core.database import Base


class StoreSection(Base):
    """Sekcja/dział sklepu (np. Warzywa i owoce, Nabiał) używana do sortowania listy zakupów.

    V1: jedna globalna lista sekcji z jednym sort_order (brak wariantów per-sklep) -
    zgodnie z zasadą "nie komplikuj pierwszej wersji ponad potrzebę". Kolejność per-sklep
    to naturalne rozszerzenie później (osobna tabela StoreSectionOrder), nie łamiące V1.
    """

    __tablename__ = "store_sections"

    id = Column(Integer, primary_key=True, index=True)
    name_pl = Column(String, nullable=False)
    name_en = Column(String, nullable=False)
    sort_order = Column(Integer, default=0, nullable=False)
