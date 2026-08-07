# Production Guardrails

Data obserwacji: 2026-08-07 UTC.

## Cel

Ten dokument jest obowiązkową instrukcją dla osób i agentów pracujących nad Meal Plannerem bez bezpośredniego dostępu do VPS. Opisuje stan faktyczny, granice bezpiecznych zmian i procedurę weryfikacji. Nie jest planem migracji ani docelową architekturą.

## Źródła prawdy

* Kod uruchomiony na produkcji: `/var/www/meal-planner`, obecnie commit `9e64b73e1ee84eed4e296ee09dac7844005e0ceb`.
* Kod w GitHubie: remote `origin`; na dzień obserwacji `origin/main` wskazuje `feacd6c51e5d562a0568244f63d577aa3323581d` i nie jest tym samym stanem co uruchomiona produkcja. Nie zakładaj, że `main` jest źródłem aktualnego runtime.
* Konfiguracja produkcji: systemd, `/var/www/meal-planner/.env` oraz aktywny plik Nginx na VPS. Wartości sekretów pozostają wyłącznie na VPS.
* Dokumentacja: pliki `docs/` w repo, z zastrzeżeniem, że starsze audyty mogą opisywać stan historyczny.
* Dane i konta: PostgreSQL `fastapi_db` na localhost, tabele aplikacyjne `users`, `recipes`, `ingredients`, `login_log`, `request_log`.
* Sesje i logowanie: kod aplikacji oraz konfiguracja cookies w runtime; dane kont są w tabeli `users`, a sesja jest w cookie `access_token`.
* Uploady: `/var/www/meal-planner/app/static/uploads` na VPS.
* Reverse proxy i domeny: `/etc/nginx/sites-available/meal-planner` oraz aktywne linki w `/etc/nginx/sites-enabled/`.
* Deployment: ręczna obsługa checkoutu/systemd na VPS; nie znaleziono potwierdzonego automatycznego pipeline’u ani harmonogramu backupu Meal Plannera.
* Backupy: `/home/deploy/backups/meal-planner/`. Znany poprawny produkcyjny dump custom z 2026-08-05 to `meal-planner-fastapi_db-20260805T083834Z.dump`; `pg_restore -l` przechodzi. Plik z 2026-08-04 o rozmiarze 0 B jest nieużywalny.

## Topologia produkcji

Stan obecny:

* `meal-planner.service` (systemd, enabled) uruchamia Uvicorn z `/var/www/meal-planner` na `0.0.0.0:8000`.
* Nginx terminates HTTPS dla `maciak.online` i `www.maciak.online`, a następnie proxy’uje do `127.0.0.1:8000`.
* PostgreSQL nasłuchuje lokalnie na `127.0.0.1:5432`; produkcyjna baza to `fastapi_db`.
* Aplikacja nie korzysta obecnie z Docker Compose ani obrazu Docker. Znalezione kontenery `map-*` i `n8n` należą do odrębnego stosu MAP/n8n i nie są częścią Meal Plannera.

RC:

* `/var/www/meal-planner-rc` jest osobnym checkoutem.
* `meal-planner-rc.service` jest obecnie `disabled` i `inactive`; gdy jest uruchamiany, nasłuchuje tylko na `127.0.0.1:8001`.
* Nginx ma osobny vhost `rc.maciak.online`, ograniczony allowlistą IP, proxy’ujący do `127.0.0.1:8001`.
* RC używa `ENV=prod`, `APP_INSTANCE=rc`, `DATABASE_NAME=fastapi_db_rc`, `EXPECTED_DATABASE_NAME=fastapi_db_rc`; potwierdzona konfiguracja nie wskazuje produkcyjnej bazy.

Nazwy planowane, nieaktywne i niekonfigurowane w tej sesji: `meal.maciak.online` oraz `rc.meal.maciak.online`. Nie zmieniaj domen.

## Logowanie

Meal Planner ma własne logowanie FastAPI. Endpointy `/login`, `/logout` i `/auth/me` są w `app/main.py`, a API logowania jest pod `/api/v1/auth/login`. Hasła są przechowywane jako hashe w `users`; nie zapisujemy danych kont ani sekretów w repo. Cookie `access_token` jest HttpOnly, `SameSite=Lax`, ma ścieżkę `/`, a w produkcji jest Secure. Redirecty, domena cookies i HTTPS zależą od aplikacji oraz Nginx.

Nie zmieniaj bez testu na RC logowania, cookies, redirectów, middleware ani ustawień proxy. Reset hasła i publiczna rejestracja nie są obecnie potwierdzonymi funkcjami. Integracja logowania z MAP nie należy do tego baseline’u.

## Krytyczne pliki i ścieżki

