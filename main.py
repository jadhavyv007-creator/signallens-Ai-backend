"""
Root entrypoint for SignalLens AI.
"""

import os
import sys

file_dir = os.path.dirname(os.path.abspath(__file__))
for p in [file_dir, os.path.join(file_dir, "api"), "/var/task", "/var/task/api"]:
    if os.path.exists(p) and p not in sys.path:
        sys.path.insert(0, p)

from api.main import app

__all__ = ["app"]
