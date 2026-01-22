from fastapi import Request, HTTPException
from sqlalchemy.orm import Session
from app.db.models.login_log import LoginLog
from datetime import datetime, timedelta

def is_ip_blocked(db: Session, ip: str, limit=5, minutes=5):
    since = datetime.utcnow() - timedelta(minutes=minutes)

    fails = db.query(LoginLog).filter(
        LoginLog.ip_address == ip,
        LoginLog.success == False,
        LoginLog.created_at >= since
    ).count()

    return fails >= limit
