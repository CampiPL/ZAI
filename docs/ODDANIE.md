# Przygotowanie zgłoszenia — 26Z

Terminy według materiałów: E1 7.11.2026, E2 21.11.2026, oba do 23:59. Na dzień implementacji (8.11.2026) termin E1 minął. Specyfikacja dopuszcza E1 razem z E2 za maksymalnie 5 pkt. Nie oznaczaj E1 jako zgłoszonego, jeżeli nie wysłano formularza.

## Dane do uzupełnienia po wdrożeniu

- [ ] Publiczny adres aplikacji: …
- [ ] Adres API (ta sama domena; endpointy `/api`): …
- [ ] Repozytorium dostępne prowadzącemu: …
- [ ] Działające konto testowe, hasło i status CI: …
- [ ] Wynik E2 z `--lighthouse` na publicznej domenie: …
- [ ] Ewentualny czas wybudzenia hostingu: …

Wdrożenie i konto muszą pozostać dostępne do wystawienia oceny. Lokalne wyniki testów nie zastępują oceny publicznego adresu.

## Scenariusz nagrania (plan na około 6 minut)

Nagraj działającą **publicznie wdrożoną** aplikację z widocznym paskiem adresu. Podawaj kody wymagań. Poniższe minuty są planem, nie deklaracją istniejącego nagrania.

| Plan | Pokaz |
| --- | --- |
| 0:00–0:40 | F1, F2, F11: pulpit, 3 serie, wykres i kolumny tabeli, minimum 15 danych w każdej serii. |
| 0:40–1:15 | F5, F6: wybór serii, daty, kliknięcie pomiaru i wyróżnienie punktu; nawigacja klawiaturą. |
| 1:15–1:45 | F7, F10, B2: podgląd wydruku bez kontrolek oraz ekran 360 px. |
| 1:45–2:25 | F3, F8, F9: logowanie, utworzenie serii, Enter, błąd walidacji zakresu, zmiana nazwy/koloru/znacznika. |
| 2:25–3:50 | F12, F13: rejestracja nowego czujnika, skopiowanie klucza do SPLOT_API_KEY w terminalu, generator bieżący; SSE pokazuje nowe punkty bez odświeżania. |
| 3:50–4:25 | F4: generator z `--mode constant --value 999 --count 1`; czytelne 422 w generatorze i wpis `measurement_rejected` w logu serwera; konflikt 409 przy zawężeniu serii. |
| 4:25–4:55 | F12: wyrejestrowanie czujnika, ponowne wysłanie z tym samym kluczem kończy się 401, wcześniejsze wyniki pozostają. |
| 4:55–5:25 | F8: zmiana hasła, koniec sesji, logowanie nowym hasłem i wylogowanie. Przywróć lub zaktualizuj dane konta zgłoszeniowego. |
| 5:25–6:10 | B3–B5: ERD/migracja, Argon2id i skróty kluczy w kodzie/bazie, dokumentacja; opcjonalnie zielony CI. |

Eksport: MP4, 5–7 minut, maksymalnie 100 MB. Nie publikuj kluczy i hasła na publicznym nagraniu; użyj czujnika demonstracyjnego i wyrejestruj go pod koniec. Nagranie dla prowadzącego można przekazać zgodnie z formularzem kursu.

## Lista kontrolna (wypełnij po nagraniu)

| Element | Implementacja | Minuta faktycznego nagrania |
| --- | --- | --- |
| F1–F2 | Pomiary API, osobne serie/kolumny/krzywe | … |
| F3 | Role i panel zarządzania | … |
| F4 | Walidacja, log odrzuceń i generator | … |
| F5–F6 | Filtry i wyróżnienie punktu | … |
| F7 | CSS `@media print` | … |
| F8–F9 | Konto, formularze, błędy, ładowanie | … |
| F10–F11 | Telefon 360 px, 3 × 72 dane przez API | … |
| F12–F13 | Cykl czujnika i generator w obu trybach | … |
| B2 | Widok telefonu i wydruk | … |
| B3 | Argon2id, SHA-256 kluczy/tokenów, autoryzacja | … |
| B4 | ERD i migracja SQL | … |
| B5 | PDF do 8 stron po uzupełnieniu adresów/konta | … |
| Bonus SSE | Aktualizacja wykresu przez `/api/events` | … |
| Bonus CI | Własne testy; status potwierdzić po wysłaniu repozytorium | … |

Archiwum generuje `uv run python scripts/package.py`. Nie zawiera `.env`, bazy, kluczy, zależności, nagrań ani certyfikatów. PDF jest generowany przez `scripts/documentation.py`; przed zgłoszeniem ustaw adresy i dane konta testowego zgodnie z README. Sam wygenerowany ZIP nie stanowi zgłoszenia w Leia.
