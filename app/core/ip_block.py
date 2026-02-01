from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from app.db.models.login_log import LoginLog, RequestLog


def is_ip_blocked(db: Session, ip: str):
    now = datetime.utcnow()

    # === 1️⃣ LOGIN BRUTE FORCE ===
    login_fails = db.query(LoginLog).filter(
        LoginLog.ip_address == ip,
        LoginLog.success == False,
        LoginLog.created_at >= now - timedelta(minutes=5)
    ).count()

    if login_fails >= 5:
        return True

    # === 2️⃣ REQUEST SCANNING ===
    suspicious_requests = db.query(RequestLog).filter(
        RequestLog.ip_address == ip,
        RequestLog.is_suspicious == True,
        RequestLog.created_at >= now - timedelta(minutes=5)
    ).count()

    if suspicious_requests >= 3:
        return True

    return False

