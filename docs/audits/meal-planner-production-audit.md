# Meal Planner Production Audit

Data audytu: 2026-08-04
Zakres: audyt działającej instancji produkcyjnej na VPS, bez zmian w kodzie, konfiguracji i bazie danych.

## 1. Executive Summary

Produkcyjna aplikacja działa publicznie pod `https://maciak.online/`, jest uruchomiona jako usługa `systemd`, reverse proxy zapewnia `nginx`, a dane aplikacyjne są faktycznie przechowywane w PostgreSQL 14 (`fastapi_db`). Równolegle istnieje ograniczona IP instancja RC pod `https://rc.maciak.online/`.

Realny produkt to dziś przede wszystkim Recipe Manager z prostą, lokalną listą zakupów. Działa logowanie, UI przepisów, upload obrazów, role admin/super_admin, panel logów i chronione API. Nie ma modelu tygodnia, dnia, slotów posiłków, porcji, historii planów ani trwałej serwerowej listy zakupów.

Największe ryzyka nie wynikają z bieżącej awarii, tylko z driftu środowiskowego i technicznego: publiczna produkcja ma `ENV=dev`, co włącza `Base.metadata.create_all()` na starcie i wyłącza `COOKIE_SECURE`; `.env` wskazuje SQLite, ale kod ignoruje to i na stałe łączy się z PostgreSQL; brak migracji; brak testów; brak potwierdzonego automatycznego backupu; frontend i routing są niespójnie rozwijane. Mimo tego rdzeń działa stabilnie i nadaje się do odświeżenia, ale najpierw trzeba uporządkować warstwę operacyjną i bezpieczeństwo.

## 2. Zakres i ograniczenia audytu

Dostęp obejmował:
- checkout produkcyjny i RC na VPS,
- konfigurację `nginx` i `systemd`,
- działające procesy i porty,
- tylko-odczytowe zapytania do PostgreSQL,
- bezpieczne requesty HTTP/HTTPS bez logowania,
- logi systemowe i agregaty z tabel logów.

Celowo nie wykonywałem:
- logowania na konto użytkownika,
- tworzenia, edycji i usuwania danych,
- restartów usług,
- migracji,
- zmian plików aplikacji i konfiguracji poza utworzeniem tego raportu.

Ograniczenia:
- `docs/audits/meal-planner-audit.md` nie istnieje w wdrożonym repo, więc weryfikacja wcześniejszego audytu opiera się na treści dostarczonej w zadaniu oraz na stanie produkcji i kodu.
- Nie było bezpiecznego konta testowego do pełnego potwierdzenia zalogowanego CRUD przez UI.
- Część logów `journalctl` była ograniczona uprawnieniami grup systemowych, ale wystarczająca do oceny ostatnich zdarzeń i statusu usług.

## 3. Środowisko produkcyjne

- Ścieżka aplikacji: `/var/www/meal-planner`
- Dodatkowa instancja: `/var/www/meal-planner-rc`
- Repozytorium: `https://github.com/maciak-dev/meal-planner.git`
- Branch produkcji: `main`
- Commit produkcji: `feacd6c` (`UI polish and admin redesign`)
- `git status` produkcji: `M app/core/config.py`
- `git status` RC: czysty
- Proces produkcji: `uvicorn app.main:app --host 0.0.0.0 --port 8000`
- Proces RC: `uvicorn app.main:app --host 127.0.0.1 --port 8001`
- Mechanizm uruchomienia: `systemd`, jednostka `meal-planner.service`
- Port backendu produkcji: `8000`
- Port backendu RC: `8001`
- Reverse proxy: `nginx`
- Domena produkcyjna: `maciak.online`, `www.maciak.online`
- Domena RC: `rc.maciak.online`, ograniczona przez `allow 84.40.235.93; deny all;`
- Baza danych używana przez proces produkcyjny: PostgreSQL 14 na `localhost:5432`, baza `fastapi_db`
- Uploady: `/var/www/meal-planner/app/static/uploads`
- Logi: `journalctl`, globalne logi `nginx` w `/var/log/nginx/access.log` i `/var/log/nginx/error.log` skonfigurowane w `nginx.conf`; aplikacja zapisuje requesty i loginy także do PostgreSQL
- Deployment: ręczny checkout + `systemd`; brak śladu Dockera dla Meal Plannera

### 3.1. Skąd runtime bierze `ENV` i `DATABASE_URL`

Źródło runtime trzeba rozdzielić na dwa poziomy:

- `systemd` dla produkcji i RC przekazuje tylko `PATH`.
- `WorkingDirectory` ustawia odpowiednio `/var/www/meal-planner` i `/var/www/meal-planner-rc`.
- `app/core/config.py` wykonuje `load_dotenv()` bez jawnej ścieżki, więc ładuje `.env` z bieżącego katalogu roboczego procesu.

To oznacza:

- produkcyjny proces pobiera `ENV` z `/var/www/meal-planner/.env`,
- RC pobiera `ENV` z `/var/www/meal-planner-rc/.env`,
- ale `DATABASE_URL` z `.env` nie jest realnym źródłem prawdy dla żadnej z tych instancji, bo `app/core/config.py` nadpisuje je stałą wartością PostgreSQL wpisaną bezpośrednio w kodzie.

W praktyce działający kod robi więc to:

1. `load_dotenv()` ładuje `.env`,
2. `ENV = os.getenv("ENV", "dev")` bierze wartość z `.env`,
3. `DATABASE_URL = "postgresql://..."` ignoruje `DATABASE_URL` z `.env`,
4. `COOKIE_SECURE = ENV == "prod"` zależy wyłącznie od `ENV`.

### 3.2. Dlaczego `.env` wskazuje SQLite, a proces używa PostgreSQL

Produkcja ma w `.env` wpis:

- `ENV=dev`
- `DATABASE_URL=sqlite:////var/www/meal-planner/data/meal_etl.db`

Jednocześnie wdrożony kod w `app/core/config.py` ma twardo wpisane PostgreSQL. To nie jest zachowanie warunkowe ani fallback. To zwykłe nadpisanie wartości z `.env`.

Wniosek:

- `.env` jest legacy artefaktem lub niesfinalizowaną konfiguracją po wcześniejszym etapie pracy ze SQLite,
- rzeczywista produkcja działa na PostgreSQL dlatego, że wymusza to kod, nie dlatego, że poprawnie skonfigurowano `.env`.

To samo dotyczy RC:

- RC `.env` wskazuje PostgreSQL,
- ale i tak runtime RC kończy na tym samym hardcoded PostgreSQL z `config.py`.

### 3.3. Niezacommitowany `app/core/config.py`

Pełny semantyczny diff zmian niezacommitowanych w `app/core/config.py`, z pominięciem sekretów, bo raport nie może ich ujawniać:

```diff
diff --git a/app/core/config.py b/app/core/config.py
index e8ab553..4cebb63 100644
--- a/app/core/config.py
+++ b/app/core/config.py
@@ -7,7 +7,7 @@ load_dotenv()
ENV = os.getenv("ENV", "dev")  # dev lub prod
 SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret")
 DATABASE_URL = "postgresql://<redacted>@localhost:5432/fastapi_db"
-#DATABASE_URL = "sqlite:////home/vboxuser/fastapi-projekt/app/db/app.db"
+# DATABASE_URL = "sqlite:////home/vboxuser/fastapi-projekt/app/db/app.db"
 COOKIE_SECURE = ENV == "prod"
 ALGORITHM = "HS256"
-ACCESS_TOKEN_EXPIRE_MINUTES = 60
\ No newline at end of file
+ACCESS_TOKEN_EXPIRE_MINUTES = 60
```

To ważne: niezacommitowany diff nie dodaje SQLite ani PostgreSQL. Zmienia tylko:

- odstęp po `#` w zakomentowanej linii SQLite,
- końcowy newline pliku.

Substancjalna zmiana z SQLite na PostgreSQL została dodana wcześniej w commicie `55963dc` z 2026-05-19 (`Add PostgreSQL support and template compatibility fixes`).

### 3.4. Czy niezacommitowana zmiana pochodzi z próby przełączenia na SQLite

Nie. Sama niezacommitowana zmiana nie wygląda na próbę dodania SQLite ani przełączenia bazy. Jest czysto kosmetyczna.

Natomiast plik jako całość nosi ślad wcześniejszej migracji lub ręcznego przejścia:

- przed commitem `55963dc` aktywna była linia SQLite,
- w commicie `55963dc` aktywna linia została zmieniona na PostgreSQL,
- stara linia SQLite została pozostawiona w komentarzu.

To oznacza:

- ślad SQLite w `config.py` jest historyczny,
- obecny niezacommitowany diff nie jest źródłem przejścia na SQLite,
- wcześniejszy lokalny audyt, który traktował SQLite jako prawdę produkcyjną, pomylił stan `.env` i legacy komentarzy ze stanem runtime.

### 3.5. Czy działający proces startował przed czy po tej zmianie

Obecne procesy `meal-planner` i `meal-planner-rc` wystartowały `2026-08-04 11:24:38 UTC`.

Metadane plików:

- `/var/www/meal-planner/app/core/config.py` ma `mtime=2026-05-22 21:04:49 UTC`,
- `/var/www/meal-planner-rc/app/core/config.py` ma `mtime=2026-05-19 19:51:43 UTC`.

Wniosek:

- oba działające dziś procesy zostały uruchomione po zapisaniu obecnej treści `config.py`,
- produkcja i RC startowały już z plikiem zawierającym twardo wpisane PostgreSQL,
- nie da się z tego wywnioskować, kiedy dokładnie powstał kosmetyczny diff w sensie `git`, ale da się wywnioskować, że działające procesy nie zostały uruchomione ze starszą wersją `config.py` sprzed aktywnego PostgreSQL.

### 3.6. Czy produkcja i RC używają tej samej bazy PostgreSQL

Tak. Potwierdzenie:

- produkcyjny runtime engine: `postgresql://fastapi_user:***@localhost:5432/fastapi_db`
- RC runtime engine: `postgresql://fastapi_user:***@localhost:5432/fastapi_db`
- RC `.env` również wskazuje `fastapi_db`

To oznacza, że:

- RC nie ma odseparowanej bazy danych,
- RC i produkcja współdzielą ten sam PostgreSQL i ten sam logical database,
- wszelkie testy zapisujące na RC byłyby testami na produkcyjnych danych.

To jest bardzo ważne ograniczenie bezpieczeństwa zmian.

### 3.7. Backup i odtwarzanie

Stan potwierdzony na VPS:

