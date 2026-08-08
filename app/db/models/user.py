from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime
from app.core.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(String, nullable=False, default="user")
    created_at = Column(DateTime, default=datetime.utcnow)

    # Preferowany język interfejsu. Przełącznika języka jeszcze nie ma - kolumna
    # istnieje, żeby i18n UI weszło bez migracji. Istniejące konta dostają 'pl'
    # przez server_default w migracji d17abcef39ac.
    language = Column(String(2), nullable=False, default="pl", server_default="pl")