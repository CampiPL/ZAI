#!/usr/bin/env python3
import os
import sys
from pathlib import Path

import uvicorn
from dotenv import load_dotenv

root = Path(__file__).resolve().parent.parent
os.chdir(root)
sys.path.insert(0, str(root))
load_dotenv(root / ".env")
uvicorn.run("backend.app:app", host=os.getenv("HOST", "127.0.0.1"), port=int(os.getenv("PORT", "8000")),
            proxy_headers=True, forwarded_allow_ips=os.getenv("FORWARDED_ALLOW_IPS", "127.0.0.1"))
