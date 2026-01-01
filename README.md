# 🍽️ Meal Planner

Simple recipe manager built with **FastAPI**, **SQLAlchemy**, and **JWT authentication**. 

GitHub: [https://github.com/maciak-dev/meal-planner](https://github.com/maciak-dev/meal-planner)

---

## Features

- User login & role-based access (`user` / `admin`) 
- Create, view, edit recipes 
- Automatic admin in development 
- Environment-based config (`dev` / `prod`) 
- Secure password hashing (bcrypt) 

---

## Quick Start (DEV)

```bash
git clone https://github.com/maciak-dev/meal-planner.git
cd meal-planner
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload

Open in browser:

http://127.0.0.1:8000/login

Swagger UI:

http://127.0.0.1:8000/docs

Default Admin (DEV only)

username: admin
password: admin
role: admin

⚠️ Not created in production.
Environment Variables

Create .env from .env.example:

ENV=dev
DATABASE_URL=sqlite:///meal_etl.db
SECRET_KEY=your-super-secret-key
ACCESS_TOKEN_EXPIRE_MINUTES=60
COOKIE_SECURE=False

Deployment Notes

    Gunicorn + Uvicorn for server

    Nginx + HTTPS for production

    Use .env on server, never commit secrets

    SQLite can be replaced with PostgreSQL for production

License

MIT
