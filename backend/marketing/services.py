# =============================================================================
# RestaurantFlow — Marketing Services Entry Point
# Phase 18
#
# Re-exports all service classes for convenient imports.
# Business logic lives in the individual *_services.py modules.
# =============================================================================

from marketing.campaign_services import CampaignService, CampaignApprovalService  # noqa: F401
from marketing.audience_services import CampaignAudienceService                   # noqa: F401
from marketing.promotion_services import (                                         # noqa: F401
    PromotionService,
    PromotionEligibilityService,
    PromotionUsageService,
)
from marketing.scheduling_services import CampaignSchedulingService                # noqa: F401
from marketing.tracking_services import (                                           # noqa: F401
    MarketingConsentService,
    CampaignDeliveryService,
    CampaignConversionService,
)
