#!/usr/bin/env python3
"""Generate a six-page PDF. Submission credentials only go to ignored artifacts/."""
import argparse
import os
from pathlib import Path

from dotenv import load_dotenv
from fpdf import FPDF

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")
p = argparse.ArgumentParser()
p.add_argument("--url", default="Nie wdrożono publicznie — do uzupełnienia")
p.add_argument("--repo", default="Repozytorium lokalne — do uzupełnienia")
p.add_argument("--font-dir", type=Path, default=Path("/usr/share/fonts/truetype/dejavu"))
p.add_argument("--submission", action="store_true")
args = p.parse_args()
if args.submission and (not args.url.startswith("https://") or not args.repo.startswith("https://") or not os.getenv("ADMIN_PASSWORD")):
    p.error("Wersja do oddania wymaga --url HTTPS, --repo HTTPS i ADMIN_PASSWORD w środowisku lub .env.")


class PDF(FPDF):
    def footer(self):
        self.set_y(-13)
        self.set_font("DejaVu", size=8)
        self.set_text_color(95, 110, 90)
        self.cell(0, 6, f"SPLOT / ZAI 26Z                                                {self.page_no()} / {{nb}}")


pdf = PDF()
pdf.set_margins(18, 18, 18)
pdf.set_auto_page_break(auto=True, margin=20)
pdf.add_font("DejaVu", fname=str(args.font_dir / "DejaVuSans.ttf"))
pdf.add_font("DejaVu", style="B", fname=str(args.font_dir / "DejaVuSans-Bold.ttf"))
pdf.alias_nb_pages()
pdf.set_title("Splot — dokumentacja projektu ZAI 26Z")
pdf.set_author("Projekt ZAI 26Z; opracowanie z pomocą OpenAI Codex")


