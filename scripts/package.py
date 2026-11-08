#!/usr/bin/env python3
"""Build a source submission ZIP without secrets, dependencies or runtime data."""
import argparse
from pathlib import Path
import zipfile

root = Path(__file__).resolve().parent.parent
p = argparse.ArgumentParser()
p.add_argument("--documentation", type=Path, help="Opcjonalny prywatny PDF do oddania")
o = p.parse_args()
allowed_dirs = {"backend", "frontend", "generator", "scripts", "tests", "docs", "vendor", ".github"}
allowed_files = {"README.md", "pyproject.toml", "uv.lock", ".python-version", ".env.example", ".gitignore", ".dockerignore", "Dockerfile", "compose.yaml", "Caddyfile"}
excluded = {"node_modules", "dist", "__pycache__", ".pytest_cache", "test-results", "playwright-report"}
output = root / "artifacts/splot-zai-26z.zip"
output.parent.mkdir(exist_ok=True)
if o.documentation and not o.documentation.is_file():
    p.error("Nie znaleziono wskazanego PDF.")
with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as z:
    for file in sorted(root.rglob("*")):
        relative = file.relative_to(root)
        if any(part in excluded for part in relative.parts) or not file.is_file():
            continue
        if relative.parts[0] not in allowed_dirs and str(relative) not in allowed_files:
            continue
        if file.name.startswith(".env") and file.name != ".env.example":
            continue
        source = o.documentation if relative.as_posix() == "docs/dokumentacja.pdf" and o.documentation else file
        z.write(source, "splot/" + relative.as_posix())
with zipfile.ZipFile(output) as z:
    assert z.testzip() is None
    assert "splot/docs/dokumentacja.pdf" in z.namelist(), "Najpierw wygeneruj dokumentację PDF."
    assert not any("/data/" in n or n.endswith("/.env") for n in z.namelist())
    print(f"Gotowe: {output} ({len(z.namelist())} plików, {output.stat().st_size} bajtów).")
