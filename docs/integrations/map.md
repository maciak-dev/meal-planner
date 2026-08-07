---
status: Proposed — kontrakt do zatwierdzenia w Sprincie 0, implementacja w Sprincie 2
last_updated: 2026-08-07
---

# Integracja z MAP

## Zasada nadrzędna

**Meal Planner pozostaje osobnym produktem. Nie zostaje wchłonięty.**

Osobne repozytorium, osobny deployment, osobne logowanie, osobna baza, osobna
roadmapa, osobny cykl wydań. Ta zasada jest zapisana po obu stronach: w
[North Star Meal Plannera](../north-star.md) oraz w MAP jako ADR-001
(„Meal Planner pozostaje osobnym systemem") i ADR-007 („MAP integruje, nie
wchłania").

Integracja odbywa się wyłącznie przez **jeden wersjonowany kontrakt HTTP**.
Nie przez wspólną bazę, nie przez wspólną sesję, nie przez współdzielony kod,
nie przez kopiowanie danych.

Kierunek zależności jest jednostronny: **MAP zna Meal Plannera. Meal Planner
nie wie o istnieniu MAP.** Meal Planner wystawia kontrakt i nic nie zakłada o
jego konsumencie. Wyłączenie MAP nie może w żaden sposób wpłynąć na działanie
Meal Plannera.

## Po co ta integracja istnieje

MAP jest pierwszym miejscem otwieranym rano. Meal Planner jest otwierany dwa
razy w tygodniu. Bez integracji odpowiedź na pytanie „co dziś na obiad" wymaga
przełączenia aplikacji — czyli dokładnie tego tarcia, które MAP ma usuwać
(cel 2 North Star MAP: oszczędność czasu; cel 3: integracja projektów).

Wartość integracji dla Meal Plannera jest odwrotna: plan zaczyna być widoczny
w miejscu, w którym użytkownik i tak patrzy, więc plan zaczyna być używany.

## 1. Jakie informacje MAP powinien widzieć

MAP dostaje **decyzje, nie surowe dane** (ADR-005 po stronie MAP). Każde pole
poniżej odpowiada na pytanie, które użytkownik zadaje rano, patrząc na pulpit.

| Informacja | Po co | Odpowiada na |
|---|---|---|
| **Posiłek na dziś** — nazwa, `recipe_id`, deep-link | Główna wartość integracji | „Co jemy dziś?" |
| **Posiłek na jutro** — nazwa, deep-link | Pozwala zareagować z wyprzedzeniem (rozmrożenie, dokupienie) | „Czy muszę coś dziś przygotować?" |
| **Kompletność planu bieżącego tygodnia** — zaplanowane dni / wszystkie dni, lista luk | Sygnał, że trzeba usiąść do planowania | „Czy plan jest domknięty?" |
| **Liczba pozycji do kupienia** (nieodhaczonych) + deep-link do listy | Decyzja „czy po drodze wpaść do sklepu" | „Czy trzeba zrobić zakupy?" |
| **Sygnały wymagające uwagi** — znormalizowana lista `{code, severity, message_key}` (np. `week_incomplete`, `shopping_list_empty_but_plan_exists`) | Pulpit MAP pokazuje powód, nie każe interpretować liczb | „Co zasługuje na uwagę?" |
| **Status instancji** — nazwa aplikacji, wersja, środowisko, czas wygenerowania odpowiedzi | Health w portfolio projektów MAP | „Czy Meal Planner działa?" |
| **Agregaty katalogu** — liczba przepisów, ewentualnie liczba zaimportowanych | Dowód życia projektu w portfolio/Hire Me | „Czy projekt żyje?" |

Czego MAP **nie** dostaje:

- treści przepisów (nazwy poza dzisiejszym i jutrzejszym posiłkiem, opisów,
  instrukcji, składników, zdjęć),
- zawartości listy zakupów pozycja po pozycji,
- danych użytkowników, ról, logów logowania ani logów requestów,
- historii planów i historii zakupów.

Reguła: **MAP dostaje liczniki, jedną nazwę dania i linki. Wszystko, co
wymaga przeglądania, wymaga wejścia do Meal Plannera.**

## 2. Kształt kontraktu

Jeden endpoint, jeden znormalizowany obiekt wyniku (ADR-003 po stronie MAP):

```
GET /api/v1/integration/summary
Authorization: Bearer <service token>
```

```jsonc
{
  "contract_version": "1.0",
  "generated_at": "2026-08-07T06:30:00Z",
  "app": {
    "name": "meal-planner",
    "instance": "production",
    "version": "1.4.0",
    "healthy": true
  },
  "today": {
    "date": "2026-08-07",
    "meal": { "recipe_id": 42, "name": "Kurczak z warzywami", "url": "https://meal.maciak.online/plan?date=2026-08-07" }
  },
  "tomorrow": {
    "date": "2026-08-08",
    "meal": null
  },
  "week": {
    "start": "2026-08-03",
    "planned_days": 4,
    "total_days": 7,
    "url": "https://meal.maciak.online/plan"
  },
  "shopping": {
    "open_items": 12,
    "done_items": 5,
    "url": "https://meal.maciak.online/shopping"
  },
  "attention": [
    { "code": "week_incomplete", "severity": "info", "context": { "missing_days": 3 } }
  ],
  "stats": { "recipes_total": 64 }
}
```

Zasady kontraktu:

- **Wersjonowany od pierwszego dnia** (`contract_version`). Zmiana łamiąca
  kontrakt wymaga nowej wersji, nie modyfikacji istniejącej — inaczej zmiana w
  Meal Plannerze psuje pulpit MAP.
- **Wszystkie pola opcjonalne z punktu widzenia konsumenta.** MAP musi umieć
  wyrenderować pulpit, gdy `today.meal` jest `null` albo gdy całej sekcji brak.
- **Kody, nie zdania.** `attention[].code` jest maszynowy; tłumaczenie na tekst
  należy do MAP. Meal Planner nie narzuca języka pulpitu MAP.
- **Bez PII.** W odpowiedzi nie ma nazw użytkowników, adresów IP ani niczego,
  co identyfikuje osobę.
- **Read-only, idempotentne, cache'owalne.** Wywołanie kontraktu niczego nie
  zmienia.

Uwierzytelnienie: **osobny token serwisowy** przekazywany nagłówkiem, całkowicie
niezależny od sesji użytkownika i cookie `access_token`. Token ma jeden zakres:
odczyt tego jednego endpointu. Brak tokena, zły token, brak danych → **fail
closed**: `401`/`503`, nigdy dane częściowe udające pełne.

Degradacja po stronie MAP: błąd lub timeout oznacza kafelek „brak danych z Meal
Plannera", nigdy mock prezentowany jako prawda.

## 3. Jakie akcje MAP powinien móc wykonać

### Wersja 1 — zero akcji zapisu

Kontrakt v1 jest **wyłącznie do odczytu**. Jedyne „akcje" MAP to **deep-linki**
otwierające Meal Plannera w odpowiednim miejscu:

| Akcja w MAP | Efekt |
|---|---|
| „Zobacz dzisiejszy posiłek" | `…/plan?date=YYYY-MM-DD` |
| „Otwórz plan tygodnia" | `…/plan` |
| „Otwórz listę zakupów" | `…/shopping` |

To jest świadomy wybór, nie ograniczenie techniczne. Zapis przez integrację
tworzy dwa źródła prawdy dla tego samego stanu i podwaja powierzchnię błędów,
zanim ktokolwiek udowodnił, że kontrakt read-only jest w ogóle używany.

### Wersja 2 — dokładnie dwie akcje, po udowodnieniu wartości v1

| Akcja | Endpoint | Dlaczego akurat ta |
|---|---|---|
| Dodaj pozycję do listy zakupów | `POST /api/v1/integration/shopping-items` | MAP jest miejscem, gdzie rano zapisuje się „kup mleko"; przełączanie aplikacji dla jednej pozycji to dokładnie to tarcie, które integracja ma usuwać |
| Oznacz dzisiejszy posiłek jako ugotowany | `POST /api/v1/integration/today/cooked` | Jedno kliknięcie zamyka pętlę dnia i zasila przyszłą historię |

Warunki dla obu: wąski zakres tokena (osobny od read-only), idempotencja
(klucz idempotencji w żądaniu), limit tempa, pełny audyt po stronie Meal
Plannera, i **żadnych innych akcji**. Rozszerzanie tej listy wymaga decyzji
produktowej, nie decyzji implementacyjnej.

## 4. Czego MAP nie powinien robić

Lista jest twarda i jest częścią kontraktu:

1. **Nie replikuje danych Meal Plannera.** Żadnej kopii przepisów, planu ani
   listy zakupów po stronie MAP. Cache odpowiedzi kontraktu — tak, z krótkim
   TTL i jawnym znacznikiem czasu. Własna baza danych domenowych — nie.
2. **Nie renderuje UI Meal Plannera.** Bez iframe'ów, bez odtwarzania listy
   przepisów, bez formularzy edycji. MAP pokazuje kafelek i link.
3. **Nie planuje posiłków.** Planowanie jest rdzeniem Meal Plannera. W dniu, w
   którym MAP zacznie planować, przestaje integrować i zaczyna wchłaniać.
4. **Nie edytuje ani nie usuwa przepisów, planów i pozycji listy.** W v1 nie
   pisze nic; w v2 wyłącznie dwie akcje wymienione wyżej.
5. **Nie dotyka bazy Meal Plannera.** Żadnego wspólnego PostgreSQL, żadnego
   czytania `fastapi_db` z zewnątrz, żadnego SQL przez granicę systemów.
   Wyłącznie HTTP.
6. **Nie współdzieli sesji ani tożsamości.** Meal Planner ma własne logowanie i
   własną tabelę `users`. MAP nie loguje użytkownika do Meal Plannera, nie
   wystawia SSO i nie zarządza kontami Meal Plannera.
7. **Nie wystawia danych Meal Plannera publicznie.** Publiczna część MAP
   (Hire Me, konto demo) może zobaczyć co najwyżej anonimowe agregaty
   („projekt żyje: N przepisów") — nigdy dzisiejszego posiłku ani listy
   zakupów.
8. **Nie wymusza wspólnego stosu technologicznego, repozytorium, harmonogramu
   wydań ani wspólnego deploymentu.** Meal Planner może zmienić framework,
   bazę i hosting bez pytania MAP o zgodę — o ile kontrakt pozostaje spełniony.
9. **Nie traktuje niedostępności Meal Plannera jako awarii MAP.** Brak
   odpowiedzi to pusty kafelek, nie błąd pulpitu.
10. **Nie definiuje roadmapy Meal Plannera.** Potrzeba MAP może być zgłoszona
    jako pozycja w backlogu Meal Plannera i przechodzi ten sam test North Star
    co każda inna.

## 5. Warunki wejścia i kolejność

Integracja **nie ma sensu przed** [planem posiłków](../modules/meal-plan.md) i
[serwerową listą zakupów](../modules/shopping-list.md) — bez nich kontrakt
zwróciłby wyłącznie liczbę przepisów, a to nie jest odpowiedź na żadne pytanie
z pulpitu MAP.

Kolejność:

1. **Sprint 0** — zatwierdzenie tego dokumentu jako deklaracji kontraktu;
   zgłoszenie do backlogu MAP, że zależność „kontrakt statusu po stronie Meal
   Plannera" ma właściciela i kształt.
2. **Sprint 1** — powstaje plan i serwerowa lista zakupów, czyli dane, które
   kontrakt ma wystawić.
3. **Sprint 2** — implementacja `GET /api/v1/integration/summary`, token
   serwisowy, deep-linki, kafelek po stronie MAP.
4. **Później** — v2 z dwiema akcjami zapisu, jeżeli v1 udowodni, że jest
   używana.

## Source Of Truth

- Kierunek Meal Plannera: [North Star](../north-star.md)
- Plan wdrożenia: [roadmapa](../product/roadmap.md)
- Po stronie MAP: `MAP/docs/ecosystem.md`, `MAP/docs/decisions/ADR-001.md`,
  `ADR-003.md`, `ADR-005.md`, `ADR-007.md`, pozycja „Obszar Integrations — Meal
  Planner w MAP" w `MAP/docs/product/backlog.md`
