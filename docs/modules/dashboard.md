---
status: Planned — nie istnieje w kodzie
last_updated: 2026-08-07
---

# Dashboard

## Purpose

Pierwszy ekran po zalogowaniu. Ma odpowiadać na jedno pytanie: **co dzisiaj
powinienem zrobić?** Służy celowi 1 North Star.

Kryterium projektowe: w 10 sekund odpowiedzieć na cztery pytania — _co jemy
dziś? co jemy dalej w tym tygodniu? czy trzeba coś kupić? gdzie kontynuować
pracę?_

## Current Capabilities

Brak. `GET /` przekierowuje zalogowanego użytkownika na `/recipes-ui`, czyli na
płaską listę wszystkich widocznych przepisów posortowaną po dacie dodania.

Na pytanie „co dzisiaj?" obecny pierwszy ekran odpowiada „oto 64 przepisy". To
nie jest odpowiedź, to jest zrzut bazy danych.

## Current Limitations

Dashboard nie może powstać przed [planem posiłków](meal-plan.md) — bez planu
nie ma czego pokazać poza liczbą przepisów, a licznik przepisów nie jest
odpowiedzią na żadne pytanie użytkownika.

## Design Direction

Pełny projekt ekranu, strefy, źródła danych i zasady degradacji:
[product/dashboard.md](../product/dashboard.md).

Trzy zasady, które obowiązują niezależnie od układu:

1. **Dashboard prezentuje decyzje, nie dane.** Żadnych statystyk, żadnych
   logów, żadnych liczników dla samego licznika.
2. **Pusty stan zawsze proponuje jedno konkretne działanie.** „Brak planu na
   dziś" musi mieć obok siebie przycisk, który to naprawia w jednym kliknięciu.
3. **Degradacja zamiast błędu.** Strefa bez danych pokazuje komunikat i
   działanie, nigdy nie wywraca ekranu.

## Source Of Truth

- Projekt: [product/dashboard.md](../product/dashboard.md)
- Zależność: [Plan posiłków](meal-plan.md),
  [Lista zakupów](shopping-list.md)
- Plan: [roadmapa — Sprint 2](../product/roadmap.md)
