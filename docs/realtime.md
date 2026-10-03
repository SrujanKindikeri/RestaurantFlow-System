# Real-Time Architecture — RestaurantFlow Phase 7

## Stack

| Component | Technology |
|---|---|
| Transport | WebSocket |
| Server-side | Django Channels 4.x |
| Channel Layer | channels-redis (Redis backend) |
| Client-side | Browser WebSocket API (native) |
| Authentication | JWT (simplejwt) via query string |

---

## Architecture Diagram

```
Cashier / Waiter
      │
      ▼
Django REST API  ──→  PostgreSQL  (Order CONFIRMED)
      │
      ▼
kitchen/signals.py  ──→  send_order_to_kitchen()
      │
      ▼
PostgreSQL  (KitchenOrder created)
      │
      ▼
publish_kitchen_event()  ──→  Redis Channel Layer
      │
      ▼
KitchenConsumer.kitchen_event()
      │
      ▼
WebSocket  ──→  KDS Browser
```

The reverse path (kitchen → POS):

```
Kitchen Staff (KDS browser)
      │
      ▼
POST /api/kitchen/orders/<id>/accept/
      │
      ▼
Django  ──→  PostgreSQL  (state updated)
      │
      ▼
publish_kitchen_event()  ──→  Redis  ──→  all KDS consumers for branch
```

---

## WebSocket URL

```
ws://host/ws/kitchen/<branch_id>/
```

The `branch_id` (UUID) is validated server-side. Supplying a different branch UUID does not grant access — the consumer checks `can_access_branch(user, branch)` regardless.

---

## Channel Group Naming

```
kitchen_{branch_id}
```

One group per branch. All KDS screens connected to the same branch share one group, so any event reaches all of them.

**Branch isolation:** A consumer for Branch A is only added to group `kitchen_{branch_a_id}`. Events sent to `kitchen_{branch_b_id}` never reach Branch A consumers.

Future station groups (not built in Phase 7):
```
kitchen_{branch_id}_station_{station_id}
```

---

## Authentication Flow

```
Client → ws://host/ws/kitchen/{branch_id}/?token={jwt}
                │
                ▼
KitchenConsumer.connect()
  1. Extract JWT from query string
  2. validate_jwt_token() → User
  3. Check user.is_active
  4. Check has_permission(user, "kitchen.view")
  5. Check can_access_branch(user, branch)
  6. channel_layer.group_add(group_name, channel_name)
  7. accept()
  8. _send_initial_sync() → current kitchen state
```

**Close codes on rejection:**

| Code | Reason |
|---|---|
| 4001 | Invalid / missing JWT token |
| 4003 | Authenticated but no `kitchen.view` permission |
| 4004 | Authenticated but no access to requested branch |
| 4005 | Redis group_add failed |

---

## Event Types

All events follow this envelope:

```json
{
  "type": "kitchen.event",
  "payload": {
    "event_id": "uuid",
    "event": "kitchen.order.created",
    "kitchen_order_id": "uuid",
    "order_id": "uuid",
    "order_number": "C01-20261003-0001",
    "order_type": "TAKEAWAY",
    "status": "NEW",
    "priority": "NORMAL",
    "branch_id": "uuid",
    "received_at": "2026-10-03T10:00:00Z",
    "timestamp": "2026-10-03T10:00:01Z",
    "table": null,
    "counter": "C01"
  }
}
```

| Event | Trigger |
|---|---|
| `kitchen.order.created` | Order confirmed → KitchenOrder created |
| `kitchen.order.accepted` | KitchenOrder NEW → ACCEPTED |
| `kitchen.order.preparing` | KitchenOrder ACCEPTED → PREPARING |
| `kitchen.order.ready` | KitchenOrder PREPARING → READY |
| `kitchen.order.cancelled` | KitchenOrder → CANCELLED |
| `kitchen.item.preparing` | KitchenOrderItem NEW → PREPARING |
| `kitchen.item.ready` | KitchenOrderItem PREPARING → READY |
| `kitchen.priority.changed` | Priority updated |

