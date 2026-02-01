from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
import asyncio

from app.core.database import get_db
from app.services.auth_service import login_user
from app.core import security
from app.core.config import COOKIE_SECURE
from app.core.login_delay import get_login_fail_count  # 👈 helper

router = APIRouter()


@router.post("/login")
async def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    ip = request.client.host if request.client else None
    agent = request.headers.get("user-agent")

    user = login_user(db, username, password, ip, agent)

    if not user:
        # 🔐 DELAY LOGIKI
        fails = get_login_fail_count(db, ip)

        delay = min(fails, 3)  # max 3 sekundy
        if delay > 0:
            await asyncio.sleep(delay)

        return RedirectResponse(url="/login?error=1", status_code=302)

    # ✅ SUCCESS
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
