#!/usr/bin/env python3
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

root = Path(__file__).resolve().parent.parent
os.chdir(root)
sys.path.insert(0, str(root))
load_dotenv(root / ".env")
from generator.seed_demo import main
main()
