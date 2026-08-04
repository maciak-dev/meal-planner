# Panel Admin Extraction

Data aktualizacji: 2026-08-04

## Obecny stan

`panel_admin` nie jest osobną aplikacją. To część obecnego monolitu Meal Plannera.

Najważniejsze elementy:

- HTML: `app/templates/admin_panel.html`
- CSS: `app/static/admin.css`
- UI route: `GET /admin`
- HTML route z logami: `GET /admin/login-logs`
- API routes:
  - `GET /api/v1/admin/login-logs`
  - `GET /api/v1/admin/requests`
- zależności auth:
  - `super_admin` w `app/core/security.py`
  - `super_admin_required` w `app/core/dependencies.py`
- modele/tabele:
  - `users`
  - `login_log`
  - `request_log`

## Zależności od Meal Plannera

Silne:

- wspólny login i cookie JWT,
- wspólne role użytkowników,
- wspólny monolit FastAPI,
- wspólne middleware IP block i request logging,
- wspólne template/static routing.

Słabe:

- ekran admina ma własny template i CSS,
- dane logów są domenowo bardziej „platformowe” niż „meal-plannerowe”.

## Funkcje globalne, kandydat do MAP

- zarządzanie użytkownikami i rolami,
- logi logowania,
- request logs,
- polityki `super_admin`,
- ewentualne blokady i mechanizmy bezpieczeństwa,
- przyszłe health/system diagnostics.

## Funkcje domeny Meal Plannera, które powinny zostać przy module

Na dziś takich funkcji w panelu prawie nie ma. Jeśli w przyszłości dojdą:

- moderacja publicznych przepisów,
- słownik składników,
- kolejność alejek/sklepów,
- domenowe ustawienia list zakupowych,

to powinny zostać przy module Meal Planner, nie w globalnym panelu MAP.

## Najłatwiejsze elementy do wydzielenia

1. API logów (`/api/v1/admin/login-logs`, `/api/v1/admin/requests`)
2. template `admin_panel.html`
3. `admin.css`
4. serwisy `admin_service.py`

## Co wymaga wspólnego auth

- `super_admin`
- model `User`
- JWT cookie i walidacja sesji
- kontrola dostępu do request logów i logów logowania

## Proponowana granica MAP vs Meal Planner

- MAP:
  - auth wspólny,
  - role globalne,
  - system logs,
  - globalny panel administracyjny
- Meal Planner:
  - przepisy,
  - shopping list,
  - ingredients dictionary,
  - planowanie posiłków

## Ryzyka

- obecny panel korzysta z tych samych modeli i sesji co aplikacja,
- duplikacja auth/admin między `main.py` i `app/api/v1/admin.py` utrudni wydzielenie,
- brak odseparowanego kontraktu API i brak testów.

## Weryfikacja po zmianach Sprint 0

- zmiany Sprintu 0 nie modyfikują ścieżek `/admin`, `/admin/login-logs`, `/api/v1/admin/login-logs`, `/api/v1/admin/requests`,
- ręczny start checkoutu RC na branchu `chore/meal-planner-sprint-0` zakończył się poprawnym startupem aplikacji,
- import aplikacji z nową konfiguracją RC nie wykazał błędu zależności auth ani panelu,
- smoke systemowej instancji RC potwierdził `GET /admin -> 401`, co jest poprawnym zachowaniem dla niezalogowanego użytkownika,
- do smoke panelu należy używać `GET`, nie `HEAD`, bo endpointy nie obsługują `HEAD`.

## Rekomendowana kolejność migracji

1. Ujednolicić auth/admin routing.
2. Oddzielić serwisy i router admina od `main.py`.
3. Dodać testy do admin API.
4. Wydzielić panel do osobnego routera/aplikacji w tym samym repo.
5. Dopiero potem przenosić go do MAP.

## Ocena złożoności

- wydzielenie do osobnego routera: niska do średniej
- wydzielenie do osobnej aplikacji z wspólnym auth: średnia
- pełne przeniesienie do MAP: średnia do wysokiej