**Events never contain:** unit_price, tax_rate, cash amounts, discount, profit, or any financial data.

---

## Initial State Sync

On every connect (including reconnect), the consumer sends the current kitchen state:

```json
{
  "type": "kitchen.sync",
  "branch_id": "uuid",
  "orders": [ ...KitchenOrderListSerializer data... ]
}
```

This reconciles any events missed during a disconnection. The client merges this full list into its local state, replacing the previous snapshot.

---

## Reconnection Strategy (Client)

Implemented in `useKitchenWebSocket.ts`:

```
WebSocket closes (non-auth error)
  │
  ├─→ Wait 1s  → reconnect attempt
  │   (failure)
  ├─→ Wait 2s  → reconnect attempt
  │   (failure)
  ├─→ Wait 4s  → ...
  │
  └─→ Max backoff: 30s
      On success: backoff resets to 1s
      On connect: receive kitchen.sync → reconcile state
```

Auth-related close codes (4001, 4003, 4004) do **not** trigger reconnect.

---

## Event Deduplication (Client)

The client maintains a `Set<string>` of seen `event_id` values (capped at 500). If the same event arrives twice (e.g. after a reconnect that overlaps with a new event), it is discarded silently. This prevents duplicate sound notifications and duplicate UI state updates.

---

## Transaction-First Event Publishing

Events are published **after** the database transaction is committed:

```python
with transaction.atomic():
    # ... update state ...
    locked.save(...)
# transaction committed here

publish_kitchen_event(event_type, kitchen_order)  # after commit
```

If Redis is unavailable, `publish_kitchen_event` logs an error but does **not** raise. The DB state is already correct. The KDS recovers via REST sync on the next WebSocket reconnect.

**This means:** Redis failure = delayed/missing real-time events. DB failure = the operation did not succeed at all. The DB is always the source of truth.

---

## Transactional Outbox (Future)

For stronger at-least-once delivery guarantees, a transactional outbox can be introduced:

```
DB transaction:
  UPDATE kitchen_order SET status = 'ACCEPTED'
  INSERT kitchen_event_outbox (event_type, payload, sent=False)
COMMIT

Background worker:
  SELECT * FROM kitchen_event_outbox WHERE sent=False
  → channel_layer.group_send(...)
  → UPDATE sent=True
```

Phase 7 does not implement the outbox. The service functions are structured to support this pattern without architectural changes.

---

## Redis Failure Behaviour

| Scenario | Result |
|---|---|
| Redis down at startup | Channel layer unavailable; WebSocket connections fail; REST API still works |
| Redis down during publish | Event not delivered; DB state already committed; logged as ERROR |
| Redis down during connect | Consumer cannot join group; connection closed with code 4005 |
| Redis recovers | Next WebSocket reconnect succeeds; initial sync delivers current state |

The application never falsely reports a DB operation as successful based only on a Redis event being published.

---

## Django Channels ASGI Configuration

`config/asgi.py`:

```python
application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AuthMiddlewareStack(
        URLRouter(websocket_urlpatterns)
    ),
})
```

WebSocket URL patterns (`kitchen/routing.py`):

```python
websocket_urlpatterns = [
    re_path(r"^ws/kitchen/(?P<branch_id>[0-9a-f-]{36})/$", KitchenConsumer.as_asgi()),
]
```

---

## Running with Channels

Django Channels requires an ASGI server (not the default WSGI/Gunicorn):

```bash
# Development
uvicorn config.asgi:application --reload --host 0.0.0.0 --port 8000

# Production
daphne -b 0.0.0.0 -p 8000 config.asgi:application
```

The existing `docker-compose.yml` Redis service (`restaurantflow_redis`) is used as the channel layer backend. No additional Redis instance is needed.
