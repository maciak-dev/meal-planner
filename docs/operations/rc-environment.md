# RC Environment

Data aktualizacji: 2026-08-08

## Stan bieżący

- Checkout RC na VPS: `/var/www/meal-planner-rc`
- Branch checkoutu RC przed odświeżeniem PR #17: `rc/meal-alembic-foundation-validation`
- Commit checkoutu RC przed odświeżeniem: `b733644`
- Docelowy branch walidacyjny PR #17: `rc/meal-ui-i18n-validation`, tworzony bezpośrednio z `origin/main=0443a4f`
- Usługa systemowa: `meal-planner-rc.service`
- WorkingDirectory usługi: `/var/www/meal-planner-rc`
- Port usługi: `127.0.0.1:8001`
- Nginx: `rc.maciak.online`
- Baza RC: PostgreSQL `fastapi_db_rc`
- `ENV=prod`
- `COOKIE_SECURE=True`
- `AUTO_CREATE_SCHEMA=False`
- Autostart po zakończeniu smoke: `disabled`
- Status po zakończeniu smoke: `inactive (dead)`

## Co zostało już przygotowane

- checkout RC został przełączony na branch `chore/meal-planner-sprint-0`,
- lokalny plik `/var/www/meal-planner-rc/.env` został zaktualizowany do:
  - `ENV=prod`
  - `APP_INSTANCE=rc`
  - `EXPECTED_DATABASE_NAME=fastapi_db_rc`
  - `PRODUCTION_DATABASE_NAME=fastapi_db`
  - `DATABASE_URL` wskazującego `fastapi_db_rc`
- odczytowy test `psql` potwierdza, że nowe `DATABASE_URL` łączy się jako `fastapi_user` z bazą `fastapi_db_rc`,
- import konfiguracji z checkoutu RC potwierdza:
  - `COOKIE_SECURE=True`
  - `AUTO_CREATE_SCHEMA=False`

## Stan po smoke

- systemowa instancja RC została uruchomiona z checkoutu `/var/www/meal-planner-rc`,
- smoke potwierdził poprawne zachowanie niezalogowanej sesji,
- autostart usługi został wyłączony,
- po smoke usługa RC została zatrzymana,
- produkcja pozostała bez zmian.

## Stan przed walidacją PR #17

- `origin/main=0443a4f` zawiera PR #15, PR #16 i PR #17.
- RC PostgreSQL ma `current=head=69eea78ac02c` i `alembic check` nie wykazuje driftu.
- PR #17 wymaga jeszcze smoke UI PL/EN; nie należy traktować go jako wdrożonego na produkcji.

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

## Wynik smoke testu RC

Smoke należy wykonywać żądaniami `GET`. Aplikacja nie obsługuje `HEAD`, więc wcześniejsze testy typu `curl -I` mogły zwracać `405` mimo poprawnego działania endpointu.

Potwierdzone odpowiedzi systemowej instancji RC:

- `GET /`: `307`
- `GET /login`: `200`
- `GET /static/main.css`: `200`
- `GET /recipes-ui`: `302`
- `GET /admin`: `401`

Interpretacja:

- `307` z `/` jest poprawnym redirectem dla niezalogowanego użytkownika,
- `302` z `/recipes-ui` jest poprawnym przekierowaniem do logowania,
- `401` z `/admin` jest poprawnym zachowaniem dla niezalogowanego użytkownika.

## Wynik smoke testu ręcznego RC

- startup: OK
- połączenie z `fastapi_db_rc`: OK
- `GET /`: `307 -> /login`
- `GET /login`: `200`
- `GET /static/main.css`: `200`
- `GET /api/v1/recipes/`: `401`
- `GET /admin`: `401`
- `GET /openapi.json`: `401`

Dodatkowo po wdrożeniu branchu do checkoutu RC:

- ręczny start checkoutu RC na `127.0.0.1:8002` kończył się poprawnym startupem Uvicorna,
- startup ładował `DB FILE: postgresql://fastapi_user:***@localhost:5432/fastapi_db_rc`,
- lokalny smoke HTTP z osobnego procesu nie był możliwy do pełnego dokończenia z powodu ograniczeń środowiska wykonawczego Codex, ale sam start aplikacji był poprawny.

## Docelowy model RC

RC powinno być:

- na osobnej bazie `fastapi_db_rc`,
- uruchamiane tylko na żądanie,
- wyłączone z autostartu,
- restartowane ręcznie po wdrożeniu nowego checkoutu lub zmianie `.env`,
- zatrzymywane po zakończeniu testów.

## Co wymaga uprawnień administracyjnych

- `systemctl daemon-reload`
- `systemctl stop meal-planner-rc`
- `systemctl disable meal-planner-rc`
- `systemctl restart meal-planner-rc`
- modyfikacja `/etc/systemd/system/meal-planner-rc.service`, jeśli ma wskazywać nowy checkout lub nowe `EnvironmentFile`

## Minimalna procedura aktywacji RC

```bash
sudo systemctl daemon-reload
sudo systemctl restart meal-planner-rc
sudo systemctl status meal-planner-rc --no-pager
sudo systemctl disable meal-planner-rc
```

Po ręcznym starcie należy sprawdzić:

- `systemctl status meal-planner-rc --no-pager`
- `curl -fsS http://127.0.0.1:8001/ -o /dev/null -w '%{http_code}\n'`
- `curl -fsS http://127.0.0.1:8001/login -o /dev/null -w '%{http_code}\n'`
- `curl -fsS http://127.0.0.1:8001/static/main.css -o /dev/null -w '%{http_code}\n'`
- `curl -fsS http://127.0.0.1:8001/recipes-ui -o /dev/null -w '%{http_code}\n'`
- `curl -fsS http://127.0.0.1:8001/admin -o /dev/null -w '%{http_code}\n'`
- odczytowo `psql` na `fastapi_db_rc`
