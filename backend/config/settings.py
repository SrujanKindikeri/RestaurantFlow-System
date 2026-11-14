# =============================================================================
# RestaurantFlow — Django Settings
# Phase 1 Foundation
# =============================================================================

import os
from pathlib import Path
from datetime import timedelta
from dotenv import load_dotenv

# Load .env from backend directory
load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env")

# -----------------------------------------------------------------------------
# Base paths
# -----------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent

# -----------------------------------------------------------------------------
# Security
# -----------------------------------------------------------------------------
# Phase 21 — Remove insecure fallbacks.  In production, SECRET_KEY MUST be
# set via the environment.  A weak fallback is only kept for development.
_SECRET_KEY_FALLBACK = "dev-only-insecure-key-DO-NOT-USE-IN-PRODUCTION"
SECRET_KEY = os.getenv("SECRET_KEY", _SECRET_KEY_FALLBACK)

# Phase 21 — DEBUG defaults to False for safety.
# Must explicitly set DEBUG=True in development.
DEBUG = os.getenv("DEBUG", "False").lower() in ("true", "1", "yes")

# If running in production (DEBUG=False) with the fallback key, fail fast.
if not os.getenv("SECRET_KEY") and not DEBUG:
    raise RuntimeError(
        "SECRET_KEY must be set via environment variable in production. "
        "Do not rely on the insecure development fallback."
    )

ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")

# -----------------------------------------------------------------------------
# Applications
# -----------------------------------------------------------------------------
DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    "channels",
    "django_filters",
    # Phase 16 — Celery beat for periodic notification tasks
    "django_celery_beat",
    "django_celery_results",
]

LOCAL_APPS = [
    "common",
    "accounts",
    "core",
    "organizations",
    "counters",
    "menu",
    "orders",
    "kitchen",
    "billing",
    "payments",
    "inventory",
    "recipes",
    "financials",
    "accounting",
    "reporting",
    "central_control",
    # Phase 16 — Notification & Communication Center
    "notifications",
    # Phase 17 — Customer CRM, Loyalty & Feedback
    "crm",
    # Phase 18 — Marketing, Promotions & Campaign Management
    "marketing",
    # Phase 19 — Advanced POS & Restaurant Operations
    "operations",
    # Phase 20 — Multi-Branch Enterprise Operations & Configuration
    "enterprise",
    # Phase 24 — Monitoring, logging & observability
    "observability",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# -----------------------------------------------------------------------------
# Middleware
# -----------------------------------------------------------------------------
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    # Phase 24 — request correlation (binds X-Request-ID + structured-log context)
    "observability.middleware.RequestCorrelationMiddleware",
    # Phase 24 — API metrics (count/latency/errors); never breaks a request
    "observability.middleware.MetricsMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

# -----------------------------------------------------------------------------
# URL configuration
# -----------------------------------------------------------------------------
ROOT_URLCONF = "config.urls"

# -----------------------------------------------------------------------------
# Templates
# -----------------------------------------------------------------------------
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# -----------------------------------------------------------------------------
# WSGI / ASGI
# -----------------------------------------------------------------------------
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# -----------------------------------------------------------------------------
# Database — PostgreSQL
# -----------------------------------------------------------------------------
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("DB_NAME", "restaurantflow"),
        "USER": os.getenv("DB_USER", "restaurantflow"),
        "PASSWORD": os.getenv("DB_PASSWORD", "change_me"),
        "HOST": os.getenv("DB_HOST", "localhost"),
        "PORT": os.getenv("DB_PORT", "5432"),
        # Phase 22 — Persistent connections (1 connection per Gunicorn sync worker).
        # Set to 0 (or unset) if using PgBouncer in transaction-pooling mode.
        "CONN_MAX_AGE": 60,
    }
}

# Phase 21 — In production, warn if DB_PASSWORD is still the default.
if not DEBUG and os.getenv("DB_PASSWORD", "change_me") == "change_me":
    import warnings
    warnings.warn(
        "DB_PASSWORD is using the insecure default 'change_me'. "
        "Set a strong password via the environment variable in production.",
        stacklevel=2,
    )

