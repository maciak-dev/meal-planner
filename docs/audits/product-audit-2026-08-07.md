---
status: Sprint 0 deliverable
last_updated: 2026-08-07
---

# Meal Planner — Product Audit

Data audytu: 2026-08-07
Zakres: **audyt produktowy**. Nie code review, nie security review, nie
architecture review. Oceniany jest produkt: wizja, moduły, wartość, UX,
przepływy, złożoność.

Metoda: przegląd kodu jako źródła prawdy o zachowaniu produktu (`app/`,
`app/templates/`, `app/static/recipes.js`, słowniki `app/i18n/`), przegląd
istniejącej dokumentacji (`docs/`), oraz dane produkcyjne z audytu
infrastrukturalnego z 2026-08-04. **Nie dotykano** produkcji, RC, bazy, API,
deploymentu ani konfiguracji.

Branch w chwili audytu: `feature/i18n-recipe-import-ingredients`.

---

## 1. Ocena produktu

**Ocena ogólna: 5/10 jako produkt, 8/10 jako fundament techniczny.**

| Wymiar | Ocena | Uzasadnienie |
|---|---|---|
| Zgodność nazwy z produktem | 2/10 | Produkt nazywa się „Meal Planner" i nie zawiera planu |
| Wartość rdzenia (planowanie) | 1/10 | Nie istnieje: brak tygodnia, dnia, posiłku, historii |
| Wartość katalogu przepisów | 7/10 | Działa, używany (64 przepisy, 4 autorów), świeżo wzmocniony importem z linku |
| Wartość listy zakupów | 4/10 | Dobry tryb sklepowy, ale `localStorage`, brak trwałości i brak generowania z planu |
| UX prowadzenia użytkownika | 3/10 | Brak pierwszego ekranu z odpowiedzią; użytkownik sam musi wiedzieć, co zrobić |
| Spójność produktu | 4/10 | Dwa motywy, martwe kontrolki, panel admina po angielsku w dwujęzycznej aplikacji |
| Jakość fundamentu (dane, migracje, testy, ops) | 8/10 | Alembic, 121 testów, rozdzielone prod/RC, backup, runbooki |
| Gotowość do integracji z MAP | 3/10 | Brak kontraktu; nie ma jeszcze czego pokazać poza liczbą przepisów |

Jednozdaniowa diagnoza: **to jest dobrze zbudowany katalog przepisów z bardzo
dobrym importem i przyzwoitą listą zakupów, który nosi nazwę produktu, którym
nie jest.**

---

## 2. Wizja — czy istnieje?

**Nie istnieje jako dokument i nie istnieje jako spójna intencja.**

Dowody:

- `README.md` opisuje produkt jako _„Simple recipe manager"_ — czyli inaczej
  niż nazwa repozytorium, domeny i katalogu.
- `ISSUES.md` — jedyny dokument zbliżony do planu produktu — zawiera sześć
  pozycji, z czego jedna to _„cyberpunk 4–5 linii na tle, które będą mrugać"_,
  jedna to _„upewnić się, że repozytorium jest gotowe"_, a jedna („składniki
  ważne/nieważne") jest produktowa. To jest lista życzeń, nie wizja.
- Dokumentacja `docs/` do dziś zawierała wyłącznie warstwę operacyjną,
  architektoniczną i audytową — zero warstwy produktowej. Nie było dokumentu,
  względem którego dałoby się odrzucić pomysł.
- Ekosystem MAP opisuje Meal Plannera jako „planowanie posiłków"
  (`MAP/docs/ecosystem.md`), czyli zewnętrzny obserwator zakłada funkcję, której
  produkt nie ma.

**Czy projekt urósł organicznie? Tak, i widać dokładnie jak.** Kolejność
powstawania funkcji według historii repo: CRUD przepisów → role i panel admina
→ logi requestów i blokowanie IP → tryb zakupów i animacje FLIP → dwa motywy →
import listy zakupów → PostgreSQL → i18n → import przepisu z URL z pełnym SSRF
guardem → model normalizacji składników.

To jest kolejność napędzana ciekawością techniczną i tym, co akurat było pod
ręką — nie wartością dla użytkownika. Produkt dostał enterprise'owy request
logging (318 016 wierszy) i hardening SSRF na poziomie pinowania IP, zanim
dostał pytanie „co jemy w czwartek".

