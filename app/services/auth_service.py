from sqlalchemy.orm import Session
from app.db.models.user import User
from app.db.models.login_log import LoginLog
from app.core import security


def authenticate_user(db: Session, username: str, password: str):
    user = db.query(User).filter(User.username == username).first()

    if not user:
        return None

    if not security.verify_password(password, user.hashed_password):
        return None

    return user


def log_login(db: Session, user_id, username, ip, agent, success: bool):
    log = LoginLog(
        user_id=user_id,
        username=username,
        ip_address=ip,
        user_agent=agent,
        success=success
    )
    db.add(log)
    db.commit()


def login_user(db: Session, username: str, password: str, ip: str, agent: str):
    user = authenticate_user(db, username, password)

    if not user:
        log_login(db, None, username, ip, agent, False)
        return None

    log_login(db, user.id, user.username, ip, agent, True)
    return user