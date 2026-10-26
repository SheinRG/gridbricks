"""Vercel serverless entrypoint. Vercel serves the ASGI `app` exported from this module."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.main import app

__all__ = ["app"]
