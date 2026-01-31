from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.db.models.user import User
from app.db.models.login_log import LoginLog
from app.services.permissions_service import require_super_admin


def get_login_logs(
    db: Session,
    current_user,
    range: str = "today",
    limit: int = 200,
):
    """Zwraca logi logowania (tylko super admin)."""
    require_super_admin(current_user)

    HARD_LIMIT = 2000
    limit = min(limit, HARD_LIMIT)

    q = db.query(LoginLog)

    now = datetime.utcnow()

    if range == "today":
        q = q.filter(LoginLog.created_at >= now.replace(
            hour=0, minute=0, second=0, microsecond=0
        ))
    elif range == "7d":
        q = q.filter(LoginLog.created_at >= now - timedelta(days=7))
    elif range == "30d":
        q = q.filter(LoginLog.created_at >= now - timedelta(days=30))
    elif range == "all":
        pass  # bez filtra daty
    else:
        # fallback bezpieczeństwa
        q = q.filter(LoginLog.created_at >= now.replace(
            hour=0, minute=0, second=0, microsecond=0
        ))

    return (
        q.order_by(LoginLog.created_at.desc())
         .limit(limit)
         .all()
    )

def get_all_users(db: Session, current_user):
    """Lista wszystkich użytkowników."""
    require_super_admin(current_user)
    return db.query(User).all()
