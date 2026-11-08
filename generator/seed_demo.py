#!/usr/bin/env python3
"""Create demonstration series/sensors and measurements via the same public API."""
import argparse
import getpass
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .sensor import ApiError, generate, request

DEMO = [
    ("Szklarnia", "#34765a", "circle", 20, 27, 0.4),
    ("Ogród zimowy", "#b17b32", "diamond", 17, 23, 1.2),
    ("Taras", "#638aa4", "square", 13, 20, 2.0),
]


def main():
    p = argparse.ArgumentParser(description="Utwórz 3 serie po 72 pomiary, korzystając wyłącznie z API.")
    p.add_argument("--api", default=os.getenv("SPLOT_API_URL", "http://127.0.0.1:8000"))
    p.add_argument("--user", default=os.getenv("ADMIN_USERNAME", "admin"))
    p.add_argument("--keys-file", default="data/demo-keys.json", help="Lokalny plik kluczy, uprawnienia 0600, poza Git")
    o = p.parse_args()
    password = os.getenv("ADMIN_PASSWORD") or getpass.getpass("Hasło administratora: ")
    token = request(o.api, "/auth/login", method="POST", body={"username": o.user, "password": password})["accessToken"]
    keypath = Path(o.keys_file)
    keys = json.loads(keypath.read_text()) if keypath.exists() else {}
    start = datetime.now(timezone.utc) - timedelta(seconds=71 * 1200)
    try:
        existing = request(o.api, "/series")
        for name, color, icon, low, high, phase in DEMO:
            series = next((s for s in existing if s["name"] == name), None)
            if series:
                count = len(request(o.api, f"/measurements?series={series['id']}&limit=10000"))
                if count >= 15:
                    print(f"Pomijam {name}: zawiera już {count} pomiarów.")
                    continue
            else:
                series = request(o.api, "/series", method="POST", token=token,
                                 body={"name": name, "minValue": -30, "maxValue": 60, "color": color, "icon": icon, "unit": "°C"})
            sensor = request(o.api, "/sensors", method="POST", token=token,
                             body={"name": f"{name} · termometr", "seriesId": series["id"]})
            keys[name] = {"sensorId": sensor["id"], "apiKey": sensor["apiKey"], "api": o.api}
            keypath.parent.mkdir(parents=True, exist_ok=True)
            fd = os.open(keypath, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
            os.chmod(keypath, 0o600)
            with os.fdopen(fd, "w") as file:
                json.dump(keys, file, ensure_ascii=False, indent=2)
            status = generate(o.api, sensor["apiKey"], count=72, historical=True, start=start,
                              step=1200, minimum=low, maximum=high, phase=phase)
            if status:
                raise ApiError(f"Nie udało się wprowadzić wszystkich danych serii {name}.")
        print(f"Dane gotowe. Klucze czujników zapisano lokalnie: {keypath} (nie dołączaj do zgłoszenia).")
    finally:
        request(o.api, "/auth/logout", method="POST", token=token)


if __name__ == "__main__":
    try:
        main()
    except (ApiError, OSError, ValueError) as exc:
        print(f"Błąd inicjalizacji: {exc}", file=sys.stderr)
        sys.exit(1)
