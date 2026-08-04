# RC Environment

Data aktualizacji: 2026-08-04

## Stan bieżący

- Checkout RC na VPS: `/var/www/meal-planner-rc`
- Branch: `main`
- Commit: `feacd6c`
- Usługa: `meal-planner-rc.service`
- Port: `127.0.0.1:8001`
- Nginx: `rc.maciak.online`
- Autostart: `enabled`
- Status podczas audytu: `active (running)`

## Problemy obecnego RC

- usługa działa stale, mimo że docelowo ma być ad hoc,
- `systemctl restart meal-planner-rc` z konta `deploy` kończy się `Interactive authentication required`,
- działający RC checkout nie został jeszcze przełączony na osobną bazę, bo nie wdrażano zmian bez akceptacji,
- historycznie RC współdzielił produkcyjną bazę przez hardcoded DSN.

## Sprawdzona bezpieczna ścieżka testowa

Zweryfikowano ręczny RC smoke poza produkcją:

- branch roboczy: `/home/deploy/meal-planner-sprint-0`
- lokalny `.env` w branchu roboczym:
  - `ENV=prod`
  - `APP_INSTANCE=rc`
  - `EXPECTED_DATABASE_NAME=fastapi_db_rc`
  - `DATABASE_URL` wskazujące `fastapi_db_rc`
- ręczny start:

```bash
cd /home/deploy/meal-planner-sprint-0
PYTHONPATH=/home/deploy/meal-planner-sprint-0 \
  /var/www/meal-planner/venv/bin/python -m uvicorn app.main:app \
  --host 127.0.0.1 --port 8002
```

## Wynik smoke testu ręcznego RC

- startup: OK
- połączenie z `fastapi_db_rc`: OK
- `GET /`: `307 -> /login`
- `GET /login`: `200`
- `GET /static/main.css`: `200`
- `GET /api/v1/recipes/`: `401`
- `GET /admin`: `401`
- `GET /openapi.json`: `401`

## Docelowy model RC

RC powinno być:

- na osobnej bazie `fastapi_db_rc`,
- uruchamiane tylko na żądanie,
- wyłączone z autostartu,
- podniesione dopiero po zatwierdzeniu wdrożenia RC i po zmianie jednostki lub checkoutu.

## Co wymaga uprawnień administracyjnych

- `systemctl stop meal-planner-rc`
- `systemctl disable meal-planner-rc`
- `systemctl restart meal-planner-rc`
- modyfikacja `/etc/systemd/system/meal-planner-rc.service`, jeśli ma wskazywać nowy checkout lub nowe `EnvironmentFile`
