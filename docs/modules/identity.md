---
status: Active
last_updated: 2026-08-07
---

# Konta i dostęp

## Purpose

Moduł usługowy. Odpowiada za to, kto jest właścicielem przepisu i kto co widzi.
Nie ma własnej roadmapy — rozwija się wyłącznie pod potrzeby modułów
produktowych.

## Current Capabilities

- Logowanie hasłem (bcrypt), token JWT w cookie `access_token` (`httponly`,
  `samesite=lax`, `secure` zależne od środowiska), wylogowanie.
- Trzy role: `user`, `admin`, `super_admin`. `super_admin` ma dostęp do panelu
  administracyjnego i do Swaggera.
- Własność przepisu (`Recipe.user_id`) i widoczność (`is_public`) — przepis
  widzi właściciel oraz, jeśli publiczny, każdy zalogowany.
- Preferowany język przypisany do konta (`User.language`).
- Tworzenie użytkowników przez `POST /users` (tylko admin) i skrypt
  `scripts/bootstrap_admin.py`.
- Logowanie prób logowania (`login_log`), opóźnienie po nieudanych próbach,
  blokowanie IP.

Na produkcji: 5 kont, 4 z nich są autorami przepisów.

## Current Limitations

- **Brak pojęcia gospodarstwa domowego.** Model zna użytkownika i flagę
  „publiczny", a produkt służy rodzinie. Rozstrzygnięte przez
  [ADR-002](../decisions/ADR-002.md): encji gospodarstwa **nie wprowadzamy** —
  granicą gospodarstwa jest granica instancji.
- Brak samodzielnej rejestracji, resetu hasła i zmiany hasła z poziomu UI —
  konta zakłada administrator.
- Brak UI zarządzania użytkownikami; panel administracyjny pokazuje wyłącznie
  logi.
- `GET /ingredients/map` nie wymaga uwierzytelnienia — pojedynczy wyjątek od
  reguły, że wszystko jest za logowaniem.

## Design Direction

Rozstrzygnięte przez [ADR-002](../decisions/ADR-002.md): **jeden plan i jedna
lista zakupów na instancję**, bez encji gospodarstwa i bez multi-tenancy.
Wprowadzanie modelu wielu domów byłoby budowaniem SaaS-a bez potrzeby.

Wynikające z tego zadania dla modułu — wszystkie drobne:

- Plan i lista dostają `created_by` / `updated_by` wyłącznie do audytu, nie do
  kontroli dostępu.
- Flagę `is_public` przy przepisach można uprościć do „mój / wspólny", bo
  „publiczny" w obrębie jednego domu znaczy „wspólny". Osobna zmiana, poza
  zakresem ADR-002.

Poza tym moduł jest zamrożony: żadnych ról, uprawnień ani mechanizmów kont bez
konkretnej potrzeby produktowej.

## Source Of Truth

- Kod: `app/core/security.py`, `app/api/v1/auth.py`,
  `app/services/auth_service.py`, `app/services/permissions_service.py`,
  `app/db/models/user.py`
- Środowiska i bezpieczeństwo wdrożeniowe:
  [operations/production-environment.md](../operations/production-environment.md)
