#!/usr/bin/env python3
"""Create local credentials once; never overwrite an existing .env."""
import os
import secrets
from pathlib import Path

root = Path(__file__).resolve().parent.parent
env = root / ".env"
if env.exists():
    print("Plik .env już istnieje; pozostawiono bez zmian.")
else:
    password = secrets.token_urlsafe(18)
    fd = os.open(env, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as out:
        out.write(f"ADMIN_USERNAME=admin\nADMIN_PASSWORD={password}\nDATABASE_PATH=data/splot.sqlite3\nSESSION_TTL_SECONDS=3600\nREQUIRE_HTTPS=false\nPORT=8000\n")
    print("Utworzono .env z losowym hasłem lokalnego administratora (uprawnienia 0600).")
print("Następnie: uv sync --locked; cd frontend && npm ci && npm run build")
print("Uruchomienie z katalogu projekt: uv run python scripts/serve.py")