# -----------------------------------------------------------------------------
# Custom User Model
# -----------------------------------------------------------------------------
AUTH_USER_MODEL = "accounts.User"

# -----------------------------------------------------------------------------
# Password validation
# -----------------------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# -----------------------------------------------------------------------------
# Internationalization
# -----------------------------------------------------------------------------
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# -----------------------------------------------------------------------------
# Static & Media files
# -----------------------------------------------------------------------------
STATIC_URL = os.getenv("STATIC_URL", "/static/")
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

MEDIA_URL = os.getenv("MEDIA_URL", "/media/")
MEDIA_ROOT = BASE_DIR / "mediafiles"

# -----------------------------------------------------------------------------
# Default primary key
# -----------------------------------------------------------------------------
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# -----------------------------------------------------------------------------
# Django REST Framework
# -----------------------------------------------------------------------------
# Phase 21 — Throttle rates (defined before REST_FRAMEWORK so it's available)
THROTTLE_RATES = {
    "auth_login": os.getenv("THROTTLE_AUTH_LOGIN", "30/hour"),
    "auth_register": os.getenv("THROTTLE_AUTH_REGISTER", "5/hour"),
    "auth_password": os.getenv("THROTTLE_AUTH_PASSWORD", "10/hour"),
    "sensitive_op": os.getenv("THROTTLE_SENSITIVE_OP", "60/hour"),
    "export": os.getenv("THROTTLE_EXPORT", "20/hour"),
    "search": os.getenv("THROTTLE_SEARCH", "120/hour"),
    # Phase 24 — anonymous frontend error reporting
    "frontend_errors": os.getenv("THROTTLE_FRONTEND_ERRORS", "120/min"),
}

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_THROTTLE_CLASSES": [
        # Global fallback throttle — not aggressive, catches runaway clients.
        # Per-endpoint throttles override this with tighter limits where needed.
    ],
    "DEFAULT_THROTTLE_RATES": THROTTLE_RATES,
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
    "DEFAULT_PARSER_CLASSES": [
        "rest_framework.parsers.JSONParser",
        "rest_framework.parsers.MultiPartParser",
        "rest_framework.parsers.FormParser",
    ],
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_PAGINATION_CLASS": "core.pagination.SafePageNumberPagination",
    "PAGE_SIZE": 20,
    "EXCEPTION_HANDLER": "core.exceptions.custom_exception_handler",
}

# -----------------------------------------------------------------------------
# Simple JWT
# -----------------------------------------------------------------------------
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(
        minutes=int(os.getenv("JWT_ACCESS_TOKEN_LIFETIME", "60"))
    ),
    "REFRESH_TOKEN_LIFETIME": timedelta(
        days=int(os.getenv("JWT_REFRESH_TOKEN_LIFETIME", "7"))
    ),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "ALGORITHM": "HS256",
    "SIGNING_KEY": SECRET_KEY,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "AUTH_HEADER_NAME": "HTTP_AUTHORIZATION",
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
}

# -----------------------------------------------------------------------------
# CORS
# -----------------------------------------------------------------------------
# Phase 21 — In debug mode, allow localhost origins only.
# In production, only explicitly-listed origins are allowed.
if DEBUG:
    CORS_ALLOWED_ORIGINS = os.getenv(
        "CORS_ALLOWED_ORIGINS",
        "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173"
    ).split(",")
else:
    CORS_ALLOWED_ORIGINS = os.getenv(
        "CORS_ALLOWED_ORIGINS", "http://localhost:5173"
    ).split(",")

CORS_ALLOW_CREDENTIALS = True

CORS_ALLOW_HEADERS = [
    "accept",
    "accept-encoding",
    "authorization",
    "content-type",
    "dnt",
    "origin",
    "user-agent",
    "x-csrftoken",
    "x-requested-with",
]

# Phase 23 — CSRF trusted origins (required for DRF session auth and Django admin behind a proxy)
CSRF_TRUSTED_ORIGINS = os.getenv("CSRF_TRUSTED_ORIGINS", "").split(",") if os.getenv("CSRF_TRUSTED_ORIGINS") else []

