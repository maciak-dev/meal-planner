---
status: Active
last_updated: 2026-08-07
current_milestone: Sprint 0 — Wizja i audyt produktowy
current_goal: Ustalić, czym Meal Planner jest i czym nie jest, zamknąć wiszące elementy poprzedniego sprintu i zdefiniować kontrakt integracyjny dla MAP — bez rozpoczynania prac programistycznych nad nowymi funkcjami.
---

# Meal Planner Roadmap

Roadmapa opisuje produkt, nie backend. Kierunek nadrzędny:
[North Star](../north-star.md). Diagnoza stanu wyjściowego:
[audyt produktowy](../audits/product-audit-2026-08-07.md).

## Obecny stan

- Produkcja działa publicznie, jako `systemd` + `nginx` + PostgreSQL
  `fastapi_db`; RC działa na osobnej bazie `fastapi_db_rc`, uruchamiane na
  żądanie.
- Katalog przepisów działa: CRUD, zdjęcia, widoczność prywatny/publiczny, role.
  Na produkcji 64 przepisy, 4 autorów, 5 kont.
- Import przepisu z URL (schema.org + fallback HTML, draft z korektą,
  pobieranie zdjęcia) jest zaimplementowany i przetestowany na branchu
  `feature/i18n-recipe-import-ingredients`; **nie jest jeszcze na produkcji**.
- Dwujęzyczne UI PL/EN działa; treść przepisów w EN jest osiągalna wyłącznie
  przez import z linku.
- Lista zakupów działa wyłącznie w `localStorage` przeglądarki.
- Model normalizacji składników (`ingredients`, `ingredient_aliases`,
  `recipe_ingredients`, `store_sections`) istnieje w schemacie i nie ma
  jeszcze ani UI, ani danych.
- **Nie istnieje plan tygodnia, dzień, posiłek, historia ani dashboard.**
- Warstwa operacyjna uporządkowana: Alembic (7 migracji, jeden head), 121
  testów, backup zweryfikowany, runbooki wdrożenia i rollbacku.
- Meal Planner nie jest zintegrowany z MAP; MAP nie ma jeszcze kontraktu, z
  którego mógłby korzystać.

## Teraz

**Sprint 0 — Wizja i audyt produktowy.** Bez prac programistycznych nad nowymi
funkcjami.

1. Przyjąć [North Star](../north-star.md) i [Vision](../product/vision.md) jako
   obowiązujące kryterium przyjmowania zadań do sprintów.
2. Przyjąć [kontrakt integracyjny dla MAP](../integrations/map.md) jako
   deklarację (implementacja: Sprint 2) i zgłosić go do backlogu MAP jako
   spełnioną zależność „kontrakt statusu po stronie Meal Plannera".
3. Zamknąć wiszące elementy poprzedniej pracy:
   - uruchomić migrację `69eea78ac02c` na RC (jedyna niewykonana),
   - domknąć decyzję o wdrożeniu importu przepisu na produkcję,
   - zdecydować, czy branch `feature/i18n-recipe-import-ingredients` idzie do
     `main`.