- `/home/deploy/backups/prod_postgres_backup.sql` istnieje, ale ma rozmiar `0 B` i `mtime=2026-05-22 20:37:34 UTC`
- `/home/deploy/backups/prod_sqlite_backup.db` istnieje i ma ok. `8.1 MB`
- `/home/deploy/backups/rc_backup.sql` istnieje i ma ok. `31 KB`
- w historii powłoki istnieją ślady ręcznych poleceń `pg_dump` i kopiowania SQLite

Wniosek operacyjny:

- nie ma potwierdzonego aktualnego, użytecznego backupu produkcyjnego PostgreSQL,
- istnieje materialny ślad nieudanego lub pustego dumpa PostgreSQL,
- istnieje backup RC, ale RC współdzieli tę samą bazę, więc nie jest to oddzielna strategia ochrony produkcji,
- nie znalazłem udokumentowanej, wersjonowanej i potwierdzalnej procedury restore.

Nie można więc dziś uczciwie stwierdzić, że backup i procedura odtworzenia są gotowe operacyjnie.

### 3.8. Gdzie dokładnie ustawiane są `ENV=dev` i `COOKIE_SECURE`

`ENV=dev`:

- jest ustawione wprost w `/var/www/meal-planner/.env`.
- produkcyjna jednostka `systemd` nie nadpisuje `ENV`.
- `load_dotenv()` ładuje ten plik przy starcie procesu.

`COOKIE_SECURE`:

- nie jest ustawiane w `.env`,
- jest obliczane w `app/core/config.py` jako `COOKIE_SECURE = ENV == "prod"`.

Na publicznej produkcji daje to dziś:

- `ENV == "dev"`
- `COOKIE_SECURE == False`

### 3.9. Skutki zmiany produkcji na `ENV=prod`

Skutki bezpośrednie wynikające z obecnego kodu:

- `Base.metadata.create_all()` przestanie być wykonywane przy starcie aplikacji,
- `COOKIE_SECURE` zmieni się z `False` na `True`.

Skutki praktyczne:

- nowe logowanie ustawi cookie z flagą `Secure`,
- sesje po HTTPS powinny działać poprawnie,
- jeśli istnieją ukryte zależności od trybu dev, wyjdą przy restarcie lub deployu,
- brak `create_all()` oznacza, że kolejne starty będą zależeć wyłącznie od istniejącego schematu PostgreSQL, co jest pożądane, ale trzeba to sprawdzić najpierw poza produkcją,
- ponieważ produkcja i RC współdzielą bazę, nie wolno traktować samej zmiany `ENV` na RC jako w pełni bezpiecznego testu bez dodatkowej izolacji.

Najważniejszy wniosek: samo przełączenie na `ENV=prod` jest merytorycznie właściwe, ale operacyjnie nie powinno być pierwszym ruchem bez wcześniejszego backupu, staging i smoke testów.

### 3.10. Co najpierw da się bezpiecznie testować na RC

Ponieważ RC współdzieli produkcyjną bazę, bezpieczne są tylko testy niedotykające zapisu danych lub schematu. Najpierw można tam sprawdzać:

- zachowanie `nginx` i reverse proxy,
- odpowiedzi `GET` bez logowania,
- statyczne pliki, uploady i routing,
- nagłówki bezpieczeństwa,
- health/ready po ich dodaniu, o ile byłyby tylko odczytowe,
- zachowanie cookie i redirectów po zmianach konfiguracyjnych, ale dopiero po odseparowaniu RC od produkcyjnej bazy albo przy absolutnej pewności, że test nie zapisze nic do DB.

Przed bezpiecznym testowaniem zmian funkcjonalnych na RC trzeba najpierw odseparować przynajmniej jedno z:

- bazę PostgreSQL,
- uploady,
- konto i dane testowe,
- lub całe środowisko staging.

## 4. Architektura

- Backend: pojedyncza aplikacja FastAPI w `app/main.py`
- Frontend: Jinja templates + jeden główny plik JS `app/static/recipes.js` + CSS
- Routing:
  - UI i część auth/admin w `app/main.py`
  - API v1 w `app/api/v1/router.py`
  - osobne moduły `auth.py`, `admin.py`, `recipes.py`
- Baza:
  - rzeczywisty runtime: PostgreSQL
  - w repo i plikach są też legacy artefakty SQLite (`app.db`, backup SQLite, `meal_etl.db`, `.env` wskazujące SQLite)
- Auth: JWT w cookie `access_token`, role `user` / `admin` / `super_admin`
- Admin: panel HTML `/admin` oraz API `/api/v1/admin/*`
- API:
  - `/api/v1/auth/login`
  - `/api/v1/recipes/*`
  - `/api/v1/admin/*`
- Uploady obrazków: pliki w `app/static/uploads`, ścieżka URL zapisywana w `recipes.image`
- Obserwowalność: `login_log`, `request_log`, panel admina, middleware logujące

Najważniejsze obserwacje architektoniczne:
- Produkcja nie korzysta z Dockera dla Meal Plannera.
- Kod commitowany na `main` ma twardo wpisane połączenie do PostgreSQL w `app/core/config.py`.
- Produkcyjny `.env` ma `ENV=dev` oraz ustawione `DATABASE_URL`, ale `DATABASE_URL` nie jest używane, bo kod je nadpisuje stałą wartością.
- `main.py` duplikuje auth/admin względem `app/api/v1/auth.py` i `app/api/v1/admin.py`.

## 5. PostgreSQL

