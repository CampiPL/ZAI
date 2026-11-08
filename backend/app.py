import asyncio
import hashlib
import json
import logging
import os
import secrets
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

from argon2.exceptions import VerificationError
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException

from .db import HASHER, changed, connect, initialize
from .models import Login, MeasurementInput, PasswordChange, SensorInput, SeriesInput, now_iso, timestamp

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")
logger = logging.getLogger("splot")
DUMMY_HASH = HASHER.hash("dummy-password-for-constant-work")


class Problem(Exception):
    def __init__(self, status, detail):
        self.status, self.detail = status, detail


TITLES = {400: "Niepoprawne żądanie", 401: "Wymagane uwierzytelnienie", 403: "Brak uprawnień",
          404: "Nie znaleziono", 405: "Niedozwolona metoda", 406: "Nieobsługiwany format odpowiedzi",
          409: "Konflikt danych", 413: "Zbyt duże żądanie", 415: "Nieobsługiwany format danych",
          422: "Błąd walidacji", 429: "Zbyt wiele prób", 500: "Błąd serwera"}


def problem_response(status, detail, path, errors=None):
    body = {"type": "about:blank", "title": TITLES.get(status, "Błąd"), "status": status,
            "detail": detail, "instance": path}
    if errors:
        body["errors"] = errors
    return JSONResponse(body, status_code=status, media_type="application/problem+json")


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def series_json(row):
    return {"id": row["id"], "name": row["name"], "minValue": row["min_value"],
            "maxValue": row["max_value"], "color": row["color"], "icon": row["icon"], "unit": row["unit"]}


def sensor_json(row):
    return {"id": row["id"], "name": row["name"], "seriesId": row["series_id"],
            "createdAt": row["created_at"], "lastMeasurementAt": row["last_measurement_at"]}


def measurement_json(row):
    result = {"id": row["id"], "seriesId": row["series_id"], "value": row["value"], "timestamp": row["timestamp"]}
    if row["sensor_id"] is not None:
        result["sensorId"] = row["sensor_id"]
    return result


def get_row(conn, table, identifier):
    # Table names are internal constants, never client input.
    row = conn.execute(f"SELECT * FROM {table} WHERE id = ?", (identifier,)).fetchone()
    if row is None:
        raise Problem(404, "Wybrany zasób nie istnieje.")
    return row


def admin(request, conn):
    scheme, _, token = request.headers.get("authorization", "").partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise Problem(401, "Zaloguj się jako administrator.")
    row = conn.execute("SELECT admin_id, token_hash FROM sessions WHERE token_hash = ? AND expires_at > ?",
                       (digest(token), time.time())).fetchone()
    if row is None:
        raise Problem(401, "Sesja wygasła lub została zakończona. Zaloguj się ponownie.")
    return row


def accept_json(header):
    matches = []
    for item in header.split(","):
        media, *params = item.lower().strip().split(";")
        quality = 1.0
        for param in params:
            if param.strip().startswith("q="):
                try:
                    quality = float(param.strip()[2:])
                except ValueError:
                    quality = 0
        if media in ("application/json", "application/*", "*/*"):
            matches.append(({"application/json": 2, "application/*": 1, "*/*": 0}[media], quality))
    return bool(matches) and max(matches)[1] > 0


