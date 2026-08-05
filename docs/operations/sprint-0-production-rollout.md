# Sprint 0 Production Rollout

Data aktualizacji: 2026-08-05

Ten runbook opisuje wdrożenie Sprintu 0 na produkcję. Faza wykonywana przez Codex kończy się przed restartem usługi. Restart wykonuje ręcznie użytkownik z uprawnieniami `sudo` po otrzymaniu pozytywnego pre-checku.

## Docelowy stan

- produkcja pobiera `DATABASE_URL` z lokalnego `.env`,
- baza pozostaje PostgreSQL `fastapi_db`,
- `ENV=prod`,
- `APP_INSTANCE=production`,
- `COOKIE_SECURE=True`,
- `AUTO_CREATE_SCHEMA=False`,
- `Base.metadata.create_all()` nie wykonuje się przy starcie,
- brak fallbacku do SQLite,
- port, domena, uploady i dane pozostają bez zmian.

## Prerequisites

- zweryfikowany backup PostgreSQL, np. `/home/deploy/backups/meal-planner/meal-planner-fastapi_db-20260804T193513Z.dump`,
- dostęp użytkownika do `sudo systemctl`,
- zatwierdzony commit branchu `chore/meal-planner-sprint-0`,
- rozpoznane lokalne zmiany produkcji,
- kopia produkcyjnego `app/core/config.py` i `.env` poza repozytorium,
- potwierdzony DSN wskazujący `fastapi_db`,
- działające `nginx`, PostgreSQL i `meal-planner.service`,
- działający RC z tym samym commitem i osobną bazą `fastapi_db_rc`.

## Faza A — Codex bez sudo

Codex wykonuje poniższe czynności bez restartowania produkcji.

### 1. Backup i pre-check

```bash
ts=$(date -u +%Y%m%dT%H%M%SZ)
dest=/home/deploy/backups/meal-planner/prod-predeploy-$ts
mkdir -p "$dest"
cp /var/www/meal-planner/app/core/config.py "$dest/app-core-config.py"
cp /var/www/meal-planner/.env "$dest/prod.env"

git -C /var/www/meal-planner status --short --branch
git -C /var/www/meal-planner log -1 --oneline
ss -lntp | rg ':8000\b'
curl -sS -o /dev/null -w '/ -> %{http_code}\n' https://maciak.online/
curl -sS -o /dev/null -w '/login -> %{http_code}\n' https://maciak.online/login
curl -sS -o /dev/null -w '/static/main.css -> %{http_code}\n' https://maciak.online/static/main.css
curl -sS -o /dev/null -w '/recipes-ui -> %{http_code}\n' https://maciak.online/recipes-ui
curl -sS -o /dev/null -w '/admin -> %{http_code}\n' https://maciak.online/admin
```

Wykonać świeży `pg_dump -Fc` faktycznie używanej bazy i sprawdzić go przez `ls`, `file` oraz `pg_restore -l`. Nie nadpisywać wcześniejszych dumpów.

### 2. Zabezpieczenie lokalnych zmian

Przed zmianą checkoutu zaklasyfikować każdy lokalny plik jako zachowany, zastąpiony wersją Sprintu 0, zarchiwizowany albo pominięty. Nie używać `git reset --hard` i nie stosować ślepego `rsync --delete`.

Nie usuwać:

- `.env`,
- `venv/`,
- `app/static/uploads/`,
- backupów,
- plików runtime,
- lokalnych raportów audytowych.

### 3. Checkout i konfiguracja

Przełączyć produkcyjny checkout dokładnie na zatwierdzony commit Sprintu 0, zachowując `.env` i uploady. Uzupełnić lokalny `.env` o wartości:

```text
ENV=prod
APP_INSTANCE=production
DATABASE_URL=<produkcyjny DSN PostgreSQL do fastapi_db>
EXPECTED_DATABASE_NAME=fastapi_db
PRODUCTION_DATABASE_NAME=fastapi_db
```

DSN, hasła i `SECRET_KEY` nie mogą trafić do Git ani raportu. Nie kopiować `.env` z RC.

### 4. Walidacja izolowana

W branchu Sprintu 0 uruchomić:

```bash
scripts/test-sprint-0.sh
```

Skrypt czyści środowisko procesu, ustawia fikcyjny DSN `meal_planner_test`, wyłącza dotenv, uruchamia compileall i testy, a następnie sprawdza brak aktywnego hardcoded DSN. Nie łączy się z bazą i nie otwiera socketu.

Następnie zweryfikować rzeczywisty produkcyjny `.env` bez drukowania DSN:

```bash
./scripts/validate-production-config.py --checkout /var/www/meal-planner
```

Oczekiwany wynik:

```text
ENV=prod
APP_INSTANCE=production
DATABASE_NAME=fastapi_db
COOKIE_SECURE=True
AUTO_CREATE_SCHEMA=False
```

Opcjonalne połączenie odczytowe można wykonać wyłącznie jawnie:

```bash
./scripts/validate-production-config.py \
  --checkout /var/www/meal-planner \
  --check-connection
```

### 5. Start tymczasowy i smoke

Na wolnym porcie lokalnym uruchomić krótką instancję tego samego kodu, np. `127.0.0.1:8002`, z produkcyjnym `.env`. Nie wykonywać logowania ani CRUD.

```bash
/var/www/meal-planner/venv/bin/python -m uvicorn app.main:app \
  --host 127.0.0.1 --port 8002
```

W drugim terminalu:

```bash
scripts/smoke-local.sh 8002
```

Oczekiwane kody GET: `/` `307`, `/login` `200`, `/static/main.css` `200`, `/recipes-ui` `302`, `/admin` `401`. Po teście zatrzymać tylko proces tymczasowy.

### 6. Punkt zatrzymania

Codex zatrzymuje się po pozytywnym validatorze i smoke na `8002`, przed `daemon-reload`, `restart` i jakąkolwiek zmianą stanu usługi systemd. Użytkownik otrzymuje wynik pre-deployment oraz poniższe polecenia ręczne.

## Faza B — użytkownik wykonuje sudo

Po zaakceptowaniu pre-checków użytkownik wykonuje:

```bash
sudo systemctl daemon-reload
sudo systemctl restart meal-planner
sleep 3
sudo systemctl status meal-planner --no-pager
```

Następnie należy sprawdzić:

```bash
ss -lntp | rg ':8000\b'
sudo journalctl -u meal-planner -n 100 --no-pager
sudo systemctl status nginx --no-pager
```

Smoke HTTPS wykonuje się żądaniami `GET`, nie `curl -I`:

```bash
curl -sS -o /dev/null -w '/ -> %{http_code}\n' https://maciak.online/
curl -sS -o /dev/null -w '/login -> %{http_code}\n' https://maciak.online/login
curl -sS -o /dev/null -w '/static/main.css -> %{http_code}\n' https://maciak.online/static/main.css
curl -sS -o /dev/null -w '/recipes-ui -> %{http_code}\n' https://maciak.online/recipes-ui
curl -sS -o /dev/null -w '/admin -> %{http_code}\n' https://maciak.online/admin
```

Po restarcie potwierdzić brak `500`, brak SQLite w logach, brak próby `create_all()`, połączenie z `fastapi_db`, dostępność uploadów i poprawne działanie HTTPS. Test cookie `Secure` wymaga bezpiecznego konta testowego; nie wykonywać CRUD na produkcji bez osobnej zgody.

## Stop conditions

Przerwać przed restartem, jeśli:

- backup jest pusty, nieczytelny albo nieweryfikowalny,
- checkout produkcji ma nierozpoznane zmiany,
- validator odrzuca `ENV`, `APP_INSTANCE` lub nazwę bazy,
- `DATABASE_URL` wskazuje SQLite albo inną bazę,
- RC z tym samym commitem nie startuje,
- `scripts/test-sprint-0.sh` nie przechodzi,
- start na `8002` lub lokalny smoke nie przechodzi.

Po restarcie przerwać i rollbackować kod, jeśli usługa nie startuje, wchodzi w restart loop, pojawia się traceback, `500`, SQLite, `COOKIE_SECURE=False`, `AUTO_CREATE_SCHEMA=True` albo brak portu `8000`.

## Rollback

Rollback kodu i restore bazy są osobnymi operacjami. Przy regresji kodu:

```bash
git -C /var/www/meal-planner checkout <previous_commit>
cp /home/deploy/backups/meal-planner/prod-predeploy-<timestamp>/prod.env /var/www/meal-planner/.env
cp /home/deploy/backups/meal-planner/prod-predeploy-<timestamp>/app-core-config.py /var/www/meal-planner/app/core/config.py
sudo systemctl restart meal-planner
```

Po rollbacku wykonać status usługi, logi i smoke HTTPS. Nie odtwarzać bazy przy zwykłym rollbacku kodu. Restore PostgreSQL rozważać dopiero po potwierdzeniu utraty lub uszkodzenia danych albo schematu i po osobnej decyzji operacyjnej.
