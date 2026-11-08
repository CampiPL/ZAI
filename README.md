# Splot — obserwatorium mikroklimatu

Projekt ZAI 26Z: FastAPI + React SPA + SQLite/PostgreSQL. Czytelnik ogląda wykres i tabelę, administrator zarządza seriami i czujnikami, a emulator przesyła pomiary przez API. Interfejs i komunikaty są po polsku.

Zaimplementowano F1–F13, wspólny kontrakt REST, trwałą bazę z migracją, generator, wydruk, responsywny widok, testy i dodatkowe odświeżanie przez SSE. Przykładowe dane: Szklarnia, Ogród zimowy i Taras, po 72 pomiary temperatury. Dane tworzy generator przez API.

**Stan oddania:** implementacja i lokalna weryfikacja są gotowe. Repozytorium jest opublikowane pod adresem https://github.com/CampiPL/ZAI (branch `main`). Publiczne wdrożenie, nagranie na publicznym adresie i wysłanie formularza Leia wymagają jeszcze skonfigurowania hostingu oraz uzupełnienia danych. Lokalny ZIP/PDF nie jest zgłoszeniem. E1 miał termin 7.11.2026; zgodnie ze specyfikacją można dołączyć go do E2 (21.11.2026) za maksymalnie 5 pkt.

## Docker i hosting — zacznij tutaj

Pełna instrukcja: [docs/WDROZENIE.md](docs/WDROZENIE.md). `compose.local.yaml` uruchamia aplikację lokalnie pod http://127.0.0.1:8080; `render.yaml` przygotowuje publiczną usługę **Render Free**, a trwałe dane przechowuje **Neon Free (PostgreSQL)**. Oba plany są bezpłatne w swoich limitach. Render usypia usługę po 15 minutach bez ruchu; pierwsze otwarcie może potrwać około minuty. Konta i połączenie z hostingiem trzeba skonfigurować według instrukcji.

Po zainstalowaniu Dockera i utworzeniu `.env`:

```bash
docker compose -f compose.local.yaml up -d --build --wait
docker compose -f compose.local.yaml exec -T app /app/.venv/bin/python -m generator.seed_demo --api http://127.0.0.1:8000
```

## Szybki start bez kontenerów

Wymagane: Python 3.12+, `uv`, Node.js 22.12+ z npm. Zweryfikowano na Python 3.12.16 i Node 22.23.4. Wersje zależności są zapisane w `uv.lock` i `frontend/package-lock.json`.

W katalogu `projekt`:

```bash
python3 scripts/setup.py
uv sync --locked
cd frontend
npm ci
npm run build
cd ..
uv run python scripts/serve.py
```

Otwórz **http://127.0.0.1:8000**. W drugim terminalu, w katalogu `projekt`, wprowadź dane:

```bash
uv run python scripts/seed.py
```

Login to `admin`. Losowe hasło znajduje się w lokalnym `.env` w polu `ADMIN_PASSWORD`; plik ma uprawnienia 0600 i jest ignorowany przez Git. Nie ma wspólnego hasła zaszytego w aplikacji. Skrypt setup nie nadpisuje istniejącej konfiguracji. Konto jest tworzone tylko przy pierwszym uruchomieniu nowej bazy — późniejsza zmiana `.env` **nie resetuje** hasła w bazie. Hasło zmienia się w panelu administratora.

W tym środowisku `uv`, `node`, `npm` i `npx` zainstalowano w katalogu użytkownika; polecenia są dostępne w `~/.local/bin`. Jeśli nie masz ich w PATH, użyj `export PATH="$HOME/.local/bin:$PATH"`. Node znajduje się trwale w `~/.local/share/node-v22.23.4-linux-x64`.

Tryb rozwoju: uruchom backend, a następnie `npm run dev` w `frontend`. Vite przekazuje `/api` do backendu na porcie 8000. Do oceny i testów bezpieczeństwa używaj zbudowanej aplikacji serwowanej przez backend lub publiczną domenę, ponieważ serwer deweloperski nie ma produkcyjnych nagłówków CSP.