Nie jest to zarzut wobec jakości tych rzeczy — SSRF guard i warstwa operacyjna
są zrobione dobrze. Jest to obserwacja o **priorytetach**: brakuje mechanizmu,
który by je ustawiał. Tym mechanizmem jest [North Star](../north-star.md).

---

## 3. Inwentarz modułów

Pełna analiza per moduł: [modules/README.md](../modules/README.md).
Poniżej skrót z oceną wartości.

| Moduł | Co daje | Realnie używane | Ocena |
|---|---|---|---|
| **Przepisy (CRUD, widoczność, zdjęcia)** | Katalog, na którym stoi wszystko inne | Tak: 64 przepisy, 4 autorów, 58 publicznych, 3 ze zdjęciem | **Kluczowy** |
| **Import przepisu z URL** | Usuwa największe tarcie wejścia — ręczne przepisywanie | Nowy, jeszcze nie na produkcji | **Kluczowy (enabler)** |
| **Lista zakupów** | Jedyny moduł z realną wartością „w terenie" (tryb sklepowy) | Tak, ale tylko na jednym urządzeniu | **Kluczowy, ale na złym fundamencie** |
| **Plan tygodnia** | — | **Nie istnieje** | **Brakujący rdzeń** |
| **Dashboard** | — | **Nie istnieje** | **Brakujący rdzeń** |
| **Model składników (normalizacja)** | Docelowo: agregacja i sortowanie listy po działach sklepu | 4 tabele, 0 wierszy, 0 UI | **Uśpiony enabler** |
| **i18n PL/EN** | Dwujęzyczne UI | UI tak; treść przepisów praktycznie nie | **Połowiczny** |
| **Konta i role** | Rozdzielenie własności przepisów | Tak, 5 użytkowników | **Fundament** |
| **Panel admina / logi** | Wgląd operacyjny | Tylko dla operatora | **Poboczny** |
| **Motywy (cyber/scandi)** | Estetyka | Przełącznik istnieje | **Poboczny, kosztowny** |

Kluczowe: przepisy, import, lista zakupów, plan (do zbudowania), dashboard (do
zbudowania).
Poboczne: motywy, panel admina, import listy zakupów przez wklejenie tekstu.

---

## 4. Ocena UX

### 4.1. Czy aplikacja prowadzi użytkownika?

**Nie.** Po zalogowaniu użytkownik trafia na `/recipes-ui` — płaską listę
wszystkich widocznych przepisów, posortowaną po dacie dodania. Nie ma nagłówka
z odpowiedzią, nie ma sugestii, nie ma stanu „dziś". Aplikacja pokazuje
zawartość bazy i czeka.

Cała architektura informacji to dwie zakładki: **Przepisy** i **Lista
zakupów**. Nic ich nie łączy poza przyciskiem „+ Dodaj do listy" na karcie
przepisu.

### 4.2. Czy wymaga zbyt wielu kliknięć?

Tak, i to w scenariuszu, który jest sensem produktu. Żeby zebrać zakupy na
pięć obiadów:

1. zakładka Przepisy →
2. wyszukaj/przewiń do przepisu →
3. odznacz składniki, które masz w domu (średnio kilkanaście checkboxów) →
4. „+ Dodaj do listy" →
5. **powtórz 2–4 pięć razy**, pamiętając z głowy, które przepisy już wybrałeś →
6. zakładka Lista zakupów →
7. ręcznie posprzątaj duplikaty i sprzeczne ilości.

To jest ~40–70 interakcji na tydzień, plus pamięć robocza użytkownika jako
brakujący komponent systemu. Kartka papieru wygrywa.

Docelowo ta sama czynność powinna wyglądać tak: zaplanuj 5 dni (5 kliknięć) →
„Generuj listę" (1 kliknięcie).

### 4.3. Co jest nieintuicyjne lub wprost mylące

Znaleziono kilka miejsc, gdzie UI obiecuje coś, czego nie robi. To najgorszy
rodzaj długu produktowego, bo użytkownik nie wie, że stracił dane.

