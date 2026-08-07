# 🍽️ Meal Planner

Simple recipe manager built with **FastAPI**, **SQLAlchemy**, and **JWT authentication**.

GitHub: [https://github.com/maciak-dev/meal-planner](https://github.com/maciak-dev/meal-planner)

---

## Features

- User login & role-based access (`user` / `admin`) 
- Create, view, edit recipes 
- Automatic admin in development 
- Environment-based config (`dev`, `prod`, `rc`)
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
```

Create `.env` from `.env.example` and set at least:

```env
ENV=dev
APP_INSTANCE=dev
SECRET_KEY=change-me
DATABASE_URL=sqlite:////absolute/path/to/meal-planner.db
EXPECTED_DATABASE_NAME=meal-planner.db
```

Open in browser:

`http://127.0.0.1:8000/login`

Swagger UI:

`http://127.0.0.1:8000/docs`

## Environment Variables

- `ENV`
  - `dev` enables automatic schema creation.
  - `prod` disables automatic schema creation and sets secure cookies.
  - `rc` is allowed for non-production RC identity, but still requires an explicit database URL.
- `APP_INSTANCE`
  - Use `production` for public production.
  - Use `rc` for release-candidate/staging-like instances.
  - Use `dev` for local work.
- `DATABASE_URL`
  - Required.
  - No hardcoded fallback exists in code.
- `EXPECTED_DATABASE_NAME`
  - Optional guard to stop an instance from connecting to the wrong database.
- `PRODUCTION_DATABASE_NAME`
  - Optional name used by the RC guard. Default: `fastapi_db`.
- `SECRET_KEY`
  - Required outside `ENV=dev`.

## Deployment Notes

- `uvicorn` is used to run the application process.
- `nginx` should terminate HTTPS and forward `X-Forwarded-Proto`.
- Keep production and RC on separate databases.
- Never commit real `.env` files or secrets.
- Use SQLite only when it is explicitly configured for local development.
- Before changing deployment, domains, database, volumes, authentication, cookies, reverse proxy, or persistent data, read [Production Guardrails](docs/operations/production-guardrails.md).

License

MIT
