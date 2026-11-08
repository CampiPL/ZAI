import concurrent.futures
import hashlib
import os
import time
import uuid
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import psycopg
from psycopg import sql

import pytest
from fastapi.testclient import TestClient

from backend.app import create_app
from backend.db import connect

PASSWORD = "Testing-secret-2026"


@pytest.fixture
def client(tmp_path):
    database = os.getenv("TEST_DATABASE_URL")
    schema = "test_" + uuid.uuid4().hex
    if database:
        with psycopg.connect(database, autocommit=True) as conn:
            conn.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
        url = urlsplit(database)
        query = dict(parse_qsl(url.query)) | {"options": "-csearch_path=" + schema}
        path = urlunsplit(url._replace(query=urlencode(query)))
    else:
        path = tmp_path / "test.sqlite3"
    try:
        with TestClient(create_app(path, "admin", PASSWORD)) as c:
            yield c
    finally:
        if database:
            with psycopg.connect(database, autocommit=True) as conn:
                conn.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema)))


def login(client, password=PASSWORD):
    return client.post("/api/auth/login", json={"username": "admin", "password": password})


def token(client):
    return {"Authorization": "Bearer " + login(client).json()["accessToken"]}


def setup_sensor(client, low=0, high=100):
    auth = token(client)
    series = client.post("/api/series", headers=auth, json={"name": "Test", "minValue": low, "maxValue": high, "color": "#123456"}).json()
    sensor = client.post("/api/sensors", headers=auth, json={"name": "Sensor", "seriesId": series["id"]}).json()
    return auth, series, sensor, {"X-API-Key": sensor["apiKey"]}


def test_password_change_revokes_all_sessions_and_persists(client):
    first, second = token(client), token(client)
    assert client.put("/api/auth/password", headers=first, json={"currentPassword": PASSWORD, "newPassword": "short"}).status_code == 422
    assert client.put("/api/auth/password", headers=first, json={"currentPassword": PASSWORD, "newPassword": "New-secret-2026"}).status_code == 204
    assert login(client).status_code == 401
    assert login(client, "New-secret-2026").status_code == 200
    for auth in [first, second]:
        assert client.get("/api/sensors", headers=auth).status_code == 401
    # Startup must not overwrite a password changed through the API.
    app = create_app(client.app.state.database_path, "admin", PASSWORD)
    with TestClient(app) as reopened:
        assert login(reopened).status_code == 401
        assert login(reopened, "New-secret-2026").status_code == 200


def test_secrets_are_hashed_and_expired_token_rejected(client):
    auth, _, sensor, _ = setup_sensor(client)
    with connect(client.app.state.database_path, write=True) as conn:
        assert conn.execute("SELECT password_hash FROM admins").fetchone()["password_hash"].startswith("$argon2id$")
        assert conn.execute("SELECT key_hash FROM sensors").fetchone()["key_hash"] == hashlib.sha256(sensor["apiKey"].encode()).hexdigest()
        stored = conn.execute("SELECT token_hash FROM sessions").fetchone()["token_hash"]
        assert stored != auth["Authorization"].split()[1]
        conn.execute("UPDATE sessions SET expires_at=?", (time.time() - 1,))
    assert client.get("/api/sensors", headers=auth).status_code == 401


def test_revocation_preserves_measurements_and_series_delete_cascades(client):
    auth, s, sensor, key = setup_sensor(client)
    m = client.post("/api/measurements", headers=key, json={"value": 7}).json()
    assert client.delete(f"/api/sensors/{sensor['id']}", headers=auth).status_code == 204
    assert client.post("/api/measurements", headers=key, json={"value": 8}).status_code == 401
    assert client.get(f"/api/measurements/{m['id']}").json()["value"] == 7
    assert "sensorId" not in client.get(f"/api/measurements/{m['id']}").json()
    assert client.delete(f"/api/series/{s['id']}", headers=auth).status_code == 204
    assert client.get(f"/api/measurements/{m['id']}").status_code == 404


@pytest.mark.parametrize("query", ["limit=0", "limit=10001", "limit=1.5", "sort=name", "from=yesterday", "from=2026-01-01T00:00:00", "from=2026-02-01T00:00:00Z&to=2026-01-01T00:00:00Z", "series=", "series=1,,2"])
def test_bad_filters(client, query):
    r = client.get("/api/measurements?" + query)
    assert r.status_code == 400
    assert r.headers["content-type"] == "application/problem+json"


