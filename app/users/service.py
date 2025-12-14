from sqlalchemy.orm import Session
from .. import models, schemas
from app.core.security import hash_password

def create_user(db: Session, user: schemas.UserCreate):
    db_user = models.User(
        username=user.username,
        hashed_password=hash_password(user.password)
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


