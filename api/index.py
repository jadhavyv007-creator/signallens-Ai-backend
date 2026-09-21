"""
Vercel Serverless Entrypoint for SignalLens AI.
"""

import os
import sys

file_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(file_dir)
cwd = os.getcwd()

for p in [file_dir, parent_dir, cwd, "/var/task", "/var/task/api"]:
    if os.path.exists(p) and p not in sys.path:
        sys.path.insert(0, p)

os.environ["VERCEL"] = "1"

try:
    from api.main import app
except Exception:
    try:
        from main import app
    except Exception:
        import api.main
        app = api.main.app

__all__ = ["app"]