| Obszar | Stan | Dowód | Ryzyko |
| ------ | ---- | ----- | ------ |
| Wersja i baza | PostgreSQL 14.23, baza `fastapi_db` | odczyt runtime engine + zapytania `select version(), current_database()` | niskie |
| Realne użycie PostgreSQL | potwierdzone | runtime `engine.url` i log `DB FILE: postgresql://...`; tabele zawierają dane | niskie |
| Tabele public | `users`, `recipes`, `ingredients`, `login_log`, `request_log` | introspekcja `information_schema.tables` | niskie |
| Legacy tables | brak dodatkowych tabel w `public` | zapytanie na tabele poza modelami zwróciło pusty wynik | niskie |
| Liczność danych | `users=5`, `recipes=64`, `ingredients=0`, `login_log=39`, `request_log=318016` | agregaty `count(*)` | średnie dla `request_log` |
| Model planowania tygodnia | brak | brak tabel i kolumn planu/dnia/tygodnia | wysokie produktowe |
| Lista zakupów w bazie | brak | brak tabel shopping/list/plan; frontend zapisuje `shoppingList` do `localStorage` | wysokie produktowe |
| Porcje | brak | brak kolumn/relacji dla servings/portions | średnie produktowe |
| Składniki | pół-normalizowane i faktycznie nieużywane relacyjnie | `recipes.ingredients` to `varchar`; tabela `ingredients` istnieje, ale ma 0 rekordów | średnie |
| Relacje | tylko `recipes.user_id -> users.id` | introspekcja FK | niskie |
| Indeksy | podstawowe indeksy na PK, `users.username`, `recipes.name`, `recipes.created_at` | `pg_indexes` | niskie |
| Constraints | podstawowe PK/UNIQUE/NOT NULL, brak bardziej zaawansowanych walidacji | `information_schema.table_constraints` | średnie |
| Migracje | brak Alembica i katalogów migracji | brak `alembic.ini`, `alembic/`, `migrations/` | wysokie |
| `create_all` | aktywne na publicznej produkcji | `main.py` robi `Base.metadata.create_all(bind=engine)` gdy `ENV == "dev"`; produkcyjny `.env` ma `ENV=dev` | wysokie |
| Spójność z modelami | obecny schemat odpowiada obecnym modelom | tabele i kolumny zgodne z modelami SQLAlchemy | średnie, bo bez migracji |
| Backupy | znaleziono ślady ręcznych backupów, brak potwierdzonej automatyzacji | pliki w `/home/deploy/backups` i wpisy w historii powłoki; brak potwierdzonego harmonogramu | wysokie operacyjne |

Dodatkowe fakty:
- 58 przepisów jest publicznych, 6 prywatnych.
- 3 przepisy mają obrazki.
- 45 przepisów ma wielowierszowe `ingredients`, co potwierdza tekstowy model składników.
- W bazie istnieją przepisy 4 autorów.
- `ingredients` istnieje jako model i tabela, ale w praktyce jest pusta.

## 6. Stan produkcji

| Element | Status | Dowód | Uwagi |
| ------- | ------ | ----- | ----- |
| `meal-planner.service` | działa | `systemctl status meal-planner` | aktywna od `2026-08-04 11:24:38 UTC` |
| `meal-planner-rc.service` | działa | `systemctl status meal-planner-rc` | aktywna od `2026-08-04 11:24:38 UTC` |
| `nginx.service` | działa | `systemctl status nginx` | reverse proxy dla domeny produkcyjnej i RC |
| PostgreSQL | działa | aktywny proces `postgres`, połączenie runtime i zapytania SQL | nasłuch na `127.0.0.1:5432` |
| HTTPS | działa | `GET https://maciak.online/` i `/login` | port 443 odpowiada poprawnie |
| Redirect HTTP -> HTTPS | działa | `GET http://maciak.online/` zwraca `301` | zgodne z konfiguracją `nginx` |
| Root app | działa | `GET /` zwraca `307` do `/login` | spodziewane dla niezalogowanego użytkownika |
| Strona logowania | działa | `GET /login` zwraca `200` | render HTML |
| Statyczne pliki | działają | `GET /static/main.css` i upload JPG zwracają `200` | uploady publicznie serwowane |
| 404 handling | działa | `GET /no-such-page`, `/health`, `/ready` zwracają `404` | brak health endpointów |
| Endpointy chronione | działają | `/docs`, `/openapi.json`, `/api/v1/recipes/`, `/auth/me` zwracają `401` | poprawne zachowanie bez logowania |
| 5xx w logach aplikacji | niepotwierdzone | agregat `request_log` z 30 dni nie zawiera 5xx | pozytywny sygnał |
| Kontenery Meal Plannera | brak | `docker ps` nie pokazuje Meal Plannera | aplikacja nie działa w Dockerze |

## 7. Funkcje