def create_app(database_path=None, initial_username=None, initial_password=None):
    dbpath = str(database_path or os.getenv("DATABASE_PATH", ROOT / "data/splot.sqlite3"))
    username = initial_username if initial_username is not None else os.getenv("ADMIN_USERNAME", "admin")
    password = initial_password if initial_password is not None else os.getenv("ADMIN_PASSWORD", "")
    ttl = int(os.getenv("SESSION_TTL_SECONDS", "3600"))
    if ttl < 60:
        raise ValueError("SESSION_TTL_SECONDS musi wynosić co najmniej 60.")

    @asynccontextmanager
    async def lifespan(app):
        initialize(dbpath, username, password)
        yield

    app = FastAPI(title="Splot API", lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
    app.state.database_path = dbpath

    @app.exception_handler(Problem)
    async def problem_handler(request, exc):
        if request.url.path == "/api/measurements" and request.method == "POST":
            logger.warning("measurement_rejected status=%s reason=%s", exc.status, exc.detail)
        return problem_response(exc.status, exc.detail, request.url.path)

    @app.exception_handler(RequestValidationError)
    async def validation_handler(request, exc):
        errors = [{"field": ".".join(str(x) for x in e["loc"][1:]), "message": e["msg"]} for e in exc.errors()]
        status = 400 if any(e["type"] == "json_invalid" for e in exc.errors()) else 422
        if request.url.path == "/api/measurements":
            logger.warning("measurement_rejected status=%s validation_error", status)
        return problem_response(status, "Sprawdź przesłane pola.", request.url.path, errors)

    @app.exception_handler(HTTPException)
    async def http_handler(request, exc):
        return problem_response(exc.status_code, TITLES.get(exc.status_code, "Błąd żądania"), request.url.path)

    @app.middleware("http")
    async def protocol(request, call_next):
        try:
            if os.getenv("REQUIRE_HTTPS", "false").lower() == "true" and request.url.scheme != "https":
                response = Response(status_code=308, headers={"Location": str(request.url.replace(scheme="https"))})
            elif request.url.path.startswith("/api/") and request.url.path != "/api/events" and not accept_json(request.headers.get("accept", "*/*")):
                response = problem_response(406, "API udostępnia application/json.", request.url.path)
            else:
                response = None
                if request.url.path.startswith("/api/") and request.method in ("POST", "PUT", "PATCH"):
                    # Read a bounded body, including chunked requests, before Pydantic parsing.
                    body = bytearray()
                    async for chunk in request.stream():
                        body.extend(chunk)
                        if len(body) > 65536:
                            response = problem_response(413, "Maksymalny rozmiar żądania: 64 KB.", request.url.path)
                            break
                    if response is None:
                        request._body = bytes(body)
                        if body and request.headers.get("content-type", "").split(";")[0].lower() != "application/json":
                            response = problem_response(415, "Wyślij treść jako application/json.", request.url.path)
                if response is None:
                    response = await call_next(request)
        except Exception:
            logger.exception("request_failed path=%s", request.url.path)
            response = problem_response(500, "Nie udało się wykonać operacji. Spróbuj ponownie.", request.url.path)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; "
            "connect-src 'self'; font-src 'self'; object-src 'none'; base-uri 'self'; "
            "frame-ancestors 'none'; form-action 'self'"
        )
        if request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = "max-age=31536000"
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        return response

    @app.get("/api/health")
    def health():
        with connect(dbpath) as conn:
            conn.execute("SELECT 1 FROM schema_migrations LIMIT 1").fetchone()
        return {"status": "ok"}

    @app.post("/api/auth/login")
    def login(body: Login, request: Request):
        bucket = digest((request.client.host if request.client else "local") + ":" + body.username)
        with connect(dbpath, write=True) as conn:
            now = time.time()
            conn.execute("DELETE FROM login_attempts WHERE attempted_at < ?", (now - 300,))
            count = conn.execute("SELECT COUNT(*) FROM login_attempts WHERE bucket = ?", (bucket,)).fetchone()[0]
            if count >= 20:
                raise Problem(429, "Zbyt wiele błędnych prób. Spróbuj za 5 minut.")
            account = conn.execute("SELECT * FROM admins WHERE username = ?", (body.username,)).fetchone()
            try:
                HASHER.verify(account["password_hash"] if account else DUMMY_HASH, body.password)
                valid = account is not None
            except VerificationError:
                valid = False
            if not valid:
                conn.execute("INSERT INTO login_attempts VALUES (?, ?)", (bucket, now))
                # Return, instead of raising, to commit the rate-limit counter.
                return problem_response(401, "Nieprawidłowy login lub hasło.", request.url.path)
            conn.execute("DELETE FROM login_attempts WHERE bucket = ?", (bucket,))
            conn.execute("DELETE FROM sessions WHERE expires_at <= ?", (now,))
            token = secrets.token_urlsafe(32)
            conn.execute("INSERT INTO sessions VALUES (?, ?, ?)", (digest(token), account["id"], now + ttl))
            return {"accessToken": token, "tokenType": "Bearer", "expiresIn": ttl}

    @app.post("/api/auth/logout", status_code=204)
    def logout(request: Request):
        with connect(dbpath, write=True) as conn:
            session = admin(request, conn)
            conn.execute("DELETE FROM sessions WHERE token_hash = ?", (session["token_hash"],))
        return Response(status_code=204)

    @app.put("/api/auth/password", status_code=204)
    def change_password(body: PasswordChange, request: Request):
        with connect(dbpath, write=True) as conn:
            session = admin(request, conn)
            account = get_row(conn, "admins", session["admin_id"])
            try:
                HASHER.verify(account["password_hash"], body.currentPassword)
            except VerificationError:
                raise Problem(403, "Bieżące hasło jest niepoprawne.")
            conn.execute("UPDATE admins SET password_hash = ? WHERE id = ?", (HASHER.hash(body.newPassword), account["id"]))
            conn.execute("DELETE FROM sessions WHERE admin_id = ?", (account["id"],))
        return Response(status_code=204)

    @app.get("/api/series")
    def list_series():
        with connect(dbpath) as conn:
            return [series_json(r) for r in conn.execute("SELECT * FROM series ORDER BY id")]

    @app.get("/api/series/{series_id}")
    def read_series(series_id: str):
        with connect(dbpath) as conn:
            return series_json(get_row(conn, "series", series_id))

    @app.post("/api/series", status_code=201)
    def add_series(body: SeriesInput, request: Request):
        with connect(dbpath, write=True) as conn:
            admin(request, conn)
            rowid = conn.execute("INSERT INTO series(name,min_value,max_value,color,icon,unit) VALUES (?,?,?,?,?,?)",
                                 (body.name, body.minValue, body.maxValue, body.color, body.icon, body.unit)).lastrowid
            result = series_json(get_row(conn, "series", rowid))
            changed(conn)
        return JSONResponse(result, status_code=201, headers={"Location": f"/api/series/{rowid}"})

    @app.put("/api/series/{series_id}")
    def update_series(series_id: str, body: SeriesInput, request: Request):
        with connect(dbpath, write=True) as conn:
            admin(request, conn)
            get_row(conn, "series", series_id)
            conflict = conn.execute("SELECT 1 FROM measurements WHERE series_id=? AND (value < ? OR value > ?) LIMIT 1",
                                    (series_id, body.minValue, body.maxValue)).fetchone()
            if conflict:
                raise Problem(409, "Nowy zakres wyklucza istniejące pomiary. Poszerz zakres.")
            conn.execute("UPDATE series SET name=?,min_value=?,max_value=?,color=?,icon=?,unit=? WHERE id=?",
                         (body.name, body.minValue, body.maxValue, body.color, body.icon, body.unit, series_id))
            changed(conn)
            return series_json(get_row(conn, "series", series_id))

    @app.delete("/api/series/{series_id}", status_code=204)
    def remove_series(series_id: str, request: Request):
        with connect(dbpath, write=True) as conn:
            admin(request, conn)
            get_row(conn, "series", series_id)
            conn.execute("DELETE FROM series WHERE id=?", (series_id,))
            changed(conn)
        return Response(status_code=204)

    @app.get("/api/sensors")
    def list_sensors(request: Request):
        with connect(dbpath) as conn:
            admin(request, conn)
            return [sensor_json(r) for r in conn.execute("SELECT * FROM sensors ORDER BY id")]

    @app.get("/api/sensors/{sensor_id}")
    def read_sensor(sensor_id: str, request: Request):
        with connect(dbpath) as conn:
            admin(request, conn)
            return sensor_json(get_row(conn, "sensors", sensor_id))

    @app.post("/api/sensors", status_code=201)
    def add_sensor(body: SensorInput, request: Request):
        with connect(dbpath, write=True) as conn:
            admin(request, conn)
            if not conn.execute("SELECT 1 FROM series WHERE id=?", (body.seriesId,)).fetchone():
                raise Problem(422, "Wybrana seria nie istnieje.")
            key = secrets.token_urlsafe(32)
            rowid = conn.execute("INSERT INTO sensors(name,series_id,key_hash,created_at) VALUES (?,?,?,?)",
                                 (body.name, body.seriesId, digest(key), now_iso())).lastrowid
            result = sensor_json(get_row(conn, "sensors", rowid)) | {"apiKey": key}
            changed(conn)
        return JSONResponse(result, status_code=201, headers={"Location": f"/api/sensors/{rowid}"})

    @app.delete("/api/sensors/{sensor_id}", status_code=204)
    def remove_sensor(sensor_id: str, request: Request):
        with connect(dbpath, write=True) as conn:
            admin(request, conn)
            get_row(conn, "sensors", sensor_id)
            conn.execute("DELETE FROM sensors WHERE id=?", (sensor_id,))
            changed(conn)
        return Response(status_code=204)

    @app.post("/api/measurements", status_code=201)
    def add_measurement(body: MeasurementInput, request: Request):
        key = request.headers.get("x-api-key", "")
        with connect(dbpath, write=True) as conn:
            sensor = conn.execute("SELECT * FROM sensors WHERE key_hash=?", (digest(key),)).fetchone() if key else None
            if sensor is None:
                raise Problem(401, "Brak ważnego klucza czujnika X-API-Key.")
            series = get_row(conn, "series", sensor["series_id"])
            if not series["min_value"] <= body.value <= series["max_value"]:
                raise Problem(422, f"Wartość musi należeć do przedziału [{series['min_value']}, {series['max_value']}].")
            if datetime.fromisoformat(body.timestamp.replace("Z", "+00:00")).timestamp() > time.time() + 300:
                raise Problem(422, "Pomiar nie może pochodzić z przyszłości dalszej niż 5 minut.")
            rowid = conn.execute("INSERT INTO measurements(series_id,sensor_id,value,timestamp) VALUES (?,?,?,?)",
                                 (sensor["series_id"], sensor["id"], body.value, body.timestamp)).lastrowid
            conn.execute("UPDATE sensors SET last_measurement_at = CASE WHEN last_measurement_at IS NULL OR last_measurement_at < ? THEN ? ELSE last_measurement_at END WHERE id=?",
                         (body.timestamp, body.timestamp, sensor["id"]))
            changed(conn)
            result = measurement_json(get_row(conn, "measurements", rowid))
        return JSONResponse(result, status_code=201, headers={"Location": f"/api/measurements/{rowid}"})

    @app.get("/api/measurements")
    def list_measurements(request: Request):
        q = request.query_params
        clauses, params = [], []
        try:
            limit = int(q.get("limit", "1000"))
            if not 1 <= limit <= 10000 or q.get("sort", "timestamp") not in ("timestamp", "-timestamp"):
                raise ValueError()
            start = timestamp(q["from"]) if "from" in q else None
            end = timestamp(q["to"]) if "to" in q else None
            if start and end and start > end:
                raise ValueError()
            if "series" in q:
                ids = q["series"].split(",")
                if len(ids) > 100 or any(not x.strip() for x in ids):
                    raise ValueError()
                clauses.append("series_id IN (" + ",".join("?" for _ in ids) + ")")
                params.extend(ids)
            for column, operator, value in [("timestamp", ">=", start), ("timestamp", "<=", end)]:
                if value:
                    clauses.append(f"{column} {operator} ?")
                    params.append(value)
        except (ValueError, OverflowError):
            raise Problem(400, "Niepoprawne filtry: sprawdź daty, kolejność czasu, serie, sort i limit (1–10000).")
        direction = "DESC" if q.get("sort") == "-timestamp" else "ASC"
        sql = "SELECT * FROM measurements" + (" WHERE " + " AND ".join(clauses) if clauses else "")
        sql += f" ORDER BY timestamp {direction}, id {direction} LIMIT ?"
        with connect(dbpath) as conn:
            return [measurement_json(r) for r in conn.execute(sql, [*params, limit])]

    @app.get("/api/measurements/{measurement_id}")
    def read_measurement(measurement_id: str):
        with connect(dbpath) as conn:
            return measurement_json(get_row(conn, "measurements", measurement_id))

    @app.get("/api/events")
    async def events(request: Request):
        async def stream():
            revision = None
            heartbeat = 0
            while not await request.is_disconnected():
                with connect(dbpath) as conn:
                    current = conn.execute("SELECT revision FROM changes WHERE id=1").fetchone()[0]
                if current != revision:
                    yield f"event: update\ndata: {json.dumps({'revision': current})}\n\n"
                    revision = current
                elif heartbeat % 15 == 0:
                    yield ": heartbeat\n\n"
                heartbeat += 1
                await asyncio.sleep(1)
        return StreamingResponse(stream(), media_type="text/event-stream", headers={"X-Accel-Buffering": "no"})

    @app.get("/api/{unknown:path}")
    def unknown_api(unknown: str):
        raise Problem(404, "Endpoint nie istnieje.")

    dist = ROOT / "frontend/dist"
    if (dist / "assets").is_dir():
        app.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")

    @app.get("/favicon.svg")
    def favicon():
        return FileResponse(ROOT / "frontend/public/favicon.svg")

    @app.get("/")
    def frontend():
        if not (dist / "index.html").exists():
            return Response("Zbuduj frontend: cd frontend && npm ci && npm run build", status_code=503)
        return FileResponse(dist / "index.html", headers={"Cache-Control": "no-cache"})

    return app


app = create_app()
