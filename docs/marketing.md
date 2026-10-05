# Marketing, Promotions & Campaign Management

**Phase 18 — RestaurantFlow**

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Campaign Lifecycle](#campaign-lifecycle)
4. [Audience Targeting](#audience-targeting)
5. [Promotion Rules & Eligibility](#promotion-rules--eligibility)
6. [Promo Code Validation](#promo-code-validation)
7. [Billing Integration](#billing-integration)
8. [Loyalty Integration](#loyalty-integration)
9. [Notification Integration](#notification-integration)
10. [Consent & Frequency Control](#consent--frequency-control)
11. [Campaign Scheduling](#campaign-scheduling)
12. [Delivery Tracking](#delivery-tracking)
13. [Conversion Tracking](#conversion-tracking)
14. [Permissions](#permissions)
15. [Security](#security)
16. [Concurrency & Idempotency](#concurrency--idempotency)
17. [API Reference](#api-reference)
18. [Celery Tasks](#celery-tasks)
19. [Data Retention](#data-retention)

---

## Overview

Phase 18 adds a production-grade **Marketing, Promotions & Campaign Management** system to RestaurantFlow.

The system answers three questions:

- **WHO** receives a campaign (audience targeting via CRM segments and tags)
- **WHAT** they receive (promotion, loyalty bonus, or announcement)
- **WHEN** and **WHERE** (scheduled delivery via the existing Notification Center)

### Authoritative Systems

Marketing **does not own** or duplicate any of the following. Each remains authoritative in its own module:

| Domain | Authoritative System |
|---|---|
| Customer data | CRM (Phase 17) |
| Order data | Orders (Phase 6) |
| Bill totals / discount calculation | Billing (Phase 8) |
| Payment processing | Payments (Phase 9) |
| Loyalty point transactions | CRM / LoyaltyService (Phase 17) |
| Notification delivery | Notifications (Phase 16) |
| Financial accounting | Accounting (Phase 13) |
| Reporting / analytics | Reporting (Phase 14) |

Marketing **only defines**: WHO, WHAT, WHEN, WHERE, eligibility, and campaign intent.

---

## Architecture

```
Customer
    ↓
CRM (segments / tags / consent)
    ↓
Campaign (MarketingCampaign)
    ↓
Audience (CampaignAudience + CampaignAudienceMember)
    ↓
Promotion / Offer (Promotion + PromotionRule)
    ↓
Eligibility check (PromotionEligibilityService)
    ↓
Notification Center (Phase 16 NotificationService)
    ↓
Customer receives message
    ↓
Customer places Order / redeems Promotion
    ↓
Billing Discount Service (Bill.discount_type + apply_discount())
    ↓
Loyalty bonus (LoyaltyService.earn_points_for_bill())
    ↓
Conversion tracked (CampaignConversion)
    ↓
Analytics / Reporting
```

### Django App: `marketing/`

```
marketing/
├── __init__.py
├── apps.py                   # App config; registers notification types at startup
├── admin.py
├── constants.py              # All magic strings, permission codes, status choices
├── exceptions.py             # Domain-specific exceptions
├── models.py                 # All 15 models
├── access.py                 # Queryset scoping (mirrors accounts/access.py pattern)
├── permissions.py            # DRF permission classes
├── validators.py             # Code validators, message body safety, field validators
├── serializers.py            # Read/write serializers (separate per use-case)
├── views.py                  # Thin views; all logic in services
├── urls.py                   # URL routing
├── services.py               # Re-exports all service classes
├── campaign_services.py      # CampaignService, CampaignApprovalService
├── audience_services.py      # CampaignAudienceService
├── promotion_services.py     # PromotionService, PromotionEligibilityService, PromotionUsageService
├── scheduling_services.py    # CampaignSchedulingService
├── tracking_services.py      # MarketingConsentService, CampaignDeliveryService, CampaignConversionService
├── selectors.py              # Read-only queryset builders
├── tasks.py                  # Celery tasks (idempotent)
└── tests/
    ├── base.py               # Shared test fixture setup
    ├── test_campaigns.py
    ├── test_promotions.py
    ├── test_audience.py
    ├── test_consent.py
    ├── test_security.py
    ├── test_api.py
    └── test_validators.py
```

---

## Campaign Lifecycle

### Status Machine

```
DRAFT
  ↓ submit_for_approval()
PENDING_APPROVAL
  ↓ approve()           ↓ reject() → DRAFT
APPROVED
  ↓ schedule()
SCHEDULED ←────────────── PAUSED
  ↓ start()                  ↑ pause()
RUNNING ────────────────────┘
  ↓ complete (end_at passed) / cancel()
COMPLETED / CANCELLED / FAILED
```

All transitions go through `CampaignService.transition_status()`. Arbitrary status jumps are blocked.

Terminal statuses (no further transitions): `COMPLETED`, `CANCELLED`, `FAILED`.

### Creating a Campaign

```python
from marketing.campaign_services import CampaignService

campaign = CampaignService.create_campaign(
    company=org,
    restaurant=restaurant,
    data={
        "name": "Weekend Special",
        "code": "WEEKEND24",
        "campaign_type": "PROMOTION",
        "start_at": "2026-10-10T10:00:00Z",
        "end_at": "2026-10-12T23:59:59Z",
    },
    actor=request.user,
)
```

Campaigns always start in `DRAFT`. The code is normalized to uppercase.

### Approval Workflow

Campaigns require approval before running. A creator **cannot self-approve** their own campaign (unless `MarketingSettings.allow_self_approval` is enabled).

```python
from marketing.campaign_services import CampaignApprovalService

# Creator submits
approval = CampaignApprovalService.submit_for_approval(campaign, actor=marketer)

# Reviewer approves
approval = CampaignApprovalService.approve(campaign, approval, actor=approver, note="Looks good")

# Or rejects (note required)
approval = CampaignApprovalService.reject(campaign, approval, actor=approver, note="Needs revision")
```

Permission required: `marketing.campaign.approve`

### Pause / Resume

```python
# Pause a running campaign (no new deliveries generated while paused)
CampaignService.transition_status(campaign, new_status="PAUSED", actor=user)

# Resume — safe, no duplicate deliveries
CampaignService.transition_status(campaign, new_status="SCHEDULED", actor=user)
```

---

## Audience Targeting

Audiences reuse Phase 17 CRM models — `CustomerSegment`, `CustomerTag`, `CustomerConsent`. No second segmentation system is created.

### Audience Types

| Type | Resolution |
|---|---|
| `ALL_CUSTOMERS` | All active, non-blocked customers in the restaurant |
| `NEW_CUSTOMERS` | `total_orders <= 1` |
| `RETURNING_CUSTOMERS` | `total_orders > 1` |
| `VIP` | Customers with `VIP` segment assignment |
| `HIGH_VALUE` | Customers with `HIGH_VALUE` segment assignment |
| `FREQUENT` | Customers with `FREQUENT` segment assignment |
| `INACTIVE` | `last_order_at < now - days_since_last_order` (default 60d) |
| `AT_RISK` | Inactive but previously returning customers |
| `CUSTOM_SEGMENT` | Specific `segment_id` or `segment_code` |
| `CUSTOM_TAG` | Specific `tag_id` or `tag_code` |
| `CUSTOM_FILTER` | JSON criteria: `min_orders`, `min_lifetime_spend`, `days_since_last_order`, `birthday_in_days` |

### Generating Audience Members

For large audiences, generation is asynchronous via Celery:

```python
from marketing.audience_services import CampaignAudienceService

audience = CampaignAudienceService.create_audience(
    campaign,
    audience_type="CUSTOM_SEGMENT",
    criteria={"segment_code": "VIP"},
    actor=user,
)
# Triggers Celery task
# marketing.tasks.generate_campaign_audience
```

Members are stored in `CampaignAudienceMember` with statuses:
`ELIGIBLE` → `CONTACTED` → `CONVERTED` (or `EXCLUDED` / `UNSUBSCRIBED`)

### Exclusion Rules

The following customers are automatically excluded:
- `is_blocked = True`
- `is_active = False`
- `merged_into` set (merged record)
- Marketing consent not granted for the target channel

---

## Promotion Rules & Eligibility

### Promotion Types

| Type | Description |
|---|---|
| `PERCENTAGE_DISCOUNT` | e.g., 10% off subtotal |
| `FIXED_DISCOUNT` | e.g., ₹50 off |
| `FREE_ITEM` | Adds a free menu item reference |
| `BUY_X_GET_Y` | Buy X quantity, get Y free |
| `LOYALTY_BONUS` | Multiplied points (e.g., 2× weekend) |
| `OTHER` | Custom logic |

### Rule Types

Rules are AND-combined. All must pass for a promotion to be eligible.

| Rule Type | Configuration |
|---|---|
| `MIN_ORDER_VALUE` | `{"amount": "300.00"}` |
| `MIN_QUANTITY` | `{"quantity": 3}` |
| `CUSTOMER_SEGMENT` | `{"segment_code": "VIP"}` |
| `CUSTOMER_TAG` | `{"tag_code": "FREQUENT"}` |
| `FIRST_ORDER` | `{}` — no previous completed orders |
| `REPEAT_ORDER` | `{"min_orders": 2}` |
| `SPECIFIC_MENU_ITEM` | `{"menu_item_id": "<uuid>"}` |
| `MENU_CATEGORY` | `{"category_id": "<uuid>"}` |
| `BRANCH` | `{"branch_id": "<uuid>"}` |
| `ORDER_TYPE` | `{"order_types": ["DINE_IN", "TAKEAWAY"]}` |
| `DAY_OF_WEEK` | `{"days": [5, 6]}` — 0=Mon, 6=Sun |
| `TIME_WINDOW` | `{"start": "18:00", "end": "22:00"}` |
| `LOYALTY_POINTS` | `{"min_points": 500}` |

### Eligibility Validation

**Always server-side. Never trust frontend.**

```python
from marketing.promotion_services import PromotionEligibilityService
from decimal import Decimal

result = PromotionEligibilityService.validate(
    promotion_code="SAVE10",
    customer=customer,
    order=order,
    branch=branch,
    order_subtotal=Decimal("450.00"),
)

# result = {
#   "eligible": True,
#   "promotion_id": "...",
#   "promotion_name": "10% Off",
#   "promotion_type": "PERCENTAGE_DISCOUNT",
#   "estimated_discount": Decimal("45.00"),
#   "discount_type": "PERCENTAGE",
#   "discount_value": Decimal("10.00"),
#   "reason": "eligible",
# }
```

The `estimated_discount` is an estimate only. The **final discount is always recalculated by the Billing service**.

---

## Promo Code Validation

Promo codes are:
- Case-insensitive (normalized to uppercase on save)
- Scope-aware (branch → restaurant → company)
- Time-limited (checked against `start_at` / `end_at`)
- Usage-limited (global `usage_limit` and per-customer `usage_limit_per_customer`)

### API

```
POST /api/marketing/promotions/validate/

{
  "promotion_code": "SAVE10",
  "customer_id": "<uuid>",
  "order_id": "<uuid>",
  "branch_id": "<uuid>",
  "order_subtotal": "300.00"
}
```

Response:
```json
{
  "eligible": true,
  "promotion_id": "...",
  "promotion_name": "10% Off",
  "promotion_type": "PERCENTAGE_DISCOUNT",
  "estimated_discount": "30.00",
  "discount_type": "PERCENTAGE",
  "discount_value": "10.00",
  "reason": "eligible"
}
```

---

## Billing Integration

Marketing **does not calculate** discounts. It defines promotions and validates eligibility. The existing Billing service (`billing.services.apply_discount()`) remains authoritative.

### Flow

```
POS → Enter Promo Code
  ↓
POST /api/marketing/promotions/validate/
  ↓
PromotionEligibilityService.validate() → { eligible, estimated_discount }
  ↓
PromotionUsageService.reserve_usage()   ← locks the usage slot
  ↓
billing.services.apply_discount(bill, discount_type, discount_value)
  ↓
Bill recalculated (subtotal, tax, grand_total)
  ↓
On bill finalization:
PromotionUsageService.apply_usage(usage, bill=bill, discount_amount=bill.discount_amount)
```

### Rollback / Cancellation

If the bill is cancelled or voided before finalization:

```python
PromotionUsageService.cancel_usage(usage)  # RESERVED → CANCELLED
```

If the bill is voided after finalization (e.g., payment reversal):

```python
PromotionUsageService.reverse_usage(usage, reason="Bill voided")  # APPLIED → creates REVERSED record
```

The original APPLIED record is **never edited**. A new `REVERSED` record is created. This preserves the immutable audit trail.

### Source Attribution

When a promotion is applied to a bill, the marketing module passes:
- `source_type = "MARKETING_PROMOTION"`
- `source_id = promotion.pk`

This links the billing discount back to the originating promotion.

---

## Loyalty Integration

For `LOYALTY_BONUS` promotions, Marketing **does not touch** `LoyaltyAccount.points_balance` directly. It triggers `LoyaltyService` which handles the actual point transaction.

### Bonus Points Multiplier

Example: 2× points on weekends.

```python
# Promotion definition
promotion = Promotion(
    promotion_type="LOYALTY_BONUS",
    loyalty_bonus_multiplier=Decimal("2.00"),
    ...
)

# When campaign conversion is detected, the integration layer calls:
LoyaltyService.earn_points_for_bill(bill, ...)
# The multiplier is applied to the standard earn calculation:
# points = int(grand_total × points_per_currency_unit × multiplier)
```

The idempotency key `BILL:<bill_pk>` prevents double-awarding from the same bill.

---

## Notification Integration

Marketing **does not implement** email/SMS providers. All delivery goes through the Phase 16 Notification Center.

### Delivery Flow

```
Campaign (RUNNING)
  ↓
CampaignDeliveryService.create_delivery(campaign, customer, channel)
  → consent check (MarketingConsentService)
  → frequency check (MarketingContactPolicy)
  ↓
CampaignDeliveryService.send_via_notification_service(delivery, body, subject)
  ↓
notifications.NotificationService.create_notification(
    notification_type="MARKETING_CAMPAIGN_DELIVERY",
    source_type="MARKETING_CAMPAIGN",
    source_id=campaign.pk,
    ...
)
  ↓
NotificationDelivery → Provider (email / SMS / WhatsApp / etc.)
```

Marketing tracks delivery at a campaign level in `CampaignDelivery`. The authoritative delivery record remains in `notifications.NotificationDelivery`.

### Notification Types Registered at Startup

The `MarketingConfig.ready()` method appends the following to `notifications.constants.NOTIFICATION_TYPE_CHOICES`:

| Code | Label |
|---|---|
| `MARKETING_CAMPAIGN_DELIVERY` | Marketing Campaign Delivery |
| `MARKETING_PROMOTION_AVAILABLE` | Marketing Promotion Available |
| `MARKETING_LOYALTY_BONUS` | Marketing Loyalty Bonus |

---

## Consent & Frequency Control

### Marketing Consent

Before sending any campaign message, the system checks `CustomerConsent` (Phase 17):

| Channel | Required Consent Type |
|---|---|
| `EMAIL` | `MARKETING_EMAIL` |
| `SMS` | `MARKETING_SMS` |
| `WHATSAPP` | `MARKETING_WHATSAPP` |
| `TELEGRAM` | `MARKETING_TELEGRAM` |
| `IN_APP` | No consent required (follows notification preferences) |

Consent must be `status=GRANTED`. Missing or `REVOKED` → delivery is skipped, `UNSUBSCRIBED` record created.

**Transactional notifications are never affected by marketing consent.**

### Frequency Limits

Per-channel limits prevent customer spam. Configured in `MarketingContactPolicy`:

```
max_messages_per_day   = 3   (default)
max_messages_per_week  = 10  (default)
cooldown_hours         = 0   (default, no cooldown)
```

Frequency counts are tracked via Redis (TTL: 24h for daily, 7d for weekly). One record per `(restaurant, customer, channel, date/week)`.

### Unsubscribe

Customers can opt out of marketing without affecting transactional notifications. The consent record is set to `REVOKED`, and future campaign deliveries for that channel are skipped.

---

## Campaign Scheduling

Campaign scheduling reuses the **existing Celery** infrastructure. No second scheduler is introduced.

### Immediate vs. Scheduled

| `start_at` | Behaviour |
|---|---|
| `null` or in the past | Transitions directly to `RUNNING`, enqueues `send_campaign_batch` |
| Future datetime | Transitions to `SCHEDULED`, enqueues `start_scheduled_campaign` with `eta=start_at` |

### Idempotency

`start_scheduled_campaign` checks current status before transitioning. If the campaign is already `RUNNING` (e.g., due to a retry), it returns without error.

```python
# Idempotent — safe to call multiple times
CampaignSchedulingService.schedule(campaign, actor=user)
```

### Celery Beat Tasks (settings.py)

| Task | Schedule |
|---|---|
| `marketing.expire_campaigns` | Every 5 minutes |
| `marketing.expire_promotions` | Hourly |
| `marketing.update_campaign_delivery_status` | Every 5 minutes |
| `marketing.calculate_campaign_metrics` | Every 30 minutes |
| `marketing.cleanup_campaign_data_if_configured` | Daily |

---

## Delivery Tracking

`CampaignDelivery` tracks the marketing-level status of each message sent.

### Delivery Statuses

| Status | Meaning |
|---|---|
| `PENDING` | Delivery record created, not yet sent |
| `QUEUED` | Handed to Notification Center |
| `SENT` | Notification created, delivery attempted |
| `DELIVERED` | Confirmed delivered by provider |
| `FAILED` | Delivery failed |
| `SKIPPED` | Frequency limit reached |
| `UNSUBSCRIBED` | Customer has no marketing consent |

The `notification_id` field links back to the `notifications.Notification` record for full delivery history.

### Failure Isolation

A single delivery failure **does not stop** the campaign. Each customer's delivery is independent. Failed deliveries are retried by the existing Notification Center retry mechanism — marketing does not implement a second retry engine.

---

## Conversion Tracking

`CampaignConversion` records when a campaign audience member takes a qualifying action.

### Conversion Types

| Type | Trigger |
|---|---|
| `PROMOTION_REDEEMED` | Customer applies a promotion linked to this campaign |
| `ORDER_PLACED` | Customer places an order after receiving a campaign |
| `REPEAT_ORDER` | Returning customer places another order |
| `LOYALTY_ACTION` | Customer earns/redeems loyalty points |
| `FEEDBACK_ACTION` | Customer submits feedback |

### Attribution Principle

All conversions are labeled **DIRECTLY ATTRIBUTED**. This means the customer received the campaign AND took the action. It does not prove causality.

**Never claim this as incremental or causal revenue.** For official financial reporting, use Phase 14 Reporting.

### ROI Calculation

If campaign cost is explicitly captured:
```
ROI = (attributed_revenue - campaign_cost) / campaign_cost
```

If cost is not captured:
- Show: Revenue attributed, Discount given
- Do not fabricate ROI

---

## Permissions

| Permission Code | Description |
|---|---|
| `marketing.dashboard.view` | View Marketing Dashboard |
| `marketing.campaign.view` | View Campaigns |
| `marketing.campaign.create` | Create Campaigns |
| `marketing.campaign.update` | Update Draft/Approved Campaigns |
| `marketing.campaign.submit` | Submit for Approval |
| `marketing.campaign.approve` | Approve Campaigns |
| `marketing.campaign.reject` | Reject Campaigns |
| `marketing.campaign.schedule` | Schedule Approved Campaigns |
| `marketing.campaign.pause` | Pause Running Campaigns |
| `marketing.campaign.resume` | Resume Paused Campaigns |
| `marketing.campaign.cancel` | Cancel Campaigns |
| `marketing.audience.view` | View Audience Definitions & Members |
| `marketing.audience.manage` | Create/Generate Audiences |
| `marketing.promotion.view` | View Promotions |
| `marketing.promotion.create` | Create Promotions |
| `marketing.promotion.update` | Update Inactive Promotions |
| `marketing.promotion.activate` | Activate Promotions |
| `marketing.promotion.deactivate` | Deactivate Promotions |
| `marketing.promotion.apply` | Apply Promotions to Bills (POS) |
| `marketing.promotion.approve` | Approve High-Impact Promotions |
| `marketing.analytics.view` | View Campaign Analytics |
| `marketing.export` | Export Marketing Data |
| `marketing.settings.view` | View Marketing Settings |
| `marketing.settings.manage` | Manage Marketing Settings |

### Role Defaults

| Role | Access |
|---|---|
| Company Head | Full company-wide marketing management |
| Restaurant Owner | Full restaurant marketing management |
| Restaurant Manager | Campaign/promotion management (configurable) |
| Cashier | Promotion validation/application only (`marketing.promotion.apply`) |
| Waiter | Promotion application if explicitly granted |
| Kitchen / Inventory | No marketing access |
| Accountant | `marketing.analytics.view` if granted |
| Central Control | Monitoring visibility only |

**Roles are never hard-coded.** All access is permission-based.

---

## Security

### Scope Isolation

Every API endpoint validates:
1. Authentication (`IsAuthenticated`)
2. Permission code check
3. Company scope — no cross-company access
4. Restaurant scope — campaigns/promotions scoped to user's accessible restaurants
5. Branch scope — branch-specific promotions don't leak to other branches

### IDOR Prevention

Views use `get_accessible_campaigns(user)` and `get_accessible_promotions(user)` querysets. A user cannot access objects outside their scope by guessing a UUID.

### Promotion Abuse Prevention

- Usage limits enforced via `select_for_update()` — concurrent redemptions never exceed the limit
- Per-customer limits enforced atomically in the same transaction
- Promo codes are validated server-side — frontend input is never trusted
- Cross-restaurant / cross-branch promotion leakage is blocked at the eligibility service level
- Discount amounts are never accepted from the frontend — always recalculated by Billing

### Message Safety

Campaign message bodies are validated against unsafe template expressions:
- No `{% %}` template tags
- No `{{ arbitrary.expression }}` interpolation
- Only safe named placeholders: `{{customer_name}}`, `{{restaurant_name}}`, `{{promotion_code}}`, `{{reward_name}}`, `{{expiry_date}}`
- `eval()` and `exec()` are never used

### Audit Trail

All significant actions are recorded in `MarketingAuditLog` (immutable, append-only). Records cannot be updated — `save()` raises `ValueError` on any update attempt.

---

## Concurrency & Idempotency

### Promotion Usage Limits

```python
with transaction.atomic():
    # Lock the promotion row
    locked_promo = Promotion.objects.select_for_update().get(pk=promotion.pk)

    # Check limits inside the lock
    applied_count = PromotionUsage.objects.filter(
        promotion=locked_promo, status="APPLIED"
    ).count()
    reserved_count = PromotionUsage.objects.filter(
        promotion=locked_promo, status="RESERVED"
    ).count()
    if (applied_count + reserved_count) >= locked_promo.usage_limit:
        raise PromotionUsageLimitReached(...)

    usage = PromotionUsage.objects.create(status="RESERVED", ...)
```

200 simultaneous attempts against `usage_limit=100` will result in exactly 100 successful reservations.

### Campaign Audience Generation

`CampaignAudienceMember` uses `get_or_create()` — generating audience twice does not create duplicates.

### Campaign Delivery Idempotency

`CampaignDeliveryService.create_delivery()` checks for an existing non-failed delivery record before creating a new one. A campaign will never send duplicate messages to the same customer on the same channel.

### Notification Idempotency

`NotificationService.create_notification()` uses `(company, notification_type, source_type, source_id)` within 24h as a deduplication key.

### Celery Task Idempotency

All Celery tasks are safe to retry:
- `generate_campaign_audience`: uses `get_or_create` on `CampaignAudienceMember`
- `start_scheduled_campaign`: checks status before transitioning
- `send_campaign_batch`: `create_delivery()` is idempotent
- `expire_campaigns` / `expire_promotions`: `update()` on filtered sets

---

## API Reference

### Dashboard

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/marketing/dashboard/` | Overall marketing KPIs |

### Campaigns

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/marketing/campaigns/` | List campaigns (paginated, filterable) |
| POST | `/api/marketing/campaigns/` | Create campaign |
| GET | `/api/marketing/campaigns/{id}/` | Campaign detail |
| PATCH | `/api/marketing/campaigns/{id}/` | Update campaign |
| POST | `/api/marketing/campaigns/{id}/submit/` | Submit for approval |
| POST | `/api/marketing/campaigns/{id}/approve/` | Approve |
| POST | `/api/marketing/campaigns/{id}/reject/` | Reject (note required) |
| POST | `/api/marketing/campaigns/{id}/schedule/` | Schedule |
| POST | `/api/marketing/campaigns/{id}/pause/` | Pause |
| POST | `/api/marketing/campaigns/{id}/resume/` | Resume |
| POST | `/api/marketing/campaigns/{id}/cancel/` | Cancel |
| GET | `/api/marketing/campaigns/{id}/audience/` | Get audience definitions |
| POST | `/api/marketing/campaigns/{id}/audience/` | Create audience |
| POST | `/api/marketing/campaigns/{id}/audience/generate/` | Generate members (async) |
| GET | `/api/marketing/campaigns/{id}/audience/members/` | List audience members |
| GET | `/api/marketing/campaigns/{id}/analytics/` | Campaign analytics |
| GET | `/api/marketing/conversions/` | All conversions (paginated) |

### Promotions

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/marketing/promotions/` | List promotions |
| POST | `/api/marketing/promotions/` | Create promotion |
| POST | `/api/marketing/promotions/validate/` | Validate promo code |
| GET | `/api/marketing/promotions/{id}/` | Promotion detail |
| PATCH | `/api/marketing/promotions/{id}/` | Update inactive promotion |
| POST | `/api/marketing/promotions/{id}/activate/` | Activate |
| POST | `/api/marketing/promotions/{id}/deactivate/` | Deactivate |
| GET | `/api/marketing/promotions/{id}/usage/` | Usage records |
| GET | `/api/marketing/promotions/{id}/rules/` | Eligibility rules |
| POST | `/api/marketing/promotions/{id}/rules/` | Add rule |

### Settings

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/marketing/settings/` | Get settings for restaurant |
| PATCH | `/api/marketing/settings/` | Update settings |

### Query Parameters

**Campaigns list:**
- `search` — search by name or code
- `status` — filter by status
- `campaign_type` — filter by type
- `restaurant` — filter by restaurant UUID
- `page`, `page_size` — pagination

**Promotions list:**
- `search` — search by name or code
- `is_active` — `true` or `false`
- `restaurant` — filter by restaurant UUID

---

## Celery Tasks

All tasks registered in `settings.CELERY_BEAT_SCHEDULE` via the `marketing.*` namespace:

| Task Name | Trigger | Description |
|---|---|---|
| `marketing.generate_campaign_audience` | On demand | Resolve audience members asynchronously |
| `marketing.start_scheduled_campaign` | ETA (campaign start_at) | Transition SCHEDULED → RUNNING |
| `marketing.send_campaign_batch` | On demand (campaign start) | Send messages to ELIGIBLE members |
| `marketing.update_campaign_delivery_status` | Every 5 min | Sync delivery status from Notification system |
| `marketing.calculate_campaign_metrics` | Every 30 min | Update analytics for running campaigns |
| `marketing.expire_campaigns` | Every 5 min | Mark expired RUNNING campaigns COMPLETED |
| `marketing.expire_promotions` | Hourly | Deactivate expired active promotions |
| `marketing.cleanup_campaign_data_if_configured` | Daily | Optional: clean old CampaignEvent records |

---

## Data Retention

By default, all marketing records are retained indefinitely.

To enable event cleanup, set in your environment:

```
MARKETING_DATA_RETENTION_DAYS=365
```

This will clean `CampaignEvent` records older than the retention window. The following are **never deleted**:
- `MarketingCampaign`
- `Promotion`
- `PromotionUsage`
- `CampaignConversion`
- `MarketingAuditLog`

---

## Frontend Pages

| Route | Component | Description |
|---|---|---|
| `/marketing` | `MarketingDashboard` | KPIs, quick links, attribution summary |
| `/marketing/campaigns` | `CampaignsListPage` | Paginated list with search/filter |
| `/marketing/campaigns/:id` | `CampaignDetailPage` | Detail, actions, analytics |
| `/marketing/promotions` | `PromotionsPage` | Promotion list with activate/deactivate |
| `/marketing/analytics` | `MarketingAnalyticsPage` | Conversion tracking |

Navigation is displayed only to users with `marketing.dashboard.view` permission. Sub-items are filtered by individual permission codes.

---

## Integration Checklist

When implementing new features that interact with marketing:

- [ ] **Orders** — After order completion, call `CampaignConversionService.record_conversion()` if the customer is in an active campaign audience
- [ ] **Billing** — When applying a promo code discount, call `billing.services.apply_discount()` with `source_type="MARKETING_PROMOTION"`
- [ ] **Billing (reversal)** — On bill void/cancellation, call `PromotionUsageService.reverse_usage()` or `cancel_usage()`
- [ ] **Loyalty** — For `LOYALTY_BONUS` campaigns, the earn multiplier is passed to `LoyaltyService.earn_points_for_bill()`
- [ ] **Consent** — Before any marketing delivery, `MarketingConsentService.has_marketing_consent()` must return `True`

---

*Phase 18 — RestaurantFlow*  
*Do not proceed to Phase 19 until all Phase 18 acceptance criteria are verified.*