## Generator czujnika

Narzędzie `generator/sensor.py` korzysta wyłącznie ze standardowej biblioteki Pythona i HTTP. Nie otwiera bazy danych. Utwórz serię i zarejestruj czujnik w panelu; klucz jest prezentowany tylko raz.

```bash
# Wklej klucz bez pokazywania go w terminalu ani historii poleceń:
read -rs -p 'Klucz czujnika: ' SPLOT_API_KEY
export SPLOT_API_KEY
export SPLOT_API_URL=http://127.0.0.1:8000

# Dane historyczne, kończące się w chwili uruchomienia:
python3 -m generator.sensor --historical --count 72 --step 1200 --min 18 --max 26

# Bieżące dane co 5 s; wykres odświeża się przez SSE:
python3 -m generator.sensor --count 0 --interval 5 --mode random --min 18 --max 26

# Demonstracja odrzucenia wartości spoza zakresu serii:
python3 -m generator.sensor --count 1 --mode constant --value 999
unset SPLOT_API_KEY
```

Parametry: `--api`, `--key` (alternatywnie zmienne powyżej), `--count` (0 = do Ctrl+C), `--interval`, `--mode sinusoid|random|constant`, `--min`, `--max`, `--value`, `--historical`, `--start` (ISO 8601 ze strefą), `--step`, `--phase`, `--seed`. `--help` opisuje wartości domyślne. Historia wymaga dodatniej liczby wyników; `--start` działa tylko z `--historical`. Odrzucenia mają czytelny status HTTP i kod wyjścia 1; utrata ważności klucza zatrzymuje generator.

`scripts/seed.py` tworzy demonstrację idempotentnie: pomija serie o tych samych nazwach, jeśli mają już co najmniej 15 pomiarów. Klucze czujników zapisuje lokalnie w `data/demo-keys.json` (0600, poza Git i archiwum). Nie traktuj tych plików jako części zgłoszenia. Po zmianie adresu lub bazy uruchom seed z właściwymi danymi i osobnym `--keys-file`, jeżeli chcesz zachować wcześniejsze klucze.

## Testy

```bash
uv run pytest -q
# Opcjonalnie ta sama pula testów na dedykowanym PostgreSQL:
# TEST_DATABASE_URL=postgresql://... uv run pytest -q
uv run python scripts/contract.py --stage E1
# Na publicznym HTTPS, z Chrome/Chromium:
uv run python scripts/contract.py --stage E2 --app https://TWOJA-DOMENA --lighthouse

cd frontend
npx playwright install chromium
npm run test:e2e
```

Testy przeglądarkowe wymagają działającej aplikacji z danymi demonstracyjnymi; używają lokalnego `.env` lub `ADMIN_USERNAME`/`ADMIN_PASSWORD` ze środowiska. Tworzą własną serię `E2E obserwacja` i usuwają ją po poprawnym przebiegu. Uruchamiaj testy kontraktu i przeglądarki kolejno, na bazie testowej lub lokalnej. Dane testów prowadzącego mają prefiks `ZAI-TEST-`.

`vendor/zai-tests.mjs` oraz YAML są niezmienionymi kopiami materiałów prowadzącego. `scripts/contract.py` przekazuje parametry i zwraca niezerowy kod wyjścia, jeśli raport zawiera niezaliczony test. Oryginalny skrypt nie robi tego dla zwykłych niepowodzeń testów.

Szczegółowe wyniki: [docs/WERYFIKACJA.md](docs/WERYFIKACJA.md). Workflow `.github/workflows/test.yml` uruchamia własne testy, build, E1 oraz testy przeglądarki po push/PR. Zielony status na GitHub trzeba potwierdzić po wysłaniu repozytorium; nie jest deklarowany na podstawie samego istnienia pliku YAML.

## Architektura i bezpieczeństwo

