from pydantic import BaseModel
from fastapi import FastAPI, Request, Response, Depends, Form, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from app import models
from app.database import Base, engine, get_db, SessionLocal
from app.models import Recipe, User
from app.core import security
from app.core.config import ENV,COOKIE_SECURE
from app.recipes.routers import router as recipes_router
# --- Tworzymy aplikację ---
app = FastAPI()
if ENV == "dev":
    Base.metadata.create_all(bind=engine)


app.include_router(recipes_router)
# --- Templates ---
templates = Jinja2Templates(directory="app/templates")

# --- Static ---
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# --- ADMIN BOOTSTRAP ---

def ensure_admin(db: Session):
    admin = db.query(User).filter(User.username == "admin").first()
    if not admin:
        admin = User(
            username="admin",
            hashed_password=security.hash_password("admin"),
            role="admin"
        )
        db.add(admin)
        db.commit()

class UserCreate(BaseModel):
    username: str
    password: str
    role: str = "user"

@app.on_event("startup")
def startup_event():
    if ENV == "dev":
        db = SessionLocal()
        try:
            ensure_admin(db)
        finally:
            db.close()

# --- ENDPOINTY LOGOWANIA ---
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
    user = db.query(User).filter(User.username == username).first()

    if not user or not security.verify_password(password, user.hashed_password):
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Invalid credentials"},
            status_code=401
        )

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


# --- ENDPOINT RECIPE UI ---
@app.get("/recipes-ui")
def recipes_ui(
    request: Request,
    user=Depends(security.get_current_user),
    db: Session = Depends(get_db)
):
    recipes = db.query(Recipe).all()

    ingredients_map = {
        i.name.lower(): i.is_essential
        for i in db.query(models.Ingredient).all()
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

# --- LOGOUT ---
@app.get("/logout")
def logout():
    response = RedirectResponse(url="/login", status_code=302)
    response.delete_cookie("access_token", path="/")
    return response

# --- NEW USER ---
@app.post("/users")
def create_user(
    user: UserCreate,
    current_user=Depends(security.require_admin),
    db: Session = Depends(get_db)
):
    existing = db.query(User).filter(User.username == user.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists")

    new_user = User(
        username=user.username,
        hashed_password=security.hash_password(user.password),
        role=user.role
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {
        "id": new_user.id,
        "username": new_user.username,
        "role": new_user.role
    }

@app.get("/ingredients/map")
def ingredients_map(db: Session = Depends(get_db)):
    return {
        i.name.lower(): i.is_essential
        for i in db.query(models.Ingredient).all()
    }