# =============================================================================
# RestaurantFlow — Marketing Exceptions
# Phase 18
# =============================================================================

from rest_framework.exceptions import APIException
from rest_framework import status


class MarketingPermissionDenied(APIException):
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = "You do not have permission to perform this marketing action."
    default_code = "marketing_permission_denied"


class CampaignNotFound(APIException):
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = "Campaign not found."
    default_code = "campaign_not_found"


class CampaignInvalidTransition(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = "This status transition is not allowed."
    default_code = "campaign_invalid_transition"


class CampaignAlreadyExists(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = "A campaign with this code already exists."
    default_code = "campaign_already_exists"


class PromotionNotFound(APIException):
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = "Promotion not found."
    default_code = "promotion_not_found"


class PromotionIneligible(APIException):
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    default_detail = "Customer or order is not eligible for this promotion."
    default_code = "promotion_ineligible"


class PromotionExpired(APIException):
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    default_detail = "This promotion has expired."
    default_code = "promotion_expired"


class PromotionUsageLimitReached(APIException):
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    default_detail = "This promotion has reached its usage limit."
    default_code = "promotion_usage_limit_reached"


class PromotionAlreadyUsed(APIException):
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    default_detail = "You have already used this promotion."
    default_code = "promotion_already_used"


class PromotionCodeInvalid(APIException):
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    default_detail = "The promotion code is invalid or not applicable."
    default_code = "promotion_code_invalid"


class MarketingConsentRequired(APIException):
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    default_detail = "Customer has not consented to receive this type of marketing."
    default_code = "marketing_consent_required"


class AudienceGenerationError(APIException):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_detail = "Failed to generate campaign audience."
    default_code = "audience_generation_error"


class CampaignDeliveryError(APIException):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_detail = "Campaign delivery encountered an error."
    default_code = "campaign_delivery_error"


class FrequencyLimitExceeded(APIException):
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    default_detail = "Marketing frequency limit reached for this customer/channel."
    default_code = "frequency_limit_exceeded"
