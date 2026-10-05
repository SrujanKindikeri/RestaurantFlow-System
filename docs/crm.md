# RestaurantFlow — CRM, Loyalty & Feedback

**Phase 17**

---

## Table of Contents

1. [Overview](#1-overview)
2. [Architecture](#2-architecture)
3. [Customer Lifecycle](#3-customer-lifecycle)
4. [Customer Identity Matching](#4-customer-identity-matching)
5. [Customer / Order Relationship](#5-customer--order-relationship)
6. [Loyalty Rules](#6-loyalty-rules)
7. [Reward Redemption Flow](#7-reward-redemption-flow)
8. [Feedback Workflow](#8-feedback-workflow)
9. [Customer Segmentation](#9-customer-segmentation)
10. [Customer Consent](#10-customer-consent)
11. [Customer Merge Workflow](#11-customer-merge-workflow)
12. [Permissions Reference](#12-permissions-reference)
13. [Security & Privacy](#13-security--privacy)
14. [API Reference](#14-api-reference)
15. [Event Integrations](#15-event-integrations)
16. [Celery Periodic Tasks](#16-celery-periodic-tasks)
17. [Database Design Notes](#17-database-design-notes)

---

## 1. Overview

Phase 17 introduces a production-grade Customer Management / CRM / Loyalty / Feedback system for RestaurantFlow. It is designed as a **domain layer** that consumes, but never duplicates, data from existing systems (Orders, Billing, Payments, Accounting, Notifications).

**What CRM owns:**
- Customer profile and identity
- Customer visits
- Loyalty accounts and points ledger
- Loyalty rewards and redemptions
- Customer feedback and moderation
- Customer segmentation and tags
- Customer consent (GDPR-style marketing consent)
- Customer merge workflow

**What CRM does NOT own:**
- Order calculations (owned by Orders)
- Bill / tax / discount calculations (owned by Billing)
- Payment processing (owned by Payments)
- Accounting entries (owned by Accounting)
- Notification delivery (owned by Notifications)
- Inventory costing (owned by Inventory)

---

## 2. Architecture

```
Customer
    ↓
Order (optional FK — guest orders still work)
    ↓
Bill (via Order)
    ↓
Payment (via Bill)

Customer
    ↓
CustomerVisit (idempotent, order-keyed)
    ↓
CustomerStatistics (backend-authoritative)

Customer
    ↓
LoyaltyAccount
    ↓
LoyaltyTransaction (immutable ledger)
    ↓
RewardRedemption

Customer
    ↓
CustomerFeedback
    ↓
FeedbackModeration
    ↓
CentralIssue (when escalated — reuses Phase 15)

Customer
    ↓
CustomerConsent
    ↓
CustomerConsentHistory (immutable)

Customer
    ↓
CustomerSegmentAssignment (criteria-evaluated)
CustomerTagAssignment (manually assigned)
```

**App location:** `backend/crm/`

**Django app name:** `crm`

---

## 3. Customer Lifecycle

### Creation

1. Staff (cashier, manager) creates a customer via POS or CRM UI.
2. `CustomerIdentityService.resolve_or_create_customer()` is called.
3. Phone and email are normalized before any comparison.
4. If a match is found → existing customer is returned (no duplicate).
5. If no match → `CustomerService.create_customer()` generates a unique customer number and creates the record.

### Customer Number

- Format: `CUS-000001`, `CUS-000002`, …
- Immutable after creation.
- Unique per restaurant.
- Generated using `CustomerSequence.select_for_update()` — concurrency-safe, never `MAX()+1`.

### Soft Disable

- Customers are never hard-deleted if they have transactional history.
- Use `is_active = False` or `merged_into` (after merge approval).
- Orders, Bills, Payments, and Accounting data are never deleted.

### Statistics

These fields are **never trusted from frontend input** — they are computed exclusively by `CustomerStatisticsService.refresh_statistics()`:

| Field | Source |
|---|---|
| `total_orders` | `Order.objects.filter(customer=…, status=CONFIRMED).count()` |
| `total_visits` | `CustomerVisit.objects.filter(customer=…, status=COMPLETED).count()` |
| `lifetime_spend` | `Bill.objects.filter(order__customer=…, status=FINALIZED).aggregate(Sum("grand_total"))` |
| `last_order_at` | Latest confirmed order created_at |
| `first_order_at` | Earliest confirmed order created_at |
| `last_visit_at` | Latest completed visit started_at |

Stats are refreshed asynchronously by the `crm.refresh_customer_statistics` Celery task, triggered after order confirmation and bill finalization.

---

## 4. Customer Identity Matching

`CustomerIdentityService` prevents obvious duplicates without auto-merging on weak evidence.

### Matching rules

| Scenario | Result |
|---|---|
| Phone matches existing customer | Return existing customer |
| Email matches existing customer | Return existing customer |
| Phone AND email both match the **same** customer | Return existing customer |
| Phone matches customer A, email matches customer B | Return `CustomerIdentityConflict` error |
| No match | Create new customer |

### Normalization

- **Phone:** strips spaces, dashes, dots, parentheses. Preserves leading `+`.
- **Email:** strips whitespace, lowercases.

Matching is always scoped to a single restaurant — a customer from Restaurant A is invisible to Restaurant B's identity matching.

---

## 5. Customer / Order Relationship

The `Order` model has a nullable `customer` FK added in Phase 17:

```python
customer = ForeignKey("crm.Customer", null=True, blank=True, on_delete=SET_NULL)
```

**Rules:**
- Guest orders (customer=NULL) continue to work exactly as before. No existing functionality breaks.
- POS staff can optionally search/select/create a customer before placing an order.
- Linking requires `customer.link` permission.
- Creating a customer requires `customer.create` permission.
- A customer can only be linked to an order in the same restaurant.

**Idempotency:**  
`CustomerService.link_customer_to_order()` is idempotent — linking the same customer twice is a no-op.

---

## 6. Loyalty Rules

### Earning

Points are earned when a bill is **finalized**:

```
points = floor(grand_total × points_per_currency_unit)
```

- Only FINALIZED bills earn points.
- DRAFT, CANCELLED, and VOID bills never earn points.
- Anonymous orders (no customer) never earn points.
- Earning is **idempotent** via `reference_type=BILL` + `reference_id=bill_uuid`.
  - The same bill can never trigger two EARN transactions.

### Redemption

1. Customer selects a reward.
2. `RewardService.validate_reward_availability()` checks active/valid date.
3. `LoyaltyAccount` is locked with `select_for_update()`.
4. Balance is validated: `balance >= points_required`.
5. Points are deducted via `LoyaltyService.redeem_points()` (creates `LoyaltyTransaction(REDEEM)`).
6. `RewardRedemption` is created with a short alphanumeric `reference_code`.
7. All steps in a single `transaction.atomic()` — any failure rolls back completely.

### Refund / Cancellation Reversal

When a bill is cancelled/voided or a refund is processed:

1. `LoyaltyService.reverse_points_for_bill()` is called.
2. A new `LoyaltyTransaction(REVERSAL)` is created — the original EARN is **never edited**.
3. If the customer already spent those points: the reversal is capped at the current balance.
   - Balance cannot go negative.
   - A controlled adjustment is used rather than silent history modification.
4. Reversal is idempotent — the same bill cannot be reversed twice.

### Balance Integrity

Every transaction enforces:

```
balance_before + points == balance_after
```

`LoyaltyTransaction` rows are **immutable** — `save()` raises `ValueError` if the pk already exists.

### Point Expiry

If `LoyaltyProgram.point_expiry_days` is set:

- The `crm.expire_loyalty_points` Celery beat task runs daily.
- Accounts where the last EARN transaction is older than `point_expiry_days` have their balance expired.
- Creates `LoyaltyTransaction(EXPIRY)` — never silently reduces balance.
- Idempotent: uses `reference_id = "EXPIRY-{date}-{account_pk}"`.

---

## 7. Reward Redemption Flow

```
POST /api/crm/customers/{id}/rewards/{reward_id}/redeem/

→ RewardService.redeem_reward(customer, reward, loyalty_account, actor)
   1. validate_reward_availability()
      - is_active check
      - valid_from / valid_until check
   2. Scope check: reward.restaurant == customer.restaurant
   3. transaction.atomic()
      a. select_for_update() on LoyaltyAccount
      b. Check: balance >= reward.points_required
      c. LoyaltyService.redeem_points() → LoyaltyTransaction(REDEEM)
      d. RewardRedemption.objects.create() → status=CONFIRMED
   4. Commit
→ Returns RewardRedemption with reference_code

Failure at any step → full rollback (no points deducted)
```

**Statuses:**
- `REQUESTED` → `CONFIRMED` (after successful redemption)
- `CONFIRMED` → `USED` (when applied to a bill by POS)
- `CONFIRMED` → `CANCELLED` (cancelled before use — refunds points via adjustment)
- `CONFIRMED` → `EXPIRED` (cleaned up by periodic task after `expires_at`)

---

## 8. Feedback Workflow

### Creating Feedback

```
POST /api/crm/feedback/

Validations:
  - rating: integer 1–5
  - sub-ratings (service, food, ambience): integer 1–5 or null
  - If order provided:
      - customer must match order.customer
      - order.status != CANCELLED
      - order.branch.restaurant == restaurant
  - Duplicate prevention: one feedback per (customer, order) pair
```

### Moderation

```
POST /api/crm/feedback/{id}/moderate/

Requires: feedback.moderate permission

Actions:
  APPROVED → feedback.status = REVIEWED
  HIDDEN   → feedback.status = HIDDEN
  REJECTED → feedback.status = HIDDEN (soft hide)

Optional: create_central_issue=true
  → Creates CentralIssue (Phase 15) with category=QUALITY
  → Links FeedbackModeration.central_issue_id to the issue
  → Triggers Phase 15 notification to assigned staff
```

Feedback is **never hard-deleted** — status-based workflow only.

### Low-Rating Notifications

Feedback with `rating <= 2` dispatches a HIGH severity notification to restaurant staff via the Phase 16 Notification Center (`CRM_FEEDBACK_SUBMITTED`).

---

## 9. Customer Segmentation

Segments are criteria-based groups evaluated deterministically.

### Criteria keys (JSON)

| Key | Type | Meaning |
|---|---|---|
| `min_orders` | int | Customer must have at least N confirmed orders |
| `min_lifetime_spend` | float | Lifetime spend (INR) must be ≥ value |
| `days_since_last_order` | int | Last order was ≥ N days ago (inactive / at-risk) |
| `max_days_since_last_order` | int | Last order was ≤ N days ago (active) |
| `min_visits` | int | Customer must have at least N completed visits |

### Example segment definitions

```json
{"min_orders": 10}                        // FREQUENT
{"min_lifetime_spend": 50000}             // HIGH_VALUE
{"days_since_last_order": 60}             // AT_RISK
{"days_since_last_order": 90}             // INACTIVE
{"min_orders": 1, "max_days_since_last_order": 30}  // NEW_ACTIVE
```

### Evaluation

- `CustomerSegmentationService.assign_segments(customer)` evaluates ALL active segments for the customer's restaurant.
- Assignments are created/removed based on current customer stats.
- Duplicate active assignments are prevented by `UniqueConstraint`.
- The `evaluation_snapshot` field captures the metrics at evaluation time for audit/debugging.
- Manually assigned tags are **not affected** by segmentation.

### Scheduled evaluation

The `crm.run_segmentation_all_restaurants` Celery beat task runs daily and re-evaluates all customers across all restaurants.

---

## 10. Customer Consent

Consent tracks whether a customer has opted in/out of marketing communications.

**Consent types:**

| Code | Meaning |
|---|---|
| `MARKETING_EMAIL` | Email marketing |
| `MARKETING_SMS` | SMS marketing |
| `MARKETING_WHATSAPP` | WhatsApp marketing |
| `MARKETING_TELEGRAM` | Telegram marketing |
| `LOYALTY` | Loyalty programme participation |
| `FEEDBACK_COMMUNICATION` | Feedback follow-up communication |

**Rules:**
- Marketing communications REQUIRE `GRANTED` consent.
- Transactional notifications (order confirmation, payment receipt) do NOT require marketing consent.
- Consent history is preserved in `CustomerConsentHistory` — every change appends an immutable row.
- Sources: `CUSTOMER`, `STAFF`, `ADMIN`, `IMPORT`, `SYSTEM`.

---

## 11. Customer Merge Workflow

Merging is dangerous. The system enforces an approval workflow.

```
Staff → POST /api/crm/customer-merge-requests/
  { source_customer_id, target_customer_id, reason }
  → CustomerMergeRequest (status=REQUESTED)
  → Requires: customer.merge.request permission

Manager → POST /api/crm/customer-merge-requests/{id}/approve/
  → Requires: customer.merge.approve permission
  → transaction.atomic() with select_for_update() on both customers
  → Transfers:
      Orders → customer = target
      CustomerVisits → customer = target
      CustomerFeedback → customer = target
      LoyaltyAccounts → merged (balance transferred via ADJUSTMENT)
  → source.is_active = False
  → source.merged_into = target
  → CustomerStatisticsService.refresh_statistics(target)
  → Commit

Manager → POST /api/crm/customer-merge-requests/{id}/reject/
  → No data changes
  → source customer remains active
```

**Hard rules:**
- Source and target must be the same restaurant.
- Source and target must be different customers.
- Only one pending request per (source, target) pair.
- Orders, Bills, Payments, Accounting data are **never deleted**.
- After merge, source customer's `customer_number` is preserved in audit logs.

---

## 12. Permissions Reference

All permissions are code-based. Never check role names in code.

| Permission Code | Description | Default Roles |
|---|---|---|
| `customer.view` | View customer list and basic details | Manager, Cashier, Waiter |
| `customer.create` | Create new customers | Manager, Cashier |
| `customer.update` | Edit customer profile | Manager |
| `customer.block` | Block/unblock customers | Manager |
| `customer.link` | Link customer to an order | Manager, Cashier, Waiter |
| `customer.history.view` | View order/visit/spending history | Manager |
| `customer.contact.view` | View full PII (phone, email, address) | Manager |
| `customer.merge.request` | Request a customer merge | Manager |
| `customer.merge.approve` | Approve/reject a merge request | Owner, Manager |
| `customer.tag.view` | View customer tags | Manager, Cashier |
| `customer.tag.manage` | Assign/remove tags | Manager |
| `customer.segment.view` | View segments | Manager |
| `customer.segment.manage` | Create/edit segments | Owner, Manager |
| `customer.preference.view` | View preferences | Manager, Cashier |
| `customer.preference.manage` | Edit preferences | Manager, Cashier |
| `loyalty.view` | View loyalty accounts and transactions | Manager, Cashier |
| `loyalty.manage` | Create/edit loyalty programs | Owner, Manager |
| `loyalty.earn` | Manually award points | Manager |
| `loyalty.redeem` | Process reward redemptions | Cashier, Manager |
| `loyalty.adjust` | Manual point adjustment | Manager |
| `reward.view` | View reward definitions | Manager, Cashier |
| `reward.manage` | Create/edit rewards | Owner, Manager |
| `reward.redeem` | Redeem a reward for a customer | Cashier, Manager |
| `feedback.view` | View customer feedback | Manager |
| `feedback.create` | Submit feedback | Cashier, Waiter |
| `feedback.update` | Edit submitted feedback | Manager |
| `feedback.moderate` | Moderate feedback | Manager |
| `feedback.resolve` | Mark feedback as resolved | Manager |
| `customer.consent.view` | View consent records | Manager |
| `customer.consent.manage` | Grant/revoke consents | Manager |
| `crm.dashboard.view` | Access CRM dashboard | Owner, Manager |
| `crm.export` | Export customer data | Owner, Manager |

---

## 13. Security & Privacy

### Scope isolation

Every CRM endpoint enforces:

1. **Authentication** — JWT required on all endpoints.
2. **Permission check** — `HasPermission(code)` via accounts RBAC.
3. **Company scope** — customers are scoped to Organization.
4. **Restaurant scope** — customers cannot cross restaurant boundaries.
5. **IDOR prevention** — all querysets use `get_accessible_customers(user)` before lookup. An unauthorized UUID returns 404, not 403.

### PII masking

**List / search responses** (no `customer.contact.view` required):
- `masked_phone`: `******1234`
- `masked_email`: `s*****@example.com`

**Detail response** with `customer.contact.view` permission:
- Full phone and email are exposed.

**Logs:** never log raw phone, email, date of birth, or addresses.

### Data retention

- Customers with transaction history are never hard-deleted.
- `is_active = False` for disabled customers.
- `merged_into` FK for merged customers.
- All audit logs are **immutable** (append-only; `save()` raises `ValueError` on update).

---

## 14. API Reference

### Customer endpoints

| Method | URL | Permission | Description |
|---|---|---|---|
| GET | `/api/crm/customers/` | `customer.view` | List customers (paginated, filterable) |
| POST | `/api/crm/customers/` | `customer.create` | Create or resolve-or-create customer |
| GET | `/api/crm/customers/{id}/` | `customer.view` | Customer detail |
| PATCH | `/api/crm/customers/{id}/` | `customer.update` | Update customer |
| GET | `/api/crm/customers/search/` | `customer.view` | Search (masked PII) |
| GET | `/api/crm/customers/{id}/orders/` | `customer.history.view` | Order history |
| GET | `/api/crm/customers/{id}/visits/` | `customer.history.view` | Visit history |
| GET | `/api/crm/customers/{id}/spending/` | `customer.history.view` | Spending history |
| GET | `/api/crm/customers/{id}/loyalty/` | `loyalty.view` | Loyalty accounts |
| GET | `/api/crm/customers/{id}/rewards/` | `reward.view` | Redemption history |
| GET | `/api/crm/customers/{id}/tags/` | `customer.tag.view` | Active tags |
| POST | `/api/crm/customers/{id}/tags/` | `customer.tag.manage` | Assign tag |
| DELETE | `/api/crm/customers/{id}/tags/{tag_id}/` | `customer.tag.manage` | Remove tag |
| GET/PATCH | `/api/crm/customers/{id}/preferences/` | `customer.preference.view/manage` | Preferences |

### Loyalty endpoints

| Method | URL | Permission | Description |
|---|---|---|---|
| GET | `/api/crm/loyalty/program/` | `loyalty.view` | List loyalty programs |
| POST | `/api/crm/loyalty/program/` | `loyalty.manage` | Create loyalty program |
| GET | `/api/crm/rewards/` | `reward.view` | List rewards |
| POST | `/api/crm/rewards/` | `reward.manage` | Create reward |
| PATCH | `/api/crm/rewards/{id}/` | `reward.manage` | Update reward |
| POST | `/api/crm/customers/{id}/rewards/{reward_id}/redeem/` | `reward.redeem` | Redeem reward |

### Feedback endpoints

| Method | URL | Permission | Description |
|---|---|---|---|
| GET | `/api/crm/feedback/` | `feedback.view` | List feedback |
| POST | `/api/crm/feedback/` | `feedback.create` | Submit feedback |
| GET | `/api/crm/feedback/{id}/` | `feedback.view` | Get feedback |
| PATCH | `/api/crm/feedback/{id}/` | `feedback.update` | Update feedback |
| POST | `/api/crm/feedback/{id}/moderate/` | `feedback.moderate` | Moderate feedback |

### Segment / Tag / Consent / Merge endpoints

| Method | URL | Permission | Description |
|---|---|---|---|
| GET | `/api/crm/segments/` | `customer.segment.view` | List segments |
| POST | `/api/crm/segments/` | `customer.segment.manage` | Create segment |
| PATCH | `/api/crm/segments/{id}/` | `customer.segment.manage` | Update segment |
| GET | `/api/crm/consents/` | `customer.consent.view` | List consents |
| POST | `/api/crm/consents/` | `customer.consent.manage` | Grant/revoke consent |
| POST | `/api/crm/customer-merge-requests/` | `customer.merge.request` | Request merge |
| POST | `/api/crm/customer-merge-requests/{id}/approve/` | `customer.merge.approve` | Approve merge |
| POST | `/api/crm/customer-merge-requests/{id}/reject/` | `customer.merge.approve` | Reject merge |

### Dashboard

| Method | URL | Permission | Description |
|---|---|---|---|
| GET | `/api/crm/dashboard/` | `crm.dashboard.view` | CRM KPIs + top customers |

### Common query parameters

| Parameter | Applies to | Description |
|---|---|---|
| `search` | Customer list | Search name/phone/email/number |
| `restaurant_id` | Customer list | Filter by restaurant |
| `segment` | Customer list | Filter by segment code |
| `tag` | Customer list | Filter by tag code |
| `is_active` | Customer list | true/false |
| `is_blocked` | Customer list | true/false |
| `date_from` / `date_to` | Order/visit/spending history | Date range |
| `branch_id` | Most sub-resources | Filter by branch |
| `rating` | Feedback | Filter by rating (1–5) |
| `status` | Feedback / visits | Filter by status |
| `page` / `page_size` | All paginated endpoints | Pagination |

---

## 15. Event Integrations

### Signals (Django post_save)

| Signal | Trigger | CRM Action |
|---|---|---|
| `orders.Order` saved (status=CONFIRMED, customer set) | `crm/signals.py` | `CustomerVisitService.record_visit_for_order()` + queue stats refresh |
| `billing.Bill` saved (status=FINALIZED, customer on order) | `crm/signals.py` | `LoyaltyService.earn_points_for_bill()` |
| `billing.Bill` saved (status=CANCELLED/VOID) | `crm/signals.py` | `LoyaltyService.reverse_points_for_bill()` |
| `payments.PaymentRefund` saved (status=PROCESSED) | `crm/signals.py` | `LoyaltyService.reverse_points_for_bill()` |

**All signal handlers use `transaction.on_commit()`** — CRM actions only fire after the source transaction commits. A CRM failure never rolls back a business transaction.

### Notifications dispatched (Phase 16 integration)

| CRM Event | Notification Type | Severity |
|---|---|---|
| Points earned for a bill | `CRM_LOYALTY_POINTS_EARNED` | LOW |
| Balance crosses a reward threshold | `CRM_REWARD_AVAILABLE` | LOW |
| Low-rating feedback submitted (≤2) | `CRM_FEEDBACK_SUBMITTED` | HIGH |
| Feedback with rating 3–5 submitted | `CRM_FEEDBACK_SUBMITTED` | MEDIUM |

All notifications go through `create_and_dispatch()` with `transaction.on_commit()`.

### Real-time WebSocket events

After DB commit, the following events are available for frontend real-time updates (via Phase 16 channel layer):
- `crm.customer.created`
- `crm.loyalty.points_earned`
- `crm.feedback.created`

---

## 16. Celery Periodic Tasks

| Task name | Schedule | Description |
|---|---|---|
| `crm.expire_loyalty_points` | Daily | Expire points in programs with `point_expiry_days` configured |
| `crm.cleanup_expired_redemptions` | Hourly | Mark `CONFIRMED` redemptions past `expires_at` as `EXPIRED` |
| `crm.run_segmentation_all_restaurants` | Daily | Re-evaluate segments for all active restaurant customers |
| `crm.refresh_customer_statistics` | On-demand (event-driven) | Refresh computed stats for a single customer |

All periodic tasks are **idempotent** — running them multiple times with the same input produces the same result without duplicate records.

---

## 17. Database Design Notes

### Key constraints

| Constraint | Model | Purpose |
|---|---|---|
| `unique_customer_number_per_restaurant` | Customer | Prevents duplicate customer numbers within a restaurant |
| `unique_loyalty_account_per_program` | LoyaltyAccount | One account per customer per program |
| `unique_loyalty_transaction_per_reference` | LoyaltyTransaction | Idempotency for earning/reversal |
| `unique_active_tag_per_customer` | CustomerTagAssignment | No duplicate active tags |
| `unique_active_segment_per_customer` | CustomerSegmentAssignment | No duplicate active segment assignments |
| `unique_consent_per_customer_type` | CustomerConsent | One consent row per type per customer |
| `unique_tag_code_per_restaurant` | CustomerTag | Tag codes are unique per restaurant |
| `unique_segment_code_per_restaurant` | CustomerSegment | Segment codes are unique per restaurant |

### Immutable models

The following models enforce append-only via `save()` guard (raise `ValueError` on update):
- `LoyaltyTransaction`
- `CustomerConsentHistory`
- `CRMAuditLog`

### Indexes

All foreign keys that appear in common filters are indexed. Composite indexes cover the most frequent access patterns:
- `(restaurant, is_active)` on Customer
- `(customer, created_at)` on CustomerVisit
- `(reference_type, reference_id)` on LoyaltyTransaction
- `(restaurant, status)` on CustomerFeedback

### Decimal precision

All monetary and point values use `DecimalField` — never `float`. Loyalty `points_per_currency_unit` uses 4 decimal places to support fractional earning rates (e.g., `0.5000` = 1 point per ₹2).

---

*RestaurantFlow Phase 17 — Customer CRM, Loyalty & Feedback*