# -----------------------------------------------------------------------------
# Django Channels (WebSocket-ready foundation)
# -----------------------------------------------------------------------------
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [os.getenv("REDIS_URL", "redis://localhost:6379/0")],
        },
    },
}

# -----------------------------------------------------------------------------
# Redis / Celery (foundation — not fully activated in Phase 1)
# -----------------------------------------------------------------------------
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE

# -----------------------------------------------------------------------------
# Celery Beat — Periodic task schedule (Phase 16: notification maintenance)
# -----------------------------------------------------------------------------
CELERY_BEAT_SCHEDULE = {
    # Phase 24 — Update Celery queue depth gauges (Prometheus metric)
    "observability-celery-queue-depths": {
        "task":     "observability.tasks.update_celery_queue_depths",
        "schedule": 60,  # every minute
    },
    # Retry pending/due delivery records every 2 minutes
    "notifications-retry-pending-deliveries": {
        "task":     "notifications.retry_pending_deliveries",
        "schedule": 120,  # seconds
    },
    # Clean up old low-value notifications every day at 03:00 UTC
    "notifications-cleanup-old": {
        "task":     "notifications.cleanup_old_notifications",
        "schedule": 86400,  # 24 hours
    },
    # Phase 17 — CRM periodic tasks
    "crm-expire-loyalty-points": {
        "task":     "crm.expire_loyalty_points",
        "schedule": 86400,  # daily
    },
    "crm-cleanup-expired-redemptions": {
        "task":     "crm.cleanup_expired_redemptions",
        "schedule": 3600,  # hourly
    },
    "crm-run-segmentation": {
        "task":     "crm.run_segmentation_all_restaurants",
        "schedule": 86400,  # daily
    },
    # Phase 18 — Marketing, Promotions & Campaign Management
    "marketing-expire-campaigns": {
        "task":     "marketing.expire_campaigns",
        "schedule": 300,    # every 5 minutes
    },
    "marketing-expire-promotions": {
        "task":     "marketing.expire_promotions",
        "schedule": 3600,   # hourly
    },
    "marketing-update-delivery-status": {
        "task":     "marketing.update_campaign_delivery_status",
        "schedule": 300,    # every 5 minutes
    },
    "marketing-calculate-metrics": {
        "task":     "marketing.calculate_campaign_metrics",
        "schedule": 1800,   # every 30 minutes
    },
    "marketing-cleanup-data": {
        "task":     "marketing.cleanup_campaign_data_if_configured",
        "schedule": 86400,  # daily
    },
}

# Use Django database as beat scheduler backend (requires django_celery_beat)
CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"

# Phase 22 — Task time limits (global defaults)
CELERY_TASK_TIME_LIMIT = 300       # hard kill after 5 minutes
CELERY_TASK_SOFT_TIME_LIMIT = 240  # SoftTimeLimitExceeded raised after 4 minutes

# Phase 22 — Route tasks to named queues for priority isolation
CELERY_TASK_ROUTES = {
    "notifications.*": {"queue": "notifications"},
    "crm.*":           {"queue": "maintenance"},
    "marketing.*":     {"queue": "maintenance"},
}

# -----------------------------------------------------------------------------
# Cache
# -----------------------------------------------------------------------------
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": REDIS_URL,
    }
}

# -----------------------------------------------------------------------------
# Email — Phase 16: Notification delivery
# Configure via environment variables; defaults to console backend in dev.
# Never hard-code credentials here.
# -----------------------------------------------------------------------------
EMAIL_BACKEND = os.getenv(
    "EMAIL_BACKEND",
    "django.core.mail.backends.console.EmailBackend" if DEBUG else "django.core.mail.backends.smtp.EmailBackend",
)
EMAIL_HOST          = os.getenv("EMAIL_HOST", "localhost")
EMAIL_PORT          = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_USE_TLS       = os.getenv("EMAIL_USE_TLS", "True").lower() in ("true", "1", "yes")
EMAIL_HOST_USER     = os.getenv("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")  # Always from env, never hardcoded
DEFAULT_FROM_EMAIL  = os.getenv("DEFAULT_FROM_EMAIL", "noreply@restaurantflow.app")
SERVER_EMAIL        = DEFAULT_FROM_EMAIL

