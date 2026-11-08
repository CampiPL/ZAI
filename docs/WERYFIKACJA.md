# Wyniki lokalnej weryfikacji — 8.11.2026

Wyniki dotyczą lokalnej implementacji, nie oceny prowadzącego ani gotowego publicznego wdrożenia.

| Sprawdzenie | Wynik |
| --- | --- |
| Testy backendu `pytest` | 23 zaliczone |
| Oryginalny zestaw E1 | 23/23, 10/10 pkt automatycznych |
| Oryginalny zestaw E2 na lokalnym HTTPS | 45/45; kontrakt 6/6, walidacja 4/4, bezpieczeństwo 3/3 |
| Build React/Vite | poprawny, zależności z package-lock.json |
| Playwright | 2 scenariusze zaliczone: pulpit i pełny cykl administracyjny |
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

Ograniczenia: brak uruchomionego Dockera w tym środowisku, brak weryfikacji kontenera na docelowym hoście, brak zdalnego repozytorium/uruchomienia GitHub Actions, brak nagrania z publicznej domeny i zgłoszenia Leia. Biblioteka Starlette podczas pytest zgłasza ostrzeżenie o przyszłej migracji klienta testowego z httpx; nie wpływa ono na wynik. Obecne wersje są zablokowane w uv.lock.
