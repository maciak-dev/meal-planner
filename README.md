# 🍽️ Meal Planner

**Plan meals. Build the shopping list. Know what's for dinner.**

Built with **FastAPI**, **SQLAlchemy**, and **JWT authentication**.

GitHub: [https://github.com/maciak-dev/meal-planner](https://github.com/maciak-dev/meal-planner)

---

## Documentation

Product documentation is organised from product to implementation:

```
North Star → Vision → Modules → Integrations → Architecture → Operations
```

- [Documentation index](docs/README.md) — single entry point
- [North Star](docs/north-star.md) — what Meal Planner is and is not; the
  criterion every feature is judged against
- [Product vision](docs/product/vision.md), [roadmap](docs/product/roadmap.md),
  [backlog](docs/product/backlog.md)
- [Integration with MAP](docs/integrations/map.md) — boundaries and contract
- [Production Guardrails](docs/operations/production-guardrails.md) — read
  before touching anything production-related

The section below describes the current implementation, which is narrower than
the product direction set out in the North Star.

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
