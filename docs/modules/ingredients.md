---
status: Zamrożony — model istnieje, brak danych i UI
last_updated: 2026-08-07
---

# Składniki (normalizacja)

## Purpose

Docelowo: zamienić wolny tekst składników w dane, z których da się zbudować
sensowną listę zakupów — scalić „pomidor"/„pomidory"/„tomatoes" w jedną
pozycję, zsumować ilości i posortować listę po działach sklepu. Służy celowi 2
North Star.

## Current Capabilities

- Schemat w bazie: rozbudowany `ingredients` (nazwy kanoniczne PL/EN, domyślna
  sekcja sklepu, flaga `is_essential`), `ingredient_aliases`,
  `recipe_ingredients` (ilość, jednostka, notatka, `parsed_name`,
  `needs_review`), `store_sections` (nazwy PL/EN, kolejność).
- Parser linii składnika PL/EN (`app/services/ingredient_parsing/parser.py`) —
  działa i jest używany przez import przepisu.
- `GET /ingredients/map` — mapa `nazwa → is_essential` używana przez UI do
  domyślnego zaznaczania checkboxów przy składnikach przepisu.
- Import przepisu zapisuje `recipe_ingredients` z `ingredient_id = NULL` —
  strukturalne dane powstają, ale nie są z niczym powiązane.

## Current Limitations

- **Tabela `ingredients` ma zero wierszy na produkcji.** Cały mechanizm
  „składnik ważny/nieważny" jest w praktyce bezczynny: brak wpisu oznacza
  domyślne `True`, więc zawsze wszystko jest zaznaczone.
- **Brak jakiegokolwiek UI.** Pozycja „Składniki" w menu burger wywołuje toast
  „funkcja wkrótce dostępna" — jedyny widoczny ślad modułu prowadzi donikąd.
- **Brak konsumenta danych.** `store_sections` istnieją po to, by sortować
  listę zakupów po działach sklepu — a lista zakupów jest w `localStorage` i
  nie wie nic o składnikach.
- Brak `/api/v1/ingredients/*` i `/api/v1/store-sections`, brak mapowania
  składnika na słownik, brak tworzenia aliasów, brak backfillu 64 istniejących
  przepisów.

## Design Direction

**Moduł jest świadomie zamrożony.** To nie jest zaniedbanie — to decyzja
wynikająca z zasady „nie budujemy modelu danych przed jego konsumentem".

Warunek odmrożenia: **istnieje serwerowa lista zakupów generowana z planu**
(Sprint 1). Dopóki go nie ma, każda praca tutaj powiększa powierzchnię
utrzymania bez wartości dla użytkownika.

Kolejność po odmrożeniu:

1. `/api/v1/ingredients/*` + minimalne UI mapowania składnika na słownik
   (Faza C z pierwotnego planu).
2. Sekcje sklepowe i sortowanie listy zakupów po działach.
3. Aliasy — tworzone wyłącznie jawną akcją użytkownika, nigdy automatycznym
   scalaniem niepewnych dopasowań.
4. Backfill 64 przepisów — zawsze dry-run i ręczny przegląd raportu (Faza D).

Do tego czasu: **usunąć pozycję „Składniki" z menu**, żeby produkt nie
pokazywał kontrolki, która nic nie robi.

## Source Of Truth

- Kod: `app/db/models/ingredient.py`, `ingredient_alias.py`,
  `recipe_ingredient.py`, `store_section.py`,
  `app/services/ingredient_parsing/`
- Architektura: `docs/architecture/ingredient-model.md` i decyzja
  `docs/decisions/ingredient-normalization.md` — oba dokumenty żyją na branchu
  `feature/i18n-recipe-import-ingredients`, poza tym baseline'em
- Wcześniejszy przegląd: [ingredients-feature-review.md](../audits/ingredients-feature-review.md)
