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

class RequestLog(Base):
    __tablename__ = "request_log"

    id = Column(Integer, primary_key=True)
    ip_address = Column(String)
    method = Column(String)
    path = Column(String)
    status_code = Column(Integer)
    user_agent = Column(String)
    is_suspicious = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)