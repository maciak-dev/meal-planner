---
status: Active
last_updated: 2026-08-07
---

# Meal Planner Documentation

Ten katalog jest jedynym punktem wejścia do aktywnej dokumentacji projektu.

Dokumentacja jest zorganizowana od produktu do implementacji — nigdy odwrotnie:

```
North Star → Vision → Modules → Integrations → Architecture → Operations
```

## Start Here

1. [North Star](north-star.md) — najważniejszy dokument projektu
2. [Product vision](product/vision.md) — jaki problem rozwiązujemy
3. [Audyt produktowy 2026-08-07](audits/product-audit-2026-08-07.md) — stan
   wyjściowy i diagnoza
4. [Roadmap](product/roadmap.md) — Sprint 0, Sprint 1, decyzje do podjęcia
5. [Backlog](product/backlog.md)
6. [Rejestr decyzji](decisions/README.md) — ADR-001 … ADR-004
7. [Integracja z MAP](integrations/map.md) — granice i kontrakt

## Modules

- [Portfolio modułów](modules/README.md) — cel, priorytet, status, kierunek
- [Plan posiłków](modules/meal-plan.md) _(planowany)_
- [Lista zakupów](modules/shopping-list.md)
- [Dashboard](modules/dashboard.md) _(planowany)_
- [Przepisy](modules/recipes.md)
- [Import przepisu z URL](modules/recipe-import.md)
- [Składniki (normalizacja)](modules/ingredients.md) _(zamrożony)_
- [Dwujęzyczność PL/EN](modules/i18n.md)
- [Konta i dostęp](modules/identity.md)
- [Panel administracyjny i logi](modules/admin.md) _(zamrożony)_

## Product

- [Projekt dashboardu](product/dashboard.md) — specyfikacja wejściowa Sprintu 2

## Decisions

- [Rejestr decyzji](decisions/README.md)
- [ADR-001](decisions/ADR-001.md) — jeden slot posiłkowy dziennie w v1
- [ADR-002](decisions/ADR-002.md) — plan i lista należą do gospodarstwa, nie do
  użytkownika
- [ADR-003](decisions/ADR-003.md) — agregacja tylko przy zgodnej nazwie i
  jednostce
- [ADR-004](decisions/ADR-004.md) — porcje i czasy utrwalane w modelu przepisu

## Architecture

- [Wydzielenie panelu admina](architecture/panel-admin-extraction.md)

## Operations

- [Production Guardrails](operations/production-guardrails.md) — obowiązkowa
  lektura przed jakąkolwiek zmianą dotykającą produkcji
- [Środowisko produkcyjne](operations/production-environment.md)
- [Środowisko RC](operations/rc-environment.md)
- [Backup i restore PostgreSQL](operations/postgres-backup-restore.md)
- [Runbook wdrożenia Sprintu 0](operations/sprint-0-production-rollout.md)

## Audits

- [Audyt produktowy 2026-08-07](audits/product-audit-2026-08-07.md)
- [Audyt produkcyjny 2026-08-04](audits/meal-planner-production-audit.md) —
  warstwa infrastrukturalna
- [Przegląd feature'u składników](audits/ingredients-feature-review.md)
- [Próba wdrożenia 2026-08-05](audits/meal-planner-production-rollout-attempt-2026-08-05.md)

## Dokumenty spoza tego baseline'u

Warstwa produktowa opisuje także pracę, której kod i dokumentacja czekają na
akceptację na branchu `feature/i18n-recipe-import-ingredients`. Te dokumenty
**nie są** częścią tego brancha i wejdą do hierarchii dopiero po
zaakceptowaniu tamtej zmiany:

- `docs/architecture/recipe-import.md`
- `docs/architecture/ingredient-model.md`
- `docs/decisions/recipe-translations.md` — do przenumerowania na **ADR-005**
- `docs/decisions/ingredient-normalization.md` — do przenumerowania na
  **ADR-006**
- `docs/handoffs/i18n-recipe-import-ingredients.md`
- `docs/product/bilingual-recipe-import.md`
- `docs/audits/meal-planner-production-rollout-ready-2026-08-05.md`

## Source Of Truth

- Kierunek produktu: [north-star.md](north-star.md)
- Aktywny plan: [product/roadmap.md](product/roadmap.md)
- Priorytetyzowany backlog: [product/backlog.md](product/backlog.md)
- Decyzje: [decisions/README.md](decisions/README.md)
- Granice wobec MAP: [integrations/map.md](integrations/map.md)
- Dokumentacja modułów: [modules/](modules/README.md)

## Zasady dokumentacji

1. `product/roadmap.md`, `product/backlog.md` i `decisions/` pozostają jedynym
   źródłem prawdy dla aktywnego planu, backlogu i decyzji.
2. Każdy nowy moduł dostaje dokument w `modules/`.
3. Dokumenty aktywne mają `status` i `last_updated` we frontmatterze.
4. Nie utrzymujemy dwóch źródeł prawdy dla tego samego aktywnego tematu.
5. Zamknięte plany schodzą do audytów i handoffów, nie zostają w roadmapie.
6. `ISSUES.md` w katalogu głównym jest historycznym artefaktem sprzed wizji —
   jego zawartość została oceniona w
   [audycie produktowym](audits/product-audit-2026-08-07.md) i przeniesiona do
   [backlogu](product/backlog.md) albo odrzucona.
