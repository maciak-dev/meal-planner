---
status: Active
last_updated: 2026-08-07
---

# Przepisy

## Purpose

Katalog przepisów zasilający plan posiłków. Służy celowi 3 North Star:
przepisy istnieją po to, żeby dało się z nich złożyć plan — nie jako cel sam w
sobie.

## Current Capabilities

- CRUD przepisu: nazwa, opis, składniki (wolny tekst, jeden na linię),
  instrukcje.
- Widoczność prywatny/publiczny (`Recipe.is_public`) — przepisy publiczne widzą
  wszyscy zalogowani, prywatne tylko właściciel; admin i super_admin mają
  dostęp szerszy.
- Zdjęcie przepisu: upload, podgląd, usunięcie
  (`PUT/DELETE /api/v1/recipes/{id}/image`, pliki w `app/static/uploads`).
- Odznaki na karcie: „MOJE · PRYWATNY/PUBLICZNY" albo „OD <autor>".
- Wyszukiwanie tekstowe po stronie klienta (`filterRecipes()` — filtruje po
  wyrenderowanym tekście karty).
- Podgląd instrukcji w modalu.
- Zaznaczanie składników i dodanie ich do listy zakupów.
- Treść przepisu w modelu wielojęzycznym (`recipe_translations`) z fallbackiem
  do kolumn legacy — patrz [Dwujęzyczność](i18n.md).
- Metadane pochodzenia dla przepisów zaimportowanych (`source_url`,
  `source_name`, `source_author`, `imported_at`).

Na produkcji: 64 przepisy, 4 autorów, 58 publicznych, 3 ze zdjęciem, 45 z
wielolinijkowymi składnikami.

## Current Limitations

- **Widoczność nie działa w UI.** Formularz dodawania nie wysyła `is_public`
  (każdy nowy przepis jest prywatny), a przełącznik w modalu edycji jest
  podpięty pod element o zduplikowanym `id="edit-is-public"` z formularza
  dodawania, więc nie zmienia niczego. Endpoint
  `PATCH /api/v1/recipes/{id}/visibility` istnieje, ale żadna ścieżka UI go nie
  wywołuje — to martwy kod obok zepsutej funkcji.
- **Brak porcji, czasu przygotowania i czasu gotowania** w modelu, mimo że
  formularz importu te dane zbiera (i po zapisie wyrzuca). Rozstrzygnięte —
  [ADR-004](../decisions/ADR-004.md) nakazuje je utrwalić; wdrożenie w
  Sprincie 1.
- **Składniki i instrukcje to wolny tekst.** Instrukcje są przekazywane przez
  atrybut HTML `data-instructions`, co jest kruche dla długich treści i
  uniemożliwia widok kroków.
- **Wyszukiwanie jest prymitywne** — podciąg w wyrenderowanym tekście. Brak
  tagów, kategorii i filtrów (moje/publiczne, ze zdjęciem, z importu, czas
  przygotowania).
- Brak pojęcia „ostatnio gotowane" — nie da się odróżnić przepisu używanego co
  tydzień od dodanego raz i zapomnianego.

## Design Direction

Moduł jest **utrzymywany, nie rozbudowywany**. Trzy rzeczy do zrobienia,
wszystkie w kategorii „napraw obietnicę", nie „dodaj funkcję":

1. Jedna, działająca kontrolka widoczności; usunięcie drugiej drogi.
2. Kolumny `servings` (tekst), `prep_time_minutes` i `cook_time_minutes` —
   [ADR-004](../decisions/ADR-004.md). Te same pola wchodzą do formularza
   ręcznego dodawania i edycji: przepis dodany ręcznie nie może być uboższy niż
   zaimportowany.
3. Instrukcje jako lista kroków zamiast pola tekstowego w atrybucie HTML.

Filtry i tagi wchodzą dopiero wtedy, gdy rozmiar katalogu je uzasadni.
Pierwszeństwo ma plan, nie lepsze przeglądanie katalogu.

## Source Of Truth

- Kod: `app/api/v1/recipes.py`, `app/services/recipe_service.py`,
  `app/db/models/recipe.py`, `app/static/recipes.js` (obiekt `Recipes`)
- Import: [Import przepisu z URL](recipe-import.md)
- Wielojęzyczność: ADR `docs/decisions/recipe-translations.md` — dokument żyje
  na branchu `feature/i18n-recipe-import-ingredients`, poza tym baseline'em