| # | Zachowanie | Skutek dla użytkownika |
|---|---|---|
| P-1 | Formularz „Dodaj przepis" ma przełącznik PRYWATNY/PUBLICZNY, ale `Recipes.actions.create()` nie wysyła `is_public` | Każdy nowy przepis jest prywatny, niezależnie od ustawienia przełącznika |
| P-2 | `id="edit-is-public"` występuje dwa razy w `recipes.html` (formularz dodawania i modal edycji); `getElementById` zwraca pierwszy | Przełącznik widoczności **w modalu edycji nie działa** — wartość wraca niezmieniona |
| P-3 | Draft importu zbiera „Porcje", „Czas przygotowania", „Czas gotowania"; `create_recipe_from_import()` ich nie zapisuje (model `Recipe` nie ma takich kolumn) | Użytkownik wpisuje dane, klika „Zapisz przepis", dane znikają bez ostrzeżenia |
| P-4 | Przełącznik PL/EN zmienia UI, ale UI nigdy nie wysyła `language` przy tworzeniu/edycji przepisu (`data.language or 'pl'`) | Nie da się przez UI stworzyć treści EN dla przepisu. Jedyna droga do tłumaczenia to import z linku. Użytkownik EN widzi polskie przepisy |
| P-5 | „Składniki" w menu burger wywołuje `openIngredientsModal()`, które pokazuje toast „Funkcja składników wkrótce dostępna" | Pozycja menu prowadząca donikąd, obecna w produkcyjnym UI |
| P-6 | Oznaczanie składników jako „ważne/nieważne" (`ingredients_map`) — tabela `ingredients` ma 0 wierszy, domyślna wartość to `True` | Wszystkie checkboxy zawsze zaznaczone; funkcja jest niewidoczna i bezczynna |
| P-7 | Dodanie składnika do listy zakupów bierze **cały tekst linii** jako nazwę pozycji i zwiększa `qty` o 1 przy powtórzeniu | Pozycja „2 łyżki oliwy" z licznikiem 2 znaczy „dwa razy dwie łyżki". Agregacja jest semantycznie błędna |
| P-8 | Lista zakupów żyje w `localStorage` | Lista zrobiona na laptopie nie istnieje w telefonie w sklepie. To unieważnia najlepiej zrobiony moduł w aplikacji |
| P-9 | Instrukcje renderowane z atrybutu `data-instructions` w HTML | Długie instrukcje z cudzysłowami/znakami specjalnymi są kruche; brak kroków, brak formatowania |
| P-10 | Panel administracyjny jest wyłącznie po angielsku i w innym motywie | Niespójność w produkcie, który chwali się dwujęzycznością |

### 4.4. Co jest zrobione dobrze