4. Podjąć cztery decyzje produktowe blokujące Sprint 1 (patrz „Decyzje do
   podjęcia" poniżej).

## Następnie

**Sprint 1 — Tydzień i lista zakupów.** Moment, w którym nazwa produktu staje
się prawdziwa.

- Model planu: tydzień → dzień → posiłek (jeden slot na dzień w v1).
- Ekran planu tygodnia z przypisywaniem przepisu do dnia.
- Serwerowa lista zakupów per użytkownik (koniec `localStorage`).
- Generowanie listy zakupów z planu, z sensowną agregacją ilości.
- Naprawa kontrolek, które dziś kłamią: widoczność przepisu, pola porcji/czasów
  w imporcie, usunięcie martwej pozycji „Składniki" z menu.

**Sprint 2 — Dashboard i integracja.**

- Dashboard odpowiadający na pytanie „co dzisiaj?"
  ([projekt](dashboard.md)).
- Endpoint `GET /api/v1/integration/summary` — read-only kontrakt dla MAP.
- Deep-linki, z których MAP korzysta (`/plan?date=…`, `/shopping`).

## Później

- Skalowanie porcji i przeliczanie składników.
- Historia „co jedliśmy" i sugestie na podstawie rotacji.
- Ingredient Engine (Fazy C/D): mapowanie składników na słownik, aliasy,
  sekcje sklepowe, sortowanie listy po działach sklepu — **dopiero po** tym,
  jak serwerowa lista zakupów będzie z tego korzystać.
- Backfill 64 istniejących przepisów o strukturalne składniki (zawsze dry-run
  + ręczny przegląd).
- Tryb gotowania: kroki, timery, ekran kuchenny.
- Dokończenie dwujęzyczności treści przepisów (dodanie tłumaczenia z poziomu
  edycji).
- Migracja domeny na `meal.maciak.online` i `rc.meal.maciak.online`.
- Jedna, wąska akcja zapisu dla MAP (dodanie pozycji do listy zakupów) — po
  udowodnieniu wartości kontraktu read-only.

## Odłożone

- **Kalorie, makroskładniki, cele dietetyczne.**
  Powód: inny produkt, inna motywacja użytkownika; nie odpowiada na żadne
  pytanie North Star.
- **Społeczność, komentarze, oceny, publiczne udostępnianie przepisów światu.**
  Powód: Meal Planner obsługuje jedno gospodarstwo domowe.
- **Aplikacja mobilna natywna.**
  Powód: responsywne UI z trybem zakupów rozwiązuje ten sam problem taniej.
- **Integracja z zakupami online / API sklepów.**
  Powód: wysoki koszt, zależność zewnętrzna, brak dowodu, że lista zakupów jest
  w ogóle używana między urządzeniami.
- **Rozpoznawanie przepisów ze zdjęć / OCR / AI generujące plan.**
  Powód: najpierw potrzebna jest stabilna warstwa planu i danych.
- **Wchłonięcie Meal Plannera do repozytorium MAP.**
  Powód: łamie ADR-001 i ADR-007 po stronie MAP oraz izolację działającej
  produkcji.

## Decyzje do podjęcia (blokują Sprint 1)

| # | Decyzja | Dlaczego blokuje |
|---|---|---|
| D-1 | Ile slotów posiłkowych na dzień w v1: **jeden (obiad)** czy trzy (śniadanie/obiad/kolacja)? | Determinuje model danych, ekran planu i złożoność generowania listy |
| D-2 | Czy plan jest **wspólny dla gospodarstwa** czy per użytkownik? | Dziś przepisy są per użytkownik z flagą publiczny; plan wspólny wymaga pojęcia gospodarstwa domowego |
| D-3 | Jak agregujemy ilości w liście zakupów w v1: **sumowanie tylko przy zgodnej jednostce, reszta jako osobne pozycje** czy pełna normalizacja jednostek? | Decyduje, czy Ingredient Engine jest potrzebny w Sprincie 1, czy dopiero później |
| D-4 | Czy `Recipe` dostaje kolumny `servings` / `prep_time` / `cook_time`, czy usuwamy te pola z formularza importu? | Dziś dane są zbierane i wyrzucane (P-3 w audycie); stan pośredni jest niedopuszczalny |

Rekomendacja: D-1 → jeden slot, D-2 → wspólny dla gospodarstwa, D-3 → tylko
zgodne jednostki, D-4 → dodać kolumny (dane są potrzebne dla skalowania porcji
i dla dashboardu).

## Ryzyka i blokady

- **Największe ryzyko produktowe:** dołożenie kolejnej funkcji do warstwy
  treści (np. Ingredient Engine) zamiast zbudowania warstwy decyzji. Produkt
  stanie się wtedy jeszcze lepszym katalogiem i dalej nie będzie planerem.
- Serwerowa lista zakupów oznacza migrację danych z `localStorage` —
  użytkownicy mogą stracić bieżącą listę, jeśli nie przewidzimy jednorazowego
  importu przy pierwszym uruchomieniu.
- Model planu wchodzi w te same tabele, które właśnie dostały 7 migracji.
  Każda zmiana schematu wymaga backupu i przejścia przez RC (runbook:
  `operations/sprint-0-production-rollout.md`).
- Import z linku nie był jeszcze na produkcji; wdrożenie go i budowa planu
  jednocześnie zwiększają powierzchnię ryzyka. Rekomendacja: wdrożyć import
  osobno, przed Sprintem 1.
- `request_log` rośnie bez retencji (318 tys. wierszy) — nie blokuje produktu,
  ale będzie rosnąć razem z nim.
- Kontrakt dla MAP tworzy zewnętrzną zależność. Musi być wersjonowany od
  pierwszego dnia, inaczej zmiana w Meal Plannerze zepsuje pulpit MAP.