# -----------------------------------------------------------------------------
# Security headers (non-DEBUG defaults)
# -----------------------------------------------------------------------------
if not DEBUG:
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    X_FRAME_OPTIONS = "DENY"

# Phase 21 — Additional security headers (applied in all environments)
# Referrer-Policy: strict-origin-when-cross-origin
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"

# Phase 21 — Cookie security (applied in all environments for defense-in-depth)
SESSION_COOKIE_HTTPONLY = True  # Django default, explicit for clarity
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = "Lax"

# Phase 21 — Trusted proxy header for HTTPS detection behind ALB/Nginx
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# Phase 21 — Request body size limit (default 2.5MB → 10MB for file uploads)
DATA_UPLOAD_MAX_MEMORY_SIZE = int(os.getenv("DATA_UPLOAD_MAX_MEMORY_SIZE", str(10 * 1024 * 1024)))
FILE_UPLOAD_MAX_MEMORY_SIZE = int(os.getenv("FILE_UPLOAD_MAX_MEMORY_SIZE", str(10 * 1024 * 1024)))

# Phase 21 — Admin URL randomization (set ADMIN_URL_PREFIX in production)
# Default keeps /admin/ for backward compatibility; override in production for security-by-obscurity
ADMIN_URL_PREFIX = os.getenv("ADMIN_URL_PREFIX", "admin")

# Phase 21 — Security event tracking configuration
SECURITY_MAX_LOGIN_FAILURES = int(os.getenv("SECURITY_MAX_LOGIN_FAILURES", "5"))
SECURITY_LOGIN_LOCKOUT_MINUTES = int(os.getenv("SECURITY_LOGIN_LOCKOUT_MINUTES", "15"))

# Phase 21 — Audit retention period in days (set to 0 to disable auto-cleanup)
AUDIT_RETENTION_DAYS = int(os.getenv("AUDIT_RETENTION_DAYS", "365"))