- FastAPI realizuje endpointy dokładnie z kontraktu; błędy mają RFC 9457 `application/problem+json`. Walidacja Pydantic odrzuca złe typy, brakujące pola i wartości niefinitywne.
- SQLite z WAL działa lokalnie, PostgreSQL na bezpłatnym hostingu. Niepuste `DATABASE_URL` wybiera PostgreSQL i ma pierwszeństwo przed `DATABASE_PATH`. Migracje: `backend/migrations/001_initial.sql` i `001_initial.postgres.sql`; model i relacje: [docs/ERD.md](docs/ERD.md).
- `backend/db.py`: hasła Argon2id. `backend/app.py`: kryptograficznie losowe tokeny i klucze 43-znakowe; w bazie SHA-256, nigdy wartości jawne. SHA-256 jest używany dla losowych sekretów, nie haseł.
- Sesje wygasają (domyślnie 3600 s), logout usuwa token, a zmiana hasła unieważnia wszystkie sesje. React trzyma token tylko w pamięci; odświeżenie strony wymaga ponownego logowania. Nie używa localStorage ani cookies.
- Parametryzowane SQL oraz serializacja zapisów (`BEGIN IMMEDIATE` w SQLite, transakcyjna blokada advisory w PostgreSQL) zabezpieczają spójność zakresów. Usunięcie czujnika zachowuje pomiary (`SET NULL`); usunięcie serii kaskadowo usuwa czujniki i pomiary.
- Autoryzacja jest po stronie serwera. Administrator nie może zapisywać pomiarów samym Bearer. Czujnik nie może wybrać innej serii w treści żądania.
- Limit 20 błędnych logowań na parę adres/login w 5 minut, limit treści 64 KB. Log odrzuceń nie zawiera haseł ani kluczy.
- CSP bez zewnętrznych skryptów i bez `unsafe-inline`, `nosniff`, blokada ramek, Referrer-Policy, Permissions-Policy, HSTS przy HTTPS. Brak liberalnego CORS; frontend i backend działają w tej samej domenie.
- React renderuje wykres SVG bez zewnętrznej usługi. Filtry, tabela i wykres współdzielą stan. Tabela zachowuje kilka pomiarów o identycznym czasie, a wydruk obejmuje wszystkie wyniki w pobranym zakresie, nie tylko stronę tabeli.
- Rozszerzenie API: publiczne `GET /api/events` (`text/event-stream`). Serwer wysyła zdarzenie `update` z licznikiem rewizji; przeglądarka ponownie pobiera dane z REST. Odczyt rewizji co 1 s, heartbeat co 15 s, reconnect zapewnia EventSource. Zdarzenia nie zawierają sekretów.
- Lista pomiarów UI jest ograniczona do 10 000 najnowszych wyników wybranego zakresu; po osiągnięciu limitu interfejs prosi o zawężenie filtrów. API obsługuje kontraktowy limit 1–10 000.

## Publiczne wdrożenie

Zalecany wariant bezpłatny Render + Neon opisano krok po kroku w [docs/WDROZENIE.md](docs/WDROZENIE.md). Poniższa alternatywa dotyczy własnego VPS.

Dla VPS wymagany jest serwer z Docker Compose, domeną wskazującą na serwer i otwartymi portami 80/443. Dołączona konfiguracja korzysta z Caddy jako reverse proxy z HTTPS i trwałych wolumenów. Nie wymaga płatnej usługi konkretnego dostawcy; koszt serwera/domeny zależy od wybranego miejsca.

1. Umieść repozytorium na serwerze. Utwórz `.env` przez `scripts/setup.py` lub na bazie `.env.example`, ustaw mocne `ADMIN_PASSWORD` i dodaj `SPLOT_DOMAIN=pomiary.twoja-domena.pl`.
2. Uruchom `docker compose up -d --build` w katalogu projektu. Do Internetu wystawiany jest Caddy; port backendu pozostaje wewnętrzny.
3. Sprawdź `https://TWOJA-DOMENA/api/health`, a następnie uruchom lokalnie `uv run python scripts/seed.py --api https://TWOJA-DOMENA` z danymi wdrożonego administratora.
4. Uruchom E2 z `--lighthouse` i dokładnie danymi, które trafią do Leia. Sprawdź trwałość danych po `docker compose restart`.

