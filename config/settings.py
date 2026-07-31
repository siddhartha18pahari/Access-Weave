"""
AccessWeave settings.

Deliberately dependency-light: the app runs with only Django installed so the
demo is reliable on any machine. Optional capabilities (OCR, a cloud language
model) are feature-flagged and degrade gracefully to a deterministic local mode.
"""
from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


# --- Core -------------------------------------------------------------------
SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY", "dev-insecure-key-change-in-production-please"
)
DEBUG = _env_bool("DJANGO_DEBUG", True)
ALLOWED_HOSTS = [h.strip() for h in os.environ.get(
    "DJANGO_ALLOWED_HOSTS", "127.0.0.1,localhost,*"
).split(",") if h.strip()]

# Vercel injects the deployment hostname; trust it (and any custom domain) so
# the app works on both the preview and production URLs without reconfiguration.
_VERCEL_URL = os.environ.get("VERCEL_URL", "").strip()
_VERCEL_BRANCH_URL = os.environ.get("VERCEL_BRANCH_URL", "").strip()
_ON_VERCEL = bool(os.environ.get("VERCEL"))
if _ON_VERCEL:
    for host in (_VERCEL_URL, _VERCEL_BRANCH_URL):
        if host and host not in ALLOWED_HOSTS:
            ALLOWED_HOSTS.append(host)
    if ".vercel.app" not in ALLOWED_HOSTS:
        ALLOWED_HOSTS.append(".vercel.app")

CSRF_TRUSTED_ORIGINS = [
    o.strip() for o in os.environ.get("DJANGO_CSRF_TRUSTED_ORIGINS", "").split(",")
    if o.strip()
]
if _ON_VERCEL:
    CSRF_TRUSTED_ORIGINS.append("https://*.vercel.app")
    for host in (_VERCEL_URL, _VERCEL_BRANCH_URL):
        if host:
            CSRF_TRUSTED_ORIGINS.append(f"https://{host}")

# Vercel terminates TLS upstream, so Django must read the forwarded header or it
# will think every request is plain HTTP and redirect-loop.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # AccessWeave
    "core",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

# WhiteNoise serves static files in production (Docker/gunicorn). It is optional
# for local dev — if it isn't installed, the runserver static handler is used.
try:
    import whitenoise  # noqa: F401
    MIDDLEWARE.insert(1, "whitenoise.middleware.WhiteNoiseMiddleware")
    STORAGES = {
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {
            "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"
        },
    }
except ImportError:
    pass

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "core.context.accessweave_context",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# --- Database ---------------------------------------------------------------
# SQLite locally (zero setup); a hosted Postgres in production when DATABASE_URL
# is set. Serverless hosts have an ephemeral filesystem, so SQLite there would
# silently lose every account and task — Postgres is required for a real deploy.
def _database_from_url(url: str) -> dict:
    """Parse a postgres:// URL without adding a dependency."""
    from urllib.parse import urlparse, unquote, parse_qs
    u = urlparse(url)
    qs = parse_qs(u.query)
    cfg = {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": unquote(u.path.lstrip("/")),
        "USER": unquote(u.username or ""),
        "PASSWORD": unquote(u.password or ""),
        "HOST": u.hostname or "",
        "PORT": str(u.port or ""),
        "CONN_MAX_AGE": 0,          # serverless: never hold a connection open
        "OPTIONS": {},
    }
    cfg["OPTIONS"]["sslmode"] = (qs.get("sslmode") or ["require"])[0]

    # Supabase/PgBouncer transaction pooling (port 6543) cannot carry server-side
    # prepared statements between requests. Django's psycopg3 backend already
    # defaults prepare_threshold to None, but set it explicitly so the intent
    # survives a future default change — and never enable server-side binding.
    cfg["OPTIONS"]["prepare_threshold"] = None
    cfg["OPTIONS"]["server_side_binding"] = False

    # Supabase's pooler expects the username as-is (project-scoped, e.g.
    # "postgres.abcdefgh"), which urlparse already gives us unquoted above.
    return cfg


_DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()
if _DATABASE_URL:
    DATABASES = {"default": _database_from_url(_DATABASE_URL)}
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": os.environ.get("SQLITE_PATH", str(BASE_DIR / "db.sqlite3")),
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
]

LANGUAGE_CODE = "en"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# --- Static / media ---------------------------------------------------------
STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Bump to force browsers to fetch fresh CSS/JS after an update (dev + prod).
AW_STATIC_VERSION = os.environ.get("AW_STATIC_VERSION", "19")

LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "home"
LOGOUT_REDIRECT_URL = "home"

# Sessions: keep them for demo convenience but do not persist forever.
SESSION_COOKIE_AGE = 60 * 60 * 24 * 7
SESSION_EXPIRE_AT_BROWSER_CLOSE = False

MESSAGE_STORAGE = "django.contrib.messages.storage.session.SessionStorage"

# --- AccessWeave feature flags (privacy-first defaults) ---------------------
ACCESSWEAVE = {
    # AI: "local" = deterministic engine only (no network, always works).
    # "auto" = try a configured provider, fall back to local on any failure.
    "AI_BACKEND": os.environ.get("AI_BACKEND", "local"),
    "AI_MODEL": os.environ.get("AI_MODEL", ""),
    "AI_API_KEY": os.environ.get("AI_API_KEY", ""),
    # ElevenLabs high-quality TTS (optional). Set ELEVENLABS_API_KEY to enable;
    # the browser's built-in speech is the always-available fallback.
    "ELEVENLABS_API_KEY": os.environ.get("ELEVENLABS_API_KEY", ""),
    "ELEVENLABS_VOICE_ID": os.environ.get(
        "ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM"),  # "Rachel", a clear default
    "ELEVENLABS_MODEL": os.environ.get("ELEVENLABS_MODEL", "eleven_turbo_v2_5"),
    # OCR: attempts pytesseract if installed; otherwise a graceful message.
    "OCR_BACKEND": os.environ.get("OCR_BACKEND", "tesseract"),
    "OCR_LANGUAGES": os.environ.get("OCR_LANGUAGES", "eng"),
    # Uploads are NOT stored by default. Bytes are processed in memory and
    # discarded. This is a core privacy guarantee, not a setting to relax lightly.
    "STORE_UPLOADS": _env_bool("STORE_UPLOADS", False),
    "MAX_UPLOAD_MB": int(os.environ.get("MAX_UPLOAD_MB", "15")),
    "ENABLE_LOCATION": _env_bool("ENABLE_LOCATION", False),
    "ENABLE_SUPPORT_CIRCLE": _env_bool("ENABLE_SUPPORT_CIRCLE", True),
    "PRIVACY_MIN_GROUP_SIZE": int(os.environ.get("PRIVACY_MIN_GROUP_SIZE", "10")),
}

FILE_UPLOAD_MAX_MEMORY_SIZE = ACCESSWEAVE["MAX_UPLOAD_MB"] * 1024 * 1024
DATA_UPLOAD_MAX_MEMORY_SIZE = FILE_UPLOAD_MAX_MEMORY_SIZE + 1024 * 1024

# Security niceties (safe in dev, correct in prod behind HTTPS)
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
if not DEBUG:
    # Behind real HTTPS, force secure cookies + redirect. For a local Docker demo
    # over plain HTTP, set DJANGO_SSL_REDIRECT=0 so cookies still work.
    _ssl = _env_bool("DJANGO_SSL_REDIRECT", True)
    SECURE_SSL_REDIRECT = _ssl
    SESSION_COOKIE_SECURE = _ssl
    CSRF_COOKIE_SECURE = _ssl
