---
status: Zamrożony — utrzymanie
last_updated: 2026-08-07
---

# Panel administracyjny i logi

## Purpose

Moduł operacyjny, nie produktowy. Daje właścicielowi instancji wgląd w to, kto
się logował i co dzieje się z ruchem HTTP. Nie odpowiada na żadne pytanie
North Star i nie jest rozwijany.

## Current Capabilities

- `/admin` — panel dla roli `super_admin`, dwie zakładki: logi logowań i logi
  requestów.
- Zakresy czasowe (dziś / 7 dni / wszystko) i filtry requestów (wszystkie /
  podejrzane / błędy / zablokowane).
- Middleware zapisujące każdy request do `request_log` z oznaczaniem
  podejrzanych ścieżek oraz blokowanie IP.
- Swagger `/docs` i `/openapi.json` dostępne wyłącznie dla administratora.

## Current Limitations

- **`request_log` rośnie bez retencji** — 318 016 wierszy na produkcji,
  zdominowanych przez skanowanie botów. Filtr „wszystko" pobiera cały zbiór.
- Panel jest w całości po angielsku i poza systemem i18n, w aplikacji, która
  chwali się dwujęzycznością.
- Ładuje Font Awesome z zewnętrznego CDN — jedyna taka zależność w produkcie.
- Osobny arkusz stylów (`admin.css`) i osobna konwencja UI względem reszty
  aplikacji.
- Poziom rozbudowania telemetrii bezpieczeństwa jest nieproporcjonalny do
  produktu z pięcioma kontami.

## Design Direction

**Zamrozić i ograniczyć.** Docelowo panel odpowiada na dwa pytania: _kto się
logował_ i _co się zepsuło_. Wszystko poza tym jest szumem.

Prace utrzymaniowe, w kolejności wartości:

1. Retencja `request_log` (np. 30 dni) albo agregacja — problem rośnie sam.
2. Ograniczenie logowania szumu skanowania albo oddzielenie go od ruchu
   aplikacyjnego.
3. Domyślny zakres inny niż „wszystko".

Nie robić: rozbudowy filtrów, wykresów, alertów, eksportu. Jeżeli pojawi się
potrzeba realnego monitoringu, właściwym miejscem jest warstwa operacyjna
(health endpoint + zewnętrzny monitoring), nie panel w aplikacji do gotowania.

## Source Of Truth

- Kod: `app/api/v1/admin.py`, `app/services/admin_service.py`,
  `app/core/request_log_middleware.py`, `app/core/ip_block.py`,
  `app/templates/admin_panel.html`
- Kontekst operacyjny: [audyt produkcyjny 2026-08-04](../audits/meal-planner-production-audit.md), MPP-005