- **Tryb zakupów** — duże cele dotykowe, przełączniki „zrobione", pozycje
  odhaczone spadają na dół, animacja FLIP, zabezpieczenie przed przypadkowym
  usunięciem („dotknij ponownie"). To jest projektowane pod realny kontekst:
  jedna ręka, koszyk, sklep. Najlepszy fragment UX w aplikacji.
- **Draft importu** — użytkownik widzi, co system zrozumiał, może poprawić
  każdą linię składnika, a niepewne pozycje są oznaczone „Sprawdź". Wzorcowe
  podejście „człowiek zatwierdza, maszyna proponuje".
- **Komunikaty błędów importu** są zmapowane na zrozumiałe zdania w obu
  językach zamiast surowych wyjątków.

---

## 5. Ocena dashboardu

**Dashboardu nie ma.** `GET /` przekierowuje zalogowanego użytkownika na
`/recipes-ui`, czyli na listę przepisów.

Na pytanie **„co dzisiaj powinienem zrobić?"** obecny pierwszy ekran odpowiada:
_„oto 64 przepisy, posortowane od najnowszego"_. To nie jest odpowiedź, to jest
zrzut bazy danych.

Żeby dashboard mógł powstać, musi istnieć plan — dziś nie ma czego pokazać poza
liczbą przepisów. Dlatego dashboard jest w roadmapie **po** planie, nie przed.
Projekt docelowego ekranu: [product/dashboard.md](../product/dashboard.md).

---

## 6. Przepływy użytkownika

| # | Scenariusz | Wsparcie | Komentarz |
|---|---|---|---|
| F-1 | **„Co dziś na obiad?"** | ❌ brak | Rdzeń produktu. Zero wsparcia: brak planu, brak historii, brak sugestii |
| F-2 | **„Zaplanuj tydzień"** | ❌ brak | Brak modelu tygodnia/dnia/posiłku |
| F-3 | **„Zrób listę zakupów na tydzień"** | ⚠️ częściowe | Ręcznie, przepis po przepisie, z błędną agregacją ilości (P-7) i bez trwałości (P-8) |
| F-4 | **„Kup w sklepie"** | ✅ dobre | Najlepszy przepływ w aplikacji — pod warunkiem, że lista jest na tym samym urządzeniu |
| F-5 | **„Zapisz przepis znaleziony w internecie"** | ✅ dobre | Import z URL: wklej link → podgląd → korekta → zapis. Nowy, jeszcze nie na produkcji |
| F-6 | **„Dodaj własny przepis"** | ⚠️ przeciętne | Składniki i instrukcje jako wolny tekst; przełącznik widoczności nie działa (P-1) |
| F-7 | **„Znajdź przepis"** | ⚠️ słabe | Wyszukiwanie tekstowe po stronie klienta na wyrenderowanym tekście. Brak tagów, kategorii, filtrów (moje/publiczne, z importu, ze zdjęciem, czas przygotowania) |
| F-8 | **„Gotuj według przepisu"** | ⚠️ słabe | Instrukcje w prostym modalu; brak kroków, skalowania porcji, trybu kuchennego |
| F-9 | **„Podziel się przepisem z domownikiem"** | ❌ zepsute | Widoczność nie działa ani przy tworzeniu, ani przy edycji (P-1, P-2) |
| F-10 | **„Używaj aplikacji po angielsku"** | ⚠️ połowiczne | UI tak, treść przepisów nie (P-4) |

Wniosek: **produkt dobrze wspiera przepływy zaplecza (F-4, F-5) i nie wspiera
żadnego z przepływów, które są powodem jego istnienia (F-1, F-2, F-3).**

---

## 7. Architektura produktu

Nie kodu — produktu. Meal Planner ma trzy naturalne warstwy:

```
   ┌─────────────────────────────────────────────────────────┐
   │  WARSTWA TREŚCI        katalog przepisów, składniki,     │
   │  (zaplecze)            tłumaczenia, zdjęcia, import      │
   │                        ██████████████████████ zbudowana  │
   ├─────────────────────────────────────────────────────────┤
   │  WARSTWA DECYZJI       plan tygodnia, dzień, posiłek,    │
   │  (rdzeń produktu)      historia, sugestie, dashboard     │
   │                        ░░░░░░░░░░░░░░░░░░░░░░ BRAK       │
   ├─────────────────────────────────────────────────────────┤
   │  WARSTWA WYKONANIA     lista zakupów, tryb sklepowy,     │
   │  (w terenie)           tryb gotowania                    │
   │                        ████████░░░░░░░░░░░░░░ częściowo  │
   └─────────────────────────────────────────────────────────┘
```

Warstwa decyzji jest **jednocześnie rdzeniem produktu i jedyną, która nie
istnieje**. Skutek jest strukturalny, nie kosmetyczny: warstwa treści i
warstwa wykonania nie mają się przez co komunikować, więc łączy je prowizorka
— przycisk „+ Dodaj do listy" i pamięć użytkownika.

To wyjaśnia większość znalezisk UX. Błędna agregacja ilości (P-7), brak
trwałości listy (P-8), brak sensu dla sekcji sklepowych, martwa flaga
„składnik ważny" (P-6) — wszystkie te rzeczy są objawami jednej przyczyny:
**nie ma bytu, który wie, ile posiłków planujemy i z czego.**

Warstwa platformy (konta, role, logi, motywy, blokowanie IP, i18n) jest
rozwinięta nieproporcjonalnie do warstwy produktu.

---

## 8. Gdzie produkt stał się zbyt skomplikowany

| # | Miejsce | Na czym polega nadmiar |
|---|---|---|
| Z-1 | **Model składników** | Cztery tabele (`ingredients`, `ingredient_aliases`, `recipe_ingredients`, `store_sections`) zaprojektowane, zmigrowane i udokumentowane ADR-em, zanim istnieje konsument tych danych. `store_sections` służą sortowaniu listy zakupów po działach sklepu — a lista zakupów jest w `localStorage` i nie ma pojęcia o składnikach |
| Z-2 | **Cztery reprezentacje tej samej treści przepisu** | `Recipe.name/description/instructions` (legacy) + `recipe_translations` (nowy model) + `Recipe.ingredients` (tekst) + `recipe_ingredients` (relacyjne). Import zapisuje do wszystkich czterech. Każda zmiana treści musi teraz pamiętać o czterech miejscach |
| Z-3 | **Dwa motywy graficzne** | `themes.css` (8 KB) + `main.css` (30 KB) + `admin.css` (7 KB). Każda zmiana UI to podwójna weryfikacja. Motyw „cyber" jest estetycznie sprzeczny z produktem o jedzeniu |
| Z-4 | **Telemetria bezpieczeństwa** | Logowanie wszystkich requestów (318 016 wierszy, zdominowane przez skany botów), wykrywanie podejrzanych ścieżek, blokowanie IP, panel z filtrami i zakresami dat — w aplikacji z pięcioma kontami |
| Z-5 | **Formularz draftu importu** | 12 pól, z czego 3 są po zapisie wyrzucane (P-3), plus tabela składników z 6 kolumnami i przełącznik „zapisz składniki jako relacyjne", którego znaczenia użytkownik nie zna |
| Z-6 | **Dwa niezależne importy** | „Importuj z linku" (przepis) i „Dodaj listę" (wklejona lista zakupów) — dwa różne mechanizmy o podobnej nazwie w dwóch zakładkach |

Wspólny mianownik Z-1, Z-2 i Z-5: **zbudowano poprawną strukturę danych na
zapas i teraz trzeba ją utrzymywać, zanim cokolwiek z niej korzysta.**

---

## 9. Funkcje widoczne dla użytkownika, ale praktycznie nieużywane

| Funkcja | Stan | Rekomendacja |
|---|---|---|
| „Składniki" w menu burger | Toast „wkrótce" (P-5) | **Usunąć** do czasu, gdy będzie działać |
| Przełącznik PRYWATNY/PUBLICZNY (dodawanie) | Nie wysyła wartości (P-1) | **Naprawić** — funkcja ma sens |
| Przełącznik PRYWATNY/PUBLICZNY (edycja) | Podpięty pod zły element (P-2) | **Naprawić** |
| `PATCH /api/v1/recipes/{id}/visibility` + `toggleVisibility()` + `renderVisibilitySwitch()` | Martwy kod — żadna ścieżka UI tego nie wywołuje | **Usunąć** jedną z dwóch dróg zmiany widoczności |
| Ważność składnika (`is_essential`) | 0 wierszy w tabeli, zawsze `True` (P-6) | **Odłożyć** do czasu serwerowej listy zakupów |
| Pola „Porcje / Czas przygotowania / Czas gotowania" w imporcie | Zbierane i wyrzucane (P-3) | **Zapisać albo usunąć z formularza** — stan pośredni jest najgorszy |
| Przełącznik motywu | Kosmetyka bez wartości produktowej (Z-3) | **Wybrać jeden motyw** |
| Przełącznik PL/EN dla treści przepisu | Nieosiągalny przez UI (P-4) | **Dokończyć** — inaczej dwujęzyczność jest fasadą |
| „Dodaj listę" (import listy przez wklejenie) | Obejście braku generowania listy z planu | **Zachować jako awaryjne**, przestanie być potrzebne po Sprincie 1 |
| Filtry logów requestów w panelu admina | Wartość wyłącznie operacyjna, zdominowane szumem botów | **Ograniczyć** zakres i dodać retencję |
| Swagger `/docs` dla admina | Narzędzie deweloperskie w produkcie | Zostawić, bez rozwoju |

---

## 10. Co można uprościć

1. **Jedna droga zmiany widoczności** zamiast dwóch (formularz + PATCH), jeden
   działający przełącznik zamiast dwóch zepsutych.
2. **Jedno źródło prawdy dla treści przepisu** — `recipe_translations` po
   backfillu; legacy kolumny stają się mirrorem tylko do odczytu, docelowo
   znikają.
3. **Jeden motyw.** Usunięcie drugiego to natychmiastowa oszczędność w każdej
   przyszłej zmianie UI.
4. **Odłożyć aliasy składników i sekcje sklepowe** do momentu, w którym istnieje
   serwerowa lista zakupów, która ma je z czego sortować.
5. **Panel admina do dwóch rzeczy**: kto się logował i co się zepsuło. Retencja
   `request_log` (np. 30 dni) plus wyłączenie logowania szumu skanowania.
6. **Instrukcje jako lista kroków** zamiast jednego pola tekstowego renderowanego
   z atrybutu HTML.
7. **Usunąć albo dokończyć** wszystkie pozycje z sekcji 9 — produkt nie może
   pokazywać kontrolek, które nic nie robią. To jedna z najtańszych i
   najbardziej odczuwalnych poprawek jakości.
8. **Jeden import zamiast dwóch nazwanych podobnie** — po Sprincie 1 „Dodaj
   listę" schodzi do roli awaryjnej.

---

## 11. Największe problemy

1. **Produkt nie robi tego, co obiecuje nazwą.** Brak planu tygodnia to nie
   brakująca funkcja — to brakujący rdzeń, wokół którego wszystko inne miałoby
   sens.
2. **Lista zakupów w `localStorage`.** Najlepiej zaprojektowany moduł jest
   bezużyteczny w scenariuszu, dla którego powstał (plan na laptopie → sklep z
   telefonem).
3. **Kontrolki, które kłamią.** Widoczność (P-1, P-2), porcje i czasy (P-3),
   treść EN (P-4), „Składniki" (P-5), ważność składników (P-6). Każda z nich
   uczy użytkownika, że interfejsowi nie można ufać.
4. **Brak pierwszego ekranu z odpowiedzią.** Aplikacja pokazuje bazę danych,
   zamiast prowadzić.
5. **Model danych zbudowany przed konsumentem.** Cztery tabele składników i
   cztery reprezentacje treści przepisu generują koszt utrzymania, nie wartość.
6. **Rozjazd priorytetów.** Poziom dopracowania warstwy bezpieczeństwa i
   operacyjnej jest o dwie klasy wyższy niż poziom dopracowania warstwy, dla
   której użytkownik otwiera aplikację.

---

## 12. Największe zalety

1. **Fundament techniczny jest gotowy na rozwój produktu.** Alembic z liniową
   historią 7 migracji, 121 testów, rozdzielone produkcja i RC z osobnymi
   bazami, zweryfikowany backup, runbooki wdrożeniowe i rollbacku. To jest
   rzadkie w projekcie tej wielkości i to jest realna przewaga.
2. **Import przepisu z URL to najlepsza funkcja produktu.** Rozwiązuje
   największe tarcie wejścia (nikt nie przepisuje przepisów ręcznie), ma
   wzorcowy UX draftu z korektą przez człowieka, dwujęzyczne komunikaty błędów
   i bezpieczeństwo zrobione porządnie (walidacja URL, pinowanie IP, limity,
   whitelist typów obrazów).
3. **Tryb zakupów jest zaprojektowany pod realny kontekst użycia**, a nie pod
   ekran deweloperski.
4. **Model wielojęzyczny i model składników są przemyślane** — są przedwczesne
   względem produktu, ale kiedy nadejdzie ich moment, nie trzeba będzie ich
   projektować od nowa. To dług, ale dobrze udokumentowany dług z ADR-ami.
5. **Domena jest ostra i osobista.** Meal Planner nie musi być uniwersalny ani
   konkurencyjny — musi obsłużyć jedno gospodarstwo domowe. To pozwala odrzucać
   90% pomysłów bez żalu.
6. **Produkt ma realnych użytkowników i realne dane** (5 kont, 64 przepisy, 4
   autorów). Nie jest projektem-szkieletem.

---

## 13. Rekomendacja

Kolejność jest niepodlegająca negocjacji, bo wynika z zależności produktowych,
nie z preferencji:

1. **Zamknąć wizję** (ten audyt + [North Star](../north-star.md) +
   [Vision](../product/vision.md)) — Sprint 0.
2. **Zbudować plan tygodnia i serwerową listę zakupów** — Sprint 1. To jest
   moment, w którym produkt zaczyna odpowiadać swojej nazwie.
3. **Dashboard „co dzisiaj?"** — Sprint 2, dopiero gdy jest co pokazywać.
4. **Kontrakt integracyjny dla MAP** — Sprint 2, na tych samych danych co
   dashboard.
5. **Ingredient Engine (Fazy C/D)** — dopiero gdy lista zakupów istnieje po
   stronie serwera i ma z czego korzystać.

Szczegóły: [roadmapa](../product/roadmap.md) i
[backlog](../product/backlog.md).

---

## 14. Powiązane dokumenty

- [North Star](../north-star.md) — nowa wizja produktu
- [Product Vision](../product/vision.md)
- [Roadmap](../product/roadmap.md) — Sprint 0 i Sprint 1
- [Backlog](../product/backlog.md)
- [Portfolio modułów](../modules/README.md)
- [Propozycja dashboardu](../product/dashboard.md)
- [Integracja z MAP](../integrations/map.md)
- [Audyt produkcyjny 2026-08-04](meal-planner-production-audit.md) — warstwa
  infrastrukturalna, nadal aktualna jako opis środowiska
- [Ingredients Feature Review](ingredients-feature-review.md)
