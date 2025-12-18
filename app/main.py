from fastapi import FastAPI, Request, Response, Depends, Form, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from app import models
from app.database import Base, engine, get_db
from app.models import Recipe, User
from app.core import security
from app.recipes.routers import router as recipes_router
# --- Tworzymy aplikację ---
app = FastAPI()
Base.metadata.create_all(bind=engine)

app.include_router(recipes_router)
# --- Templates ---
templates = Jinja2Templates(directory="app/templates")

# --- Static ---
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# --- ADMIN BOOTSTRAP ---
def ensure_admin():
    db = Session(bind=engine)
    admin = db.query(User).filter(User.username == "admin").first()
    if not admin:
        admin = User(
            username="admin",
            hashed_password=security.hash_password("admin"),
            role="admin"
        )
        db.add(admin)
        db.commit()
    db.close()

ensure_admin()


# --- ENDPOINTY LOGOWANIA ---
@app.get("/login")
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
def login(request: Request, username: str = Form(...), password: str = Form(...)):
    db = Session(bind=engine)
    user = db.query(User).filter(User.username == username).first()
    db.close()

    if not user or not security.verify_password(password, user.hashed_password):
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Invalid credentials"}
        )

    token = security.create_access_token({"sub": user.id})
    response = RedirectResponse(url="/recipes-ui", status_code=302)
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        samesite="lax",
        path="/"
    )
    return response


# --- ENDPOINT RECIPE UI ---
@app.get("/recipes-ui")
def recipes_ui(request: Request, user=Depends(security.get_current_user), db: Session = Depends(get_db)):
    recipes = db.query(Recipe).all()
    return templates.TemplateResponse(
        "recipes.html",
        {"request": request, "user": user, "recipes": recipes}
    )


# --- LOGOUT ---
@app.get("/logout")
def logout():
    response = RedirectResponse(url="/login", status_code=302)
    response.delete_cookie("access_token", path="/")
    return response
