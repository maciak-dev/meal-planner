# Meal Planner Production Rollout Attempt

Data: 2026-08-05
Zakres: próba wdrożenia Sprintu 0 na produkcję, zakończona przed restartem usługi.

## Wynik

Wdrożenie Sprintu 0 na produkcję zostało przerwane bezpiecznie przed restartem `meal-planner.service`. Produkcyjna aplikacja pozostała uruchomiona na dotychczasowym kodzie, konfiguracji i bazie danych.

Nie wykonano:

- restartu produkcji,
- deployu zakończonego przełączeniem runtime,
- migracji,
- zmian schematu PostgreSQL,
- operacji CRUD na produkcji,
- zmian uploadów,
- pushu do produkcji.

## Stan przed próbą

- Checkout produkcji: `/path/to/production-checkout`
- Branch: `main`
- Commit: `feacd6c`
- Baza runtime: PostgreSQL `fastapi_db`
- Usługa: `meal-planner.service`
- Port: `8000`
- Reverse proxy: `nginx`
- Produkcyjny smoke HTTPS przechodził:
  - `/` -> `307`
  - `/login` -> `200`
  - `/static/main.css` -> `200`
  - `/recipes-ui` -> `302`
  - `/admin` -> `401`

Checkout produkcji miał istniejące, nierozpoznane wcześniej zmiany lokalne:

- `M app/core/config.py` - wyłącznie kosmetyczny diff,
- `?? docs/` - istniejący raport produkcyjny.

## Backup i konfiguracja

Przed próbą utworzono kopię roboczą konfiguracji i pliku `config.py` poza repozytorium:

`/path/to/backup-root/prod-predeploy-<timestamp>/`

W kopii zachowano również istniejący raport z katalogu `docs/`.

W przygotowanym wariancie Sprintu 0 zweryfikowano, że konfiguracja produkcyjna dawałaby:

```text
ENV=prod
APP_INSTANCE=production
DATABASE_NAME=fastapi_db
COOKIE_SECURE=True
AUTO_CREATE_SCHEMA=False
```

Nie ujawniano ani nie commitowano DSN, haseł ani sekretów.

## Próba uruchomienia kodu Sprintu 0

Kod branchu `chore/meal-planner-sprint-0` został tymczasowo przełączony w checkoutcie produkcyjnym wyłącznie w celu walidacji przed restartem. Nie uruchomiono usługi systemowej na tym kodzie.

Wykonano:

- kontrolę `git diff --check`,
- kompilację aplikacji i testów,
- import konfiguracji z produkcyjnym `.env`,
- tymczasowy start na `127.0.0.1:8002`,
- odczytowe requesty GET do `/login`, `/static/main.css` i `/`.

Tymczasowy start aplikacji zakończył się poprawnie. Log potwierdził połączenie z PostgreSQL `fastapi_db`, a requesty zwróciły odpowiednio `200`, `200` i `307`.

## Powód przerwania

Przed restartem nie spełniono wszystkich kryteriów bezpieczeństwa:

1. `sudo systemctl` nie mogło zostać wykonane bez interaktywnego hasła administratora. Nie było możliwości bezpiecznego restartu ani potwierdzenia stanu usługi systemd po zmianie.
2. Dokładne polecenie testów uruchomione w checkoutcie produkcyjnym nie przeszło. Testy odczytywały lokalny produkcyjny `.env` i nie były odizolowane od środowiska produkcyjnego; część testów oczekiwała również innych komunikatów błędów oraz próbowała połączyć się z portem testowym.

W tych warunkach restart produkcji byłby nieuzasadniony.

## Przywrócenie stanu

Po przerwaniu próby:

- checkout produkcji przywrócono na `main`,
- przywrócono wcześniejszy `.env`,
- przywrócono wcześniejszy `app/core/config.py`,
- nie użyto `git reset --hard`,
- nie restartowano produkcji.

Końcowy smoke HTTPS nadal przechodził:

- `/` -> `307`
- `/login` -> `200`
- `/recipes-ui` -> `302`
- `/admin` -> `401`

## Stan końcowy

Produkcja pozostaje na:

- branchu `main`,
- commicie `feacd6c`,
- dotychczasowym środowisku runtime,
- bazie PostgreSQL `fastapi_db`,
- porcie `8000`.

Nie ma podstaw, aby twierdzić, że produkcja została zmieniona lub zrestartowana.

## Zalecany następny krok

Przed ponowną próbą należy:

1. zapewnić kontrolowany dostęp sudo do statusu i restartu usług,
2. odizolować testy od produkcyjnego `.env`,
3. uruchamiać testy z jawnie przygotowanym środowiskiem testowym,
4. ponownie wykonać backup i wszystkie pre-checki,
5. dopiero wtedy przeprowadzić restart oraz smoke produkcyjny według runbooka Sprintu 0.
