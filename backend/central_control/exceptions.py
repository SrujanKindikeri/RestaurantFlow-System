# =============================================================================
# RestaurantFlow — Central Control Center Exceptions
# Phase 15
# =============================================================================

from rest_framework.exceptions import APIException
from rest_framework import status


class CentralControlError(Exception):
    """Base exception for Central Control Center business logic errors."""
    pass


class AlertNotFoundError(CentralControlError):
    """Raised when a CentralAlert does not exist or is inaccessible."""
    pass


class AlertTransitionError(CentralControlError):
    """Raised when an invalid alert status transition is attempted."""

    def __init__(self, current: str, target: str):
        self.current = current
        self.target = target
        super().__init__(
            f"Cannot transition alert from '{current}' to '{target}'."
        )


class AlertAlreadyActiveError(CentralControlError):
    """Raised when an identical active alert already exists (deduplication)."""
    pass


class IssueNotFoundError(CentralControlError):
    """Raised when a CentralIssue does not exist or is inaccessible."""
    pass


class IssueTransitionError(CentralControlError):
    """Raised when an invalid issue status transition is attempted."""

    def __init__(self, current: str, target: str):
        self.current = current
        self.target = target
        super().__init__(
            f"Cannot transition issue from '{current}' to '{target}'."
        )


class IssueImmutableError(CentralControlError):
    """Raised when attempting to modify a CLOSED issue."""
    pass


class IssueAssignmentScopeError(CentralControlError):
    """Raised when assigning an issue to a user outside the appropriate scope."""
    pass


class ResolutionNoteRequiredError(CentralControlError):
    """Raised when a resolution note is required but not provided (critical issues)."""
    pass


class ConfigurationError(CentralControlError):
    """Raised for invalid Central Control configuration values."""
    pass


class ScopeViolationError(CentralControlError):
    """Raised when a user attempts to access data outside their authorized scope."""
    pass


# ---------------------------------------------------------------------------
# DRF API Exceptions — these are raised from views and rendered by DRF
# ---------------------------------------------------------------------------

class AlertAPIError(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Alert operation failed."
    default_code = "alert_error"


class IssueAPIError(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Issue operation failed."
    default_code = "issue_error"


class PermissionAPIError(APIException):
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = "You do not have permission to perform this action."
    default_code = "permission_denied"


class ScopeAPIError(APIException):
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = "Resource is outside your authorized scope."
    default_code = "scope_violation"