| Funkcja | Status | Źródło weryfikacji | Uwagi |
| ------- | ------ | ------------------ | ----- |
| Logowanie | potwierdzone na produkcji | `GET /login`, kod `POST /login`, `login_log` | nie wykonywałem bezpiecznego logowania |
| Wylogowanie | potwierdzone w kodzie | `GET /logout` w `main.py`, formularz w template | bez aktywnej sesji nie weryfikowane runtime |
| Użytkownicy i role | potwierdzone w bazie | tabela `users`, role `admin/super_admin/user` | 5 użytkowników |
| Lista przepisów | potwierdzone w kodzie i bazie | endpoint `/api/v1/recipes/`, tabela `recipes` | endpoint chroniony |
| Dodawanie przepisu | potwierdzone w kodzie | `POST /api/v1/recipes/`, serwis `create_recipe` | bezpiecznie nie testowane na prod |
| Edycja przepisu | potwierdzone w kodzie | `PUT /api/v1/recipes/{id}` | bezpiecznie nie testowane na prod |
| Usuwanie przepisu | potwierdzone w kodzie | `DELETE /api/v1/recipes/{id}` | bezpiecznie nie testowane na prod |
| Zdjęcia | potwierdzone na produkcji i w bazie | upload endpointy, 3 rekordy z obrazkami, pliki w uploads | publicznie serwowane |
| Public/private przepisów | działa częściowo | kolumna `is_public`, API visibility, template i JS | tworzenie nowego przepisu nie przekazuje `is_public`; w HTML add/edit mają zduplikowane `id="edit-is-public"` |
| Wyszukiwanie | potwierdzone w kodzie | search input + JS `filterRecipes()` | filtr tekstowy po stronie klienta |
| Filtrowanie domenowe | nie istnieje | brak modelu/tagów/filtrów domenowych | tylko search |
| Składniki | działa częściowo | `recipes.ingredients` jako tekst, `ingredients` tabela pusta | brak realnej normalizacji |
| Porcje | nie istnieją | brak pól w schemacie, bazie i UI | wcześniejszy raport trafny |
| Lista zakupów | potwierdzone w kodzie | `localStorage.getItem('shoppingList')` i `saveList` | brak serwerowej trwałości |
| Import listy zakupów | potwierdzone w kodzie | modal importu i `importShoppingList()` | po stronie klienta |
| Eksport listy zakupów | nie istnieje | brak kodu i UI | wcześniejszy raport trafny |
| Plan tygodnia | nie istnieje | brak modeli, endpointów i UI | wcześniejszy raport trafny |
| Zmiana tygodnia | nie istnieje | brak modeli i UI | wcześniejszy raport trafny |
| Kopiowanie tygodnia/posiłków | nie istnieje | brak modeli i kodu | wcześniejszy raport trafny |
| Historia planów | nie istnieje | brak modeli i UI | wcześniejszy raport trafny |
| Responsywność | działa częściowo | mobile CSS, burger menu, moduły w UI | brak pełnej weryfikacji interakcyjnej |
| Panel admina | potwierdzone w kodzie i produkcji | `/admin`, `admin_panel.html`, tabele logów | wymaga `super_admin` |
| Logi admin/API | potwierdzone w kodzie, bazie i produkcji | `login_log`, `request_log`, `/api/v1/admin/*` | endpointy chronione |
| API | potwierdzone na produkcji | 401 dla chronionych ścieżek, routing działa | brak publicznego health endpointu |
| Funkcje meal-planning | nie istnieją | brak danych planu w kodzie, bazie i UI | aplikacja nie jest dziś planerem tygodnia |
| Wcześniejszy raport o SQLite w produkcji | wcześniejszy raport był błędny | runtime engine + PostgreSQL z danymi | produkcja działa na PostgreSQL |

## 8. Logi i błędy

### MPP-001 — Produkcja działa z `ENV=dev`

- Priorytet: P1
- Potwierdzenie: `ENV=dev` w `/var/www/meal-planner/.env`; `main.py` uruchamia `Base.metadata.create_all()` przy `ENV == "dev"`; `COOKIE_SECURE = ENV == "prod"`
- Zakres: cała publiczna instancja `maciak.online`
- Częstotliwość: stały stan konfiguracyjny
- Możliwa przyczyna: środowisko publiczne nie zostało przełączone z ustawień deweloperskich
- Wpływ: automatyczne tworzenie tabel na starcie i nieustawianie `Secure` dla cookie auth
- Rekomendowane dalsze sprawdzenie: potwierdzić flagę `Secure` na realnym loginie w staging; odseparować env publiczny od deweloperskiego
- Czy wymaga ingerencji produkcyjnej: tak, ale dopiero po backupie i przygotowaniu staging

### MPP-002 — Drift konfiguracji bazy: `.env` wskazuje SQLite, runtime używa hardcoded PostgreSQL

- Priorytet: P1
- Potwierdzenie: produkcyjne `.env` ma `DATABASE_URL=<set>` i podczas introspekcji wskazywał SQLite; `app/core/config.py` w commitowanym kodzie nadpisuje to stałym PostgreSQL DSN; runtime engine i logi potwierdzają PostgreSQL
- Zakres: produkcja i RC
- Częstotliwość: stały stan kodu i konfiguracji
- Możliwa przyczyna: migracja z SQLite do PostgreSQL wykonana bez domknięcia konfiguracji
- Wpływ: wysokie ryzyko błędnych audytów, złych deployów i pomyłek operatorskich
- Rekomendowane dalsze sprawdzenie: ujednolicić źródło prawdy dla `DATABASE_URL` i usunąć martwe artefakty tylko po przygotowaniu planu migracji/staging
- Czy wymaga ingerencji produkcyjnej: tak, planowanej

### MPP-003 — Brak migracji schematu

- Priorytet: P1
- Potwierdzenie: brak Alembica i katalogów migracji, zależność od `create_all` w trybie `dev`
- Zakres: cały lifecycle danych
- Częstotliwość: stały stan repo
- Możliwa przyczyna: projekt rozwijany bez formalnego mechanizmu zmian schematu
- Wpływ: ryzyko rozjazdu środowisk, niekontrolowanych zmian i trudnych wdrożeń
- Rekomendowane dalsze sprawdzenie: zaprojektować baseline migracji w staging
- Czy wymaga ingerencji produkcyjnej: nie natychmiast, ale przed rozwojem funkcjonalnym

