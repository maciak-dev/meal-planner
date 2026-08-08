import os
from pydantic import BaseModel
from fastapi import FastAPI, Request, Depends, Form, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from sqlalchemy.orm import Session

# =========================
# CORE
# =========================
from app.core.database import Base, engine, get_db, SessionLocal
from app.core.bootstrap import initialize_database_schema
from app.core.config import COOKIE_SECURE
from app.core import security
from app.core.i18n import (
    LANG_COOKIE_NAME,
    SUPPORTED_LANGUAGES,
    js_translations,
    resolve_language,
    t,
)
from app.core.redirects import safe_local_return_path
from app.core.request_log_middleware import RequestLogMiddleware
from app.core.middleware import IPBlockMiddleware

# =========================
# MODELS
# =========================
from app.db.models.user import User
from app.db.models.recipe import Recipe
from app.db.models.login_log import LoginLog
from app.db.models.ingredient import Ingredient

# =========================
# SERVICES
# =========================
from app.services.user_service import create_user as create_user_service
from app.services.auth_service import login_user
from app.services.admin_service import get_login_logs

# =========================
# ROUTERS
# =========================
from app.api.v1.router import api_router
from app.api.v1.auth import router as auth_router
from app.api.v1.admin import router as admin_router
from app.api.v1.recipes import router as recipes_router  # poprawny import recipes

# =========================
# USERS
# =========================
from app.schemas.user import UserCreate


# =========================
# FASTAPI APP
# =========================
app = FastAPI(
    docs_url=None,
    redoc_url=None,
    openapi_url=None
)

initialize_database_schema()

# =========================
# STATIC & TEMPLATES
# =========================
templates = Jinja2Templates(directory="app/templates")
# `t` jako global Jinja: szablony wołają t('klucz', lang) bez przekazywania
# helpera w każdym kontekście z osobna.
templates.env.globals["t"] = t
app.mount("/static", StaticFiles(directory="app/static"), name="static")


# =========================
# INCLUDE ROUTERS
# =========================
app.include_router(api_router, prefix="/api/v1")


# =========================
# IP BLOCK
# =========================
app.add_middleware(IPBlockMiddleware)
app.add_middleware(RequestLogMiddleware)


# =========================
# ROOT
# =========================
@app.get("/", include_in_schema=False)
def root(
    request: Request,
    user=Depends(security.get_current_user_optional)
):
    if user:
        return RedirectResponse("/recipes-ui")
    return RedirectResponse("/login")
# =========================
# AUTH
# =========================
@app.get("/login")
def login_page(request: Request):
    # Bez `user` - ekran logowania obsługuje osobę niezalogowaną, więc język
    # bierze się z cookie albo z Accept-Language.
    return templates.TemplateResponse(
    request=request,
    name="login.html",
    context={"lang": resolve_language(request)}
)
@app.post("/login")
def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    ip = request.client.host
    agent = request.headers.get("user-agent")

    user = login_user(db, username, password, ip, agent)
    if not user:
        lang = resolve_language(request)
        return templates.TemplateResponse(
    request=request,
    name="login.html",
    context={
        "lang": lang,
        "error": t("login.invalid_credentials", lang)
    },
    status_code=401
)

    token = security.create_access_token({"sub": str(user.id)})
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

@app.get("/logout")
def logout():
    response = RedirectResponse(url="/login", status_code=302)
    response.delete_cookie("access_token", path="/")
    return response


