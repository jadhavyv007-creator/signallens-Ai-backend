import os
import sys

_current_dir = os.path.dirname(os.path.abspath(__file__))
_root_dir = os.path.dirname(_current_dir)
for _p in [_current_dir, _root_dir]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

from .main import app

__all__ = ["app"]

