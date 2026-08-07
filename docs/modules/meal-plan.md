---
status: Planned — nie istnieje w kodzie
last_updated: 2026-08-07
---

# Plan posiłków

## Purpose

Moduł, w którym zapada decyzja: **co jemy w tym tygodniu**. Jest rdzeniem
produktu i jedynym modułem, którego brak sprawia, że nazwa „Meal Planner" jest
nieprawdziwa. Służy celowi 1 North Star i jest warunkiem koniecznym celu 2
(lista zakupów generowana z planu) oraz dashboardu.

## Current Capabilities

Brak. Moduł nie istnieje: nie ma modelu tygodnia, dnia ani posiłku, nie ma
endpointów, nie ma UI. Potwierdzone w schemacie bazy i w kodzie
([audyt produktowy](../audits/product-audit-2026-08-07.md), sekcja 7).

Dziś rolę planu pełni pamięć użytkownika: wybiera przepisy w katalogu i sam
pamięta, które z nich „są na ten tydzień".

## Design Direction

Kształt v1 — celowo minimalny, bo produkt konkuruje z kartką i przegrywa
liczbą kliknięć, nie brakiem opcji:

- **Jednostka planu to dzień, nie posiłek.** V1 zakłada jeden slot dziennie
  (obiad) — decyzja D-1 w [roadmapie](../product/roadmap.md). Trzy sloty można
  dodać później bez łamania modelu; odwrotna droga jest droższa.
- **Tydzień jest widokiem, nie bytem.** Plan to zbiór wpisów `data → przepis`.
  Tydzień w UI to zakres siedmiu dni, nie osobna encja z cyklem życia.
- **Wpis planu może być pusty albo tekstowy.** „Obiad u rodziców" i „zostało z
  wczoraj" to prawidłowe wpisy. Plan, który akceptuje tylko przepisy z katalogu,
  zostanie porzucony po dwóch tygodniach.
- **Plan jest własnością gospodarstwa domowego, nie użytkownika** (decyzja D-2).
  Dziś przepisy mają właściciela i flagę publiczności; plan wymaga pojęcia
  wspólnoty domowej albo świadomej decyzji, że jest jeden plan na instancję.
- **Z planu prowadzą dokładnie dwie akcje**: „Generuj listę zakupów" i „Gotuj"
  (otwórz przepis).
- **Kopiowanie poprzedniego tygodnia** jest funkcją pierwszej klasy, nie
  dodatkiem — realny użytkownik powtarza 60–70% dań.

Czego v1 nie robi: skalowania porcji, wielu slotów, historii i statystyk,
sugestii, cykli. Te rzeczy są w [backlogu](../product/backlog.md) i wchodzą
dopiero, gdy plan udowodni, że jest używany.

## Zależności

- **Blokuje**: [Dashboard](dashboard.md),
  [generowanie listy zakupów](shopping-list.md),
  [kontrakt dla MAP](../integrations/map.md).
- **Jest blokowany przez**: decyzje D-1 (liczba slotów) i D-2 (własność planu)
  z [roadmapy](../product/roadmap.md).

## Source Of Truth

- Kierunek: [North Star](../north-star.md), priorytet 1
- Plan: [roadmapa — Sprint 1](../product/roadmap.md)
- Diagnoza braku: [audyt produktowy](../audits/product-audit-2026-08-07.md)
