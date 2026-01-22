from fastapi import Depends, HTTPException, status
from app.core.security import get_current_user
from app.db.models.user import User

def super_admin_required(current_user: User = Depends(get_current_user)):
    if current_user.role != "super_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return current_user
