---
status: Active
last_updated: 2026-08-07
---

# Portfolio modułów

Ocena wszystkich modułów Meal Plannera względem [North Star](../north-star.md).
Priorytet wynika z trzech celów: (1) zdejmuje decyzję, (2) zdejmuje zakupy,
(3) zachowuje używane przepisy.

| Moduł | Cel | Wartość (cel NS) | Priorytet | Status | Kierunek |
|---|---|---|---|---|---|
| [Plan posiłków](meal-plan.md) | Tydzień, dzień, posiłek — decyzja podjęta raz | 1, 2 | **Najwyższy** | **Nie istnieje** | **Zbudować** — Sprint 1; bez tego produkt nie jest planerem |
| [Lista zakupów](shopping-list.md) | Jedna lista, generowana z planu, użyteczna w sklepie | 2 | **Najwyższy** | Działa lokalnie (`localStorage`), tryb sklepowy dobry | **Przebudować**: serwer + generowanie z planu (Sprint 1) |
| [Dashboard](dashboard.md) | Odpowiedź „co dzisiaj?" na pierwszym ekranie | 1 | Wysoki | **Nie istnieje** (`/` → lista przepisów) | **Zbudować** — Sprint 2, po planie |
| [Przepisy](recipes.md) | Katalog zasilający plan | 3 | Wysoki | Produkcyjny (64 przepisy, 4 autorów) | **Naprawić i utrzymywać**: widoczność, instrukcje jako kroki; bez rozbudowy |
| [Import przepisu z URL](recipe-import.md) | Usuwa tarcie wejścia — koniec przepisywania ręcznego | 3 | Wysoki | Gotowy na branchu, **nie na produkcji** | **Wdrożyć** — największa niezrealizowana wartość leżąca w repo |
| [Integracja z MAP](../integrations/map.md) | „Co dziś na obiad" widoczne z pulpitu MAP | 1, 2 | Średni | Nie istnieje (brak kontraktu) | **Zaprojektować w Sprincie 0, wdrożyć w Sprincie 2** |
| [Składniki (normalizacja)](ingredients.md) | Agregacja i sortowanie listy po działach sklepu | 2 | Średni | 4 tabele, 0 wierszy, 0 UI | **Zamrozić** do czasu serwerowej listy zakupów |
| [Dwujęzyczność PL/EN](i18n.md) | Produkt używalny w dwóch językach | 3 | Średni | UI: działa. Treść przepisów: osiągalna tylko przez import | **Dokończyć albo ograniczyć obietnicę** — stan pośredni myli użytkownika |
| [Konta i dostęp](identity.md) | Własność przepisów, rozdzielenie prywatne/publiczne | 3 | Średni (usługowy) | Produkcyjny, 5 kont | **Utrzymywać**; rozwijać tylko pod potrzeby planu (gospodarstwo domowe, D-2) |
| [Panel administracyjny i logi](admin.md) | Wgląd operacyjny | — | Niski | Działa; `request_log` 318 tys. wierszy, UI tylko po angielsku | **Zamrozić i ograniczyć**: retencja, dwa widoki zamiast filtrów |
| Motywy graficzne (cyber/scandi) | Estetyka | — | Niski | Dwa motywy, ~45 KB CSS | **Wybrać jeden** — decyzja w parking lot |

## Czytanie tabeli

**Kluczowe moduły** (produkt bez nich nie ma sensu): Plan posiłków, Lista
zakupów, Przepisy, Dashboard.

**Enablery** (zwiększają wartość rdzenia): Import z URL, Składniki,
Dwujęzyczność.

**Poboczne** (koszt utrzymania bez wpływu na cele): Panel administracyjny,
Motywy graficzne.

Uderzająca obserwacja z [audytu](../audits/product-audit-2026-08-07.md): dwa z
czterech modułów kluczowych **nie istnieją**, a wszystkie moduły poboczne są
zaimplementowane i utrzymywane.

## Zasady

- Każdy moduł ma jeden dokument w tym katalogu i jedno źródło prawdy.
- Moduł, który nie służy żadnemu celowi North Star, nie jest rozwijany — jest
  zamrażany albo usuwany.
- Moduły usługowe (konta, panel administracyjny) nie mają własnej roadmapy;
  rozwijają się wyłącznie pod potrzeby modułów produktowych.
- Moduł oznaczony jako „nie istnieje" ma dokument, bo dokument jest miejscem,
  w którym zapada decyzja o jego kształcie — zanim powstanie kod.
