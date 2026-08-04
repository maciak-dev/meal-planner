# Production Environment

Data aktualizacji: 2026-08-04

## Stan bieżący

- Checkout: `/var/www/meal-planner`
- Branch: `main`
- Commit: `feacd6c`
- Proces: `uvicorn app.main:app --host 0.0.0.0 --port 8000`
- Usługa: `meal-planner.service`
- Reverse proxy: `nginx`
- Domena: `maciak.online`
- Baza danych: PostgreSQL `fastapi_db`
- Uploady: `/var/www/meal-planner/app/static/uploads`

## Źródła konfiguracji

- `systemd` ustawia:
  - `WorkingDirectory=/var/www/meal-planner`
  - `PATH=/var/www/meal-planner/venv/bin`
- aplikacja ładuje `.env` z katalogu roboczego przez `load_dotenv()`
- `ENV` pochodzi z `/var/www/meal-planner/.env`
- `DATABASE_URL` ma docelowo pochodzić z `.env`, ale w działającej produkcji nadal jest nadpisywany przez hardcoded DSN w aktualnie wdrożonym kodzie

## Bieżące problemy produkcyjne

- `ENV=dev`
- `COOKIE_SECURE=False`
- `Base.metadata.create_all()` aktywne przy starcie
- `.env` wskazuje SQLite, choć runtime działa na PostgreSQL
- brak health/ready endpointów

## Polecenia tylko do odczytu

```bash
git -C /var/www/meal-planner status --short
git -C /var/www/meal-planner branch --show-current
git -C /var/www/meal-planner log -1 --oneline
systemctl status meal-planner --no-pager
ss -lntp | rg ':8000|:443|:80|:5432'
curl -kfsSI --resolve maciak.online:443:127.0.0.1 https://maciak.online/
```

## Plan przed przełączeniem na `ENV=prod`

1. Trzymać produkcję bez restartu do czasu zatwierdzenia.
2. Najpierw potwierdzić RC na osobnej bazie.
3. Przygotować i zachować świeży backup PostgreSQL.
4. Mieć gotowy plan rollbacku i smoke testów po restarcie.
5. Dopiero potem zaktualizować produkcyjny `.env` i wdrożyć kod bez hardcoded DSN.
