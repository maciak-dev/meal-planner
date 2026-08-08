# Production Environment

Data aktualizacji: 2026-08-08

> Aktualny stan operacyjny i ograniczenia zmian opisuje [Production Guardrails](production-guardrails.md). Ten dokument zawiera również informacje historyczne i nie zastępuje obserwacji z VPS.

## Stan bieżący

- Checkout: `/var/www/meal-planner`
- Branch: `main`
- Commit produkcji przed planowanym wdrożeniem: `a734342` (PR #15)
- Zaakceptowany `origin/main`: `0443a4f` (PR #17)
- Oczekujące na wdrożenie: PR #16 (Alembic/schemat) i PR #17 (UI PL/EN)
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
- `Base.metadata.create_all()` aktywne przy starcie — **od wprowadzenia Alembica
  ma to konsekwencję dla kolejności wdrożenia**: restart z kodem zawierającym
  nowe modele utworzy brakujące tabele, ale nie doda kolumn do istniejących, więc
  aplikacja może wystartować na schemacie połowicznym. Migracja musi poprzedzać
  restart. Szczegóły i procedura:
  [alembic-migrations.md](alembic-migrations.md)
- `.env` wskazuje SQLite, choć runtime działa na PostgreSQL
- brak health/ready endpointów
- starsze wpisy tego dokumentu i audytów opisują stan historyczny; bieżący stan commitów należy zawsze potwierdzać przez `git rev-parse HEAD` oraz `git rev-parse origin/main`

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

## Co zostało potwierdzone na RC przed rolloutem produkcyjnym

- RC działa z checkoutu `/var/www/meal-planner-rc`
- RC korzysta z PostgreSQL `fastapi_db_rc`
- RC działa z `ENV=prod`
- RC ustawia `COOKIE_SECURE=True`
- RC nie wykonuje `Base.metadata.create_all()` (`AUTO_CREATE_SCHEMA=False`)
- smoke niezalogowanej sesji przeszedł:
  - `GET / -> 307`
  - `GET /login -> 200`
  - `GET /static/main.css -> 200`
  - `GET /recipes-ui -> 302`
  - `GET /admin -> 401`
- `/admin -> 401` jest poprawnym wynikiem dla niezalogowanego użytkownika
- do smoke należy używać `GET`, ponieważ endpointy nie obsługują `HEAD`
