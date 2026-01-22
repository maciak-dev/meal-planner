from fastapi import HTTPException, status


def require_admin(user):
    if user.role not in ("admin", "super_admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)


def require_super_admin(user):
    if user.role != "super_admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)


def require_owner_or_admin(resource, user):
    if resource.user_id != user.id and user.role not in ("admin", "super_admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)


def is_owner(resource, user) -> bool:
    return resource.user_id == user.id


def is_admin(user) -> bool:
    return user.role in ("admin", "super_admin")
