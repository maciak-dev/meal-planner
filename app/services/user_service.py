from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.db.models.user import User
from app.core import security


def get_user_by_id(db: Session, user_id: int) -> User | None:
    return db.query(User).filter(User.id == user_id).first()


def get_user_by_username(db: Session, username: str) -> User | None:
    return db.query(User).filter(User.username == username).first()


def create_user(db: Session, username: str, password: str, role: str = "user") -> User:
    existing = get_user_by_username(db, username)
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists")

    user = User(
        username=username,
        hashed_password=security.hash_password(password),
        role=role
    )

    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, username: str, password: str) -> User | None:
    user = get_user_by_username(db, username)
    if not user:
        return None

    if not security.verify_password(password, user.hashed_password):
        return None

    return user
