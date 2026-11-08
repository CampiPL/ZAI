#!/usr/bin/env python3
"""Run the unchanged course tests and propagate failures to CI."""
import argparse
import os
from pathlib import Path
import subprocess
import sys

from dotenv import load_dotenv

root = Path(__file__).resolve().parent.parent
load_dotenv(root / ".env")
p = argparse.ArgumentParser()
p.add_argument("--app", default="http://127.0.0.1:8000")
p.add_argument("--api")
p.add_argument("--stage", choices=["E1", "E2"], default="E1")
p.add_argument("--lighthouse", action="store_true")
o = p.parse_args()
if not os.getenv("ADMIN_PASSWORD"):
    p.error("Ustaw ADMIN_PASSWORD w środowisku lub lokalnym .env.")
command = ["node", str(root / "vendor/zai-tests.mjs"), "--app", o.app,
           "--user", os.getenv("ADMIN_USERNAME", "admin"), "--pass", os.environ["ADMIN_PASSWORD"], "--stage", o.stage]
if o.api:
    command += ["--api", o.api]
if o.lighthouse:
    command += ["--lighthouse"]
result = subprocess.run(command, text=True, capture_output=True)
print(result.stdout, end="")
print(result.stderr, end="", file=sys.stderr)
failed = result.returncode != 0 or "✘" in result.stdout or (o.lighthouse and "Lighthouse Accessibility: błąd" in result.stdout)
sys.exit(1 if failed else 0)
