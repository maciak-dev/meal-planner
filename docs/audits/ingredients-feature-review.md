# Ingredients Feature Review

Data aktualizacji: 2026-08-16

Status: Historical snapshot before the Shop foundation. The current contract is
documented in `docs/architecture/recipe-ingredients-store.md`.

## Zakres feature

Na podstawie kodu i historii repo feature `ingredients` wygląda dziś tak:

- istnieje model `Ingredient` z polami:
  - `id`
  - `name`
  - `is_essential`
- istnieje endpoint `GET /ingredients/map`
- frontend ładuje `ingredients_map` i oznacza checkboxy składników jako domyślnie zaznaczone lub nie
- shopping list nadal działa wyłącznie po stronie klienta w `localStorage`

To nie jest jeszcze kompletny feature sortowania po sklepach/alejkach.

## Architektura

- model: `app/db/models/ingredient.py`
- ładowanie do UI:
  - `app/main.py`
  - `app/static/recipes.js`
- zużycie w UI:
  - `renderIngredients()` w `recipes.js`
  - checkboxy składników przy przepisie
- brak osobnego admina do zarządzania słownikiem składników

## Stan implementacji

### Potwierdzone w kodzie

- tabela `ingredients` istnieje w modelach
- endpoint mapujący istnieje
- UI korzysta z mapy `name -> is_essential`
- shopping list potrafi dodać zaznaczone składniki do lokalnej listy

### Potwierdzone w bazie produkcyjnej

- tabela `ingredients` istnieje
- liczba rekordów: `0`

### Niepotwierdzone

- brak branchy zdalnych związanych z `ingredients`, `store`, `aisle`, `category`
- brak kodu backendowego dla:
  - alejek,
  - sklepów,
  - kolejności działów,
  - aliasów nazw,
  - normalizacji składników,
  - serwerowego sortowania listy zakupów

## Historia w repo

Najistotniejsze ślady:

- commit `f15e3a4` dodał `app/db/models/ingredient.py`
- commit history pokazuje rozwój shopping list i importu listy:
  - `5a97474`
  - `30dbb1e`
  - `719deaf`
  - `eb9ba4b`
  - `064c8e9`

Nie znaleziono osobnego brancha feature na `origin` poza `main`.

## Stan bazy

- produkcja: tabela istnieje, ale jest pusta
- po restore w `fastapi_db_rc`: tabela również pusta
- odczytowy check RC po przepięciu `.env` potwierdził:
  - `ingredients=0`
  - kolumny: `id`, `name`, `is_essential`
  - constraints: `ingredients_pkey`, `ingredients_name_key`
- startup RC z `ENV=prod` nie próbował zmieniać schematu tabeli
- brak dodatkowych tabel wspierających feature sklepu/alejek

## Problemy znalezione w snapshotcie

1. Feature jest tylko częściowo wdrożony.
2. Model `ingredients` nie ma danych w produkcji.
3. Brak admina lub API do utrzymywania słownika składników.
4. Brak normalizacji nazw i aliasów.
5. Brak sklepu/alejek/category modelu.
6. Brak integracji z trwałą shopping list po stronie serwera.

## Brakujące elementy

- CRUD słownika składników,
- normalizacja i aliasy,
- model sklepu/alejek/kolejności,
- powiązanie z trwałą shopping list,
- testy spójności backend/frontend/baza.

## Ryzyka

- merge „na ślepo” nie istnieje, bo nie znaleziono osobnego brancha do merge,
- dokańczanie feature bez migracji i bez trwałej shopping list pogłębi dług,
- łatwo pomylić obecną pustą tabelę z martwym kodem, choć w historii widać intencję produktową,
- na dziś tabela nie jest legacy; to zalążek funkcji mapowania składników i ich późniejszego porządkowania.

## Rekomendacja

Rekomendacja: nie „merge”, bo nie ma czego scalać z osobnego brancha. Potrzebny jest nowy, świadomy continuation branch oparty o `main`.

Najbezpieczniejsza ścieżka:

1. zachować istniejący model `ingredients` jako zalążek,
2. najpierw ustabilizować konfigurację i migracje,
3. dopiero potem zaprojektować docelowy model składników i kolejności zakupów,
4. wdrożyć backend, frontend i migracje razem.

## Proponowany plan dokończenia

1. Dodać migracje Alembic dla obecnego schematu.
2. Zdecydować, czy `ingredients` ma być:
   - prostym słownikiem `is_essential`,
   - czy pełnym katalogiem z aliasami i kolejnością sklepową.
3. Dodać minimalny CRUD admina dla słownika składników.
4. Wprowadzić serwerową shopping list.
5. Dopiero potem dodać sklep/aisle/category ordering.
