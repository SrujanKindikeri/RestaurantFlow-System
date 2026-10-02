# Cash Sessions — Lifecycle & Reconciliation

## Overview

A **CounterSession** represents one complete cash session at a physical POS counter. It tracks the cash flow from session open to close, and produces a **reconciliation variance** at close time.

---

## Session Lifecycle

```
Counter ACTIVE (no session)
          │
          ▼ POST /api/counters/{id}/sessions/open/
          │ { "opening_cash": "5000.00" }
          │
     ┌────▼────┐
     │  OPEN   │  ◄── Transactions happen here (Phase 5+)
     └────┬────┘
          │
          ├──── Normal close
          │     POST /api/counter-sessions/{id}/close/
          │     { "actual_cash": "9850.00", "closing_note": "Normal" }
          │
          │                         ┌─────────────┐
          │                         │   CLOSED    │
          │                         └─────────────┘
          │
          └──── Manager force-close
                POST /api/counter-sessions/{id}/force-close/
                { "actual_cash": "4800.00", "reason": "Emergency" }

                                    ┌──────────────┐
                                    │ FORCE_CLOSED │
                                    └──────────────┘
```

---

## Opening a Session

**Who can open:** Any user with `counter.session.open` permission who has access to the counter's branch.

**Validations:**
- Counter must be `ACTIVE`
- No existing `OPEN` session on this counter (enforced at DB level + service layer)
- `opening_cash ≥ 0`
- The authenticated user is automatically set as `opened_by` — the client cannot spoof this

**Request:**
```http
POST /api/counters/{counter_id}/sessions/open/
Content-Type: application/json

{
  "opening_cash": "5000.00",
  "shift": "uuid-of-shift"  (optional)
}
```

**Response (201 Created):**
```json
{
  "id": "uuid",
  "counter": "uuid",
  "counter_code": "C01",
  "status": "OPEN",
  "opening_cash": "5000.00",
  "expected_cash": "5000.00",
  "opened_at": "2026-10-02T08:03:00Z",
  "opened_by_email": "cashier@restaurant.com"
}
```

**Concurrency protection:**  
The service layer uses `select_for_update()` inside `transaction.atomic()` to lock the counter row. If two requests arrive simultaneously, only one succeeds. The second returns `COUNTER_SESSION_ALREADY_OPEN`.

---

## Closing a Session

**Who can close:** Any user with `counter.session.close` and access to the counter.

**Validations:**
- Session must be `OPEN`
- `actual_cash ≥ 0`
- `cash_difference` is **calculated by the backend** — never accepted from the client

**Cash reconciliation formula:**
```
cash_difference = actual_cash − expected_cash
```

**Examples:**
```
Expected = ₹10,000  Actual = ₹10,000  →  Difference = ₹0      (balanced)
Expected = ₹10,000  Actual = ₹9,850   →  Difference = −₹150   (shortage)
Expected = ₹10,000  Actual = ₹10,200  →  Difference = +₹200   (surplus)
```

A non-zero difference is a **reconciliation variance** only. It is not automatically classified as fraud or theft.

**Request:**
```http
POST /api/counter-sessions/{session_id}/close/
Content-Type: application/json

{
  "actual_cash": "9850.00",
  "closing_note": "Normal closing. All clear."
}
```

**Response (200 OK):**
```json
{
  "id": "uuid",
  "status": "CLOSED",
  "opening_cash": "10000.00",
  "expected_cash": "10000.00",
  "actual_cash": "9850.00",
  "cash_difference": "-150.00",
  "closed_at": "2026-10-02T22:05:00Z",
  "closed_by_email": "cashier@restaurant.com"
}
```

---

## Force-Closing a Session

**Who can force-close:** Users with `counter.session.force_close` (Manager, Restaurant Owner, Company Head).

**Use cases:**
- Cashier left without closing
- System outage interrupted normal close
- Emergency closure

`actual_cash` is optional — it may not be available in emergency scenarios.

**Request:**
```http
POST /api/counter-sessions/{session_id}/force-close/
Content-Type: application/json

{
  "reason": "Cashier left unexpectedly before closing",
  "actual_cash": "4800.00"
}
```

The `reason` is stored in `closing_note` and `closed_by` records the manager who performed the action.

---

## Expected Cash — Phase 4 vs Future

### Phase 4 (current)

No orders or payments exist yet. Expected cash equals opening cash:

```
expected_cash = opening_cash
```

### Phase 5+ (future)

Once order/payment data is available, expected cash will be calculated as:

```
expected_cash = opening_cash
              + cash_sales
              − cash_refunds
              ± cash_adjustments
```

The model is already designed to support this. The `expected_cash` field can be updated by future transaction aggregations without any schema changes.

---

## Session Rules

| Rule | Enforcement |
|------|-------------|
| Only one OPEN session per counter | DB partial unique constraint + service `select_for_update` |
| `cash_difference` is backend-calculated | Client-submitted differences are ignored |
| Closed sessions cannot be re-closed | Service validates `status == OPEN` before any close action |
| Opening cash cannot be changed after open | Only written at creation; no patch endpoint |
| Force close requires elevated permission | `counter.session.force_close` checked in service layer |

---

## Correction Workflow (Future)

Ordinary cashiers cannot edit historical closed sessions. Future correction flow:

```
Request Correction
       ↓
Manager Approval
       ↓
Adjustment recorded
       ↓
Audit Log entry
```

Phase 4 does not implement the approval engine, but the model and service layer do not prevent future implementation. No historical session data is deleted.

---

## Error Codes

| Code                              | Meaning                                         |
|-----------------------------------|-------------------------------------------------|
| `COUNTER_NOT_FOUND`               | Counter UUID not found or out of scope          |
| `COUNTER_INACTIVE`                | Counter status is INACTIVE                      |
| `COUNTER_MAINTENANCE`             | Counter status is MAINTENANCE                   |
| `COUNTER_ACCESS_DENIED`           | User cannot access this counter                 |
| `COUNTER_SESSION_ALREADY_OPEN`    | A session is already open on this counter       |
| `COUNTER_SESSION_NOT_OPEN`        | Session is not OPEN; cannot close               |
| `COUNTER_SESSION_ALREADY_CLOSED`  | Session is already closed                       |
| `INVALID_OPENING_CASH`            | Negative or invalid opening cash value          |
| `INVALID_ACTUAL_CASH`             | Negative or invalid actual cash value           |
| `FORCE_CLOSE_NOT_ALLOWED`         | User lacks force-close permission               |

All errors follow the standard envelope:
```json
{
  "error": {
    "code": "COUNTER_SESSION_ALREADY_OPEN",
    "message": "This counter already has an open session."
  }
}
```

---

## UI Flows

### Open Counter (Cashier)

```
Login
  ↓
Counter Dashboard  →  Select Counter
  ↓
Counter Detail  →  "Open Counter" button
  ↓
OpenSessionForm:  Enter Opening Cash (₹)
                  Select Shift (optional)
  ↓
Counter now shows OPEN session with live details
```

### Close Counter (Cashier)

```
Counter Detail  →  "Close Counter" button
  ↓
CloseSessionForm:  Shows Expected Cash
                   Enter Actual Cash
                   Live difference preview
                   Enter Closing Note
  ↓
Backend calculates final cash_difference
Session status → CLOSED
```

### Force Close (Manager)

```
Counter Detail  →  "Force Close" button
  ↓
ForceCloseForm:  Warning banner shown
                 Enter Reason (required)
                 Enter Actual Cash (optional)
  ↓
Session status → FORCE_CLOSED
closed_by = Manager
```
