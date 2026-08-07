---
status: Active
last_updated: 2026-08-07
---

# Meal Planner Backlog

Backlog trzyma wyłącznie pracę aktywną lub wciąż wartościową. Historia sprintów
i zamknięte plany żyją w `docs/audits/` i `docs/handoffs/`.

**Zasada wejścia:** pozycja trafia do backlogu tylko, jeśli odpowiada na
przynajmniej jedno pytanie [North Star](../north-star.md): _pomaga zdecydować,
co jeść / skraca drogę do zakupów / sprawia, że używany przepis jest pod ręką_.
Pozycje bez odpowiedzi lądują w parking lot.

Legenda celu NS: **1** = decyzja, **2** = zakupy, **3** = katalog.

---

## Now

### Sprint 0 — Wizja, audyt, kontrakt

- Value: produkt dostaje kryterium, według którego można odrzucać pomysły; MAP dostaje deklarację kontraktu.
- Cel NS: 1, 2, 3
- Status: Active
- Dependencies: brak
- Links: [Audyt produktowy](../audits/product-audit-2026-08-07.md), [North Star](../north-star.md)

### Uruchomienie migracji `69eea78ac02c` na RC

- Value: RC przestaje być o jedną migrację za branchem; odblokowuje decyzję o wdrożeniu importu.
- Cel NS: 3
- Status: Active (jedyna niewykonana migracja)
- Dependencies: backup `fastapi_db_rc`, dostęp do VPS
- Links: handoff `docs/handoffs/i18n-recipe-import-ingredients.md` na branchu `feature/i18n-recipe-import-ingredients`

### Decyzja o wdrożeniu importu przepisu z URL na produkcję

- Value: najlepsza funkcja produktu jest gotowa i leży na branchu, nie dając nikomu wartości.
- Cel NS: 3
- Status: Decision needed
- Dependencies: RC po migracji, smoke na RC
- Links: [Recipe Import](../modules/recipe-import.md)

### ~~Cztery decyzje produktowe blokujące Sprint 1 (D-1…D-4)~~

- Value: bez nich model planu i listy zakupów nie da się zaprojektować.
- Cel NS: 1, 2
- Status: **Done (2026-08-07)** — [ADR-001](../decisions/ADR-001.md),
  [ADR-002](../decisions/ADR-002.md), [ADR-003](../decisions/ADR-003.md),
  [ADR-004](../decisions/ADR-004.md)
- Links: [Rejestr decyzji](../decisions/README.md)

---

## Next

### Model planu: tydzień → dzień → posiłek

- Value: rdzeń produktu; bez niego nazwa „Meal Planner" jest nieprawdziwa.
- Cel NS: 1
- Status: Planned (Sprint 1)
- Dependencies: D-1, D-2
- Links: [Meal Plan module](../modules/meal-plan.md)

### Ekran planu tygodnia

- Value: decyzja na cały tydzień podjęta raz, w jednym miejscu, w kilka minut.
- Cel NS: 1
- Status: Planned (Sprint 1)
- Dependencies: model planu
- Links: [Meal Plan module](../modules/meal-plan.md)

### Serwerowa lista zakupów

- Value: lista przestaje ginąć między laptopem a telefonem — dziś to unieważnia najlepiej zrobiony moduł aplikacji.
- Cel NS: 2
- Status: Planned (Sprint 1)
- Dependencies: jednorazowa migracja istniejącego `localStorage`; jedna wspólna lista wg [ADR-002](../decisions/ADR-002.md)
- Links: [Shopping List module](../modules/shopping-list.md)

### Generowanie listy zakupów z planu

- Value: zamienia ~40–70 interakcji tygodniowo w jedno kliknięcie.
- Cel NS: 1, 2
- Status: Planned (Sprint 1)
- Dependencies: model planu, serwerowa lista, reguła agregacji z [ADR-003](../decisions/ADR-003.md)
- Links: [Shopping List module](../modules/shopping-list.md)

### Kolumny `servings`, `prep_time_minutes`, `cook_time_minutes`

- Value: import przestaje wyrzucać dane użytkownika (P-3); dashboard może pokazać „45 min · 4 porcje"; skalowanie porcji dostaje podstawę.
- Cel NS: 1, 3
- Status: Planned (Sprint 1) — [ADR-004](../decisions/ADR-004.md)
- Dependencies: migracja Alembic; kolejność względem branchu `feature/i18n-recipe-import-ingredients`
- Links: [Recipes module](../modules/recipes.md), [Recipe Import module](../modules/recipe-import.md)

### Naprawa kontrolek, które kłamią

- Value: widoczność przepisu (P-1, P-2) i usunięcie martwego „Składniki" (P-5). Najtańsza poprawa zaufania do interfejsu.
- Cel NS: 3
- Status: Planned (Sprint 1)
- Dependencies: brak; P-3 (porcje i czasy) obsługuje osobna pozycja wg [ADR-004](../decisions/ADR-004.md)
- Links: [Audyt — sekcja 4.3](../audits/product-audit-2026-08-07.md)

