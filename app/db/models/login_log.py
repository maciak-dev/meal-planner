from sqlalchemy import Column, Integer, String, Boolean, DateTime
from datetime import datetime
from app.core.database import Base

class LoginLog(Base):
    __tablename__ = "login_log"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=True)
    username = Column(String)
    ip_address = Column(String)
    user_agent = Column(String)
    success = Column(Boolean)
    created_at = Column(DateTime, default=datetime.utcnow)