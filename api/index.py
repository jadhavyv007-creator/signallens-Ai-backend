"""
Vercel Serverless Entrypoint for SignalLens AI.
"""

import os
import sys

# Ensure repository root is on sys.path so 'api' and 'signalens' resolve in serverless runtime
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from api.main import app

__all__ = ["app"]

