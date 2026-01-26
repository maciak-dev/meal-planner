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
from app.core.config import ENV, COOKIE_SECURE
from app.core import security
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

# Tworzenie tabel tylko w DEV
if ENV == "dev":
    Base.metadata.create_all(bind=engine)

# =========================
# STATIC & TEMPLATES
# =========================
templates = Jinja2Templates(directory="app/templates")
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
    return templates.TemplateResponse("login.html", {"request": request})

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
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Invalid credentials"},
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
        "admin_panel.html",
        {
            "request": request,
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

    return templates.TemplateResponse(
        "recipes.html",
        {
            "request": request,
            "user": user,
            "recipes": recipes,
            "ingredients_map": ingredients_map
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
