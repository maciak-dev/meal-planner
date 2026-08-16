from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base
from datetime import datetime

class Ingredient(Base):
    __tablename__ = "ingredients"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)

    # Czy składnik obowiązkowy w bazie
    is_essential = Column(Boolean, default=True)

    # Znormalizowana nazwa produktu w każdym języku (np. "czosnek" / "garlic").
    # Mapowanie tekstu przepisu na katalog nadal wymaga jawnej akcji użytkownika;
    # preferowany sklep jest opcjonalną preferencją katalogu.
    canonical_name_pl = Column(String, nullable=True)
    canonical_name_en = Column(String, nullable=True)
    preferred_store_id = Column(Integer, ForeignKey("stores.id"), nullable=True)
    default_store_section_id = Column(Integer, ForeignKey("store_sections.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    default_store_section = relationship("StoreSection")
    preferred_store = relationship("Store")
