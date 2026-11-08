# Wyniki lokalnej weryfikacji — 8.11.2026

Wyniki dotyczą lokalnej implementacji, nie oceny prowadzącego ani gotowego publicznego wdrożenia.

| Sprawdzenie | Wynik |
| --- | --- |
| Testy backendu `pytest` — SQLite | 26/26 zaliczonych |
| Ta sama pula `pytest` — PostgreSQL 17 | 26/26 zaliczonych; osobny schemat dla każdego testu |
| Docker Engine / Compose | 29.9.3 / 5.7.0, zainstalowane i uruchomione |
| Obraz Docker | zbudowany; healthcheck działa; proces UID 10001 |
| Docker + SQLite | 3 serie × 72 pomiary zachowane po restarcie; E1 23/23 |
| PostgreSQL, lokalne HTTPS | E2 45/45, 13/13 bez Lighthouse; 216 pomiarów zachowanych po restarcie kontenera |
| Oryginalny zestaw E1 | 23/23, 10/10 pkt automatycznych |
| Oryginalny zestaw E2 na lokalnym HTTPS | 45/45; kontrakt 6/6, walidacja 4/4, bezpieczeństwo 3/3 |
| Build React/Vite | poprawny, zależności z package-lock.json |
| Playwright | 2/2 na kontenerze z PostgreSQL: pulpit i pełny cykl administracyjny |
| Axe WCAG 2/2.1/2.2 A/AA, publiczny pulpit | brak zgłoszonych naruszeń w badanym widoku |
| Lighthouse Accessibility | 100/100, osobny audyt lokalnego HTTP |
| Dane demonstracyjne | 3 serie × 72 pomiary, wprowadzone przez generator HTTP |
| Generator CLI przeciwko działającemu API | historia, tryb bieżący, odrzucenie 422 i odwołany klucz 401 — poprawne |
| Mobilny viewport 360 px | brak poziomego overflow całej strony; tabela przewija się w swoim obszarze |
| Wydruk | wykres i pełna tabela; kontrolki ukryte, wyeksportowano PDF |

E2 testowano z lokalnym certyfikatem localhost, zaufanym tylko przez proces testujący przez `NODE_EXTRA_CA_CERTS`. Lighthouse uruchomiono osobno na HTTP localhost, dlatego **nie deklarujemy wspólnego wyniku 16/16 na publicznym wdrożeniu**. Testy trzeba powtórzyć na docelowym adresie z publicznie zaufanym certyfikatem.

Własne testy sprawdzają m.in. realną zmianę hasła, odwołanie wszystkich sesji, wygaśnięcie tokenu, Argon2id i skróty kluczy w bazie, trwałość przy ponownym starcie, duplikaty znaczników czasu, domknięte zakresy, limit, niepoprawne typy, odrzucenie przyszłości, atomowość zmiany zakresu przy równoległym zapisie, zachowanie wyników po usunięciu czujnika, kaskadę serii, błędy HTTP i limit prób logowania.

Playwright testuje wybór punktu klawiaturą, filtrowanie serii, widok telefonu, CSS print, logowanie przez Enter, utworzenie serii, rejestrację czujnika, jednorazowy klucz, SSE po zapisie pomiaru, odrzucenie klucza po wyrejestrowaniu i usunięcie testowej serii. Wynik Axe nie potwierdza całej dostępności WCAG; obowiązuje również manualna ocena.

Artefakty lokalne w ignorowanym `artifacts/`: `dashboard-desktop.png`, `dashboard-mobile.png`, `raport-pomiarow.pdf`, `lighthouse.json`, raporty testów. Dokumentacja jest w `docs/dokumentacja.pdf`. Testy nie zapisują sekretów do raportów.

Ograniczenia: brak weryfikacji kontenera na publicznym hoście, repozytorium opublikowano na GitHub, lecz pierwsze uruchomienie GitHub Actions zostało zablokowane przed startem z powodu rozliczeń konta (run 42502442180); brak nagrania z publicznej domeny i zgłoszenia Leia. Biblioteka Starlette podczas pytest zgłasza ostrzeżenie o przyszłej migracji klienta testowego z httpx; nie wpływa ono na wynik. Obecne wersje są zablokowane w uv.lock.

## Przygotowanie wdrożenia

`render.yaml` zweryfikowano z oficjalnym schematem https://render.com/schema/render.yaml.json. Repozytorium: https://github.com/CampiPL/ZAI, branch `main`. Docker Engine i Compose zainstalowano i sprawdzono. Konfiguracja Render używa `plan: free`, bez dysku; PostgreSQL ma działać na Neon Free. Nie utworzono usług publicznych — potrzebne jest połączenie kont dostawców. Instrukcja: [WDROZENIE.md](WDROZENIE.md).