def page(number, title):
    pdf.add_page()
    pdf.set_fill_color(23, 62, 53)
    pdf.rect(0, 0, 210, 8, style="F")
    pdf.set_text_color(85, 105, 75)
    pdf.set_font("DejaVu", size=9)
    pdf.cell(0, 8, f"SPLOT / {number:02d}", new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(23, 62, 53)
    pdf.set_font("DejaVu", "B", 21)
    pdf.multi_cell(0, 11, title, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(7)


def section(title, text):
    pdf.set_text_color(23, 62, 53)
    pdf.set_font("DejaVu", "B", 11)
    pdf.multi_cell(0, 7, title, new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(42, 55, 46)
    pdf.set_font("DejaVu", size=9)
    pdf.multi_cell(0, 5.2, text, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)


page(1, "Obserwatorium mikroklimatu")
section("Cel i użytkownicy", "Splot zbiera pomiary temperatury z wielu miejsc. Czytelnik ma publiczny dostęp do wykresu i tabeli. Administrator zarządza seriami, czujnikami i swoim hasłem. Wyniki są dopisywane wyłącznie przez API czujnika; interfejs nie oferuje ich ręcznej edycji ani usuwania.")
section("Adresy i konto", f"Aplikacja i API: {args.url}\nRepozytorium: {args.repo}\nLogin: {os.getenv('ADMIN_USERNAME', 'admin')}\nHasło: " + (os.environ['ADMIN_PASSWORD'] if args.submission else "w lokalnym .env; wersja robocza nie zawiera sekretów"))
section("Dobór technologii", "FastAPI i Pydantic zapewniają jawny kontrakt i walidację. SQLite z WAL upraszcza odtwarzanie projektu i spełnia wymaganie relacyjnej bazy; wymaga trwałego dysku jednego hosta. React jest biblioteką SPA, współdzielącą stan filtrów, wykresu i tabeli. SVG umożliwia własne znaczniki, wybór punktów oraz wydruk bez dodatkowej usługi wykresów. Generator używa standardowej biblioteki Python.")
section("Dane i zakres", "Trzy serie demonstracyjne: Szklarnia, Ogród zimowy, Taras; po 72 pomiary w stopniach Celsjusza. Generator tworzy je przez REST, a nie przez zapis do SQL. Zakresy i nazwy można zmieniać. Wyniki API są ograniczane parametrem limit; interfejs pobiera do 10 000 najnowszych w wybranym zakresie i informuje o osiągnięciu limitu.")
section("Stan zgłoszenia", "Kod, migracja, generator i lokalne testy są przygotowane. Wersja robocza wymaga uzupełnienia publicznego adresu, repozytorium, danych konta i nagrania wdrożonej aplikacji. E1: 7.11.2026; E2: 21.11.2026, 23:59. Spóźnione E1 można oddać z E2 za maksymalnie 5 pkt. Utrzymuj adres i konto do wystawienia oceny.")

page(2, "Uruchomienie i generator")
section("Środowisko", "Weryfikacja: Python 3.12.16, Node.js 22.23.4. Wymagane Python 3.12+, uv i Node 22.12+ z npm. Dokładne zależności: uv.lock oraz frontend/package-lock.json. Polecenia wykonuj w katalogu projekt.")
section("Uruchomienie lokalne", "python3 scripts/setup.py\nuv sync --locked\ncd frontend && npm ci && npm run build\ncd ..\nuv run python scripts/serve.py\n\nAdres: http://127.0.0.1:8000. Drugie okno terminala:\nuv run python scripts/seed.py\n\nSetup jednorazowo generuje .env z losowym hasłem. Baza: data/splot.sqlite3. Kolejny start nie resetuje konta. Zmiana hasła w panelu unieważnia wszystkie sesje. Token UI istnieje tylko w pamięci; przeładowanie strony wymaga logowania.")
section("Wysyłanie pomiarów", "Zarejestruj czujnik w panelu. Ustaw SPLOT_API_KEY na otrzymany klucz i SPLOT_API_URL na adres bazowy, bez /api. Nie zapisuj klucza w kodzie.\n\npython3 -m generator.sensor --historical --count 72 --step 1200\npython3 -m generator.sensor --count 0 --interval 5 --mode random\npython3 -m generator.sensor --count 1 --mode constant --value 999")
section("Parametry", "--api / --key lub zmienne SPLOT_API_URL / SPLOT_API_KEY; --count: liczba (0 = bez końca); --interval: odstęp wysyłania w sekundach; --mode: sinusoid, random, constant; --min / --max: zakres; --value: stała; --historical: bez czekania; --start: ISO 8601 ze strefą; --step: odstęp pomiarów historycznych; --phase / --seed: konfiguracja przebiegu. Generator wypisuje status i przyczynę odrzucenia, kończy kodem 1 przy błędach i przerywa po 401. Seed pomija istniejące serie z ≥15 wynikami, a klucze zapisuje w ignorowanym data/demo-keys.json.")

page(3, "Relacyjny model danych")

def box(x, y, w, title, rows):
    height = 13 + len(rows) * 5
    pdf.set_draw_color(174, 193, 163)
    pdf.set_fill_color(245, 248, 239)
    pdf.rect(x, y, w, height, style="DF")
    pdf.set_xy(x + 3, y + 2)
    pdf.set_font("DejaVu", "B", 10)
    pdf.cell(w - 6, 7, title)
    pdf.set_xy(x + 3, y + 11)
    pdf.set_font("DejaVu", size=8)
    pdf.multi_cell(w - 6, 5, "\n".join(rows), new_x="LMARGIN", new_y="NEXT")
    return height

box(18, 54, 76, "admins", ["PK id", "UK username", "password_hash (Argon2id)"])
box(116, 54, 76, "sessions", ["PK token_hash", "FK admin_id → admins", "expires_at"])
box(18, 104, 76, "series", ["PK id; name", "min_value < max_value", "color; icon; unit"])
box(116, 104, 76, "sensors", ["PK id; name", "FK series_id → series", "UK key_hash", "created_at; last_measurement_at"])
box(60, 166, 100, "measurements", ["PK id", "FK series_id → series (CASCADE)", "FK sensor_id → sensors (SET NULL)", "value; timestamp UTC"])
pdf.set_draw_color(72, 110, 82)
pdf.line(94, 69, 116, 69)
pdf.line(94, 121, 116, 121)
pdf.line(54, 132, 54, 178)
pdf.line(54, 178, 60, 178)
pdf.line(157, 137, 157, 166)
pdf.set_xy(18, 212)
section("Klucze, indeksy i spójność", "Migracja: backend/migrations/001_initial.sql. Indeksy: measurements(series_id,timestamp) oraz timestamp. Czasy mają jednolity format UTC. Nie ma unikatowości czasu w serii — duplikaty czasowe zachowują własne ID. Usunięcie serii usuwa jej dane; usunięcie czujnika zeruje tylko opcjonalny FK pomiaru. BEGIN IMMEDIATE serializuje zapis i walidację. Tabele techniczne: schema_migrations, changes (rewizja SSE), login_attempts (limit prób logowania).")

page(4, "API i bezpieczeństwo")
section("Wspólny kontrakt", "Pełny kontrakt: vendor/zai-api-26z.yaml. /api/health; auth/login, auth/logout, auth/password; CRUD series; rejestracja, lista i wyrejestrowanie sensors; measurements: publiczny GET i POST z kluczem. Brak PUT/PATCH/DELETE pojedynczych pomiarów. Utworzenie: 201 i Location; usunięcie/logout: 204; walidacja: 400/422; brak uwierzytelnienia: 401; konflikt zakresu: 409. Błędy application/problem+json zawierają title/status/detail.")
section("Mechanizm 1: hasła i sesje", "backend/db.py używa Argon2id, funkcji przeznaczonej do haseł z losową solą. Hasło nie jest zapisywane jawnie. backend/app.py tworzy token przez secrets.token_urlsafe(32), zapisując tylko SHA-256 i termin ważności. Hasz losowego tokenu ogranicza skutki odczytu bazy. Każda operacja administracyjna sprawdza sesję. Logout usuwa token, a zmiana hasła usuwa wszystkie sesje konta. Próby logowania są limitowane. Frontend nie utrwala tokenu w localStorage.")
section("Mechanizm 2: tożsamość czujnika", "Każdy czujnik ma losowy 43-znakowy klucz. Serwer przechowuje wyłącznie jego SHA-256; jedyną odpowiedzią zawierającą jawny klucz jest rejestracja. Odczyty czujników nie ujawniają sekretów. Nagłówek X-API-Key ustala serię; seria przesłana w body nie pozwala skierować pomiaru gdzie indziej. Po usunięciu czujnika klucz natychmiast przestaje działać. Token administratora nie daje prawa zapisu pomiarów.")
section("Pozostałe zabezpieczenia", "SQL jest parametryzowany. Limit treści: 64 KB; walidacja typów, zakresu, dat i formatów. Błędy nie ujawniają stosu wywołań. CSP ogranicza źródła do tej samej domeny; X-Content-Type-Options, X-Frame-Options, Referrer-Policy i Permissions-Policy są ustawiane przez backend. HTTPS/HSTS oraz przekierowanie HTTP zapewnia docelowe wdrożenie z Caddy. Proxy headers należy akceptować wyłącznie od zaufanego reverse proxy.")
section("Rozszerzenie SSE", "GET /api/events zwraca text/event-stream. Zdarzenie update zawiera {revision: liczba}. Licznik w bazie zmienia się przy zmianach danych. Klient po zdarzeniu pobiera aktualne REST; heartbeat co 15 sekund, odczyt rewizji co 1 sekundę. EventSource wznawia połączenie. Jest to dodatkowy endpoint; wspólny kontrakt pozostaje bez zmian.")

page(5, "Interfejs i weryfikacja")
section("Prezentacja", "Każda seria ma osobną krzywą i kolumnę tabeli. Dane filtrowane są po seriach i domkniętym przedziale czasu. Wartość w tabeli jest przyciskiem dostępnym z klawiatury: wybór wyróżnia punkt na wykresie. Kilka wyników w jednej chwili pojawia się w tej samej komórce bez nadpisywania. Wykres ma różne kolory, znaczniki i wzory linii; opisy i tabela zapewniają alternatywę tekstową.")
section("Responsywność, UX i druk", "CSS korzysta z Flexbox, Grid i media queries. Sprawdzono widok 360 px, przewijanie samej tabeli, etykiety formularzy, fokus i Enter. Dialogi używają natywnego dialog, komunikaty aria-live/role=alert. Wykres dostosowuje viewBox do szerokości. Reguły @media print ukrywają kontrolki i drukują pełną pobraną tabelę wraz z wykresem.")
section("Lokalne testy", "Własne pytest: 23 testy, w tym zmiana hasła i sesje, trwałość po restarcie, skróty sekretów, duplikaty czasu, limit, ścisłe typy, usuwanie czujnika i równoczesna zmiana zakresu. Testy prowadzącego: E1 23/23 (10/10), E2 45/45 w grupach kontrakt/walidacja/bezpieczeństwo (13/13) na lokalnym HTTPS. Testy Playwright obejmują publiczny pulpit i cykl administracyjny, klucz, SSE, odwołanie oraz logout. Szczegóły i ograniczenia: docs/WERYFIKACJA.md.")
section("CI i dokumentacja wyników", "Workflow GitHub Actions instaluje zależności z lockfile, uruchamia pytest, build, seed, kontrakt E1 i Playwright. Kod wyjścia wrappera kontraktu zależy od wyników testów. Repozytorium nie zostało jeszcze wysłane; zielony status zdalnego CI musi być potwierdzony po push. Nie uruchomiono obrazu Docker ani testów publicznego wdrożenia. Lokalny wynik nie jest gwarancją oceny prowadzącego.")
section("Polecenia kontrolne", "uv run pytest -q\nuv run python scripts/contract.py --stage E1\ncd frontend && npm run test:e2e\n\nNa publicznej domenie, z Chrome/Chromium:\nuv run python scripts/contract.py --app https://DOMENA --stage E2 --lighthouse")

page(6, "Wdrożenie, źródła i oddanie")
section("Publiczny serwer", "Dockerfile buduje frontend, następnie uruchamia FastAPI jako użytkownik bez uprawnień root. compose.yaml i Caddyfile udostępniają porty 80/443, kierują ruch do wewnętrznego app:8000 i zachowują dane na nazwanym wolumenie. Ustaw SPLOT_DOMAIN i dane administratora w .env, wskaż DNS na serwer, uruchom docker compose up -d --build. Wprowadź dane generatorem przez publiczne API, sprawdź testy oraz trwałość po restarcie. Konfiguracji kontenerowej nie uruchomiono w środowisku implementacji.")
section("Archiwum i demonstracja", "scripts/package.py tworzy ZIP z kodem aplikacji, generatora, SQL, .env.example, testami i tym PDF. Wyklucza bazę, klucze, .env i zależności. docs/ODDANIE.md zawiera scenariusz 5–7 minut i listę kontrolną. Nagraj publiczną aplikację z paskiem adresu, pokaż F1–F13, telefon 360 px, wydruk i dwa mechanizmy bezpieczeństwa. Pełny cykl: rejestracja → klucz w generatorze → dane → 422 poza zakresem → wyrejestrowanie → 401. MP4 do 100 MB. Minuty checklisty wpisz po nagraniu.")
section("Źródła", "Wymagania i testy: materiały prowadzącego ZAI 26Z, kopie kontraktu/testów w vendor. Dokumentacja: fastapi.tiangolo.com/deployment/docker/; react.dev/reference/react/useEffect; caddyserver.com/docs/caddyfile/directives/reverse_proxy. React i Vite: MIT; ikony Lucide: ISC. Z materiałów AngularJS/GWT nie kopiowano kodu aplikacji. Pełne wersje zależności znajdują się w lockfile.")
section("Deklaracja użycia AI", "Wykorzystano asystenta OpenAI Codex do analizy wymagań, projektowania architektury, generowania i poprawiania implementacji, testów oraz dokumentacji. Zakres pomocy obejmował cały projekt. Autor zgłoszenia odpowiada za zweryfikowanie kodu, bezpieczeństwa i zgodności wymagań oraz powinien umieć wyjaśnić zastosowane rozwiązania.")
section("Odtworzenie tego dokumentu", "uv run python scripts/documentation.py\nPo wdrożeniu podaj --url i --repo oraz --submission. Wersja dla prowadzącego pobiera hasło z ADMIN_PASSWORD i jest zapisywana poza Git w artifacts/dokumentacja-oddanie.pdf. Wersja robocza w docs/dokumentacja.pdf nie zawiera sekretów. Nie deklarowano nieistniejącego wdrożenia, nagrania ani zdalnego statusu CI.")

assert pdf.page_no() <= 8, f"Dokument przekracza limit: {pdf.page_no()} stron"
output = ROOT / ("artifacts/dokumentacja-oddanie.pdf" if args.submission else "docs/dokumentacja.pdf")
output.parent.mkdir(exist_ok=True)
pdf.output(output)
if args.submission:
    output.chmod(0o600)
print(f"Zapisano {output} ({pdf.page_no()} stron).")
