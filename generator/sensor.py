#!/usr/bin/env python3
"""Autonomous sensor emulator. Python standard library only; no database access."""
import argparse
import json
import math
import os
import random
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone


class ApiError(Exception):
    pass


def request(base, path, *, method="GET", body=None, token=None, key=None):
    headers = {"Accept": "application/json"}
    if body is not None:
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = "Bearer " + token
    if key:
        headers["X-API-Key"] = key
    req = urllib.request.Request(base.rstrip("/") + "/api" + path,
                                 data=json.dumps(body, allow_nan=False).encode() if body is not None else None,
                                 headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            raw = response.read()
            return json.loads(raw) if raw else None
    except urllib.error.HTTPError as exc:
        try:
            detail = json.loads(exc.read()).get("detail", exc.reason)
        except (ValueError, AttributeError):
            detail = exc.reason
        raise ApiError(f"HTTP {exc.code}: {detail}") from None
    except (urllib.error.URLError, TimeoutError) as exc:
        raise ApiError("Brak połączenia z API; sprawdź adres i dostępność serwera.") from exc


def generate(base, key, *, count=60, interval=5, mode="sinusoid", minimum=18, maximum=26,
             value=21, historical=False, start=None, step=1200, phase=0, seed=None):
    rng = random.Random(seed)
    if historical and start is None:
        start = datetime.now(timezone.utc) - timedelta(seconds=max(0, count - 1) * step)
    accepted = rejected = 0
    try:
        i = 0
        while count == 0 or i < count:
            if mode == "constant":
                result = value
            elif mode == "random":
                result = rng.uniform(minimum, maximum)
            else:
                # Full daily curve for historical data, continuous waveform for live data.
                result = (minimum + maximum) / 2 + (maximum - minimum) / 2 * math.sin(i * 2 * math.pi / 72 + phase)
            stamp = start + timedelta(seconds=i * step) if historical else datetime.now(timezone.utc)
            body = {"value": round(result, 3), "timestamp": stamp.isoformat()}
            try:
                saved = request(base, "/measurements", method="POST", body=body, key=key)
                accepted += 1
                print(f"OK  {saved['timestamp']}  {saved['value']}", flush=True)
            except ApiError as exc:
                rejected += 1
                print(f"ODRZUCONO  {body['timestamp']}  {body['value']} — {exc}", file=sys.stderr, flush=True)
                # Revoked/invalid keys cannot recover autonomously; stop instead of retrying indefinitely.
                if "HTTP 401:" in str(exc):
                    break
            i += 1
            if not historical and (count == 0 or i < count):
                time.sleep(interval)
    except KeyboardInterrupt:
        print("\nZatrzymano generator.", file=sys.stderr)
    print(f"Przyjęto: {accepted}; odrzucono: {rejected}.", flush=True)
    return 1 if rejected else 0


def main():
    p = argparse.ArgumentParser(description="Splot — emulator czujnika. Wysyła pomiary wyłącznie przez HTTP API.")
    p.add_argument("--api", default=os.getenv("SPLOT_API_URL", "http://127.0.0.1:8000"), help="Adres bazowy, bez /api")
    p.add_argument("--key", default=os.getenv("SPLOT_API_KEY"), help="Klucz czujnika (alternatywnie SPLOT_API_KEY)")
    p.add_argument("--count", type=int, default=60, help="Liczba wyników; 0 = bez końca w trybie bieżącym")
    p.add_argument("--interval", type=float, default=5, help="Odstęp wysyłania w sekundach")
    p.add_argument("--mode", choices=["sinusoid", "random", "constant"], default="sinusoid")
    p.add_argument("--min", dest="minimum", type=float, default=18)
    p.add_argument("--max", dest="maximum", type=float, default=26)
    p.add_argument("--value", type=float, default=21, help="Wartość dla trybu constant")
    p.add_argument("--historical", action="store_true", help="Wyślij wyniki z przeszłości bez czekania")
    p.add_argument("--start", help="Początek historii, ISO 8601 ze strefą; domyślnie historia kończy się teraz")
    p.add_argument("--step", type=float, default=1200, help="Odstęp czasu pomiarów historycznych w sekundach")
    p.add_argument("--phase", type=float, default=0, help="Przesunięcie sinusoidy w radianach")
    p.add_argument("--seed", type=int, help="Opcjonalne ziarno losowości")
    o = vars(p.parse_args())
    if not o["key"]:
        p.error("Podaj --key lub zmienną SPLOT_API_KEY.")
    if not o["api"].startswith(("http://", "https://")):
        p.error("Adres API musi zaczynać się od http:// lub https://.")
    if o["count"] < 0 or (o["historical"] and o["count"] == 0):
        p.error("Tryb historyczny wymaga dodatniej liczby wyników.")
    if not all(math.isfinite(o[k]) for k in ("minimum", "maximum", "interval", "step", "phase", "value")) or o["minimum"] >= o["maximum"] or o["step"] <= 0 or o["interval"] <= 0:
        p.error("Wymagane skończone liczby, min < max oraz dodatnie interval i step.")
    if o["start"]:
        try:
            o["start"] = datetime.fromisoformat(o["start"].replace("Z", "+00:00"))
            if o["start"].tzinfo is None or not o["historical"]:
                raise ValueError()
        except ValueError:
            p.error("--start wymaga --historical i czasu ISO 8601 ze strefą.")
    return generate(o.pop("api"), o.pop("key"), **o)


if __name__ == "__main__":
    sys.exit(main())