### MPP-004 — Brak potwierdzonego automatycznego backupu i procedury odtworzenia

- Priorytet: P1
- Potwierdzenie: znaleziono ślady ręcznych backupów (`/home/deploy/backups`, historia powłoki), ale nie znaleziono potwierdzonego harmonogramu lub procedury
- Zakres: operacje i bezpieczeństwo danych
- Częstotliwość: stan ciągły
- Możliwa przyczyna: operacje wykonywane ad hoc
- Wpływ: wysokie ryzyko przy zmianach produkcyjnych lub awarii
- Rekomendowane dalsze sprawdzenie: spisać i przetestować backup/restore na staging
- Czy wymaga ingerencji produkcyjnej: nie natychmiast, ale przed kolejnym sprintem zmian

### MPP-005 — `request_log` rośnie bez ograniczeń i jest zaszumiony botami

- Priorytet: P2
- Potwierdzenie: `request_log=318016`, brak 5xx w 30 dniach, dominują 404; 351 suspicious requests w 30 dniach
- Zakres: baza PostgreSQL i panel admina
- Częstotliwość: ciągła
- Możliwa przyczyna: middleware loguje praktycznie cały ruch aplikacji, w tym skany botów
- Wpływ: wzrost bazy, niższa czytelność logów, potencjalny koszt wydajnościowy
- Rekomendowane dalsze sprawdzenie: retencja, agregacja lub oddzielenie security noise od ruchu aplikacyjnego
- Czy wymaga ingerencji produkcyjnej: nie pilnie

### MPP-006 — Brak twardych nagłówków bezpieczeństwa na odpowiedziach aplikacji

- Priorytet: P2
- Potwierdzenie: próbki odpowiedzi HTTPS nie zawierają `Strict-Transport-Security`, `X-Frame-Options`, `X-Content-Type-Options`, `Content-Security-Policy`
- Zakres: publiczna powierzchnia HTTP
- Częstotliwość: stała
- Możliwa przyczyna: minimalna konfiguracja `nginx`
- Wpływ: słabsza warstwa hardeningu, choć aplikacja działa
- Rekomendowane dalsze sprawdzenie: wdrożyć nagłówki najpierw na staging i zweryfikować wpływ na UI
- Czy wymaga ingerencji produkcyjnej: nie natychmiast

### MPP-007 — UI tworzenia przepisu ma niespójny przełącznik public/private

- Priorytet: P2
- Potwierdzenie: w `recipes.html` add i edit używają tego samego `id="edit-is-public"`; `Recipes.actions.create()` nie przekazuje `is_public`; tworzenie opiera się tylko na polach tekstowych
- Zakres: formularz dodawania przepisu
- Częstotliwość: deterministyczna w kodzie
- Możliwa przyczyna: niedokończone spięcie refaktoru UI
- Wpływ: użytkownik może sądzić, że ustawia widoczność przy tworzeniu, ale kod tego nie zapisuje
- Rekomendowane dalsze sprawdzenie: odtworzyć w staging i naprawić testem UI/API
- Czy wymaga ingerencji produkcyjnej: nie krytycznie, ale przed dalszym rozwojem UI

## 9. Audyt UX

### Recipe Manager

Scenariusz „dodaj, znajdź, edytuj i wykorzystaj przepis” jest wspierany umiarkowanie dobrze jak na prosty monolit. Użytkownik dostaje listę przepisów, prostą wyszukiwarkę, formularz dodawania/edycji, upload zdjęć i akcję dodawania składników do lokalnej listy zakupów. Feedback istnieje w postaci toastów, a UI ma podstawową responsywność i rozróżnienie właściciela/publiczności przepisu.

Największe tarcia:
- formularz przepisu jest prosty, ale składniki i instrukcje są tylko tekstem,
- przełącznik public/private przy tworzeniu jest niespójny z kodem,
- brak jawnych loading states,
- obsługa błędów jest nierówna,
- frontend jest duży i trudny do przewidywalnego utrzymania.

Ocena UX jako Recipe Manager: średnia. Da się używać, ale czuć warstwowe dokładanie funkcji.

### Meal Planner

Scenariusz „zaplanować tydzień w kilka minut i dostać kompletną listę zakupów” praktycznie nie istnieje w obecnym produkcie. Nie ma dni, tygodni, slotów posiłków, porcji, kopiowania tygodnia ani trwałej listy zakupów. Lista zakupów działa lokalnie w przeglądarce i nie ma serwerowego modelu agregacji składników.

To nie jest dziś UX planera posiłków. To katalog przepisów z pomocniczą listą zakupów. Do planowania tygodnia użytkownik musiałby ręcznie pamiętać, które przepisy wybrał, ręcznie agregować składniki i polegać na stanie konkretnej przeglądarki.

Ocena UX jako Meal Planner: niska, ale głównie z powodu zakresu produktu, nie dlatego, że obecna funkcja przepisów jest całkowicie zepsuta.

## 10. Weryfikacja wcześniejszego raportu

