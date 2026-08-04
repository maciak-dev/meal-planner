# PostgreSQL Backup And Restore

Data aktualizacji: 2026-08-04

## Faktyczny backup wykonany w tym sprincie

- Źródłowa baza: `fastapi_db`
- Ścieżka: `/home/deploy/backups/meal-planner/meal-planner-fastapi_db-20260804T193513Z.dump`
- Format: PostgreSQL custom dump (`pg_dump -Fc`)
- Rozmiar: około `4.7M`
- Integralność:
  - `file` rozpoznaje plik jako `PostgreSQL custom database dump - v1.14-0`
  - `pg_restore -l` odczytuje TOC poprawnie

## Polecenie użyte do backupu

Hasło nie było zapisywane w skrypcie ani dokumentacji. Backup został wykonany przez istniejące dane połączeniowe aplikacji.

Logicznie odpowiada to:

```bash
pg_dump -Fc -h localhost -p 5432 -U <masked_user> -d fastapi_db \
  -f /home/deploy/backups/meal-planner/meal-planner-fastapi_db-<timestamp>.dump
```

## Weryfikacja backupu

```bash
ls -lh /home/deploy/backups/meal-planner/meal-planner-fastapi_db-20260804T193513Z.dump
file /home/deploy/backups/meal-planner/meal-planner-fastapi_db-20260804T193513Z.dump
pg_restore -l /home/deploy/backups/meal-planner/meal-planner-fastapi_db-20260804T193513Z.dump
```

## Test restore wykonany w tym sprincie

Restore wykonano do istniejącej pomocniczej bazy:

- cel: `fastapi_db_rc`
- wynik: sukces
- po restore liczności tabel zgadzają się z produkcją:
  - `users=5`
  - `recipes=64`
  - `ingredients=0`
  - `login_log=39`
  - `request_log=318025`

Logika polecenia restore:

```bash
pg_restore --clean --if-exists --no-owner --no-privileges \
  -h localhost -p 5432 -U <masked_user> \
  -d fastapi_db_rc \
  /home/deploy/backups/meal-planner/meal-planner-fastapi_db-20260804T193513Z.dump
```

## Stan bazy RC po smoke

- checkout RC używa `DATABASE_URL` wskazującego `fastapi_db_rc`
- odczytowy test `psql` potwierdza aktywną bazę `fastapi_db_rc`
- aplikacja RC działa z `ENV=prod`
- `AUTO_CREATE_SCHEMA=False`, więc startup RC nie próbuje wykonać `create_all`
- read-only smoke HTTP mógł zwiększyć liczbę rekordów w `request_log`, bo aplikacja loguje żądania także na RC

## Ograniczenia

- nie potwierdzono automatycznego harmonogramu backupów,
- historyczny `prod_postgres_backup.sql` ma `0 B` i nie jest wiarygodnym backupem,
- restore do `fastapi_db_rc` został potwierdzony,
- nowe `DATABASE_URL` checkoutu RC łączy się już odczytowo z `fastapi_db_rc`,
- aktywacja systemowej usługi RC nadal wymaga restartu przez administratora.

## Minimalna procedura przed restartem produkcji

1. Wykonać świeży backup produkcyjnej bazy.
2. Zweryfikować `pg_restore -l`.
3. Odtworzyć dump do bazy RC/testowej.
4. Porównać liczności i schemat z produkcją.
5. Dopiero potem planować restart produkcji lub zmianę `ENV`.
