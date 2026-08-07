---
status: Gotowy na branchu — nie wdrożony na produkcję
last_updated: 2026-08-07
---

# Import przepisu z URL

## Purpose

Usuwa największe tarcie wejścia do produktu: nikt nie przepisuje przepisów
ręcznie. Wklejenie linku ma być najszybszą drogą od „znalazłem coś w
internecie" do „mam to w planie". Służy celowi 3 North Star i jest enablerem
dla celu 1 — plan jest tyle wart, ile katalog, z którego się go składa.

## Current Capabilities

- `POST /api/v1/recipe-import/preview` — pobiera stronę, parsuje
  `schema.org/Recipe` (JSON-LD, w tym `@graph` i wiele bloków), z fallbackiem
  do parsowania HTML; nic nie zapisuje.
- Parser składników PL/EN: rozbija linię na ilość, jednostkę, nazwę i notatkę,
  obsługuje ułamki i zwroty typu „do smaku"; każda pozycja dostaje
  `confidence` i flagę „wymaga sprawdzenia".
- **Draft z korektą przez człowieka** — wszystkie pola edytowalne, tabela
  składników z dodawaniem i usuwaniem wierszy, oznaczone tylko pozycje
  niepewne („Sprawdź"). Wzorcowe podejście: maszyna proponuje, człowiek
  zatwierdza.
- `POST /api/v1/recipe-import/confirm` — zapisuje **wyłącznie** to, co przyszło
  w payloadzie; nigdy nie pobiera strony ponownie.
- Opcjonalne pobranie zdjęcia po zatwierdzeniu: whitelist JPEG/PNG/WebP,
  sniffing magic bytes, własna nazwa pliku; nieudane pobranie nie blokuje
  zapisu przepisu.
- Ochrona przed przypadkowym podwójnym zatwierdzeniem (okno 120 s po
  `user_id` + `source_url` zwraca istniejący przepis).
- Ostrzeżenia i błędy zmapowane na kody i przetłumaczone na PL/EN — użytkownik
  widzi zdanie, nie wyjątek.
- Bezpieczeństwo pobierania: walidacja schematu i portów, odrzucanie userinfo,
  blokada adresów prywatnych i metadanych, pinowanie połączenia TCP do
  zwalidowanego IP przy zachowaniu Host/SNI, pełna rewalidacja na każdym
  przekierowaniu, limit rozmiaru po dekompresji.

## Current Limitations

- **Nie jest na produkcji.** Kod, testy i migracje leżą na branchu
  `feature/i18n-recipe-import-ingredients`; migracja `69eea78ac02c` nie została
  jeszcze uruchomiona nawet na RC. To jest największa gotowa wartość w repo,
  która nikomu nic nie daje.
- **Pola „Porcje", „Czas przygotowania", „Czas gotowania" są zbierane i
  wyrzucane.** Schemat `RecipeImportConfirmRequest` je waliduje,
  `create_recipe_from_import()` ich nie zapisuje, bo model `Recipe` nie ma
  takich kolumn. Użytkownik traci dane bez ostrzeżenia (P-3 w audycie).
  Rozstrzygnięte — [ADR-004](../decisions/ADR-004.md): pola zostają i są
  utrwalane, a `total_time` znika z kontraktu `confirm`, bo formularz go nie
  pokazuje.
- Zaimportowany przepis jest zawsze prywatny i — dopóki widoczność w UI jest
  zepsuta — nie da się go upublicznić.
- Przełącznik „zapisz składniki jako relacyjne" pokazuje użytkownikowi decyzję
  techniczną, której znaczenia nie zna; strukturalne składniki i tak nie mają
  dziś konsumenta.
- Import jest schowany jako drugorzędny przycisk w zakładce Przepisy, choć jest
  najszybszą drogą wypełnienia katalogu.
- Brak zbiorczego importu i brak ponownej synchronizacji ze źródłem.

## Design Direction

- **Wdrożyć.** Kolejność: migracja na RC → smoke na RC → decyzja o merge do
  `main` → produkcja. Osobno od Sprintu 1, żeby nie łączyć dwóch obszarów
  ryzyka.
- Domknąć P-3: zapisać porcje i czasy albo usunąć te pola z formularza.
- Ukryć przełącznik składników relacyjnych do czasu, aż będą używane; decyzja
  techniczna nie należy do użytkownika.
- Po wdrożeniu planu: akcja „importuj i dodaj do planu" jednym krokiem.

## Source Of Truth

- Kod: `app/api/v1/recipe_import.py`, `app/services/recipe_import/`,
  `app/services/ingredient_parsing/`
- Architektura `docs/architecture/recipe-import.md`, handoff
  `docs/handoffs/i18n-recipe-import-ingredients.md` i przegląd produktowy Faz
  A/B `docs/product/bilingual-recipe-import.md` — wszystkie trzy dokumenty żyją
  na branchu `feature/i18n-recipe-import-ingredients` razem z kodem, którego
  dotyczą, i wejdą do tej hierarchii dopiero po zaakceptowaniu tamtego brancha
