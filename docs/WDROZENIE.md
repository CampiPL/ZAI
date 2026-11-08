# Docker i publiczne uruchomienie

Repozytorium: https://github.com/CampiPL/ZAI, branch `main`. Repozytorium już istnieje — nie zakładaj kolejnego.

Docker buduje obraz zawierający backend, frontend i zależności. Kontener uruchamia ten obraz. Lokalnie trwały wolumen przechowuje SQLite także po wymianie kontenera; bezpłatny hosting korzysta z osobnej bazy PostgreSQL w Neon. Hosting zapewnia działający stale serwer oraz publiczny adres, pod którym prowadzący uruchomi testy.

## 1. Docker na Ubuntu

Do lokalnego uruchomienia wystarczą Docker Engine, Buildx i Compose; Docker Desktop ani konto Docker Hub nie są potrzebne. Skrypt instalacyjny korzysta z oficjalnego repozytorium Docker dla Ubuntu:

```bash
cd ~/Desktop/ZaawansowaneAplikacjeInternetowe/projekt
sudo bash scripts/install-docker-ubuntu.sh "$(id -un)"
```

Hasło systemowe wpisuj wyłącznie w terminalu Ubuntu lub systemowym oknie uwierzytelniania. Po instalacji wyloguj i zaloguj użytkownika, aby terminale odziedziczyły członkostwo w grupie `docker`. Ta grupa ma uprawnienia administracyjne do zarządzania kontenerami.

Sprawdzenie:

```bash
docker version
docker compose version
docker run --rm hello-world
```

W tej instalacji Docker Engine i Compose są już zainstalowane. Jeśli bieżący terminal nie odziedziczył grupy, wyloguj się i zaloguj ponownie; tymczasowo działa `sudo -u "$(id -un)" docker version` (uruchamia Docker jako ten sam użytkownik z odświeżonymi grupami).

## 2. Projekt lokalnie w Dockerze

Nie wymaga instalowania Pythona, Node ani npm do budowania aplikacji na hoście; budowanie odbywa się wewnątrz obrazu. Python systemowy jest używany tylko przez jednorazowy setup `.env`.

```bash
python3 scripts/setup.py
docker compose -f compose.local.yaml up -d --build --wait
docker compose -f compose.local.yaml exec -T app /app/.venv/bin/python -m generator.seed_demo --api http://127.0.0.1:8000
```

Otwórz **http://127.0.0.1:8080**. Login `admin`, hasło z lokalnego `.env`. Ten kontener ma osobną bazę w wolumenie `splot-local_splot_local_data`; nie modyfikuje wcześniejszej bazy lokalnego procesu w `data/splot.sqlite3`.

```bash
# Stan i logi
docker compose -f compose.local.yaml ps
docker compose -f compose.local.yaml logs --tail=50 app

# Restart zachowuje dane
docker compose -f compose.local.yaml restart app

# Zatrzymanie bez usuwania danych
docker compose -f compose.local.yaml down

# Kolejny start
docker compose -f compose.local.yaml up -d --wait
```

Nie dodawaj `-v` do `down`, chyba że świadomie chcesz usunąć bazę. Jeśli port 8080 jest zajęty, ustaw `SPLOT_LOCAL_PORT=8082` w `.env` i uruchom ponownie.

## 3. Bezpłatny hosting: Render Free + Neon Free

`render.yaml` definiuje usługę Docker w planie **Free**, bez płatnego dysku. Dane przechowuje zewnętrzny PostgreSQL na **Neon Free**. Ustawienie `DATABASE_URL` wybiera PostgreSQL; bez niego aplikacja korzysta z SQLite. Model danych i API są wspólne dla obu baz.

Według ofert sprawdzonych 8.11.2026 obie usługi mają plan 0 USD. Wybieraj wyłącznie Free; nie włączaj płatnych rozszerzeń. Render ma limity m.in. 750 godzin bezpłatnych instancji miesięcznie na workspace, transferu i budowania. Neon Free ma limity m.in. 100 CU-h i 1 GB na projekt. Baza Neon nie ma 30-dniowego terminu wygaśnięcia charakterystycznego dla bezpłatnego Render Postgres. Obowiązują aktualne warunki dostawców.

Render usypia aplikację po 15 minutach bez ruchu. Pierwsze wejście może trwać około minuty. Dane w Neon przetrwają restart i ponowne wdrożenie aplikacji. Przed demonstracją/testami otwórz `/api/health` i poczekaj na `{"status":"ok"}`. Nie używaj usług sztucznie utrzymujących aplikację aktywną. Otwarty pulpit SSE i ciągły generator zwiększają zużycie zasobów; zamykaj je po demonstracji.

### A. Baza danych

