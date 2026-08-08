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
`app/core/bootstrap.py`, wywoływane pod flagą `AUTO_CREATE_SCHEMA` — włączoną
tylko w `dev`. Na produkcji i RC (`AUTO_CREATE_SCHEMA=False`) każda zmiana
schematu była operacją ręczną: bez zapisu, bez wersji i bez drogi powrotnej.

`create_all()` **zostaje** dla `dev` — jest wygodne przy pracy lokalnej i nie
koliduje z Alembikiem, dopóki dev nie udaje produkcji. Nie polegaj na nim nigdzie,
gdzie dane mają znaczenie.

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

Migracja `41e1afa8db94` **tworzy** tabele produkcyjne. Na bazie, która już je ma
(czyli na produkcji i RC), nie wolno jej uruchamiać — trzeba ją oznaczyć jako
wykonaną:

```bash
alembic stamp 41e1afa8db94
```

Dopiero potem `alembic upgrade head` zastosuje migracje 2–7. Uruchomienie
`upgrade` bez `stamp` na istniejącej bazie skończy się błędem „table already
exists" — nieszkodliwym, ale mylącym.

Na pustej bazie (dev, testy, świeży RC) `upgrade head` przechodzi całą drogę od
zera i jest właściwym poleceniem.

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

1. Backup `fastapi_db_rc` (`pg_dump -Fc`), weryfikacja przez `pg_restore -l`.
2. Potwierdzenie konfiguracji RC (odczyt, bez zmian): `APP_INSTANCE=rc`,
   `DATABASE_NAME=fastapi_db_rc`, `EXPECTED_DATABASE_NAME=fastapi_db_rc`.
   Guard w `app/core/config.py` odmówi startu, jeśli RC wskaże `fastapi_db` —
   to zabezpieczenie, nie zastępstwo dla sprawdzenia.
3. `pip install -r requirements.txt` — dochodzi `alembic` i `Mako`.
4. `alembic current` — ustalić stan wyjściowy. Baza bez tabeli
   `alembic_version` wymaga `stamp 41e1afa8db94` przed `upgrade`.
5. Policzyć wiersze w `recipes`, `users`, `ingredients` **przed**.
6. `alembic upgrade head`.
7. Policzyć te same wiersze **po** — muszą się zgadzać. Sprawdzić, że
   `recipe_translations` jest pusta i że `users.language` ma wszędzie `pl`.
8. Start `meal-planner-rc.service`, smoke CRUD przepisów, widoczność,
   `GET /ingredients/map`, usunięcie przepisu. Po smoke `stop` + `disable` —
   stanem spoczynkowym RC jest `inactive`.
9. `alembic downgrade 41e1afa8db94` i ponowny `upgrade head` jako test drogi
   powrotnej, z ponownym policzeniem wierszy.
10. Backfill: dry-run, przegląd, `--apply` — dopiero po punktach 1–9.

Produkcja jest osobną decyzją, po potwierdzeniu na RC.

## Dodawanie nowej migracji

```bash
alembic revision --autogenerate -m "opis zmiany"
```

Zawsze przeczytaj wygenerowany plik przed commitem — autogenerate nie wykrywa
zmian nazw kolumn (widzi drop + add, czyli utratę danych) i nie zna intencji.
Wymagania: niepusty `downgrade()`, `server_default` dla każdej nowej kolumny
NOT NULL na tabeli z danymi, oraz `alembic check` bez driftu po `upgrade head`.

## Powiązane dokumenty

- [Production guardrails](production-guardrails.md) — granice zmian bez dostępu
  do VPS
- [RC environment](rc-environment.md) — konfiguracja i stan RC
- [Backup i restore PostgreSQL](postgres-backup-restore.md)
- `docs/decisions/recipe-translations.md` (branch RC) — dlaczego treść
  wielojęzyczna żyje w osobnej tabeli
- `docs/decisions/ingredient-normalization.md` (branch RC) — zakres modelu
  składników i powód, dla którego jest zamrożony
