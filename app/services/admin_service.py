from sqlalchemy.orm import Session

from app.db.models.user import User
from app.db.models.login_log import LoginLog
from app.services.permissions_service import require_super_admin


def get_login_logs(db: Session, current_user, limit: int = 200):
    """Zwraca logi logowania (tylko super admin)."""
    require_super_admin(current_user)

    return (
        db.query(LoginLog)
        .order_by(LoginLog.created_at.desc())
        .limit(limit)
        .all()
    )


def get_all_users(db: Session, current_user):
    """Lista wszystkich użytkowników."""
    require_super_admin(current_user)
    return db.query(User).all()
