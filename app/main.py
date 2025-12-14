from fastapi import FastAPI, Request, Response, Depends, HTTPException, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session as DbSession

from app import models
from app.database import Base, engine, get_db
from app.models import Recipe
from app.core import security
from app.recipes.routers import router as recipes_router

# --- Tworzymy aplikację ---
app = FastAPI()

# --- Tworzymy bazę (jeśli jeszcze nie istnieje) ---
Base.metadata.create_all(bind=engine)

# --- Templates ---
templates = Jinja2Templates(directory="app/templates")
sessions = {}

# mount folder ze statycznymi plikami
app.mount("/static", StaticFiles(directory="app/static"), name="static")


# --- ENDPOINTY LOGOWANIA ---
@app.get("/login")
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    db = DbSession(bind=engine)
    user = db.query(models.User).filter(models.User.username == username).first()
    db.close()
    if not user or not security.verify_password(password, user.hashed_password):
        return templates.TemplateResponse("login.html", {"request": request, "error": "Invalid credentials"})
    
    # Tworzymy losowy token sesji
    import secrets
    token = secrets.token_hex(16)
    sessions[token] = username
    
    response = RedirectResponse(url="/recipes-ui", status_code=302)
    response.set_cookie(key="session_token", value=token, httponly=True)
    return response

def get_current_user(request: Request):
    token = request.cookies.get("session_token")
    if not token or token not in sessions:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return sessions[token]

# --- ENDPOINT RECIPE UI ---
@app.get("/recipes-ui")
def recipes_ui(request: Request, user: str = Depends(get_current_user), db: sessions = Depends(get_db)):
    # pobieramy wszystkie przepisy z bazy
    recipes = db.query(Recipe).all()
    return templates.TemplateResponse(
        "recipes.html",
        {"request": request, "user": user, "recipes": recipes}
    )

app.include_router(recipes_router)
# --- LOGOUT ---
@app.get("/logout")
def logout(response: Response, request: Request):
    token = request.cookies.get("session_token")
    if token in sessions:
        del sessions[token]
    response = RedirectResponse(url="/login", status_code=302)
    response.delete_cookie(key="session_token")
    return response

# --- ROOT ---
@app.get("/")
def root():
    return {"message": "MealETL API is running!"}