@app.post("/set-lang", include_in_schema=False)
def set_lang(
    request: Request,
    code: str = Form(...),
    db: Session = Depends(get_db),
    user=Depends(security.get_current_user_optional),
):
    """Przełącza język interfejsu.

    POST, nie GET, mimo że zmiana języka wygląda niewinnie. Ten endpoint
    zapisuje `users.language`, czyli mutuje stan — a `SameSite=Lax` wysyła
    cookie sesji przy nawigacji GET najwyższego poziomu, więc jako GET dałby
    się wywołać zwykłym linkiem z obcej strony. Cross-site POST cookie `Lax`
    nie dostaje, więc zapis do bazy jest nieosiągalny z zewnątrz.

    Działa też dla osoby niezalogowanej — wtedy zapisuje wyłącznie cookie,
    żeby ekran logowania dało się przełączyć przed zalogowaniem.
    """
    if code not in SUPPORTED_LANGUAGES:
        raise HTTPException(status_code=400, detail="Unsupported language")

    if user is not None:
        user.language = code
        db.commit()

    # Wracamy tam, skąd użytkownik przyszedł - Referer jest sterowany przez
    # klienta, więc przepuszczamy go przez walidację same-origin.
    response = RedirectResponse(
        url=safe_local_return_path(
            request.headers.get("referer"),
            allowed_netloc=request.url.netloc,
        ),
        status_code=303,  # POST -> GET, żeby odświeżenie nie ponawiało zapisu
    )
    response.set_cookie(
        key=LANG_COOKIE_NAME,
        value=code,
        httponly=False,  # czytane też przez JS przy wyborze wariantu tekstu
        samesite="lax",
        secure=COOKIE_SECURE,
        path="/",
    )
    return response

@app.get("/auth/me")
def read_me(current_user=Depends(security.get_current_user)):
    return {
        "id": current_user.id,
        "username": current_user.username,
        "role": current_user.role
    }

# =========================
# USER MANAGEMENT================
@app.post("/users")
def create_user(
    user: UserCreate,
    current_user=Depends(security.require_admin),
    db: Session = Depends(get_db)
):
    new_user = create_user_service(db, user.username, user.password, user.role)
    return {
        "id": new_user.id,
        "username": new_user.username,
        "role": new_user.role
    }
# =========================
# ADMIN PANEL
# =========================
@app.get("/admin")
def admin_panel(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(security.get_current_user)
):
    if current_user.role != "super_admin":
        raise HTTPException(status_code=403)

    logs = db.query(LoginLog).order_by(LoginLog.created_at.desc()).limit(200).all()

    return templates.TemplateResponse(
    request=request,
    name="admin_panel.html",
    context={
        "user": current_user,
        "logs": logs
    }
)

@app.get("/admin/login-logs")
def login_logs(
    db: Session = Depends(get_db),
    current_user=Depends(security.get_current_user)
):
    return get_login_logs(db, current_user)

# =========================
# RECIPE UI
# =========================
@app.get("/recipes-ui")
def recipes_ui(
    request: Request,
    user=Depends(security.get_current_user_optional),
    db: Session = Depends(get_db)
):
    if not user:
        return RedirectResponse("/login", status_code=302)

    recipes = db.query(Recipe).all()

    ingredients_map = {
        i.name.lower(): i.is_essential
        for i in db.query(Ingredient).all()
    }

    lang = resolve_language(request, user)

    return templates.TemplateResponse(
    request=request,
    name="recipes.html",
    context={
        "user": user,
        "recipes": recipes,
        "ingredients_map": ingredients_map,
        "lang": lang,
        # Ten sam słownik, z którego korzysta Jinja - front nie ma własnej
        # kopii stringów.
        "js_translations": js_translations(lang)
    }
)

# =========================
# INGREDIENTS
# =========================
@app.get("/ingredients/map")
def ingredients_map(db: Session = Depends(get_db)):
    return {
        i.name.lower(): i.is_essential
        for i in db.query(Ingredient).all()
    }

# =========================
# DOCS (ADMIN ONLY)
# =========================
@app.get("/openapi.json", dependencies=[Depends(security.require_admin)])
def openapi():
    return get_openapi(
        title="Recipe API",
        version="1.0.0",
        routes=app.routes,
    )

@app.get("/docs", dependencies=[Depends(security.require_admin)])
def swagger_ui():
    return get_swagger_ui_html(
        openapi_url="/openapi.json",
        title="Recipe API – Admin Docs"
    )
