---
status: Sprint 0 deliverable — projekt do realizacji w Sprincie 2
last_updated: 2026-08-07
---

# Dashboard — projekt

Projekt pierwszego ekranu Meal Plannera. **Bez implementacji** — to
specyfikacja wejściowa dla Sprintu 2, po tym jak Sprint 1 dostarczy plan i
serwerową listę zakupów.

## Zasada

Dashboard odpowiada w 10 sekund na cztery pytania:

1. **Co jemy dziś?**
2. **Co jemy dalej w tym tygodniu?**
3. **Czy trzeba coś kupić?**
4. **Gdzie kontynuować pracę?**

Wszystko, co nie odpowiada na jedno z tych pytań, nie trafia na dashboard.
Statystyki, liczniki, logi i wykresy nie trafiają na dashboard nigdy.

Dziś pierwszy ekran odpowiada na te pytania listą 64 przepisów posortowanych po
dacie dodania, czyli nie odpowiada wcale
([audyt](../audits/product-audit-2026-08-07.md), sekcja 5).

## Układ

```
┌──────────────────────────────────────────────────────────────┐
│  NAGŁÓWEK: Meal Planner · czwartek, 7 sierpnia · PL/EN · ☰   │
├──────────────────────────────────────────────────────────────┤
│  ① DZIŚ                                                       │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  [zdjęcie]   KURCZAK Z WARZYWAMI                       │  │
│  │              45 min · 4 porcje                          │  │
│  │              [ Gotuj ]   [ Zmień ]                      │  │
│  └────────────────────────────────────────────────────────┘  │
├──────────────────────────────────────────────────────────────┤
│  ② JUTRO                                                      │
│  pt · Zupa dyniowa            [ Zobacz ]                     │
├───────────────────────────────┬──────────────────────────────┤
│  ③ TEN TYDZIEŃ                │  ④ ZAKUPY                    │
│  pn ✓  wt ✓  śr ✓  cz ✓      │  12 pozycji do kupienia      │
│  pt ✓  sb ·  nd ·             │  [ Otwórz listę ]            │
│  [ Zaplanuj tydzień ]         │  [ Odśwież z planu ]         │
├───────────────────────────────┴──────────────────────────────┤
│  ⑤ SZYBKIE AKCJE                                              │
│  [ Importuj z linku ]  [ Dodaj przepis ]  [ Szukaj przepisu ] │
└──────────────────────────────────────────────────────────────┘
```

Mapowanie na pytania: ①→1, ②③→2, ④→3, ⑤→4.

## Strefy — treść, źródła i stan pusty

| # | Strefa | Źródło danych | Stan pusty |
|---|--------|---------------|------------|
| ① | **Dziś** | wpis planu na dzisiejszą datę + przepis | „Nie ma planu na dziś" + trzy propozycje z ostatnio gotowanych, każda z przyciskiem „Wybierz na dziś" (jedno kliknięcie kończy pusty stan) |
| ② | **Jutro** | wpis planu na jutro | „Jutro jeszcze nie zaplanowane" + [Zaplanuj] |
| ③ | **Ten tydzień** | wpisy planu w zakresie bieżącego tygodnia | Siedem pustych kropek + [Zaplanuj tydzień] jako główne wezwanie do działania |
| ④ | **Zakupy** | serwerowa lista zakupów: liczba pozycji nieodhaczonych | „Lista jest pusta" + [Wygeneruj z planu], jeśli plan zawiera cokolwiek |
| ⑤ | **Szybkie akcje** | statyczne | — |

## Zasady projektowe

1. **Jedna dominanta.** Strefa ① zajmuje najwięcej miejsca i jest jedyną z
   dużym zdjęciem. Jeżeli użytkownik przeczyta tylko ją, dostał wartość
   produktu.
2. **Pusty stan zawsze proponuje jedno konkretne działanie**, nigdy samego
   komunikatu. „Brak planu na dziś" bez przycisku jest błędem projektowym, nie
   stanem.
3. **Maksymalnie jedno wezwanie do działania na strefę.** Dwa przyciski
   równorzędne oznaczają, że decyzja została przerzucona na użytkownika.
4. **Bez liczników dla samego licznika.** „64 przepisy" nie trafia na
   dashboard; „12 pozycji do kupienia" trafia, bo prowadzi do działania.
5. **Degradacja zamiast błędu.** Strefa bez danych pokazuje komunikat i akcję;
   błąd jednej strefy nie wywraca ekranu.
6. **Mobile first.** Na telefonie strefy układają się pionowo w kolejności
   ①②③④⑤ — ten sam porządek wartości.
7. **Dashboard nie edytuje.** [Zmień], [Zaplanuj], [Otwórz listę] prowadzą do
   właściwych ekranów. Dashboard prezentuje i kieruje.
8. **Zero elementów operacyjnych.** Logi, statusy usług, wersje i telemetria
   nie należą do ekranu, na którym użytkownik pyta, co zjeść.

## Relacja do MAP

Strefy ①②③④ to dokładnie te dane, które wystawia
[kontrakt integracyjny dla MAP](../integrations/map.md). To nie jest zbieg
okoliczności — jeden zestaw danych obsługuje pierwszy ekran Meal Plannera i
kafelek w MAP. Kontrakt implementuje się po dashboardzie, na gotowych danych,
nie równolegle.

Różnica jest w głębokości: dashboard Meal Plannera pokazuje zdjęcie, czas i
porcje; MAP pokazuje jedno zdanie i link.

## Zakres Sprintu 2 (propozycja)

Kolejność według wartości: ① Dziś → ④ Zakupy → ③ Ten tydzień → ② Jutro →
⑤ Szybkie akcje. Pierwsze dwie strefy wystarczą, żeby pierwszy ekran przestał
być listą przepisów — to minimalny cel.

Zmiana strony startowej (`/` → dashboard zamiast `/recipes-ui`) następuje
dopiero wtedy, gdy strefy ① i ④ działają na prawdziwych danych.
