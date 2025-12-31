# app/core/config.py
import os

ENV = os.getenv("ENV", "dev")  # dev / prod
SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-secret")  # konieczne na prod
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

COOKIE_SECURE = ENV == "prod"
