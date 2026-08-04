# Sprint 0 Production Rollout

Data aktualizacji: 2026-08-04

## Cel

Wdrożyć Sprint 0 Meal Plannera na produkcję bez zmiany domeny, portu, uploadów ani danych PostgreSQL.

Docelowy efekt:

- produkcja pobiera `DATABASE_URL` z `.env`,
- produkcja nadal używa PostgreSQL `fastapi_db`,
- produkcja działa z `ENV=prod`,
- `COOKIE_SECURE=True`,
- `Base.metadata.create_all()` nie wykonuje się przy starcie,
- aplikacja nie może przełączyć się na SQLite.

## Prerequisites

- istnieje zweryfikowany backup:
  - `/home/deploy/backups/meal-planner/meal-planner-fastapi_db-20260804T193513Z.dump`
- dostęp `sudo` do:
  - `systemctl`
  - odczytu logów
- branch do wdrożenia: `chore/meal-planner-sprint-0`
- commit do wdrożenia: `cf9f17c` lub nowszy zatwierdzony commit Sprintu 0
- checkout produkcyjny jest rozpoznany i jego lokalne zmiany są zarchiwizowane
- szczególnie zabezpieczony jest lokalny diff `app/core/config.py`
- potwierdzony jest produkcyjny DSN do `fastapi_db`
- potwierdzone działanie:
  - `nginx`
  - `meal-planner.service`
  - `postgresql`

## Pre-deployment Checks

1. Sprawdzić stan checkoutu produkcyjnego:

```bash
git -C /var/www/meal-planner status --short --branch
git -C /var/www/meal-planner log -1 --oneline
```

2. Jeżeli checkout jest brudny, zapisać kopie lokalnych plików przed zmianą:

```bash
ts=$(date -u +%Y%m%dT%H%M%SZ)
dest=/home/deploy/backups/meal-planner/prod-predeploy-$ts
mkdir -p "$dest"
cp /var/www/meal-planner/app/core/config.py "$dest/app-core-config.py"
cp /var/www/meal-planner/.env "$dest/prod.env"
```

3. Wykonać świeży backup PostgreSQL:

```bash
pg_dump -Fc -h localhost -p 5432 -U <masked_user> -d fastapi_db \
  -f /home/deploy/backups/meal-planner/meal-planner-fastapi_db-$ts.dump
```

4. Zweryfikować backup:

```bash
ls -lh /home/deploy/backups/meal-planner/meal-planner-fastapi_db-$ts.dump
file /home/deploy/backups/meal-planner/meal-planner-fastapi_db-$ts.dump
pg_restore -l /home/deploy/backups/meal-planner/meal-planner-fastapi_db-$ts.dump
```

5. Sprawdzić stan usługi i portów:

```bash
sudo systemctl status meal-planner --no-pager
ss -lntp | rg ':8000|:443|:80|:5432'
```

6. Potwierdzić aktywną bazę i produkcyjny DSN bez ujawniania sekretów:

- `.env` ma zawierać `ENV=prod`
- `.env` ma zawierać `DATABASE_URL` wskazujący `fastapi_db`
- aplikacja nie może wskazywać `sqlite`

7. Wykonać smoke przed wdrożeniem:

```bash
curl -fsS http://127.0.0.1:8000/ -o /dev/null -w '%{http_code}\n'
curl -fsS http://127.0.0.1:8000/login -o /dev/null -w '%{http_code}\n'
curl -fsS http://127.0.0.1:8000/static/main.css -o /dev/null -w '%{http_code}\n'
curl -fsS http://127.0.0.1:8000/recipes-ui -o /dev/null -w '%{http_code}\n'
curl -fsS http://127.0.0.1:8000/admin -o /dev/null -w '%{http_code}\n'
```

Do smoke należy używać `GET`. Endpointy nie obsługują `HEAD`, więc `curl -I` może zwracać `405`.

## Deployment

1. Potwierdzić, że commit Sprintu 0 jest zatwierdzony i przetestowany na RC.

2. Przygotować produkcyjny checkout do dokładnie tego commita.

Preferowany model:

- checkout produkcyjny ma wskazać commit Sprintu 0,
- `.env` produkcji ma zostać zachowany lokalnie i poprawiony ręcznie,
- uploady w `app/static/uploads` pozostają nietknięte.

3. Ustawić produkcyjny `.env` tak, aby zawierał co najmniej:

