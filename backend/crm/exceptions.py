# =============================================================================
# RestaurantFlow — CRM Domain Exceptions
# Phase 17
# =============================================================================

from rest_framework.exceptions import APIException, ValidationError, NotFound
from rest_framework import status


class CustomerNotFound(NotFound):
    default_detail = "Customer not found."
    default_code = "customer_not_found"


class CustomerAlreadyExists(ValidationError):
    default_detail = "A customer with these details already exists."
    default_code = "customer_already_exists"


class CustomerBlocked(APIException):
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = "This customer is blocked."
    default_code = "customer_blocked"


class CustomerScopeViolation(APIException):
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = "Customer does not belong to your scope."
    default_code = "customer_scope_violation"


class CustomerIdentityConflict(ValidationError):
    default_detail = "Customer identity conflict: phone and email match different customers."
    default_code = "customer_identity_conflict"


class LoyaltyAccountNotFound(NotFound):
    default_detail = "Loyalty account not found."
    default_code = "loyalty_account_not_found"


class InsufficientLoyaltyPoints(ValidationError):
    default_detail = "Insufficient loyalty points for this operation."
    default_code = "insufficient_loyalty_points"


class LoyaltyTransactionConflict(ValidationError):
    default_detail = "Duplicate loyalty transaction detected."
    default_code = "loyalty_transaction_conflict"


class RewardUnavailable(ValidationError):
    default_detail = "This reward is currently unavailable."
    default_code = "reward_unavailable"


class RewardExpired(ValidationError):
    default_detail = "This reward has expired."
    default_code = "reward_expired"


class RewardRedemptionConflict(ValidationError):
    default_detail = "A redemption conflict occurred."
    default_code = "reward_redemption_conflict"


class FeedbackNotAllowed(ValidationError):
    default_detail = "Feedback is not allowed for this order."
    default_code = "feedback_not_allowed"


class FeedbackAlreadyExists(ValidationError):
    default_detail = "Feedback already exists for this customer/order."
    default_code = "feedback_already_exists"


class FeedbackModerationNotAllowed(APIException):
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = "You are not authorised to moderate this feedback."
    default_code = "feedback_moderation_not_allowed"


class CustomerMergeConflict(ValidationError):
    default_detail = "Customer merge conflict detected."
    default_code = "customer_merge_conflict"


class CustomerMergeNotAllowed(APIException):
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = "Customer merge is not allowed."
    default_code = "customer_merge_not_allowed"


class CRMPermissionDenied(APIException):
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = "You do not have permission to perform this CRM action."
    default_code = "crm_permission_denied"
