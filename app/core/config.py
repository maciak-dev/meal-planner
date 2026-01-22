import os
from dotenv import load_dotenv

# załaduj .env (jeśli istnieje)
load_dotenv()

ENV = os.getenv("ENV", "dev")  # dev lub prod
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret")
DATABASE_URL = "sqlite:////home/vboxuser/fastapi-projekt/app/db/app.db"
COOKIE_SECURE = ENV == "prod"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60