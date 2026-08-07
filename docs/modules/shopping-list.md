---
status: Active — wymaga przebudowy
last_updated: 2026-08-07
---

# Lista zakupów

## Purpose

Zamienia decyzję („to jemy w tym tygodniu") w konkretne działanie w sklepie.
Służy celowi 2 North Star. Docelowo jedyne poprawne źródło listy to plan
posiłków; ręczne dopisanie pozycji zostaje jako wyjątek.

## Current Capabilities

- Lista pozycji z nazwą, ilością i stanem „zrobione", trzymana w
  `localStorage` przeglądarki (`Shopping.getList/saveList`).
- Ręczne dodawanie pozycji, zwiększanie i zmniejszanie ilości.
- **Tryb zakupów** — osobny tryb interfejsu: duże cele dotykowe, przełączniki
  „zrobione", pozycje odhaczone zjeżdżają na dół listy, animacja FLIP przy
  przestawianiu, ochrona przed przypadkowym usunięciem („dotknij ponownie, aby
  usunąć"). Najlepiej zaprojektowany fragment produktu.
- Dodanie zaznaczonych składników przepisu do listy z karty przepisu.
- Import listy przez wklejenie tekstu (jedna pozycja na linię).
- Czyszczenie listy z potwierdzeniem.

## Current Limitations

- **`localStorage`.** Lista złożona na laptopie nie istnieje w telefonie w
  sklepie. To unieważnia cały sens najlepiej zrobionego modułu w aplikacji.
- **Agregacja jest semantycznie błędna.** Pozycja bierze całą linię składnika
  jako nazwę i zwiększa licznik o 1 przy powtórzeniu, więc „2 łyżki oliwy" z
  ilością 2 znaczy „dwa razy dwie łyżki". Ilości z przepisów nie są sumowane
  ani porównywane.
- **Brak połączenia z planem** — bo planu nie ma. Lista powstaje przez
  przeklikanie przepisów pojedynczo (~40–70 interakcji na tydzień).
- Flaga „składnik ważny/nieważny" (`ingredients_map`) jest bezczynna: tabela
  `ingredients` ma zero wierszy, więc domyślnie wszystko jest zaznaczone.
- Brak sortowania po działach sklepu, mimo że model `store_sections` już
  istnieje w schemacie.
- Brak historii zakupów i brak pojęcia „mam to w domu".

## Design Direction

Sprint 1 przebudowuje moduł w trzech ruchach:

1. **Serwerowa trwałość** — lista per gospodarstwo/użytkownik w bazie, z
   jednorazową migracją zawartości `localStorage` przy pierwszym uruchomieniu
   (użytkownik nie może stracić bieżącej listy).
2. **Generowanie z planu** — jedno kliknięcie „Generuj listę z planu"
   zastępuje przeklikiwanie przepisów. Ręczne dodawanie zostaje.
3. **Uczciwa agregacja** (decyzja D-3): sumowanie tylko przy zgodnej jednostce
   i zgodnej nazwie; wszystko inne trafia jako osobne pozycje z widocznym
   tekstem źródłowym. Lepiej pokazać dwie pozycje niż skłamać jedną.

Tryb zakupów zostaje bez zmian — jest wzorcem dla reszty produktu, nie
kandydatem do przeprojektowania.

Sortowanie po działach sklepu i scalanie aliasów („pomidor"/„pomidory") wchodzą
dopiero po tym, jak lista będzie serwerowa — patrz [Składniki](ingredients.md).

## Source Of Truth

- Kod: `app/static/recipes.js` (obiekty `Shopping`, `ShoppingUI`),
  `app/templates/recipes.html` (`#shopping-module`)
- Plan: [roadmapa — Sprint 1](../product/roadmap.md)
- Zależność: [Plan posiłków](meal-plan.md)
