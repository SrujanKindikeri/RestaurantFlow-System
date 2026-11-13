# =============================================================================
# RestaurantFlow — Test Settings
# Overrides for running tests with SQLite (no PostgreSQL required)
# =============================================================================

from config.settings import *  # noqa: F401, F403

# Override database to use SQLite for tests
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

# Disable migrations for speed during testing — Django creates tables directly
# from model definitions when migrations are skipped.
# CONCURRENTLY index syntax is PostgreSQL-only and fails on SQLite.
class DisableMigrations:
    def __contains__(self, item):
        return True
    def __getitem__(self, item):
        return None
MIGRATION_MODULES = DisableMigrations()

# Use locmem cache instead of Redis for tests
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}

# Disable Celery task execution during tests
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# Use in-memory channel layer for WebSocket tests
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer",
    }
}
