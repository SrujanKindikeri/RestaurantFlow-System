# =============================================================================
# RestaurantFlow — Notifications Exceptions
# Phase 16
# =============================================================================


class NotificationError(Exception):
    """Base class for notification-related errors."""


class NotificationNotFoundError(NotificationError):
    """Notification or recipient record does not exist / is out of scope."""


class NotificationPermissionError(NotificationError):
    """Caller is not authorised to perform this action."""


class NotificationDeliveryError(NotificationError):
    """A delivery attempt failed (non-retryable by default)."""


class NotificationTemplateError(NotificationError):
    """Template rendering or lookup failed."""


class NotificationPreferenceError(NotificationError):
    """An error in preference creation or update."""


class NotificationProviderError(NotificationError):
    """A provider is misconfigured or unavailable."""


class NotificationProviderNotConfigured(NotificationProviderError):
    """The external provider for this channel is not configured."""


class NotificationRateLimited(NotificationError):
    """This notification type is within its cooldown window and should be suppressed."""


class NotificationDuplicateError(NotificationError):
    """An identical notification already exists (idempotency guard)."""


class InvalidTemplateVariable(NotificationTemplateError):
    """A template variable that is not in the safe allow-list was used."""
