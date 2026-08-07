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
  „publiczny", a produkt służy rodzinie. To blokuje decyzję D-2: czy plan
  posiłków jest wspólny, czy prywatny.
- Brak samodzielnej rejestracji, resetu hasła i zmiany hasła z poziomu UI —
  konta zakłada administrator.
- Brak UI zarządzania użytkownikami; panel administracyjny pokazuje wyłącznie
  logi.
- `GET /ingredients/map` nie wymaga uwierzytelnienia — pojedynczy wyjątek od
  reguły, że wszystko jest za logowaniem.

## Design Direction

Do rozstrzygnięcia w Sprincie 1 razem z modelem planu: **czy wprowadzamy
gospodarstwo domowe jako byt** (plan, lista zakupów i przepisy współdzielone w
obrębie domu), **czy pozostajemy przy jednym planie na instancję**.

Rekomendacja: jeden plan i jedna lista zakupów na instancję w v1 — Meal Planner
obsługuje jedno gospodarstwo domowe, a wprowadzanie pełnego modelu wielu domów
byłoby budowaniem SaaS-a bez potrzeby. Flagę `is_public` przy przepisach można
wtedy uprościć do „mój / wspólny".

Poza tym moduł jest zamrożony: żadnych ról, uprawnień ani mechanizmów kont bez
konkretnej potrzeby produktowej.

## Source Of Truth

- Kod: `app/core/security.py`, `app/api/v1/auth.py`,
  `app/services/auth_service.py`, `app/services/permissions_service.py`,
  `app/db/models/user.py`
- Środowiska i bezpieczeństwo wdrożeniowe:
  [operations/production-environment.md](../operations/production-environment.md)
