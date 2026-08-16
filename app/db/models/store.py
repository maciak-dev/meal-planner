from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String

from app.core.database import Base


class Store(Base):
    """A user-managed store preference target for the ingredient catalogue."""

    __tablename__ = "stores"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
