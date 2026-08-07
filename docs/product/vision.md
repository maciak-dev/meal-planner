---
status: Active
last_updated: 2026-08-07
---

# Meal Planner Product Vision

Dokument nadrzędny: [North Star](../north-star.md). Wizja konkretyzuje North
Star na poziomie produktu; nie powtarza go.

## Jaki problem rozwiązuje Meal Planner

Problem nie brzmi „nie mam gdzie trzymać przepisów". Przepisy da się trzymać w
notatkach, w zakładkach przeglądarki i w głowie — i tak właśnie są trzymane.

Problem brzmi:

> **Codziennie trzeba podjąć tę samą decyzję („co jemy?"), a raz w tygodniu
> przełożyć ją na zakupy — i obie te czynności są wykonywane od zera, z
> pamięci, pod presją czasu.**

Koszt tego problemu to: powtarzalne dania, zakupy „na oko", wyprawy do sklepu
po jeden brakujący składnik, marnowanie jedzenia i decyzja o 17:00 w złym
nastroju.

Meal Planner rozwiązuje ten problem w trzech ruchach:

1. **plan** — decyzja podjęta raz, na spokojnie, dla całego tygodnia,
2. **lista** — plan zamieniony automatycznie w jedną listę zakupów,
3. **katalog** — przepisy zebrane po to, żeby plan dało się złożyć w minuty, a
   nie w pół godziny.

## Product Intent

Meal Planner ma być aplikacją otwieraną **dwa razy w tygodniu i raz dziennie**:

- raz w tygodniu, żeby ułożyć plan i wygenerować listę,
- raz na zakupach, w sklepie, z telefonu,
- codziennie na 10 sekund, żeby zobaczyć, co jest dziś.

To jest zupełnie inny profil użycia niż „przeglądarka przepisów" i wynikają z
niego wszystkie decyzje UX: pierwszy ekran to plan i dziś, nie lista wszystkich
przepisów; tryb zakupów jest osobnym, dużym trybem; szukanie przepisu jest
czynnością pomocniczą, nie główną.

## Czym Meal Planner jest dzisiaj

Repozytorium zawiera działający produkt: logowanie z rolami, katalog przepisów
(64 przepisy, 4 autorów na produkcji), widoczność prywatny/publiczny, zdjęcia,
import przepisu z linku (schema.org + fallback HTML, z twardym SSRF guardem),
dwujęzyczne UI PL/EN, lokalną listę zakupów z trybem sklepowym oraz panel
administracyjny z logami. Warstwa operacyjna jest uporządkowana: Alembic,
rozdzielone produkcja i RC, backup, runbook wdrożeniowy.

Nie zawiera natomiast **planu**: nie ma tygodnia, dnia, posiłku, historii ani
generowania listy zakupów z planu. Lista zakupów żyje w `localStorage` jednej
przeglądarki.

Innymi słowy: zbudowano zaplecze (cel 3) i część kuchni (cel 2), ale sala, do
której przychodzi użytkownik (cel 1), jeszcze nie istnieje. Pełna diagnoza:
[audyt produktowy](../audits/product-audit-2026-08-07.md).

## Ekosystem

Meal Planner jest jedną z trzech aplikacji ekosystemu `maciak.online` obok
Public Website i MAP (Personal Operating System). Docelowa domena:
`meal.maciak.online`, przedprodukcja: `rc.meal.maciak.online`.

Meal Planner **pozostaje osobnym produktem**: osobne repo, deployment,
logowanie, roadmapa i cykl wydań. MAP go integruje przez jawny kontrakt —
szczegóły i granice: [integrations/map.md](../integrations/map.md).

## Product Principles

- **Produkt odpowiada na pytanie, nie prezentuje danych.** Pierwszy ekran mówi
  „dziś jest X, do kupienia zostało Y", a nie „oto 64 przepisy".
- **Plan generuje listę; lista nie jest wpisywana ręcznie.** Ręczne dopisanie
  pozycji zostaje jako wyjątek, nie jako główna ścieżka.
- **Każdy element UI ma właściciela w postaci celu North Star.** Element bez
  celu jest usuwany, nie utrzymywany.
- **Nie budujemy modelu danych przed jego konsumentem.**
- **Pusty stan zawsze proponuje jedno konkretne działanie.**
- **Dwujęzyczność dotyczy interfejsu i treści przepisu, nie jest połowiczna** —
  jeżeli produkt oferuje przełącznik EN, musi istnieć droga do treści EN.

## Near-Term Product Focus

1. **Zamienić katalog w planer** — model tygodnia/dnia/posiłku i ekran planu.
2. **Przenieść listę zakupów na serwer i generować ją z planu.**
3. **Dać pierwszy ekran, który odpowiada „co dzisiaj?"**
   ([projekt dashboardu](dashboard.md)).
4. **Zamknąć niedokończone obietnice UI** (widoczność przepisu, treść EN,
   martwy przycisk „Składniki") — produkt nie może pokazywać kontrolek, które
   nic nie robią.
5. **Wystawić kontrakt integracyjny dla MAP** — read-only, wersjonowany, fail
   closed.