- `ENV=prod`
- `DATABASE_URL=<masked fastapi_db dsn>`
- `SECRET_KEY=<existing secret>`
- `PRODUCTION_DATABASE_NAME=fastapi_db`

Opcjonalnie:

- `APP_INSTANCE=production`
- `EXPECTED_DATABASE_NAME=fastapi_db`

4. Upewnić się, że w kodzie:

- nie ma hardcoded DSN,
- brak `DATABASE_URL` kończy start czytelnym błędem,
- brak fallbacku do SQLite,
- `AUTO_CREATE_SCHEMA=False` dla `ENV=prod`.

5. Nie wykonywać migracji.

## Restart

```bash
sudo systemctl daemon-reload
sudo systemctl restart meal-planner
sudo systemctl status meal-planner --no-pager
journalctl -u meal-planner -n 100 --no-pager
ss -lntp | rg ':8000\b'
sudo systemctl status nginx --no-pager
```

## Smoke po wdrożeniu

Wszystkie kontrole robić żądaniami `GET`.

```bash
curl -fsS http://127.0.0.1:8000/ -o /dev/null -w '%{http_code}\n'
curl -fsS http://127.0.0.1:8000/login -o /dev/null -w '%{http_code}\n'
curl -fsS http://127.0.0.1:8000/static/main.css -o /dev/null -w '%{http_code}\n'
curl -fsS http://127.0.0.1:8000/recipes-ui -o /dev/null -w '%{http_code}\n'
curl -fsS http://127.0.0.1:8000/admin -o /dev/null -w '%{http_code}\n'
curl -fsS http://127.0.0.1:8000/api/v1/recipes/ -o /dev/null -w '%{http_code}\n'
```

Do potwierdzenia:

- `/` odpowiada poprawnym redirectem
- `/login` działa
- statyczne assety działają
- `/recipes-ui` zachowuje się poprawnie dla niezalogowanej sesji
- `/admin` nie zwraca `500`
- chronione API zwraca kontrolowany `401`, nie `500`
- cookie po logowaniu ma flagę `Secure`
- runtime łączy się z `fastapi_db`
- logi startowe nie pokazują `create_all`
- brak odpowiedzi `500`
- brak śladów użycia SQLite

## Rollback

Rollback kodu i restore bazy to dwie różne operacje.

### Rollback kodu

Stosować, gdy:

- aplikacja nie startuje,
- smoke po wdrożeniu nie przechodzi,
- występują regresje konfiguracyjne,
- baza danych pozostała nienaruszona.

Kroki:

```bash
git -C /var/www/meal-planner checkout <previous_commit>
cp /home/deploy/backups/meal-planner/prod-predeploy-<timestamp>/prod.env /var/www/meal-planner/.env
cp /home/deploy/backups/meal-planner/prod-predeploy-<timestamp>/app-core-config.py /var/www/meal-planner/app/core/config.py
sudo systemctl restart meal-planner
sudo systemctl status meal-planner --no-pager
```

Po rollbacku:

- sprawdzić smoke produkcji,
- potwierdzić połączenie z `fastapi_db`,
- potwierdzić, że aplikacja nie używa SQLite.

### Restore bazy

Restore bazy rozważać tylko wtedy, gdy problem dotyczy danych lub schematu. Sam rollback kodu nie powinien wymagać restore bazy.

Warunki użycia restore:

- potwierdzona utrata lub uszkodzenie danych,
- zwykły rollback kodu nie przywraca poprawnego działania,
- istnieje zweryfikowany dump,
- decyzja została świadomie zatwierdzona.

## Stop Conditions

Wdrożenie należy przerwać, jeśli:

- backup nie jest poprawny,
- checkout produkcji jest brudny i zmiany nie są rozpoznane,
- `DATABASE_URL` wskazuje inną bazę niż `fastapi_db`,
- test połączenia z PostgreSQL nie przechodzi,
- aplikacja nie startuje na RC z tym samym commitem,
- smoke produkcji przed wdrożeniem nie przechodzi,
- po restarcie pojawiają się błędy `500`,
- produkcja próbuje użyć SQLite.

## Czynności wymagające sudo

- `systemctl daemon-reload`
- `systemctl restart meal-planner`
- `systemctl status meal-planner --no-pager`
- `systemctl status nginx --no-pager`
- odczyt logów usługi, jeśli lokalna polityka tego wymaga