def test_timezones_duplicates_limit_and_persistence(client):
    _, s, _, key = setup_sensor(client)
    for stamp in ["2026-01-01T12:00:00+01:00", "2026-01-01T11:00:00Z", "2026-01-01T12:00:00Z"]:
        assert client.post("/api/measurements", headers=key, json={"value": 5, "timestamp": stamp}).status_code == 201
    r = client.get("/api/measurements?from=2026-01-01T11:00:00Z&to=2026-01-01T11:00:00Z").json()
    assert len(r) == 2
    assert r[0]["timestamp"] == r[1]["timestamp"]
    assert r[0]["id"] != r[1]["id"]
    limited = client.get("/api/measurements?limit=1&sort=-timestamp").json()
    assert len(limited) == 1 and limited[0]["timestamp"].startswith("2026-01-01T12")
    with TestClient(create_app(client.app.state.database_path, "admin", PASSWORD)) as reopened:
        assert len(reopened.get(f"/api/measurements?series={s['id']}").json()) == 3


@pytest.mark.parametrize("value", [True, "1", None, [], {}])
def test_strict_numeric_values(client, value):
    _, _, _, key = setup_sensor(client)
    assert client.post("/api/measurements", headers=key, json={"value": value}).status_code == 422


def test_future_and_boundary_values(client):
    _, _, _, key = setup_sensor(client, -1, 1)
    for value in (-1, 1):
        assert client.post("/api/measurements", headers=key, json={"value": value}).status_code == 201
    for seconds, status in [(290, 201), (310, 422)]:
        stamp = (datetime.now(timezone.utc) + timedelta(seconds=seconds)).isoformat()
        assert client.post("/api/measurements", headers=key, json={"value": 0, "timestamp": stamp}).status_code == status


def test_conflicting_range_update_is_atomic(client):
    auth, s, _, key = setup_sensor(client)
    def insert():
        return client.post("/api/measurements", headers=key, json={"value": 90}).status_code
    def narrow():
        return client.put(f"/api/series/{s['id']}", headers=auth, json={"name": "Narrow", "minValue": 0, "maxValue": 10, "color": "#123456"}).status_code
    with concurrent.futures.ThreadPoolExecutor() as pool:
        a, b = pool.submit(insert), pool.submit(narrow)
        assert (a.result(), b.result()) in [(201, 409), (422, 200)]
    bounds = client.get(f"/api/series/{s['id']}").json()
    for m in client.get("/api/measurements").json():
        assert bounds["minValue"] <= m["value"] <= bounds["maxValue"]


def test_protocol_errors_and_no_mutation(client):
    auth, _, _, key = setup_sensor(client)
    assert client.get("/api/series", headers={"Accept": "application/xml"}).status_code == 406
    assert client.get("/api/series", headers={"Accept": "application/json;q=0, */*;q=1"}).status_code == 406
    assert client.get("/api/series", headers={"Accept": "application/*"}).status_code == 200
    assert client.post("/api/measurements", headers=key | {"Content-Type": "text/plain"}, content='{"value":1}').status_code == 415
    assert client.post("/api/series", headers=auth | {"Content-Type": "application/json"}, content='{"name":').status_code == 400
    assert client.post("/api/series", headers=auth | {"Content-Type": "application/json"}, content='x' * 66000).status_code == 413
    m = client.post("/api/measurements", headers=key, json={"value": 5}).json()
    for method in ("PUT", "PATCH", "DELETE"):
        assert client.request(method, f"/api/measurements/{m['id']}", headers=auth).status_code in (404, 405)
    assert client.get(f"/api/measurements/{m['id']}").json()["value"] == 5


def test_login_rate_limit(client):
    for _ in range(20):
        assert login(client, "incorrect").status_code == 401
    assert login(client, "incorrect").status_code == 429


def test_unknown_resource_and_sensor_validation(client):
    auth = token(client)
    assert client.post("/api/sensors", headers=auth, json={"name": "S", "seriesId": 999999}).status_code == 422
    assert client.get("/api/does-not-exist").status_code == 404
    response = client.get('/api/series/1%27%20OR%201=1')
    assert response.status_code == 404
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.json()["status"] == 404


@pytest.mark.parametrize("identifier", ["abc", "999999999999999999999999999999999", "-1"])
def test_non_numeric_or_out_of_range_ids(client, identifier):
    auth = token(client)
    for resource in ("series", "sensors", "measurements"):
        assert client.get(f"/api/{resource}/{identifier}", headers=auth).status_code == 404
    assert client.post("/api/sensors", headers=auth, json={"name": "S", "seriesId": identifier}).status_code == 422
    assert client.get(f"/api/measurements?series={identifier}").json() == []