# -----------------------------------------------------------------------------
# Logging
# -----------------------------------------------------------------------------
LOG_LEVEL = os.getenv("LOG_LEVEL", "DEBUG" if DEBUG else "INFO")
# Phase 24 — "json" emits structured JSON logs (for log collectors like Loki);
# "text" keeps the existing human-readable format (default in dev/test).
LOG_FORMAT = os.getenv("LOG_FORMAT", "text").lower()
LOGS_DIR = BASE_DIR / "logs"
LOGS_DIR.mkdir(exist_ok=True)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {process:d} {thread:d} {message}",
            "style": "{",
        },
        "simple": {
            "format": "{levelname} {asctime} {module} {message}",
            "style": "{",
        },
        # Phase 24 — structured JSON for log aggregation / correlation.
        "json": {
            "()": "observability.logging_config.StructuredJsonFormatter",
        },
    },
    "filters": {
        "require_debug_true": {
            "()": "django.utils.log.RequireDebugTrue",
        },
        "require_debug_false": {
            "()": "django.utils.log.RequireDebugFalse",
        },
        # Phase 24 — injects request_id + safe tenant scope into every record.
        "contextual": {
            "()": "observability.logging_config.ContextualLogFilter",
        },
    },
    "handlers": {
        "console": {
            "level": LOG_LEVEL,
            "class": "logging.StreamHandler",
            "formatter": "json" if LOG_FORMAT == "json" else "simple",
            "filters": ["contextual"],
        },
        "json_console": {
            "level": LOG_LEVEL,
            "class": "logging.StreamHandler",
            "formatter": "json",
            "filters": ["contextual"],
        },
        "file_general": {
            "level": "INFO",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": LOGS_DIR / "general.log",
            "maxBytes": 10 * 1024 * 1024,  # 10 MB
            "backupCount": 5,
            "formatter": "verbose",
        },
        "file_errors": {
            "level": "ERROR",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": LOGS_DIR / "errors.log",
            "maxBytes": 10 * 1024 * 1024,
            "backupCount": 5,
            "formatter": "verbose",
        },
        "file_security": {
            "level": "WARNING",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": LOGS_DIR / "security.log",
            "maxBytes": 10 * 1024 * 1024,
            "backupCount": 5,
            "formatter": "verbose",
        },
    },
    "loggers": {
        "django": {
            "handlers": ["console", "file_general"],
            "level": "INFO",
            "propagate": True,
        },
        "django.request": {
            "handlers": ["file_errors", "console"],
            "level": "ERROR",
            "propagate": False,
        },
        "django.security": {
            "handlers": ["file_security", "console"],
            "level": "WARNING",
            "propagate": False,
        },
        # Application loggers
        "accounts": {
            "handlers": ["console", "file_general", "file_security"],
            "level": LOG_LEVEL,
            "propagate": False,
        },
        "core": {
            "handlers": ["console", "file_general"],
            "level": LOG_LEVEL,
            "propagate": False,
        },
        "organizations": {
            "handlers": ["console", "file_general"],
            "level": LOG_LEVEL,
            "propagate": False,
        },
        "counters": {
            "handlers": ["console", "file_general", "file_errors"],
            "level": LOG_LEVEL,
            "propagate": False,
        },
        # Future app loggers (pre-declared for later phases)
        "restaurants": {
            "handlers": ["console", "file_general"],
            "level": LOG_LEVEL,
            "propagate": False,
        },
        "orders": {
            "handlers": ["console", "file_general"],
            "level": LOG_LEVEL,
            "propagate": False,
        },
        "billing": {
            "handlers": ["console", "file_general", "file_errors"],
            "level": LOG_LEVEL,
            "propagate": False,
        },
        "kitchen": {
            "handlers": ["console", "file_general", "file_errors"],
            "level": LOG_LEVEL,
            "propagate": False,
        },
        "celery": {
            "handlers": ["console", "file_general"],
            "level": LOG_LEVEL,
            "propagate": False,
        },
        # Phase 16 — Notifications
        "notifications": {
            "handlers": ["console", "file_general", "file_errors"],
            "level": LOG_LEVEL,
            "propagate": False,
        },
        # Phase 24 — Observability & monitoring
        "observability": {
            "handlers": ["console", "file_general", "file_errors"],
            "level": LOG_LEVEL,
            "propagate": False,
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "WARNING",
    },
}

# =============================================================================
# Phase 24 — Observability configuration
# =============================================================================
OBSERVABILITY_SERVICE_NAME = os.getenv("OBSERVABILITY_SERVICE_NAME", "restaurantflow-api")
OBSERVABILITY_ENVIRONMENT = os.getenv("OBSERVABILITY_ENVIRONMENT", "production" if not DEBUG else "development")

# Prometheus scrape token (header X-Prometheus-Token). Empty = metrics refused
# in production (DEBUG allows unauthenticated scraping for local dev).
PROMETHEUS_SCRAPE_TOKEN = os.getenv("PROMETHEUS_SCRAPE_TOKEN", "")

# Alertmanager webhook token (header X-Alertmanager-Token). Required to accept
# forwarded metric-based alerts into Central Control.
ALERTMANAGER_WEBHOOK_TOKEN = os.getenv("ALERTMANAGER_WEBHOOK_TOKEN", "")

# Organization that owns monitoring/alerts in multi-tenant deployments.
OBSERVABILITY_MONITORING_ORG_ID = os.getenv("OBSERVABILITY_MONITORING_ORG_ID", "")

# Distributed tracing (OpenTelemetry). Activated only when the OTel packages
# are installed AND OTEL_EXPORTER_OTLP_ENDPOINT is set. See tracing.py.
OTEL_EXPORTER_OTLP_ENDPOINT = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "")

# External error tracking (Sentry). Activated only when sentry-sdk is
# installed AND SENTRY_DSN is set. Otherwise local structured logging is the
# authoritative error record (documented limitation).
SENTRY_DSN = os.getenv("SENTRY_DSN", "")