| Wniosek wcześniejszego audytu | Ocena | Dowód | Korekta |
| ----------------------------- | ----- | ----- | ------- |
| Aplikacja jest bardziej managerem przepisów niż pełnym planerem posiłków | potwierdzony | kod, baza, UI, brak modeli planu | trafny opis produktu |
| Brak modelu planowania tygodnia | potwierdzony | brak tabel, endpointów i UI planu | bez zmian |
| Lista zakupów działa wyłącznie przez `localStorage` | potwierdzony | `recipes.js` używa `localStorage` i brak tabeli w bazie | trafne |
| Brak migracji | potwierdzony | brak Alembica/migrations | trafne |
| Brak testów | potwierdzony | brak katalogu `tests` i konfiguracji testowej | trafne |
| Duplikacja routingu auth/admin | potwierdzony | `main.py` i `app/api/v1/*` implementują podobne ścieżki | trafne |
| Monolityczny `recipes.js` | potwierdzony | jeden plik obsługuje recipes, shopping, modale, theme, mobile | trafne |
| Prosty CRUD przepisów działa | częściowo potwierdzony | kod i baza potwierdzają ścieżki CRUD; bezpiecznie nie wykonywano mutacji na produkcji | backend istnieje i jest używany |
| Produkcja działa na PostgreSQL | potwierdzony | runtime engine, logi, zapytania do `fastapi_db` | wcześniejszy błąd o SQLite obalony |
| SQLite jest elementem architektury produkcyjnej | obalony | publiczny runtime używa PostgreSQL; SQLite to legacy/drift w repo i `.env` | SQLite nie jest aktywną bazą publicznej instancji |
| `Base.metadata.create_all()` nie jest używane na produkcji | obalony | produkcja ma `ENV=dev`, więc kod uruchamia `create_all` | to realny problem produkcyjny |
| Wcześniejszy raport naprawił checkbox public/private | obalony dla wdrożonej produkcji | wdrożony HTML nadal ma zduplikowane `id`, a create JS nie przekazuje `is_public` | produkcja nie zawiera tej poprawki |
| W produkcji mogą być lokalne błędy niewidoczne w lokalnym audycie | potwierdzony | `ENV=dev`, config drift, brak health, security headers, request log noise | produkcja ma własne ryzyka operacyjne |

## 11. Mocne strony

- Działająca, publicznie dostępna instancja z prostą architekturą i małym śladem operacyjnym.
- FastAPI + PostgreSQL dają sensowną bazę pod dalszy rozwój modułu backendowego.
- Role użytkowników i panel admina już istnieją.
- CRUD przepisów, upload obrazków i filtrowanie podstawowe są obecne.
- Request i login logs dają zalążek observability.
- Istnieje oddzielna instancja RC, co można wykorzystać jako początek bezpieczniejszego procesu zmian.

## 12. Ryzyka i dług techniczny

### Realne problemy produkcyjne

- Publiczna instancja działa z `ENV=dev`.
- `DATABASE_URL` w `.env` i runtime rozchodzą się.
- Brak migracji schematu.
- Brak potwierdzonego automatycznego backupu i procedury restore.
- Brak health/ready endpointów.
- Brak twardych nagłówków bezpieczeństwa.

### Dług techniczny

- Twardo wpisany PostgreSQL DSN w kodzie.
- `main.py` duplikuje auth/admin z `app/api/v1/*`.
- `recipes.js` jest monolitem i ma oznaki martwego lub dublowanego kodu (`toggleVisibility`, `renderVisibilitySwitch`, rozproszone ścieżki shopping/UI).
- Legacy artefakty SQLite w repo i backupach aplikacji.
- `ingredients` jako tabela istnieje, ale produktowo jest praktycznie martwa.

### Brakujące funkcje produktowe

- brak tygodnia/dni/slotów posiłków,
- brak porcji,
- brak trwałej listy zakupów,
- brak historii i kopiowania planów,
- brak agregacji składników na poziomie planu.

### Elementy opcjonalne

- eksport danych,
- bardziej zaawansowane filtry,
- wersjonowany publiczny kontrakt API,
- lepsza telemetria i dashboardy.

## 13. Rola w MAP

Obecny backend warto zachować jako punkt wyjścia tylko częściowo: jako prosty moduł użytkowników, auth bazowego, przepisów i uploadów. Nie nadaje się jeszcze jako gotowy moduł Meal Planner dla MAP, bo domena planowania posiłków praktycznie nie istnieje.

Co warto zachować:
- FastAPI monolit jako początkowy moduł backendowy,
- model `Recipe` jako zalążek katalogu przepisów,
- role i panel admina jako baza pod operacje,
- PostgreSQL jako produkcyjną bazę,
- uploady obrazków.

Co wymaga przebudowy:
- model danych planowania,
- shopping list jako byt serwerowy,
- auth i sesje pod wspólny standard MAP,
- frontend, jeśli MAP ma mieć spójne doświadczenie użytkownika,
- routing i kontrakt API.

Dane, które w przyszłości mogłyby trafiać do dashboardu MAP:
- dzisiejszy zaplanowany posiłek,
- plan na jutro,
- liczba brakujących produktów,
- serwerowa lista zakupów,
- przypomnienie o przygotowaniu/rozmrożeniu,
- ostrzeżenie o nieuzupełnionych dniach tygodnia.

Potencjalne integracje:
- kalendarz: plan dnia/tygodnia,
- budżet: koszt zakupów i rotacja składników,
- zdrowie: makro, alergeny, preferencje,
- przypomnienia: przygotowanie, zakupy, leftovers.