1. Załóż konto na https://console.neon.tech/ i wybierz plan **Free**.
2. Utwórz projekt `splot-zai`, bazę `splot` (możesz też użyć domyślnej `neondb`) i region Frankfurt, jeśli dostępny.
3. W **Connect** skopiuj connection string PostgreSQL dla tej bazy. Może to być adres pooled; zachowaj parametry SSL z panelu, w tym `sslmode=require`. Wartość zaczyna się od `postgresql://` i zawiera hasło. Nie publikuj jej w Git ani w rozmowie.
4. Nie musisz ręcznie uruchamiać SQL: aplikacja utworzy tabele oraz administratora przy pierwszym starcie.

### B. Aplikacja

1. Załóż konto na https://dashboard.render.com/, np. przez GitHub, i udostępnij Render repozytorium `CampiPL/ZAI`.
2. Po opublikowaniu zmian z `render.yaml` wybierz **New → Blueprint**, to repozytorium i branch `main`.
3. Root Directory pozostaw pusty: zawartość lokalnego `projekt/` jest głównym katalogiem repozytorium. Blueprint to `render.yaml`.
4. Wpisz sekrety: `DATABASE_URL` z Neon oraz własne `ADMIN_PASSWORD` (minimum 12 znaków). Login: `admin`. Zachowaj hasło w menedżerze haseł.
5. Sprawdź, że usługa ma plan **Free**, nie ma dysku ani dodatkowej bazy Render. Uruchom wdrożenie. Jeśli panel wymaga płatnego planu, nie zatwierdzaj go — konfigurację można również przepisać do **New → Web Service → Docker → Free**: repo/branch jak wyżej, Dockerfile `./Dockerfile`, healthcheck `/api/health`, zmienne z `render.yaml`.
6. Render nada adres `https://NAZWA.onrender.com` i certyfikat HTTPS. Domeny, VPS ani Caddy nie trzeba kupować. Sprawdź `/api/health`.
7. Kolejne zmiany wdrażaj przez **Manual Deploy → Deploy latest commit**; automatyczne wdrażanie jest wyłączone w konfiguracji.

Zmiana zmiennej `ADMIN_PASSWORD` po utworzeniu konta nie resetuje hasła istniejącego w bazie. Użyj formularza zmiany hasła w aplikacji. Zmiana `DATABASE_URL` na pustą/inną bazę oznacza inny zestaw danych; nie jest migracją istniejącego SQLite. Lokalne dane demonstracyjne odtwórz generatorem.

### C. Dane i testy

Render Free nie udostępnia Shell/SSH. Uruchom generator **na swoim komputerze**, w katalogu `projekt`, z publicznym adresem. Wpisz hasło administratora utworzonego na hostingu, gdy program o nie poprosi:

```bash
env -u ADMIN_PASSWORD python3 -m generator.seed_demo --api https://NAZWA.onrender.com --user admin --keys-file data/neon-demo-keys.json
```

Generator używa wyłącznie biblioteki standardowej Pythona i publicznego API; nie potrzebuje dostępu do PostgreSQL. Tworzy 3 serie po 72 pomiary. Lokalny `.env` nie jest ładowany przez to polecenie.

Sprawdź logowanie, wykres, zapis i zachowanie danych po **Manual Deploy**. Następnie uruchom pełne E2 z Lighthouse. Wrapper testów ładuje lokalny `.env`, dlatego dane konta hostingu przekaż przez środowisko:

```bash
read -rs -p 'Hasło administratora na hostingu: ' ADMIN_PASSWORD
export ADMIN_PASSWORD
ADMIN_USERNAME=admin uv run python scripts/contract.py --stage E2 --app https://NAZWA.onrender.com --lighthouse
unset ADMIN_PASSWORD
```

Uzupełnij PDF publicznym adresem i danymi wdrożonego konta, nagraj demonstrację i zgłoś projekt w Leia. Nie usuwaj usług do zakończenia oceny.

Do utworzenia usług przez asystenta potrzebne są połączone integracje Render i Neon. Sam plik `render.yaml` nie tworzy kont ani publicznego adresu; logowanie i powiązanie kont wykonuje właściciel.

## 4. Własny VPS jako alternatywa

Pliki `compose.yaml` i `Caddyfile` służą do własnego serwera z domeną. Ustaw `SPLOT_DOMAIN` i dane administratora w `.env`, skieruj DNS na serwer, otwórz porty 80/443 i uruchom `docker compose up -d --build`. Caddy obsłuży certyfikat HTTPS. Ta konfiguracja wymaga własnego VPS/domeny i nie jest potrzebna dla Render.

## Źródła konfiguracji

- Docker Engine na Ubuntu: https://docs.docker.com/engine/install/ubuntu/
- Render Docker: https://render.com/docs/docker
- Blueprint: https://render.com/docs/blueprint-spec
- Render Free i ograniczenia: https://render.com/docs/free
- Neon Free: https://neon.com/pricing
- Połączenie PostgreSQL: https://neon.com/docs/connect/connect-from-any-app

Samo przygotowanie plików nie tworzy usługi. Publiczny adres i testy wdrożenia można potwierdzić dopiero po uruchomieniu usługi na koncie użytkownika.
