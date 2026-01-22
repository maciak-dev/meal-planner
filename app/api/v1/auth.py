from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.services.auth_service import login_user
from app.core import security
from app.core.config import COOKIE_SECURE

router = APIRouter()


@router.post("/login")
def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    user = login_user(db, username, password, ip, agent)

    if not user:
        return RedirectResponse(url="/login?error=1", status_code=302)

    token = security.create_access_token({"sub": user.id})

    response = RedirectResponse(url="/recipes-ui", status_code=302)
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        samesite="lax",
        secure=COOKIE_SECURE,
        path="/"
    )
    return response


@router.get("/logout")
def logout():
    response = RedirectResponse(url="/login", status_code=302)
    response.delete_cookie("access_token", path="/")
    return response


@router.get("/me")
def read_me(current_user=Depends(security.get_current_user)):
    return {
        "id": current_user.id,
        "username": current_user.username,
        "role": current_user.role
    }