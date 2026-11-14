# =============================================================================
# RestaurantFlow — Observability Logging Context
# Phase 24
#
# Per-request / per-task structured-log context carried via contextvars so
# every log line emitted during a request or background task automatically
# carries the request_id and safe tenant scope without threading it through
# every function signature.
# =============================================================================

import contextvars
from dataclasses import dataclass
from typing import Optional


@dataclass
class LogContext:
    """Safe tenant + correlation context for structured logs."""

    request_id: Optional[str] = None
    user_id: Optional[str] = None
    company_id: Optional[str] = None
    restaurant_id: Optional[str] = None
    branch_id: Optional[str] = None
    environment: Optional[str] = None

    def as_dict(self) -> dict:
        return {
            "request_id": self.request_id,
            "user_id": self.user_id,
            "company_id": self.company_id,
            "restaurant_id": self.restaurant_id,
            "branch_id": self.branch_id,
            "environment": self.environment,
        }


# A single contextvar holds the active LogContext. Nested set/reset is
# supported via set_context() which yields the previous value for restore.
_context_var: "contextvars.ContextVar[LogContext]" = contextvars.ContextVar(
    "restaurantflow_log_context", default=LogContext()
)


def get_context() -> LogContext:
    """Return the currently active LogContext (never None)."""
    return _context_var.get()


def set_context(ctx: LogContext) -> contextvars.Token:
    """Set the active LogContext. Returns a token for restore/reset."""
    return _context_var.set(ctx)


def reset_context(token: contextvars.Token) -> None:
    """Restore the previous LogContext from a token returned by set_context()."""
    _context_var.reset(token)


def bind(**kwargs) -> LogContext:
    """
    Return a new LogContext derived from the current one with the given
    fields overridden. Non-None values replace; None values keep the
    existing value so callers can do `bind(user_id=...)` without clobbering
    request_id.
    """
    current = get_context()
    merged = LogContext(
        request_id=kwargs.get("request_id", current.request_id),
        user_id=kwargs.get("user_id", current.user_id),
        company_id=kwargs.get("company_id", current.company_id),
        restaurant_id=kwargs.get("restaurant_id", current.restaurant_id),
        branch_id=kwargs.get("branch_id", current.branch_id),
        environment=kwargs.get("environment", current.environment),
    )
    return merged