| Element | Ryzyko zmiany |
| --- | --- |
| `app/main.py`, `app/api/`, `app/core/` | routing, auth, middleware, baza i start aplikacji mogą przerwać runtime |
| migracje Alembic i modele | nieodwracalne rozbieżności schematu lub utrata danych |
| `.env` | sekret, baza, tryb i cookies; nie commitować i nie kopiować do repo |
| `meal-planner.service`, `meal-planner-rc.service` | zły checkout, port, użytkownik lub autostart może zmienić środowisko |
| `/etc/nginx/sites-available/meal-planner*` | domeny, TLS, allowlist RC i proxy mogą odciąć usługę lub ujawnić RC |
| `/var/www/meal-planner/app/static/uploads` | trwałe dane użytkowników; nie usuwać ani nie wersjonować |
| `app/static/` i generowane zasoby | brak zasobów lub niekompatybilny frontend |
| skrypty wdrożeniowe i backupu | nieprzewidywalny deploy albo brak rollbacku |
| porty `8000`, `8001`, `5432` | kolizja usług lub połączenie z niewłaściwą bazą |

## Czego nie wolno zmieniać zdalnie bez kontroli VPS

Bez potwierdzenia administratora VPS i testu na RC nie zmieniaj nazw ani mountów wolumenów, ścieżek bazy, migracji, domen, redirectów, cookies, logowania, reverse proxy, portów, Docker build contextu, plików `.env`, uploadów, sposobu uruchamiania produkcji ani sposobu wdrażania RC. Nie zakładaj, że zmiana w MAP jest niezależna: stos MAP/n8n działa na tym samym VPS i wymaga osobnej kontroli. Nie wykonuj zmian danych, restore ani downgrade’u migracji jako automatycznej części pracy agenta.

## Ograniczenia VPS

VPS ma około 2 GB RAM i brak swapu. Nie uruchamiaj równolegle ciężkich buildów, pełnych testów obciążeniowych ani niepotrzebnych restartów. Preferuj lokalne buildy/testy. Jeśli build na VPS jest konieczny, wykonuj go sekwencyjnie, po backupie, z kontrolą pamięci i bez równoległych operacji. Nie używaj `docker compose down -v`, nie usuwaj wolumenów i nie wykonuj force push.

## Bezpieczny workflow

```text
zdalny feature branch
→ lokalne testy i build
→ PR
→ review zgodności z guardrails
→ RC
→ test logowania i danych
→ backup
→ deploy produkcyjny
→ smoke test
→ rollback albo akceptacja
```

Remote agent może przygotować kod, testy i dokumentację. Operacje na VPS, bazie, proxy, usługach, backupach i danych wymagają jawnej kontroli administratora.

## Obowiązkowe testy RC i produkcji

Checklistę dopasuj do faktycznych endpointów i UI:

* strona startowa, `/login`, routing i zasoby statyczne;
* logowanie, wylogowanie, utrzymanie sesji i `/auth/me`;
* administracyjne tworzenie użytkowników oraz logi, jeśli testujący ma uprawnienia;
* podstawowe CRUD przepisów, widoczność, obraz i listę przepisów;
* odczyt oraz zapis danych składników i posiłków/przepisów, jeśli dana wersja UI je udostępnia;
* lista zakupów, jeśli jest obecna w testowanym checkoutcie;
* API `/api/v1`, kontrola odpowiedzi 401/403/404 i brak 500;
* widok desktop/mobile;
* stan bazy i migracje wyłącznie odczytowo przed zmianą;
* brak nowych tracebacków w logach;
* trwałość danych po kontrolowanym restarcie kontenera/usługi, tylko za zgodą VPS.

Nie deklaruj rejestracji, resetu hasła, planera posiłków ani integracji MAP bez potwierdzenia ich obecności w konkretnym checkoutcie.

## Rollback

Rollback aplikacji jest ręczny i nie jest obecnie pełnym, automatycznym mechanizmem. Przed wdrożeniem zapisz commit, konfigurację i backup bazy. Administrator wybiera znany poprzedni checkout/commit, przywraca wyłącznie zatwierdzone pliki runtime, wykonuje restart `meal-planner.service` i smoke test. Przy problemie danych restore PostgreSQL z poprawnego dumpa wymaga osobnej decyzji, okna serwisowego i weryfikacji; nie wykonuj go automatycznie. Nie przywracaj `.env` z repo ani z niezweryfikowanego backupu.

## Znane ograniczenia i dług techniczny

* `/var/www/meal-planner` jest osobnym produkcyjnym checkoutem; aktywny commit nie jest aktualnym `origin/main`.
* Istnieją trzy checkouty Meal Plannera: produkcyjny `/var/www/meal-planner`, RC `/var/www/meal-planner-rc` oraz roboczy `/home/deploy/meal-planner-sprint-0`; ich role nie wynikają z samej nazwy katalogu.
* RC jest obecnie zatrzymany i ma wyłączony autostart.
* Część starszych dokumentów opisuje historyczną konfigurację i wymaga aktualizacji; ten dokument opisuje obserwację z 2026-08-07.
* W checkoutach są legacy artefakty SQLite, ale aktywna produkcja używa PostgreSQL; nie usuwaj ich bez osobnej decyzji i backupu.
* Nie potwierdzono automatycznego backupu Meal Plannera; katalog backupów zawiera zarówno poprawne dumpy, jak i historyczny plik 0 B.
* Deployment i rollback są ręczne, a brak repozytoryjnego Compose/Dockerfile oznacza, że proces kontenerowy MAP nie jest procesem Meal Plannera.
