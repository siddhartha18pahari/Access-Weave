"""Vercel serverless entry point.

Vercel's Python runtime looks for a WSGI/ASGI callable named `app` in this file.
Static files are served by WhiteNoise (see config/settings.py), so no separate
static host is needed.
"""
import os
import sys
from pathlib import Path

# The project root is one level up from api/.
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

from django.core.wsgi import get_wsgi_application  # noqa: E402

app = get_wsgi_application()
application = app
