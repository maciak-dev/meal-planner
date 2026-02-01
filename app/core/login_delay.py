from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.db.models.login_log import LoginLog

def get_login_fail_count(db: Session, ip: str, minutes: int = 5) -> int:
    since = datetime.utcnow() - timedelta(minutes=minutes)

    return db.query(LoginLog).filter(
        LoginLog.ip_address == ip,
        LoginLog.success == False,
        LoginLog.created_at >= since
    ).count()
