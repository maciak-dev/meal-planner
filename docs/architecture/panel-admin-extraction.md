# Panel Admin Extraction

Data aktualizacji: 2026-08-04

## Obecny stan

`panel_admin` nie jest osobną aplikacją. To część obecnego monolitu Meal Plannera.

MAP może odczytać dwa istniejące endpointy logów w owner-only Control Center,
ale Meal nadal jest właścicielem danych, filtrów, roli `super_admin` i sesji.
Jawna lista `MAP_CONTROL_CENTER_ORIGINS` włącza credentialed CORS tylko dla
read methods; brak konfiguracji oznacza brak cross-origin access. Legacy UI
pozostaje aktywne do potwierdzenia parity w realnym użyciu.

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

## Obowiązująca granica MAP vs Meal Planner

- MAP:
  - owner-only UI Control Center,
  - prezentacja odpowiedzi API i degraded state,
  - brak kopii logów i brak credentials Meal
- Meal Planner:
  - własny auth i rola `super_admin`,
  - `login_log` / `request_log` i admin API,
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

## Dalsza kolejność migracji

1. Zweryfikować parity Control Center z legacy UI w realnym użyciu.
2. Ujednolicić zduplikowany auth/admin routing wewnątrz Meal.
3. Zaprojektować osobno jednorazowy, asymetrycznie podpisany owner handoff;
   nie współdzielić `SECRET_KEY`.
4. Dopiero po parity oznaczyć legacy panel jako deprecated.

## Ocena złożoności

- wydzielenie do osobnego routera: niska do średniej
- wydzielenie do osobnej aplikacji z wspólnym auth: średnia
- pełne przeniesienie do MAP: średnia do wysokiej
