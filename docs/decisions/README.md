---
status: Active
last_updated: 2026-08-07
---

# Decyzje architektoniczne i produktowe

Każda ważna decyzja produktowa lub architektoniczna dostaje dokument w tym
katalogu. Decyzja raz zapisana nie jest usuwana — jeżeli przestaje
obowiązywać, dostaje status `Superseded` i wskazanie następcy.

| ID | Tytuł | Status | Data | Obszar |
|---|---|---|---|---|
| [ADR-001](ADR-001.md) | Plan posiłków ma jeden slot dziennie w v1 | Accepted | 2026-08-07 | Produkt, model planu |
| [ADR-002](ADR-002.md) | Plan i lista zakupów należą do gospodarstwa domowego, nie do użytkownika | Accepted | 2026-08-07 | Produkt, model danych, dostęp |
| [ADR-003](ADR-003.md) | Lista zakupów sumuje wyłącznie identyczny składnik przy zgodnej jednostce | Accepted | 2026-08-07 | Produkt, lista zakupów |
| [ADR-004](ADR-004.md) | Porcje i czasy są utrwalane w modelu przepisu | Accepted | 2026-08-07 | Produkt, model przepisu, import |

ADR-001 … ADR-004 to cztery decyzje odblokowujące Sprint 1, podjęte przy
przeglądzie Sprintu 0. Ich kontekst opisuje
[audyt produktowy](../audits/product-audit-2026-08-07.md), a skutki są
odzwierciedlone w [roadmapie](../product/roadmap.md) i dokumentach modułów.

## Decyzje spoza tego baseline'u

Dwie wcześniejsze decyzje istnieją na branchu
`feature/i18n-recipe-import-ingredients` pod nazwami opisowymi, sprzed
wprowadzenia numeracji ADR:

- `docs/decisions/recipe-translations.md` — model treści wielojęzycznej
  (Wariant B: osobna tabela `recipe_translations`)
- `docs/decisions/ingredient-normalization.md` — zakres normalizacji
  składników i sekcje sklepowe w V1

Przy przyjmowaniu tamtego brancha należy je przenumerować na **ADR-005** i
**ADR-006**, uzupełnić o frontmatter zgodny z pozostałymi i dopisać do tabeli
powyżej. Do tego czasu ten katalog nie jest kompletnym rejestrem decyzji
projektu.

## Zasady

1. Nowa ważna decyzja produktowa lub architektoniczna = nowy ADR w tym samym
   commicie, w którym zapada.
2. ADR opisuje kontekst, decyzję, konsekwencje i odrzucone alternatywy —
   szczególnie konsekwencje negatywne, bo to one są powodem, dla którego
   wracamy do decyzji.
3. Numeracja jest ciągła i nigdy nie jest używana ponownie.
4. Zmiana decyzji nie polega na edycji starego ADR-a, tylko na nowym ADR-ze ze
   statusem `Accepted` i oznaczeniu poprzedniego jako `Superseded by ADR-NNN`.
