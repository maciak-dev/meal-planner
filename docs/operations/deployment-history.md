# Meal Planner Deployment History

Ten dokument jest rejestrem potwierdzonych punktów wdrożeniowych, a nie
guardrailem wymagającym konkretnego SHA. Aktualny stan należy zawsze sprawdzić
odczytowo na VPS i w `origin/main`.

## Potwierdzone punkty

* 2026-08-07 — produkcja po PR #15: `a734342`.
* 2026-08-08 — `origin/main` po scaleniu PR #17: `0443a4f`.
* 2026-08-08 — RC po walidacji PR #16: PostgreSQL `fastapi_db_rc`,
  `alembic current=head=69eea78ac02c`, `alembic check` czysty; test kaskady
  zakończony powodzeniem.
* 2026-08-08 — PR #16 i PR #17 oczekują na osobne wdrożenie produkcyjne;
  PR #17 wymaga pełnego smoke UI PL/EN na świeżej linii RC.

## Reguła aktualizacji

Przed każdym wdrożeniem zapisz w raporcie:

1. `git rev-parse HEAD` produkcyjnego checkoutu;
2. `git rev-parse origin/main`;
3. wynik `git log --oneline` i ocenę, które zatwierdzone PR-y obejmuje różnica;
4. wynik kontroli schematu oraz backupu.

Historyczne SHA mogą pozostać w audytach i wpisach tego rejestru, ale muszą być
opisane datą oraz jako stan historyczny.
