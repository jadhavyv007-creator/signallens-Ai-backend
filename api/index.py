"""
Vercel Serverless Entrypoint for SignalLens AI.
"""

import os
import sys

# Ensure repository root and api directory are on sys.path in serverless runtime
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(CURRENT_DIR)

for p in [CURRENT_DIR, ROOT_DIR]:
    if p not in sys.path:
        sys.path.insert(0, p)

os.environ["VERCEL"] = "1"

from api.main import app

__all__ = ["app"]





