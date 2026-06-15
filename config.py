import os
from datetime import timedelta
from dotenv import load_dotenv
load_dotenv()


class Config:
    # ── Secret key: MUST be set in production ──────────────────────────────
    SECRET_KEY = os.environ.get('SECRET_KEY')
    if not SECRET_KEY or SECRET_KEY in ('dev-secret-key-change-in-production',):
        import secrets as _s
        SECRET_KEY = _s.token_hex(32)
        print("⚠️  WARNING: Using auto-generated SECRET_KEY. Set SECRET_KEY in .env for production!")

    # ── Database ───────────────────────────────────────────────────────────
    DATABASE_PATH   = os.environ.get('DATABASE_PATH', 'database/health_diet_app.db')
    DATABASE_URL    = os.environ.get('DATABASE_URL', '')          # PostgreSQL on Render

    # ── AI providers ───────────────────────────────────────────────────────
    OPENAI_API_KEY  = os.environ.get('OPENAI_API_KEY', '')
    GEMINI_API_KEY  = os.environ.get('GEMINI_API_KEY', '')
    AI_PROVIDER     = os.environ.get('AI_PROVIDER', 'gemini')

    # ── App settings ───────────────────────────────────────────────────────
    DEBUG              = os.environ.get('DEBUG', 'False').lower() == 'true'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024   # 16 MB upload limit

    # ── Admin credentials: MUST be set via env in production ───────────────
    ADMIN_USERNAME  = os.environ.get('ADMIN_USERNAME', 'admin')
    ADMIN_PASSWORD  = os.environ.get('ADMIN_PASSWORD')
    if not ADMIN_PASSWORD:
        import secrets as _s
        ADMIN_PASSWORD = _s.token_urlsafe(24)
        print(f"⚠️  WARNING: No ADMIN_PASSWORD set. Auto-generated: {ADMIN_PASSWORD}")

    SITE_URL = os.environ.get('SITE_URL', 'https://ai-diet-planner-ffmj.onrender.com')

    # ── Session security ───────────────────────────────────────────────────
    SESSION_COOKIE_SECURE   = os.environ.get('DEBUG', 'False').lower() != 'true'
    SESSION_COOKIE_HTTPONLY  = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = timedelta(hours=24)

    # ── CSRF (used by Flask-WTF) ──────────────────────────────────────────
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = 3600   # 1-hour token validity

    # ── Google OAuth ──────────────────────────────────────────────────────
    GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID', '')
    GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET', '')