### Dashboard „co dzisiaj?"

- Value: pierwszy ekran przestaje pokazywać bazę danych i zaczyna odpowiadać.
- Cel NS: 1
- Status: Planned (Sprint 2)
- Dependencies: model planu, serwerowa lista zakupów
- Links: [Projekt dashboardu](dashboard.md)

### Kontrakt integracyjny dla MAP (`GET /integration/summary`)

- Value: MAP pokazuje „co dziś na obiad" i „ile zostało do kupienia" bez wchodzenia do Meal Plannera; zamyka zależność z backlogu MAP.
- Cel NS: 1, 2
- Status: Planned (Sprint 2)
- Dependencies: dane dashboardu, token serwisowy
- Links: [Integracja z MAP](../integrations/map.md)

---

## Later

### Skalowanie porcji

- Value: ten sam przepis na 2 i na 6 osób bez liczenia w głowie; warunek sensownej listy zakupów.
- Cel NS: 1, 2
- Status: Idea
- Dependencies: `Recipe.servings` (D-4), strukturalne składniki

### Historia „co jedliśmy" i sugestie

- Value: eliminuje powtarzalność planów i pustą kartkę przy planowaniu.
- Cel NS: 1
- Status: Idea
- Dependencies: plan działający przez kilka tygodni

### Ingredient Engine — mapowanie, aliasy, sekcje sklepowe

- Value: lista zakupów sortowana po działach sklepu i scalająca „pomidory"/„pomidor".
- Cel NS: 2
- Status: Idea — **świadomie zablokowane** do czasu, aż serwerowa lista zakupów będzie z tego korzystać
- Dependencies: serwerowa lista zakupów, generowanie z planu
- Links: [Ingredients module](../modules/ingredients.md)

### Backfill 64 przepisów o strukturalne składniki

- Value: istniejący katalog zaczyna działać z generowaniem listy, nie tylko nowe przepisy.
- Cel NS: 2, 3
- Status: Idea
- Dependencies: Ingredient Engine, zawsze dry-run + ręczny przegląd

### Tryb gotowania

- Value: kroki, timery, ekran, który nie gaśnie — telefon w kuchni jako drugi kontekst po sklepie.
- Cel NS: 3
- Status: Idea

### Dokończenie dwujęzyczności treści przepisu

- Value: przełącznik EN przestaje być fasadą (P-4).
- Cel NS: 3
- Status: Idea
- Dependencies: decyzja, czy tłumaczenie jest ręczne, czy wspomagane
- Links: [i18n module](../modules/i18n.md)

### Filtry i tagi w katalogu

- Value: znalezienie przepisu przestaje zależeć od pamiętania jego nazwy.
- Cel NS: 3
- Status: Idea
- Dependencies: rozmiar katalogu uzasadniający filtry

### Migracja domeny na `meal.maciak.online` + `rc.meal.maciak.online`

- Value: zgodność z docelowym ekosystemem MAP (ADR-007 po stronie MAP).
- Cel NS: —
- Status: Idea (operacyjne)
- Dependencies: nginx, certyfikaty, aktualizacja kontraktu MAP

### Retencja `request_log`

- Value: baza przestaje rosnąć o szum botów (318 tys. wierszy).
- Cel NS: —
- Status: Idea (operacyjne)
- Links: [Admin module](../modules/admin.md)

### Jedna akcja zapisu dla MAP (dodanie pozycji do listy zakupów)

- Value: „kup mleko" zapisane rano w MAP trafia na listę bez przełączania aplikacji.
- Cel NS: 2
- Status: Idea — **dopiero po** udowodnieniu wartości kontraktu read-only
- Links: [Integracja z MAP](../integrations/map.md)

---

## Parking lot

### Wybór jednego motywu graficznego — decyzja potrzebna

- Value: każda zmiana UI kosztuje dziś podwójnie; motyw „cyber" jest sprzeczny z domeną produktu.
- Status: Decision needed

### Kalorie, makroskładniki, cele dietetyczne

- Status: Deferred — inny produkt, inna motywacja użytkownika

### Społeczność: komentarze, oceny, publiczny katalog

- Status: Deferred — Meal Planner obsługuje jedno gospodarstwo domowe

### Natywna aplikacja mobilna

- Status: Deferred — responsywne UI z trybem zakupów rozwiązuje ten sam problem taniej

### Integracja z zakupami online / API sklepów

- Status: Deferred — wysoki koszt i zależność zewnętrzna przed dowodem, że lista jest używana między urządzeniami

### AI generujące plan tygodnia / OCR przepisów ze zdjęć

- Status: Deferred — najpierw stabilna warstwa planu i danych

### Cyberpunkowe migające tło (z `ISSUES.md`)

- Status: Rejected — nie odpowiada na żadne pytanie North Star
