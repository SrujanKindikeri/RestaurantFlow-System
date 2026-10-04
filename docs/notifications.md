# RestaurantFlow — Notification & Communication Center

**Phase 16**

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Event Flow](#2-event-flow)
3. [Notification Lifecycle](#3-notification-lifecycle)
4. [Delivery Channels](#4-delivery-channels)
5. [Recipient Resolution](#5-recipient-resolution)
6. [Notification Types](#6-notification-types)
7. [Preferences](#7-preferences)
8. [Templates](#8-templates)
9. [Provider Abstraction](#9-provider-abstraction)
10. [Retries](#10-retries)
11. [Idempotency](#11-idempotency)
12. [Rate Limiting / Cooldown](#12-rate-limiting--cooldown)
13. [WebSockets](#13-websockets)
14. [Celery](#14-celery)
15. [Redis](#15-redis)
16. [Security & Scope](#16-security--scope)
17. [Failure Handling](#17-failure-handling)
18. [API Reference](#18-api-reference)
19. [Frontend](#19-frontend)
20. [Configuration Reference](#20-configuration-reference)
21. [Running Celery](#21-running-celery)

---

## 1. Architecture Overview

```
Business Event (payment, kitchen, inventory, expense, …)
        ↓
Django Signal (post_save / transaction.on_commit)
        ↓
notifications/event_handlers.py
        ↓
NotificationService.create_notification()   [DB write — atomic]
        ↓
transaction.on_commit → Celery: dispatch_notification.delay()
        ↓
RecipientResolver.resolve()                 [permission-scoped]
        ↓
NotificationRecipient rows created
        ↓
NotificationService.queue_delivery()
        ↓  (per channel, per recipient)
Celery: deliver_notification_channel.delay()
        ↓
DeliveryProvider.send()
        ↓
        ├── InAppProvider       → mark DELIVERED in DB
        ├── WebSocketProvider   → channels.group_send → client
        ├── EmailProvider       → django.core.mail
        ├── SMSProvider         → Twilio / Vonage (if configured)
        ├── WhatsAppProvider    → Meta Cloud API (if configured)
        └── TelegramProvider    → Telegram Bot API (if configured)
```

**Key properties:**
- Business transaction commits **before** any notification work begins.
- A failed email **never** rolls back a successful payment.
- All external delivery is asynchronous via Celery.
- WebSocket is **not** the source of truth — the REST API is.

---

## 2. Event Flow

### Signal hooks

| App | Signal | Event |
|-----|--------|-------|
| `payments` | `post_save Payment` | COMPLETED → PAYMENT_COMPLETED, FAILED → PAYMENT_FAILED |
| `payments` | `post_save PaymentRefund` | PROCESSED → REFUND_PROCESSED |
| `financials` | `post_save Expense` | SUBMITTED → EXPENSE_APPROVAL_REQUIRED, APPROVED/REJECTED → outcome |
| `inventory` | `post_save StockBalance` | LOW_STOCK / OUT_OF_STOCK detected |
| `kitchen` | `post_save KitchenOrder` | READY / DELAYED |
| `central_control` | `post_save CentralAlert` | created → CENTRAL_ALERT_CREATED |
| `central_control` | `post_save CentralIssue` | ASSIGNED / RESOLVED |

All handlers use `transaction.on_commit()` to ensure notifications fire only after the source transaction commits.

### Direct calls

Some notifications are dispatched programmatically (not via signal):
- `dispatch_accounting_posting_failed_notification()` — called from accounting error handlers
- `dispatch_payable_overdue_notification()` — called from Celery beat or alert detector

---

## 3. Notification Lifecycle

```
CREATED
   ↓
Recipients resolved → NotificationRecipient rows (status: PENDING)
   ↓
Delivery queued → NotificationDelivery rows (status: PENDING)
   ↓
Provider sends
   ↓
   ├── Success → DELIVERED
   ├── Failure (retryable) → PENDING with next_retry_at
   └── Failure (terminal) → FAILED
   
User actions:
   DELIVERED → READ (via mark_read)
   READ → ACKNOWLEDGED (via acknowledge)
```

### Expiration

`notification.expires_at` — optional. If set:
- Expired notifications are hidden from the default UI filter.
- They are **not** deleted immediately; history is preserved.
- The cleanup task removes **read** expired notifications older than 7 days.

---

## 4. Delivery Channels

| Channel | Provider | Notes |
|---------|----------|-------|
| `IN_APP` | InAppProvider | Always available. Marks recipient DELIVERED immediately. |
| `WEBSOCKET` | WebSocketProvider | Via Django Channels / Redis. Failure ≠ notification loss. |
| `EMAIL` | EmailProvider | Uses `settings.EMAIL_BACKEND`. Provider-independent. |
| `SMS` | SMSProvider | Requires `SMS_PROVIDER` env var. Returns NOT_CONFIGURED if absent. |
| `WHATSAPP` | WhatsAppProvider | Requires `WHATSAPP_PROVIDER` env var. Returns NOT_CONFIGURED if absent. |
| `TELEGRAM` | TelegramProvider | Requires `TELEGRAM_BOT_TOKEN` env var. Returns NOT_CONFIGURED if absent. |

### Severity → channel selection

| Severity | Channels used |
|----------|---------------|
| INFO / LOW | IN_APP |
| MEDIUM | IN_APP + WEBSOCKET |
| HIGH | IN_APP + WEBSOCKET + EMAIL |
| CRITICAL | All configured channels |

User preferences further filter which channels are actually used.

---

## 5. Recipient Resolution

`notifications/recipient_resolver.py` — `RecipientResolver`

**Rules:**
1. Each notification type has a registered handler that returns a list of `User` candidates.
2. All candidates are validated against `accounts.access.can_access_organization()`.
3. Inactive users are excluded.
4. Results are deduplicated by PK.

**Examples:**

| Notification | Recipients |
|-------------|-----------|
| `EXPENSE_APPROVAL_REQUIRED` | Users with `financials.expense.approve` at the restaurant scope |
| `CENTRAL_ISSUE_ASSIGNED` | The assignee user + creator |
| `PAYMENT_FAILED` | Cashier who attempted the payment + restaurant manager |
| `INVENTORY_LOW_STOCK` | Users with `inventory.view` at the branch |
| `CENTRAL_ALERT_CREATED` | Users with `central_control.alert.view` at the company |

The resolver **never** receives recipient lists from the event producer — it always derives recipients from stored permissions.

---

## 6. Notification Types

34 types across 8 categories:

| Category | Types |
|----------|-------|
| Orders | ORDER_CONFIRMED, ORDER_READY, ORDER_CANCELLED |
| Kitchen | KITCHEN_ORDER_READY, KITCHEN_ORDER_DELAYED, KITCHEN_BACKLOG |
| Inventory | INVENTORY_LOW_STOCK, INVENTORY_OUT_OF_STOCK, INVENTORY_PURCHASE_RECEIVED, INVENTORY_CONSUMPTION_FAILED |
| Payments | PAYMENT_COMPLETED, PAYMENT_FAILED, REFUND_PROCESSED |
| Expenses | EXPENSE_SUBMITTED, EXPENSE_APPROVAL_REQUIRED, EXPENSE_APPROVED, EXPENSE_REJECTED |
| Payables | PAYABLE_OVERDUE, SUPPLIER_INVOICE_SUBMITTED |
| Accounting | ACCOUNTING_POSTING_FAILED, ACCOUNTING_PERIOD_CLOSED |
| Central Control | CENTRAL_ALERT_CREATED, CENTRAL_ALERT_RESOLVED, CENTRAL_ISSUE_ASSIGNED, CENTRAL_ISSUE_RESOLVED |
| Access | USER_ACCESS_GRANTED, USER_ACCESS_REVOKED, COUNTER_SESSION_CLOSED |
| System | SYSTEM_HEALTH_DEGRADED, NOTIFICATION_PROVIDER_FAILURE |

---

## 7. Preferences

`NotificationPreference` model: `(user, notification_type, channel)` → `enabled` bool.

**Fallback chain:**
1. Explicit `NotificationPreference` row for this user.
2. `DEFAULT_CHANNEL_PREFS` in `constants.py`.

Users can update preferences via `POST /api/notifications/preferences/` or the `/settings/notifications` UI page.

**Defaults summary (partial):**

| Type | IN_APP | EMAIL |
|------|--------|-------|
| PAYMENT_FAILED | ✓ | ✓ |
| INVENTORY_LOW_STOCK | ✓ | ✗ |
| EXPENSE_APPROVAL_REQUIRED | ✓ | ✓ |
| CENTRAL_ALERT_CREATED | ✓ | ✓ |
| CENTRAL_ISSUE_ASSIGNED | ✓ | ✓ |
| SYSTEM_HEALTH_DEGRADED | ✓ | ✓ |

SMS, WhatsApp, Telegram are **off** by default (require explicit opt-in and provider configuration).

---

## 8. Templates

`NotificationTemplate` model stores per-type, per-channel message templates.

**Lookup priority:** Company-specific template → Global template → Fallback to `notification.title` / `notification.message`.

### Safe variable substitution

Templates use `{{variable_name}}` syntax. Only variables in `SAFE_TEMPLATE_VARS` are allowed:

```
order_number, branch_name, restaurant_name, company_name,
item_name, quantity, alert_title, issue_title, expense_number,
payable_amount, payable_due_date, payment_amount, refund_amount,
user_name, user_email, kitchen_order_number, delay_minutes,
low_stock_count, provider_name, channel_name, failure_reason,
action_url, timestamp
```

**No `eval()`, no arbitrary Python execution. Unknown variables raise `InvalidTemplateVariable`.**

**Example template:**

```
Subject: Low Stock Alert — {{branch_name}}
Body:    {{item_name}} is below reorder level at {{branch_name}}.
         Current quantity: {{quantity}}.
```

---

## 9. Provider Abstraction

All providers extend `BaseNotificationProvider` (`notifications/delivery/base.py`):

```python
class BaseNotificationProvider(ABC):
    provider_code: str
    channel_code: str

    def send(self, payload: DeliveryPayload) -> DeliveryResult: ...
    def validate_configuration(self) -> bool: ...
    def get_status(self) -> dict: ...
```

`DeliveryResult` always has:
- `success: bool`
- `status: str` (one of `DELIVERY_*` constants)
- `failure_reason: str` (never contains secrets)
- `not_configured: bool` (True when provider has no config)

**Adding a new provider:**
1. Create a class in `notifications/delivery/`.
2. Extend `BaseNotificationProvider`.
3. Register in `_get_provider()` in `services.py`.
4. Add `CHANNEL_*` constant if it's a new channel.

---

## 10. Retries

External delivery failures are retried up to `MAX_DELIVERY_ATTEMPTS = 3`:

| Attempt | Delay |
|---------|-------|
| 1st | Immediate |
| 2nd | 60 seconds |
| 3rd | 300 seconds (5 min) |
| After 3rd | FAILED (terminal) |

**Not retried:**
- `NOT_CONFIGURED` — provider not set up
- `CANCELLED` — delivery manually cancelled
- Invalid recipient (bad email/phone)
- Permission failures

Retries are driven by the `retry_pending_deliveries` Celery beat task (runs every 2 minutes).

---

## 11. Idempotency

### Notification creation

Before creating a new `Notification`, the service checks for an existing row with:
```
(company, notification_type, source_type, source_id)
within the last 24 hours
```
If found, the existing notification is returned — no duplicate is created.

### Delivery

Before creating a `NotificationDelivery` row, `queue_delivery()` checks for an existing non-FAILED row for the same `(notification, recipient, channel)`. If one exists, no new row is created.

### Celery tasks

Tasks check delivery status before acting. If already DELIVERED or CANCELLED, the task is a no-op.

---

## 12. Rate Limiting / Cooldown

Some notification types are subject to cooldown windows stored in Redis:

| Type | Cooldown |
|------|----------|
| INVENTORY_LOW_STOCK | 1 hour |
| INVENTORY_OUT_OF_STOCK | 1 hour |
| PAYMENT_FAILED | 5 minutes |
| KITCHEN_BACKLOG | 5 minutes |
| KITCHEN_ORDER_DELAYED | 5 minutes |

**Critical notification types are never suppressed by cooldown:**
```
CENTRAL_ALERT_CREATED, CENTRAL_ISSUE_ASSIGNED, USER_ACCESS_REVOKED,
SYSTEM_HEALTH_DEGRADED, NOTIFICATION_PROVIDER_FAILURE,
INVENTORY_OUT_OF_STOCK, ACCOUNTING_POSTING_FAILED
```

Use `bypass_cooldown=True` in `create_notification()` for programmatic overrides.

### Provider failure alerting

When an external channel (email, SMS, etc.) fails repeatedly:
- Counter is tracked in Redis with a 10-minute window.
- After 5 failures, a `NOTIFICATION_PROVIDER_FAILURE` notification is created for Central Control.
- Counter is reset after the alert is created to prevent spamming.

---

## 13. WebSockets

**URL:** `ws://host/ws/notifications/?token=<jwt>`

**Consumer:** `notifications/consumers.py` — `NotificationsConsumer`

**Group name:** `notifications_user_{user_id}`

Each authenticated user joins **only their own group**. The group name is derived server-side from the validated JWT — the client cannot join another user's group.

### Server → client events

```json
// New notification
{
  "type": "notification.event",
  "payload": {
    "type": "notification.created",
    "notification_id": "...",
    "notification_type": "KITCHEN_ORDER_DELAYED",
    "severity": "HIGH",
    "title": "Kitchen Delay: Order ORD-204",
    "created_at": "2026-10-04T12:00:00Z"
  }
}

// Read state change
{
  "type": "notification.event",
  "payload": {
    "type": "notification.read",
    "notification_id": "..."
  }
}

// Unread count update
{
  "type": "notification.unread_count",
  "count": 7
}
```

### Client → server messages

```json
{ "type": "ping" }   → { "type": "pong" }
{ "type": "sync" }   → server sends unread_count
```

### Reconnect / resync

WebSocket is **not** the source of truth. After reconnect, the frontend:
1. Calls `GET /api/notifications/?unread=true` to resync missed notifications.
2. Invalidates `useUnreadCount` and `useNotifications` React Query caches.

---

## 14. Celery

**App:** `config/celery.py` — `restaurantflow`

**Tasks:**

| Task | Name | Trigger |
|------|------|---------|
| `dispatch_notification` | `notifications.dispatch_notification` | On-demand after DB commit |
| `deliver_notification_channel` | `notifications.deliver_notification_channel` | On-demand per delivery |
| `retry_pending_deliveries` | `notifications.retry_pending_deliveries` | Beat: every 120s |
| `cleanup_old_notifications` | `notifications.cleanup_old_notifications` | Beat: every 24h |

**Starting workers:**

```bash
# Worker
celery -A config worker -l info

# Beat scheduler
celery -A config beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler

# Both in one process (dev only)
celery -A config worker --beat -l info
```

All tasks use `@shared_task` and are idempotent.

---

## 15. Redis

Redis is used for:

| Purpose | Key pattern |
|---------|-------------|
| Django Channels layer | Internal Channels keys |
| Celery broker + result backend | Internal Celery keys |
| Unread count cache | `notifications:unread:{user_id}` (TTL: 30s) |
| Cooldown window | `notifications:cooldown:{type}:{scope}` |
| Provider failure counter | `notifications:provider_fail:{channel}:{company_id}` |
| Django cache | Standard cache keys |

Redis is **not** the primary notification store. PostgreSQL is the source of truth.

---

## 16. Security & Scope

### Company isolation

Every `Notification` has a `company` FK. The recipient resolver only returns users who `can_access_organization(user, notification.company)`.

A Company A notification **can never** reach a Company B user.

### Restaurant / branch isolation

Notifications for a specific restaurant/branch only reach users with assignments scoped to that restaurant/branch.

### User notification isolation

`GET /api/notifications/` returns only the authenticated user's own `NotificationRecipient` rows. Users cannot see each other's notification state.

### WebSocket authorization

JWT is validated server-side on every WebSocket connect. The user's group name is derived from their validated `user_id` — the client cannot supply a different user's group.

### Provider configuration

`NotificationProviderConfig.configuration_metadata` must never contain raw secrets. The serializer rejects keys like `api_key`, `password`, `token`, `secret`. Actual credentials live in environment variables.

### Template safety

Template rendering uses regex-based `{{variable}}` substitution against an explicit allow-list. No `eval()`, no `exec()`, no arbitrary Python execution.

---

## 17. Failure Handling

| Scenario | Behavior |
|----------|----------|
| Redis unavailable | WS delivery returns FAILED; in-app still persisted. |
| Email provider unavailable | Retried up to 3 times, then FAILED. Provider failure counter incremented. |
| Celery worker unavailable | Delivery stays PENDING; retry task will pick it up when worker restarts. |
| WebSocket unavailable | Delivery returns FAILED; in-app notification still visible via REST. |
| Database temporarily unavailable | Notification creation fails; business transaction is unaffected (errors are caught in on_commit). |
| Provider 500 / timeout | Retried with backoff. |
| Invalid email address | Marked FAILED immediately, not retried. |
| Invalid phone number | Marked FAILED immediately, not retried. |
| Duplicate event fired twice | Second call hits idempotency check → existing notification returned, no duplicate created. |
| User preferences disabled channel | Channel delivery skipped — no NotificationDelivery row created. |
| Core transaction (payment) fails before commit | `on_commit` never fires → no notification sent. |

---

## 18. API Reference

### User endpoints

| Method | URL | Description |
|--------|-----|-------------|
| GET | `/api/notifications/` | List user's notifications (paginated) |
| GET | `/api/notifications/unread-count/` | `{"count": N}` |
| GET | `/api/notifications/{id}/` | Detail |
| POST | `/api/notifications/{id}/read/` | Mark as read |
| POST | `/api/notifications/{id}/acknowledge/` | Acknowledge |
| POST | `/api/notifications/read-all/` | Mark all read |
| GET | `/api/notifications/preferences/` | List preferences |
| POST | `/api/notifications/preferences/` | Upsert preference |
| PATCH | `/api/notifications/preferences/{id}/` | Update preference |
| GET | `/api/notifications/deliveries/` | User's own delivery history |

### Query parameters for `GET /api/notifications/`

| Param | Type | Description |
|-------|------|-------------|
| `unread` | bool | Filter unread only |
| `notification_type` | string | Exact match |
| `severity` | string | INFO/LOW/MEDIUM/HIGH/CRITICAL |
| `date_from` | ISO date | Filter by created_at |
| `date_to` | ISO date | Filter by created_at |
| `page` | int | Page number |
| `page_size` | int | Page size (max 100) |

### Admin endpoints (requires `notifications.admin` or template/provider permissions)

| Method | URL | Description |
|--------|-----|-------------|
| GET | `/api/notifications/admin/templates/` | List templates |
| POST | `/api/notifications/admin/templates/` | Create template |
| PATCH | `/api/notifications/admin/templates/{id}/` | Update template |
| GET | `/api/notifications/admin/providers/` | List provider configs |
| PATCH | `/api/notifications/admin/providers/{id}/` | Update provider config |
| GET | `/api/notifications/admin/providers/status/` | Provider health check |
| GET | `/api/notifications/admin/deliveries/` | Delivery history (company-scoped) |

---

## 19. Frontend

### Routes

| Route | Component | Description |
|-------|-----------|-------------|
| `/notifications` | `NotificationCenter` | Full notification list |
| `/settings/notifications` | `NotificationPreferences` | Channel preference toggles |

### Components

**`NotificationBell`** (`components/notifications/NotificationBell.tsx`)
- Bell icon in the top header bar
- Red badge showing unread count
- Dropdown showing 5 most recent notifications
- Mark all read / View all actions

### Hooks

| Hook | Purpose |
|------|---------|
| `useNotifications(params)` | List notifications with filters |
| `useUnreadCount()` | Unread count (polls every 20s) |
| `useMarkRead()` | Mark one notification read |
| `useMarkAllRead()` | Mark all read |
| `useAcknowledge()` | Acknowledge a notification |
| `useNotificationPreferences()` | List user preferences |
| `useUpsertPreference()` | Create/update a preference |
| `useNotificationsWebSocket(options)` | Real-time WS delivery |

### WebSocket hook

`useNotificationsWebSocket` mirrors `useKitchenWebSocket`:
- JWT passed as `?token=<jwt>` query param
- Exponential backoff reconnection (1s → 30s)
- Event deduplication by `notification_id` (last 500)
- Auth rejection codes (4001–4099) → no reconnect
- On reconnect: invalidates `useUnreadCount` + `useNotifications` caches

---

## 20. Configuration Reference

### Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `EMAIL_BACKEND` | Console (dev) / SMTP (prod) | Django email backend |
| `EMAIL_HOST` | `localhost` | SMTP server hostname |
| `EMAIL_PORT` | `587` | SMTP port |
| `EMAIL_USE_TLS` | `True` | Enable TLS |
| `EMAIL_HOST_USER` | — | SMTP username |
| `EMAIL_HOST_PASSWORD` | — | SMTP password (never in DB) |
| `DEFAULT_FROM_EMAIL` | `noreply@restaurantflow.app` | From address |
| `SMS_PROVIDER` | — | `TWILIO` or `VONAGE` to enable SMS |
| `TWILIO_ACCOUNT_SID` | — | Twilio account SID |
| `TWILIO_AUTH_TOKEN` | — | Twilio auth token |
| `TWILIO_FROM_NUMBER` | — | Twilio sender phone |
| `VONAGE_API_KEY` | — | Vonage API key |
| `VONAGE_API_SECRET` | — | Vonage API secret |
| `VONAGE_FROM_NAME` | `RestaurantFlow` | Vonage sender name |
| `WHATSAPP_PROVIDER` | — | `WHATSAPP_CLOUD` to enable |
| `WHATSAPP_ACCESS_TOKEN` | — | Meta Cloud API token |
| `WHATSAPP_PHONE_NUMBER_ID` | — | Meta phone number ID |
| `TELEGRAM_BOT_TOKEN` | — | Telegram bot token |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection URL |

### Cooldown / rate limits (constants.py)

| Constant | Default | Description |
|----------|---------|-------------|
| `COOLDOWN_LOW_STOCK_SECONDS` | 3600 | Low-stock notification cooldown |
| `COOLDOWN_PAYMENT_FAILED_SECONDS` | 300 | Payment-failed cooldown |
| `COOLDOWN_PROVIDER_FAILURE_ALERT` | 600 | Provider failure alert cooldown |
| `PROVIDER_FAILURE_THRESHOLD` | 5 | Failures before Central Control alert |
| `MAX_DELIVERY_ATTEMPTS` | 3 | Max delivery retry attempts |

---

## 21. Running Celery

```bash
# From the backend/ directory:

# Start the Celery worker
celery -A config worker -l info

# Start the Celery beat scheduler (periodic tasks)
celery -A config beat -l info \
  --scheduler django_celery_beat.schedulers:DatabaseScheduler

# Combined (development only — not for production)
celery -A config worker --beat -l info

# Monitor tasks
celery -A config flower  # requires: pip install flower
```

The beat scheduler requires `django_celery_beat` migrations to be applied:
```bash
python manage.py migrate django_celery_beat
```

---

*Phase 16 — RestaurantFlow Notification & Communication Center*