Rekomendowany sposób integracji:
- nie przenosić obecnego UI 1:1 do MAP,
- najpierw ustabilizować backend i dane,
- dopiero potem projektować nowy kontrakt API i nowy interfejs MAP.

## 14. Plan odświeżenia

### Etap 0 — zabezpieczenie i przygotowanie

- Potwierdzić i zautomatyzować backup PostgreSQL oraz uploadów.
- Spisać procedurę restore i przetestować ją poza produkcją.
- Urealnić RC do roli staging lub postawić osobne staging.
- Dodać podstawowe smoke testy HTTP.
- Ustalić plan migracji od obecnego schematu do kontrolowanych migracji.

### Etap A — stabilizacja

- Naprawić konfigurację środowiskową (`ENV`, `DATABASE_URL`, cookie security).
- Dodać health/ready endpointy.
- Uporządkować logowanie i retencję `request_log`.
- Dodać podstawowy hardening `nginx` i aplikacji.

### Etap B — uporządkowanie techniczne

- Wprowadzić Alembic.
- Usunąć hardcoded DSN z kodu.
- Rozdzielić auth/admin z `main.py` i API do jednego źródła prawdy.
- Dodać testy backendu i kilka smoke testów UI/API.
- Oczyścić legacy artefakty SQLite dopiero po bezpiecznej migracji operacyjnej.

### Etap C — produkt Meal Planner

- Dodać model tygodnia, dni i slotów posiłków.
- Dodać porcje i skalowanie składników.
- Przenieść shopping list do backendu.
- Dodać agregację zakupów z wielu zaplanowanych posiłków.
- Dodać kopiowanie poprzedniego tygodnia i historię planów.

### Etap D — MAP

- Wersjonować API modułu.
- Zdecydować, czy auth ma być wspólne z MAP.
- Zintegrować dashboard i przypomnienia.
- Ustalić wspólne modele danych z kalendarzem, budżetem i zdrowiem.

## 15. Backlog

| ID | Zadanie | Typ | Priorytet | Ryzyko | Złożoność | Wartość | Kryterium akceptacji |
| -- | ------- | --- | --------- | ------ | --------- | ------- | -------------------- |
| MPPA-01 | Przełączyć publiczną instancję z `ENV=dev` na poprawny tryb produkcyjny po przygotowaniu staging | security | P1 | wysokie | średnia | bardzo wysoka | staging potwierdza brak regresji, cookie ma `Secure`, produkcja nie wywołuje `create_all` |
| MPPA-02 | Ujednolicić konfigurację bazy i usunąć hardcoded DSN z kodu | operations | P1 | wysokie | średnia | bardzo wysoka | runtime korzysta wyłącznie z jawnej konfiguracji środowiskowej |
| MPPA-03 | Wprowadzić migracje Alembic z baseline obecnego schematu | tech debt | P1 | wysokie | średnia | bardzo wysoka | schemat może być odtworzony i zmieniany przez migracje |
| MPPA-04 | Spisać i przetestować backup/restore PostgreSQL + uploadów | operations | P1 | wysokie | średnia | bardzo wysoka | istnieje procedura i udany test odtworzenia na staging |
| MPPA-05 | Dodać health/ready endpointy oraz smoke testy HTTP | operations | P1 | średnie | niska | wysoka | monitoring i smoke test odróżniają stan zdrowy od awarii |
| MPPA-06 | Oczyścić duplikację auth/admin między `main.py` i `app/api/v1/*` | tech debt | P2 | średnie | średnia | wysoka | jedno źródło prawdy dla auth i admin |
| MPPA-07 | Naprawić create form public/private i dodać test UI/API | bug | P2 | niskie | niska | średnia | nowy przepis respektuje `is_public` i UI nie ma zduplikowanych `id` |
| MPPA-08 | Wprowadzić retencję lub agregację `request_log` | operations | P2 | średnie | średnia | średnia | logi nie rosną bez końca i zachowują wartość diagnostyczną |
| MPPA-09 | Podzielić `recipes.js` na mniejsze moduły | tech debt | P2 | średnie | średnia | wysoka | shopping, recipes i modale mają oddzielne moduły i testowalne granice |
| MPPA-10 | Dodać serwerowy model shopping list | product | P1 | wysokie | wysoka | bardzo wysoka | lista zakupów jest trwała między urządzeniami |
| MPPA-11 | Dodać model tygodnia/dnia/slotów posiłków | product | P1 | wysokie | wysoka | bardzo wysoka | użytkownik może zaplanować tydzień bez ręcznego obchodzenia aplikacji |
| MPPA-12 | Zaprojektować kontrakt API modułu pod MAP | integration | P2 | średnie | średnia | wysoka | istnieje wersjonowany szkic API niezależny od obecnego UI |

## 16. Rekomendacja pierwszego sprintu

Pierwszy sprint nie powinien zaczynać się od funkcji użytkowych. Powinien być operacyjno-stabilizacyjny:
- sformalizować staging na bazie RC lub osobnego środowiska,
- zautomatyzować backup i udokumentować restore,
- dodać smoke testy i health/ready,
- ustalić migracje Alembic,
- dopiero po tym ruszać konfigurację produkcyjną i zmiany funkcjonalne.

Najrozsądniejszy pierwszy sprint to: staging + backup/restore + smoke tests + plan migracji. Bez tego rozwój funkcji Meal Plannera będzie zbyt ryzykowny.
