# =============================================================================
# RestaurantFlow — Enterprise Exceptions
# Phase 20
#
# All domain-specific exceptions for the enterprise module.
# These are raised by service/selector functions and caught by views.
# =============================================================================

from rest_framework.exceptions import ValidationError, PermissionDenied  # noqa: F401 — re-exported


class EnterpriseError(Exception):
    """Base class for all enterprise module errors."""

    default_code = "ENTERPRISE_ERROR"
    default_message = "An enterprise operation error occurred."

    def __init__(self, message=None, code=None):
        self.code = code or self.default_code
        self.message = message or self.default_message
        super().__init__(self.message)

    def to_dict(self):
        return {"code": self.code, "message": self.message}


class BranchStatusTransitionError(EnterpriseError):
    """Raised when a branch status transition is invalid."""
    default_code = "BRANCH_STATUS_INVALID_TRANSITION"
    default_message = "Invalid branch status transition."


class BranchOperationalBlockError(EnterpriseError):
    """Raised when a branch has open operational items preventing closure."""
    default_code = "BRANCH_HAS_OPEN_OPERATIONS"
    default_message = "Branch has open operations that must be resolved before closing."


class ConfigurationKeyNotAllowedError(EnterpriseError):
    """Raised when an unrecognised or non-allow-listed configuration key is used."""
    default_code = "CONFIG_KEY_NOT_ALLOWED"
    default_message = "This configuration key is not permitted."


class ConfigurationValueTypeError(EnterpriseError):
    """Raised when the configuration value cannot be coerced to the declared type."""
    default_code = "CONFIG_VALUE_TYPE_ERROR"
    default_message = "Configuration value does not match the declared type."


class ConfigurationConflictError(EnterpriseError):
    """Raised when a duplicate active configuration key exists at the same scope."""
    default_code = "CONFIG_CONFLICT"
    default_message = "An active configuration for this key already exists at this scope."


class RolloutNotExecutableError(EnterpriseError):
    """Raised when a rollout cannot be executed in its current state."""
    default_code = "ROLLOUT_NOT_EXECUTABLE"
    default_message = "Rollout cannot be executed in its current state."


class RolloutPartialFailureError(EnterpriseError):
    """Raised (non-fatal) to report branches where rollout partially failed."""
    default_code = "ROLLOUT_PARTIAL_FAILURE"
    default_message = "Rollout completed with some branch failures."

    def __init__(self, message=None, code=None, failed_branches=None):
        super().__init__(message, code)
        self.failed_branches = failed_branches or []


class ScheduleOverlapError(EnterpriseError):
    """Raised when operating hours or closures overlap."""
    default_code = "SCHEDULE_OVERLAP"
    default_message = "The schedule overlaps with an existing entry."


class StaffTransferBlockedError(EnterpriseError):
    """Raised when a staff transfer is blocked due to active operational sessions."""
    default_code = "STAFF_TRANSFER_BLOCKED"
    default_message = "Staff transfer cannot proceed — user has active operational sessions."


class StaffTransferScopeError(EnterpriseError):
    """Raised when a staff transfer violates restaurant scope boundaries."""
    default_code = "STAFF_TRANSFER_SCOPE_ERROR"
    default_message = "Staff transfer must be within the same restaurant."


class ApprovalPolicyConflictError(EnterpriseError):
    """Raised when conflicting approval policies are detected."""
    default_code = "APPROVAL_POLICY_CONFLICT"
    default_message = "Conflicting approval policy already exists at this scope."


class BulkOperationError(EnterpriseError):
    """Raised when a bulk operation has encountered failures."""
    default_code = "BULK_OPERATION_PARTIAL_FAILURE"
    default_message = "Bulk operation completed with failures."

    def __init__(self, message=None, code=None, result=None):
        super().__init__(message, code)
        self.result = result or {
            "successful": [],
            "failed": [],
            "skipped": [],
            "warnings": [],
        }
