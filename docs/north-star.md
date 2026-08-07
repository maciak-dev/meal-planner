---
status: Active
last_updated: 2026-08-07
---

# North Star

To jest najważniejszy dokument Meal Plannera. Każdy sprint, każda funkcja i
każda decyzja są oceniane względem tego dokumentu — nie względem pomysłów,
które akurat przyszły do głowy przy kodzie.

## Czym jest Meal Planner

Meal Planner jest **osobistym systemem decyzji żywieniowych gospodarstwa
domowego**.

Meal Planner **nie** jest książką kucharską.
Meal Planner **nie** jest społecznościowym serwisem z przepisami.
Meal Planner **nie** jest aplikacją dietetyczną ani licznikiem kalorii.
Meal Planner **nie** jest modułem MAP.

Meal Planner jest osobnym produktem z własnym repo, deploymentem, logowaniem i
roadmapą. MAP go integruje, nie wchłania (ADR-001, ADR-007 w MAP).

## Misja

Skrócić drogę od pytania **„co jemy w tym tygodniu?"** do stanu **„wiem, mam
kupione, gotuję"**.

## Cele

Meal Planner ma dokładnie trzy cele:

1. **Zdejmuje decyzję.**
   Odpowiada, co jest dziś i co jest w tym tygodniu, zanim ktokolwiek stanie
   przed otwartą lodówką o 17:00.
2. **Zdejmuje zakupy.**
   Z planu powstaje jedna lista zakupów, aktualna na każdym urządzeniu i
   użyteczna w ręce w sklepie.
3. **Zachowuje przepisy, których naprawdę używamy.**
   Katalog istnieje po to, żeby zasilać plan — nie jako cel sam w sobie.

**Test North Star:** każda nowa funkcja musi odpowiadać na przynajmniej jedno
pytanie: _Czy pomaga zdecydować, co jeść? Czy skraca drogę do zakupów? Czy
sprawia, że przepis, którego używamy, jest pod ręką?_ Jeżeli nie odpowiada na
żadne — trafia do backlogu (parking lot), nie do sprintu.

Trzy cele mają porządek. Cel 1 jest rdzeniem produktu, cel 2 jest jego
naturalnym wynikiem, cel 3 jest zapleczem dla obu. Historycznie zbudowano
najpierw cel 3, dlatego produkt do dziś nazywa się planerem, a jest katalogiem
(patrz [audyt produktowy](audits/product-audit-2026-08-07.md)).

## Zasady rozwoju

- **Plan jest rdzeniem.** Funkcja, która nie dotyka planu ani listy zakupów,
  ma niski priorytet niezależnie od tego, jak dobrze wygląda.
- **Jeden krok użytkownika zamiast trzech.** Produkt konkuruje z kartką i
  pamięcią. Przegrywa nie brakiem funkcji, tylko liczbą kliknięć.
- **Dane strukturalne dopiero wtedy, gdy mają konsumenta.** Model składników
  nie rozwija się „na zapas" — rozwija się wtedy, gdy istnieje lista zakupów,
  która z niego korzysta.
- **Telefon w sklepie jest pierwszorzędnym ekranem**, nie wersją mobilną
  desktopu.
- **Małe, produkcyjne iteracje.** Każda zmiana zostawia produkt prostszym, nie
  bogatszym w opcje.
- **Jedno źródło prawdy.** Plan, backlog i decyzje mają po jednym aktywnym
  dokumencie; reszta to archiwum.
- **Osobny produkt, jasny kontrakt.** Integracja z MAP odbywa się wyłącznie
  przez jawny, wersjonowany kontrakt HTTP
  ([integrations/map.md](integrations/map.md)) — nigdy przez wspólną bazę,
  wspólną sesję ani kopiowanie danych.
- **Fail closed.** Wszystko, co wystawione na zewnątrz (kontrakt dla MAP,
  cokolwiek publicznego), jest domyślnie read-only i domyślnie odmawia.

## Definicja sukcesu

Meal Planner odnosi sukces, gdy:

1. plan tygodnia powstaje w mniej niż 5 minut i nie wymaga notatnika obok,
2. lista zakupów powstaje z planu automatycznie, a nie przez przeklikiwanie
   przepisów po kolei,
3. w sklepie wystarczy telefon i nikt nie wraca po zapomniany składnik,
4. o 17:00 nikt nie pyta „co jemy?", bo odpowiedź jest na pierwszym ekranie,
5. MAP pokazuje „co dziś na obiad" i „ile zostało do kupienia" bez wchodzenia
   do Meal Plannera.

## Priorytety

W kolejności:

1. **Plan tygodnia** — model dnia i posiłku, bez którego nazwa produktu jest
   nieprawdziwa (cel 1).
2. **Serwerowa lista zakupów generowana z planu** (cel 2).
3. **Dashboard odpowiadający na pytanie „co dzisiaj?"** (cel 1).
4. **Katalog i import przepisów** — utrzymanie i doszlifowanie tego, co już
   działa (cel 3).
5. **Kontrakt integracyjny dla MAP** (cel 1 i 2 widziane z zewnątrz).

Wszystko inne czeka w backlogu.

## Dokumenty podrzędne

- Wizja produktu: [product/vision.md](product/vision.md)
- Aktywna roadmapa: [product/roadmap.md](product/roadmap.md)
- Backlog: [product/backlog.md](product/backlog.md)
- Portfolio modułów: [modules/README.md](modules/README.md)
- Integracja z MAP: [integrations/map.md](integrations/map.md)
- Propozycja dashboardu: [product/dashboard.md](product/dashboard.md)
- Audyt produktowy: [audits/product-audit-2026-08-07.md](audits/product-audit-2026-08-07.md)