Backend ufa `X-Forwarded-*` od wewnętrznego proxy. Nie wystawiaj jego portu przy `FORWARDED_ALLOW_IPS=*`. Nie ustawiaj `REQUIRE_HTTPS=true` dla lokalnego healthchecka z dołączonego Compose; HTTPS wymusza Caddy. SSE ma wyłączone buforowanie. Certyfikaty i baza pozostają w nazwanych wolumenach; `docker compose down -v` usuwa także te dane.

Docker Engine i Compose zainstalowano. Wyniki sprawdzenia kontenera: [docs/WERYFIKACJA.md](docs/WERYFIKACJA.md). Publiczne wdrożenie wymaga dostępu do kont Render i Neon. Nie używaj nietrwałego systemu plików hostingu dla SQLite. Kopię bazy wykonuj przez SQLite Backup API albo po zatrzymaniu aplikacji, z uwzględnieniem plików WAL; samego aktywnego pliku `.sqlite3` nie należy kopiować jako kompletnej kopii.

## Dokumentacja i oddanie

- [Dokumentacja PDF](docs/dokumentacja.pdf), [ERD](docs/ERD.md), [scenariusz i lista kontrolna](docs/ODDANIE.md).
- [Analiza wejściowych materiałów](docs/ANALIZA.md) zachowuje stan z 14.10.2026; jej opis „brak implementacji” jest historyczny.
- `uv run python scripts/documentation.py` odtwarza PDF roboczy. Wymaga fontów DejaVu (domyślnie `/usr/share/fonts/truetype/dejavu`, lub `--font-dir`).
- Po wdrożeniu: `uv run python scripts/documentation.py --url https://TWOJA-DOMENA --repo https://ADRES-REPO --submission`. Hasło konta zgłoszeniowego pobierane jest z `ADMIN_PASSWORD`, nigdy z argumentu. Prywatny PDF trafia do `artifacts/dokumentacja-oddanie.pdf`, poza Git.
- `uv run python scripts/package.py` tworzy `artifacts/splot-zai-26z.zip`. Po uzupełnieniu zgłoszenia użyj `--documentation artifacts/dokumentacja-oddanie.pdf`, aby podmienić PDF wewnątrz ZIP. Taki ZIP zawiera dane konta dla prowadzącego — przekazuj go formularzem kursu.

Repozytorium: https://github.com/CampiPL/ZAI, branch `main`. Historia rozpoczyna się faktyczną implementacją 8.11.2026; nie rekonstruowano fikcyjnych wcześniejszych commitów.

## Źródła i deklaracja AI

Ta informacja wynika ze specyfikacji przedmiotu: w „Dokumentacja PDF” punkt 7 wymaga deklaracji użycia AI, a „Zasady realizacji” nakazują podać wykorzystane narzędzia i zakres pomocy oraz źródła fragmentów kodu przejętych z zewnątrz. Prowadzący wymaga deklaracji w PDF; umieszczenie jej również w README jest decyzją porządkową autora dokumentacji, a nie dodatkowym wymaganiem narzędzia.

Wymagania i testy: materiały prowadzącego ZAI 26Z w workspace i `vendor/`. Dokumentacja techniczna użyta przy realizacji: [FastAPI — Docker](https://fastapi.tiangolo.com/deployment/docker/), [React — useEffect](https://react.dev/reference/react/useEffect), [Caddy — reverse_proxy](https://caddyserver.com/docs/caddyfile/directives/reverse_proxy). Biblioteki i ich licencje: `frontend/package-lock.json`, `uv.lock` oraz metadane pakietów; ikony Lucide (ISC), React/Vite (MIT). Z materiałów dydaktycznych AngularJS/GWT nie kopiowano implementacji aplikacji.

W projekcie wykorzystano asystenta OpenAI Codex do analizy wymagań, projektowania, implementacji, testów i dokumentacji. Autor zgłoszenia powinien zweryfikować kod i rozumieć decyzje projektowe. Deklaracja dotyczy faktycznego szerokiego zakresu pomocy AI.
