# Lista Issue – Meal Planner

## 1️⃣ Tło
**Tytuł:** Tło cyberpunkowe  
**Opis:** Zrobić cyberpunk 4–5 linii na tle, które będą mrugać.  
**Label:** frontend  

---

## 2️⃣ Użytkownicy
**Tytuł:** Dodanie użytkowników  
**Opis:** Na razie mamy tylko jednego użytkownika: admin (hasło: **).  
Dodać prawidłową obsługę admina i możliwość tworzenia nowych użytkowników.  
**Label:** backend  

---

## 3️⃣ Front – drugi język
**Tytuł:** Obsługa drugiego języka strony  
**Opis:** Dodać możliwość zmiany języka strony. Na start polski i angielski.  
**Label:** frontend  

---

## 4️⃣ Front – edytowanie przepisów
**Tytuł:** Edycja przepisów w UI  
**Opis:** Dodanie funkcji edytowania już dodanych przepisów w interfejsie użytkownika.  
**Label:** frontend  

---

## 5️⃣ Baza danych – składniki ważne/nieważne
**Tytuł:** Składniki ważne/nieważne  
**Opis:** Zdefiniować, które składniki w przepisach są **ważne**, a które **nieważne** (np. sól – zawsze jest w domu).  
**Label:** backend, db  

---

## 6️⃣ Dev – przygotowanie repozytorium
**Tytuł:** Repozytorium GitHub  
**Opis:** Upewnić się, że repozytorium jest gotowe do pracy, połączone z lokalnym projektem i gotowe do commitów i push.  
**Label:** devops  

---

## 7️⃣ Front – overflow topbara na 360px
**Tytuł:** `.topbar-right` wychodzi poza viewport na wąskich telefonach  
**Opis:** Na widoku Recipes przy szerokości ~360px `.topbar-right` (przełącznik języka + user-badge + przycisk ☰) wychodzi ok. 27px poza prawą krawędź viewportu (`scrollWidth` 387px przy `innerWidth` 360px), obcinając część `user-badge`/burger. Potwierdzone jako pre-existing na `origin/main` (przed theme UX cleanup w commicie `6feb5a1`, niepowiązane z tamtą zmianą) — znalezione podczas manualnego smoke na 360px. Wymaga własnego, osobnego review responsywności topbara, nie tylko odstępów/paddingu.  
**Label:** frontend, responsive, mobile  
