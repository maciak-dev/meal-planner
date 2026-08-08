---
status: Active
last_updated: 2026-08-08
---

# Migracje Alembica i backfill tłumaczeń

Dokument opisuje, jak wygląda praca ze schematem bazy Meal Plannera po
wprowadzeniu Alembica, oraz jaka jest procedura wdrożenia tego pakietu na RC i
produkcję. Granice operacyjne pozostają takie, jak w
[production-guardrails.md](production-guardrails.md) — ten dokument ich nie
rozluźnia.

## Stan przed tą zmianą

Schemat powstawał wyłącznie przez `Base.metadata.create_all()` w
`app/core/bootstrap.py`, wywoływane pod flagą `AUTO_CREATE_SCHEMA`. Każda zmiana
schematu była operacją ręczną: bez zapisu, bez wersji i bez drogi powrotnej.

## ⚠️ Produkcja działa dziś z `ENV=dev`, czyli z aktywnym `create_all()`

To jest najważniejsza rzecz w tym dokumencie. Przeczytaj przed jakimkolwiek
wdrożeniem.

`AUTO_CREATE_SCHEMA = (ENV == "dev")` (`app/core/config.py`), a
`initialize_database_schema()` jest wywoływane **przy imporcie aplikacji**
(`app/main.py`), czyli przy każdym starcie procesu. Produkcja ma obecnie
`ENV=dev` (patrz [production-environment.md](production-environment.md), sekcja
„Bieżące problemy produkcyjne"), więc **`create_all()` jest na produkcji
aktywne**. RC działa z `ENV=prod` i tego problemu nie ma.

### Czego `create_all()` NIE robi

`create_all()` **nie jest** namiastką Alembica. Na istniejącej bazie:

| Robi | Nie robi |
|---|---|
| tworzy **brakujące tabele** | nie dodaje kolumn do istniejących tabel |
| | nie dodaje constraintów ani indeksów do istniejących tabel |
| | nie zmienia typów ani nullability |
| | nie zapisuje niczego w `alembic_version` |

### Co się stanie, jeśli wdrożysz kod przed migracją

Zweryfikowane lokalnie na bazie w stanie produkcyjnym:

1. Restart aplikacji z nowym kodem → `create_all()` tworzy `recipe_translations`,
   `recipe_ingredients`, `ingredient_aliases`, `store_sections`.
2. Kolumny `users.language` i `recipes.source_*` **nie powstają**.
3. Aplikacja startuje na częściowo zmienionym schemacie i wykłada się na
   pierwszym zapytaniu o użytkownika:
   `UndefinedColumn: column users.language does not exist` — **logowanie
   przestaje działać**.
4. Późniejsze `alembic upgrade head` pada na
   `table "recipe_translations" already exists`, bo tabele już są. Na
   PostgreSQL cały przebieg wycofa się w jednej transakcji (patrz niżej), więc
   baza nie zostaje w stanie pośrednim — ale wdrożenie i tak jest zablokowane.

### Obowiązkowa kolejność

> **Migracja bazy musi zostać wykonana PRZED restartem aplikacji z nowym kodem.**

Ta kolejność obowiązuje **niezależnie** od wartości `ENV`. Nawet przy
`ENV=prod`, gdzie `create_all()` jest wyłączone, kod odwołujący się do
`users.language` na niezmigrowanej bazie po prostu nie zadziała.

### Docelowo: `ENV=prod` na produkcji

Przełączenie produkcji na `ENV=prod` (a więc wyłączenie `create_all()`) jest
**osobną zmianą operacyjną** — nie jest częścią tego pakietu i nie zostało w nim
wykonane. Plan przejścia opisuje
[production-environment.md](production-environment.md), sekcja „Plan przed
przełączeniem na `ENV=prod`". Do czasu tej zmiany kolejność „migracja przed
kodem" jest jedynym zabezpieczeniem.

### Kiedy zatrzymać wdrożenie

**Przerwij i nie kontynuuj**, jeżeli którykolwiek warunek nie jest spełniony:

- `ENV` i `APP_INSTANCE` środowiska nie odpowiadają temu, co zakłada procedura
  poniżej,
- `DATABASE_URL` wskazuje inną bazę niż zamierzona (guard w
  `app/core/config.py` odmówi startu przy RC wskazującym `fastapi_db`, ale
  sprawdź to sam — guard nie pokrywa wszystkich pomyłek),
- introspekcja schematu nie zgadza się z baseline (patrz „Checklista
  introspekcji"),
- nie masz świeżego, zweryfikowanego backupu.

Zatrzymanie się kosztuje kilka minut. Wdrożenie na rozjechanym schemacie kosztuje
przywracanie bazy z dumpa.

## Łańcuch migracji

Liniowy, jeden head, wszystkie odwracalne.

| # | Rewizja | Treść |
|---|---|---|
| 1 | `41e1afa8db94` | **Baseline** — odzwierciedla dokładny schemat produkcyjny: `users`, `recipes`, `ingredients`, `login_log`, `request_log` wraz z indeksami |
| 2 | `d17abcef39ac` | `users.language` — `String(2)`, NOT NULL, `server_default='pl'` |
| 3 | `5a84c10939a0` | `recipe_translations` — schemat, bez danych |
| 4 | `f67f683f4e28` | `store_sections` |
| 5 | `539387eab2be` | rozbudowa `ingredients` + `ingredient_aliases` + `recipe_ingredients` |
| 6 | `8f9e43e7e225` | `recipes.source_url` / `source_name` / `source_author` / `imported_at` |
| 7 | `69eea78ac02c` | `recipe_ingredients.parsed_name` |

`alembic/env.py` bierze adres bazy z `app.core.config.DATABASE_URL`, nie z
placeholdera w `alembic.ini`. Jedno źródło prawdy — migracje nie mogą trafić w
inną bazę niż aplikacja.

## Baseline: `stamp`, nie `upgrade`

Migracja `41e1afa8db94` **tworzy** tabele produkcyjne. Na bazie, która już je ma,
nie wolno jej uruchamiać — trzeba ją oznaczyć jako wykonaną:

```bash
alembic stamp 41e1afa8db94
alembic upgrade head
```

Uruchomienie `upgrade` bez `stamp` na istniejącej bazie skończy się błędem
„table already exists" — na PostgreSQL nieszkodliwym (transakcja się wycofa),
ale blokującym.

Na pustej bazie (dev, testy, świeży RC) `upgrade head` przechodzi całą drogę od
zera i jest właściwym poleceniem — **bez** `stamp`.

### 🚫 Nigdy `alembic stamp head`

```bash
alembic stamp head   # ← NIE. Nigdy na bazie bez wykonanych migracji.
```

`stamp head` oznaczy **wszystkie siedem migracji jako wykonane, nie wykonując
żadnej z nich**. Skutek:

- schemat pozostaje niezmieniony — brak `users.language`, brak nowych tabel,
- `alembic current` pokazuje `69eea78ac02c (head)`, czyli wygląda na sukces,
- `alembic upgrade head` mówi, że nie ma nic do zrobienia,
- **błąd wychodzi dopiero w aplikacji**, jako brakująca kolumna, i to
  potencjalnie długo po wdrożeniu.

To jest cichszy i groźniejszy wariant pomyłki niż `upgrade` bez `stamp` — tamten
przynajmniej krzyczy od razu. Jedyny poprawny `stamp` w tej procedurze to
`stamp 41e1afa8db94`, i tylko na bazie, która nie ma jeszcze `alembic_version`.

### Sprawdzenie obecności tabeli wersji — jawne, nie przez `alembic current`

`alembic current` na bazie bez `alembic_version` kończy się **pustym wyjściem**,
a nie komunikatem o braku tabeli. Pusty wynik wygląda identycznie jak kilka
innych sytuacji, więc nie jest dowodem. Sprawdź wprost:

```sql
SELECT to_regclass('public.alembic_version');
```

- `NULL` → tabeli nie ma → **Stan A** (patrz „Dwa możliwe stany bazy"),
- `alembic_version` → tabela istnieje → **Stan B**, odczytaj rewizję:

```sql
SELECT version_num FROM alembic_version;
```

Równoważnie `\dt alembic_version` w `psql`. Nie zgaduj stanu bazy i nie wnioskuj
go z tego, co „powinno" być po poprzednim wdrożeniu.

## Co migracje robią z istniejącymi danymi

Nic nie usuwają i nic nie przepisują. Potwierdzone testami na fixture o
kształcie produkcyjnym (`tests/test_migrations.py`, klasa
`ProductionFixtureTests`):

- 64 przepisy zachowane, `is_public` niezmienione wiersz po wierszu,
- tekst przepisów (`name`, `description`, `instructions`, `ingredients`)
  nietknięty,
- istniejące konta dostają `language = 'pl'` przez `server_default`,
- składniki zachowane wraz z `is_essential`; nowe `created_at`/`updated_at`
  wypełniają się automatycznie,
- nowe kolumny `recipes` są `NULL` dla wszystkich istniejących wierszy,
- `recipe_translations` po migracji jest **pusta**.

Trzy decyzje projektowe, które sprawiają, że to działa:

1. **`users.language` ma `server_default`.** Bez niego `ALTER TABLE` dodający
   kolumnę NOT NULL wywaliłby się na istniejących kontach.
2. **`ingredients.created_at/updated_at` są dodawane w dwóch krokach** —
   nullable, backfill `CURRENT_TIMESTAMP`, potem zacieśnienie do NOT NULL przez
   `batch_alter_table`. SQLite odrzuca `ADD COLUMN` z niestałym defaultem, więc
   forma jednoetapowa nie byłaby przenośna.
3. **`ingredients` jest rozbudowywana w miejscu**, nie przez drop i create.
   `name` i jego unikalny constraint zostają nietknięte, żeby
   `GET /ingredients/map` działał bez zmian.

## Rollback

```bash
alembic downgrade 41e1afa8db94
```

Zdejmuje migracje 2–7 i zostawia bazę w stanie produkcyjnym. Przetestowane na
danych: po rollbacku 64 przepisy, konta i składniki są na miejscu, a ponowny
`upgrade head` przechodzi (rollback nie zostawia stanu, z którego nie da się
wjechać drugi raz).

**Czego rollback nie odwróci:** wierszy utworzonych przez backfill tłumaczeń.
`downgrade` usuwa tabelę `recipe_translations` razem z zawartością, więc dane
wprowadzone backfillem znikają. To jest bezpieczne, bo backfill kopiuje treść z
legacy kolumn `Recipe`, które zostają — ale znaczy, że po rollbacku backfill
trzeba uruchomić ponownie.

Ograniczenie rośnie w czasie. Dziś `recipe_translations` po backfillu zawiera
wyłącznie kopię legacy kolumn, więc rollback nie traci nic unikalnego. **Od
momentu, w którym wejdzie edycja treści per język (osobny pakiet), tabela zacznie
trzymać dane, których nigdzie indziej nie ma** — i wtedy `downgrade` przestaje
być bezpieczny bez wcześniejszego eksportu. Ta granica jest świadoma i warto ją
zapisać przy wdrażaniu tamtego pakietu.

Downgrade migracji `539387eab2be` i `f67f683f4e28` usuwa `recipe_ingredients`,
`ingredient_aliases` i `store_sections`. Dziś są puste, więc rollback jest
bezkosztowny. Po wdrożeniu importu z URL z zapisem strukturalnych składników
`recipe_ingredients` zacznie zawierać dane — ale są one odtwarzalne z
`recipes.ingredients`, więc utrata jest odwracalna kosztem ponownego parsowania.

## Backfill tłumaczeń — nie jest częścią wdrożenia schematu

`scripts/backfill_recipe_translations.py` tworzy dla każdego przepisu wiersz
`recipe_translations(language='pl')` z legacy kolumn `Recipe`.

**To jest osobny, ręczny krok.** Świadomie nie jest częścią migracji: wdrożenie
schematu i modyfikacja danych nie mogą dziać się w jednym, nieodwracalnym ruchu.

```bash
# dry-run - wypisuje, co BY zrobił, nie zapisuje nic
python scripts/backfill_recipe_translations.py

# zapis
python scripts/backfill_recipe_translations.py --apply
```

Właściwości:

- **domyślnie dry-run** — bez `--apply` nie zapisuje ani jednego wiersza,
- **idempotentny** — przepisy, które mają już tłumaczenie `pl`, są pomijane;
  drugie uruchomienie z `--apply` daje `Applied: 0`,
- **samowystarczalny** — nie importuje warstwy serwisów, więc działa na
  checkoucie mającym sam schemat.

Procedura, w tej kolejności:

1. **Dry-run i ręczny przegląd wyniku.** Liczba wierszy do utworzenia musi się
   zgadzać z liczbą przepisów bez tłumaczenia.
2. **`--apply` na RC**, po świeżym backupie `fastapi_db_rc`.
3. **Na produkcji wyłącznie po osobnej, jawnej zgodzie administratora VPS.**
   Backfill nie jest krokiem wdrożenia schematu i nie wykonuje się automatycznie
   przy deployu ani przy starcie aplikacji.

Wszystkie 64 przepisy dostają `pl`. Nie próbujemy wykryć innego języka z samego
tekstu — każdy fałszywy pozytyw oznaczałby przepis oznaczony błędnym językiem,
bez sposobu, żeby to zauważyć.

## Kolejność wdrożenia tego pakietu na RC

Do wykonania **po** akceptacji PR-a, przez osobę z dostępem do VPS. Nie jest
częścią tego PR-a.

Do wykonania **po** akceptacji PR-a, przez osobę z dostępem do VPS. Nie jest
częścią tego PR-a.

### Kroki wspólne (1–4)

1. **Backup** `fastapi_db_rc` (`pg_dump -Fc`), weryfikacja przez `pg_restore -l`.
   Bez zweryfikowanego backupu nie przechodź dalej.
2. **Potwierdzenie konfiguracji RC** (odczyt, bez zmian): `ENV=prod`,
   `APP_INSTANCE=rc`, `DATABASE_NAME=fastapi_db_rc`,
   `EXPECTED_DATABASE_NAME=fastapi_db_rc`. Guard w `app/core/config.py` odmówi
   startu, jeśli RC wskaże `fastapi_db` — to zabezpieczenie, nie zastępstwo dla
   sprawdzenia.
3. `pip install -r requirements.txt` — dochodzi `alembic` i `Mako`.
4. **Ustal stan bazy** — jawnie, nie przez `alembic current`:

   ```sql
   SELECT to_regclass('public.alembic_version');
   SELECT version_num FROM alembic_version;  -- jeśli tabela istnieje
   ```

   Wynik decyduje o wyborze ścieżki poniżej. **Nie zgaduj.**

### Dwa możliwe stany bazy

Handoff branchu RC (`docs/handoffs/i18n-recipe-import-ingredients.md`) mówi, że
migracje 1–6 **zostały już uruchomione na `fastapi_db_rc`** w ramach wcześniejszej
pracy, a `69eea78ac02c` nie. Jeśli to nadal prawda, RC jest w stanie B. Jeśli RC
został od tego czasu odtworzony — w stanie A. Sprawdź, nie zakładaj.

#### Stan A — brak `alembic_version` (`to_regclass` zwraca `NULL`)

Baza nigdy nie była zarządzana Alembikiem.

1. **Introspekcja schematu** i porównanie z baseline — patrz „Checklista
   introspekcji" niżej. Rozjazd = zatrzymanie procedury.
2. `alembic stamp 41e1afa8db94` — **wyłącznie baseline, nigdy `head`.**
3. `alembic current` — musi pokazać `41e1afa8db94`.
4. `alembic upgrade head` — zastosuje migracje 2–7.

#### Stan B — `alembic_version` istnieje

Baza jest już zarządzana Alembikiem. **Nie stampuj niczego.**

1. Odczytaj `version_num`. Spodziewana wartość dla RC po wcześniejszej pracy:
   `8f9e43e7e225`.
2. `alembic current` — potwierdź tę samą rewizję.
3. `alembic upgrade head` — zastosuje **wyłącznie brakujące** migracje. Przy
   `8f9e43e7e225` będzie to tylko `69eea78ac02c` (jedna nullable kolumna na
   tabeli, która ma dziś zero wierszy).
4. Jeżeli `version_num` jest inne niż `8f9e43e7e225` i inne niż
   `69eea78ac02c` — **zatrzymaj się**. Nieoczekiwana rewizja oznacza, że baza
   ma historię, której ta procedura nie opisuje.

### Kroki wspólne (5–10)

5. Policzyć wiersze w `recipes`, `users`, `ingredients` **przed** migracją.
6. Wykonać migrację według ścieżki A albo B.
7. Policzyć te same wiersze **po** — muszą się zgadzać. Sprawdzić dodatkowo, że
   `recipe_translations` jest pusta i że `users.language` ma wszędzie `pl`.
8. `alembic check` — musi zwrócić „No new upgrade operations detected".
   Od tej zmiany kontrola obejmuje też `server_default` (patrz niżej), więc na
   PostgreSQL jest to pierwszy miarodajny test zgodności modeli ze schematem.
9. Start `meal-planner-rc.service`, smoke: CRUD przepisów, widoczność,
   `GET /ingredients/map`, **usunięcie przepisu**. Po smoke `stop` + `disable` —
   stanem spoczynkowym RC jest `inactive`.
10. Test drogi powrotnej: `alembic downgrade 41e1afa8db94`, ponowne policzenie
    wierszy, `alembic upgrade head`. W stanie B rozważ downgrade tylko do
    `8f9e43e7e225`, żeby nie cofać migracji, które RC ma od dawna.
11. Backfill: dry-run, przegląd, `--apply` — dopiero po punktach 1–10.

Produkcja jest osobną decyzją, po potwierdzeniu na RC — i wymaga dodatkowo
rozstrzygnięcia sprawy `ENV=dev` opisanej na początku tego dokumentu.

## Checklista introspekcji przed pierwszym `stamp`

`stamp` jest **asercją bez weryfikacji**: mówi Alembicowi „ten schemat odpowiada
tej rewizji" i nic nie sprawdza. Jeżeli asercja jest nieprawdziwa, kolejne
migracje wjadą w schemat, którego nie zakładają.

Zgodność baseline `41e1afa8db94` z **modelami lokalnymi** jest potwierdzona —
porównanie tabela po tabeli, kolumna po kolumnie, z indeksami, unique, FK i
nullability, dało zero różnic. **Zgodność z prawdziwym PostgreSQL nie jest
potwierdzona** i musi zostać sprawdzona na RC. Poniższe zapytania są do
wykonania na `fastapi_db_rc` przed `stamp`.

```sql
-- tabele (oczekiwane: users, recipes, ingredients, login_log, request_log)
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public' ORDER BY table_name;

-- kolumny, typy, nullability, defaulty
SELECT table_name, column_name, data_type, character_maximum_length,
       is_nullable, column_default
FROM information_schema.columns
WHERE table_schema = 'public' ORDER BY table_name, ordinal_position;

-- klucze obce (oczekiwany dokładnie jeden: recipes.user_id -> users.id)
SELECT tc.table_name, kcu.column_name, ccu.table_name AS foreign_table
FROM information_schema.table_constraints tc
JOIN information_schema.key_column_usage kcu ON tc.constraint_name = kcu.constraint_name
JOIN information_schema.constraint_column_usage ccu ON tc.constraint_name = ccu.constraint_name
WHERE tc.constraint_type = 'FOREIGN KEY' AND tc.table_schema = 'public';

-- unique constraints
SELECT table_name, constraint_name FROM information_schema.table_constraints
WHERE constraint_type = 'UNIQUE' AND table_schema = 'public';

-- indeksy
SELECT tablename, indexname, indexdef FROM pg_indexes
WHERE schemaname = 'public' ORDER BY tablename, indexname;
```

Do sprawdzenia punkt po punkcie:

- [ ] zestaw tabel dokładnie jak wyżej, bez tabel dodatkowych,
- [ ] kolumny i ich kolejność zgodne z baseline,
- [ ] typy: `VARCHAR` bez długości dla pól tekstowych, `TIMESTAMP WITHOUT TIME ZONE`
      dla `created_at`, `BOOLEAN` dla `is_public`/`is_essential`/`success`/`is_suspicious`,
- [ ] nullability zgodna z baseline (`recipes`: `name`, `description`,
      `instructions`, `ingredients`, `created_at`, `is_public`, `image`,
      `user_id` są NOT NULL; `login_log`/`request_log` mają prawie wszystko
      nullable),
- [ ] `id` każdej tabeli jest `SERIAL` / `integer` z sekwencją,
- [ ] dokładnie jeden FK: `recipes.user_id → users.id`,
- [ ] unique: `users.username` (jako unikalny indeks `ix_users_username`),
      `ingredients.name`,
- [ ] indeksy: `ix_users_username` (unikalny), `ix_recipes_name`,
      `ix_recipes_created_at`,
- [ ] **`ix_ingredients_id`** — baseline go tworzy, bo model ma `index=True` na
      `id`. Audyt produkcyjny nie wymienia go osobno. **Sprawdź, czy istnieje.**
- [ ] **`ix_recipes_id`** — jak wyżej.

Jeżeli `ix_ingredients_id` albo `ix_recipes_id` nie istnieje na RC: to **nie
blokuje** wdrożenia i nie zagraża danym, ale oznacza rozjazd między historią
migracji a bazą. Po `upgrade head` uruchom `alembic check` — zgłosi brakujący
indeks. Wtedy albo dodaj go ręcznie (`CREATE INDEX`), albo zapisz różnicę jako
znaną i świadomą. Nie zostawiaj tego bez decyzji, bo następny `--autogenerate`
wyprodukuje migrację „naprawiającą" ten indeks w nieoczekiwanym momencie.

## Dodawanie nowej migracji

```bash
alembic revision --autogenerate -m "opis zmiany"
```

Zawsze przeczytaj wygenerowany plik przed commitem — autogenerate nie wykrywa
zmian nazw kolumn (widzi drop + add, czyli utratę danych) i nie zna intencji.
Wymagania: niepusty `downgrade()`, `server_default` dla każdej nowej kolumny
NOT NULL na tabeli z danymi, oraz `alembic check` bez driftu po `upgrade head`.

### Zakres kontroli driftu

`alembic/env.py` ustawia w obu trybach (online i offline):

```python
COMPARISON_OPTIONS = {
    "compare_type": True,
    "compare_server_default": True,
}
```

`compare_server_default` **nie jest domyślnie włączone w Alembicu**, a cała
bezpieczna droga migracji `d17abcef39ac` stoi na `server_default='pl'`. Bez tej
opcji zanik albo zmiana wartości domyślnej po stronie bazy byłaby dla
`alembic check` niewidoczna — czyli rozjazd, który nie boli, dopóki ktoś nie doda
kolejnej kolumny NOT NULL do tabeli z danymi. Pokryte testami
(`tests/test_migrations.py`, klasa `DriftDetectionTests`), w tym testem
dowodzącym, że bez tej opcji ten sam rozjazd przechodzi niezauważony.

Uwaga: porównywanie `server_default` jest zależne od dialektu. Testy potwierdzają
działanie na SQLite; **miarodajnym środowiskiem jest PostgreSQL na RC**, bo
normalizacja wyrażenia domyślnego różni się między dialektami.

## Powiązane dokumenty

- [Production guardrails](production-guardrails.md) — granice zmian bez dostępu
  do VPS
- [RC environment](rc-environment.md) — konfiguracja i stan RC
- [Backup i restore PostgreSQL](postgres-backup-restore.md)
- `docs/decisions/recipe-translations.md` (branch RC) — dlaczego treść
  wielojęzyczna żyje w osobnej tabeli
- `docs/decisions/ingredient-normalization.md` (branch RC) — zakres modelu
  składników i powód, dla którego jest zamrożony
