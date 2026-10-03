# Phase 8 — Billing + Invoices + Tax Calculation + Discounts + Bill Corrections

## Overview

Phase 8 introduces the **billing layer** for RestaurantFlow. It converts a confirmed operational
Order into a financial document (Bill) with full tax calculation, discount support, rounding,
finalization, immutability controls, and a correction workflow.

**Phase 8 does NOT implement:**
- Payment gateway, UPI, card, or cash payment recording
- Refunds or payment reconciliation
- Inventory, accounting, or CRM

Payment belongs to Phase 9.

---

## Architecture: Order vs Bill

| Concept | Purpose |
|---------|---------|
| **Order** | Operational transaction — menu items, table/counter, kitchen workflow |
| **Bill** | Financial document — amounts, tax, discount, rounding, grand total |
| **Payment** | Actual money received — Phase 9 |

These are **three separate domains**. An Order is never treated as a Bill.

```
CONFIRMED ORDER
      ↓
    BILL  (DRAFT)
      ↓
  BillItems (snapshots from OrderItems)
      ↓
 apply_discount() [optional]
      ↓
 calculate_bill()
      ↓
 finalize_bill()  →  BILL (FINALIZED, immutable)
      ↓
   Phase 9: PAYMENT
```

---

## Bill Number Format

```
B-{YYYY}-{seq:06d}
```

Examples:
- `B-2026-000001`
- `B-2026-000042`
- `B-2027-000001` (resets annually per branch)

**Bill numbers are different from order numbers.** Order numbers use the format `C01-20261003-0001`.

The `BillSequence` model provides annual, per-branch, concurrency-safe sequences using
`select_for_update()`. Never generated with `MAX(id)+1`.

---

## Bill Status State Machine

```
DRAFT → FINALIZED (terminal — locked forever)
DRAFT → CANCELLED (requires reason)
FINALIZED → CANCELLED (requires bill.cancel permission + reason)
FINALIZED → VOID (escalated — requires bill.void permission)
```

---

## Bill Creation Rules

Bills can only be created from **CONFIRMED** orders.

| Order Status | Can Create Bill? |
|-------------|-----------------|
| DRAFT | ❌ No |
| CONFIRMED | ✅ Yes |
| CANCELLED | ❌ No |

Order types supported: `DINE_IN`, `TAKEAWAY`, `COUNTER`.

**One bill per order** — enforced at the database level (`UniqueConstraint` on `Bill.order`).

Creation is **idempotent**: calling `create_bill_from_order()` twice returns the same bill.

---

## Calculation Sequence

The authoritative calculation happens in `billing/services.py → _compute_bill_totals()`.
This same function is used by the API, finalization, preview, and tests.

```
1. Per BillItem:
   gross_amount = quantity × unit_price_snapshot

2. subtotal = sum(gross_amount for all items)

3. discount_amount =
   PERCENTAGE: subtotal × pct / 100
   FIXED:      min(fixed_value, subtotal)

4. taxable_amount = subtotal − discount_amount

5. Per BillItem (proportional discount):
   discount_ratio = discount_amount / subtotal
   item_discount  = gross × discount_ratio
   item_taxable   = gross − item_discount
   item_tax       = item_taxable × tax_rate / 100

6. tax_amount = sum(item_tax)

7. tax_breakdown = {tax_code: sum_amount, …} (per TaxCode)

8. pre_rounding = taxable_amount + tax_amount

9. rounding_amount = nearest_integer(pre_rounding) − pre_rounding
   (ROUND_HALF_UP; range: −0.49 to +0.50)

10. grand_total = pre_rounding + rounding_amount
```

**All arithmetic uses Python `Decimal` with `ROUND_HALF_UP`. Never `float`.**

---

## Price Source

Billing uses the price **snapshot captured in Phase 6** (`OrderItem.unit_price_snapshot`).

```
At order creation:   Chicken Biryani = ₹250  (snapshot stored)
Later menu changes:  Chicken Biryani = ₹280  (does not affect existing bills)
Bill uses:           ₹250  ← from snapshot
```

This protects historical transaction integrity.

---

## Tax Source

Tax is read from `OrderItem.tax_rate_snapshot` and `OrderItem.tax_code_snapshot`.
These are frozen at order creation time.

**Future tax config changes do not retroactively alter existing bills.**

Tax breakdown is stored as JSON on the Bill:
```json
{
  "GST_5": "25.00",
  "ZERO_TAX": "0.00"
}
```

This supports multi-component taxes (CGST + SGST, etc.) without hard-coding any tax structure.

---

## Discounts

### Types
| Type | Behaviour |
|------|-----------|
| `PERCENTAGE` | e.g. 10% off subtotal |
| `FIXED_AMOUNT` | e.g. ₹50 off subtotal |

### Permission-based limits

| Permission | Allows |
|-----------|--------|
| `discount.apply` | Discounts up to 10% (default cashier tier) |
| `discount.apply_large` | Discounts up to 100% |

Maximum percentages are enforced server-side. The frontend cannot bypass them.

### Rules
- Discount cannot be negative
- Percentage cannot exceed 100%
- Fixed discount cannot exceed the subtotal
- Backend recalculates everything — frontend totals are never trusted
- Applying a discount twice **replaces**, not stacks

---

## Bill Finalization

`finalize_bill(bill, user)` transitions `DRAFT → FINALIZED`.

Process:
1. Lock bill with `select_for_update()`
2. Validate bill has items
3. Run final recalculation
4. Validate tax ≥ 0 and grand_total ≥ 0
5. Set `status = FINALIZED`, `finalized_by`, `finalized_at`

**Idempotent:** calling finalize twice returns the same result without creating a duplicate state.

After finalization:
- Financial fields are immutable
- Discounts cannot be applied or removed
- Direct edits are blocked
- Corrections require the `BillCorrectionRequest` workflow

---

## Bill Correction Workflow

```
Cashier (or authorized user)
    ↓ request_bill_correction()
BillCorrectionRequest (PENDING)
    ↓
Manager / Approver
    ↓ approve_bill_correction() or reject_bill_correction()
APPROVED / REJECTED
```

### Rules
- Only FINALIZED bills can receive correction requests
- The requester **cannot approve their own request** (enforced in services.py)
- Approval requires `bill.correction.approve` permission
- A `CANCELLATION`-type correction, when approved, transitions the bill to `VOID`
- Non-cancellation approvals preserve the bill status (for audit)
- The original financial snapshot is stored in `BillCorrectionRequest.requested_data` (JSON)

### Correction Types
| Type | Use |
|------|-----|
| `ITEM_CORRECTION` | Wrong item/quantity/price |
| `DISCOUNT_CORRECTION` | Discount was wrong |
| `TAX_CORRECTION` | Tax rate/code was wrong |
| `CANCELLATION` | Full bill cancellation after finalization |

---

## Permissions

All billing permissions follow the `module.action` pattern.

| Permission Code | Who Needs It |
|----------------|-------------|
| `bill.view` | Any staff who views bills |
| `bill.create` | Cashier |
| `bill.finalize` | Cashier |
| `bill.print` | Cashier |
| `bill.cancel` | Cashier/Manager |
| `bill.void` | Manager/Owner |
| `discount.apply` | Cashier (≤10%) |
| `discount.apply_large` | Manager (≤100%) |
| `discount.approve` | Manager |
| `bill.correction.request` | Cashier |
| `bill.correction.approve` | Manager |
| `tax.view` | Cashier/Manager |

---

## API Endpoints

| Method | URL | Description |
|--------|-----|-------------|
| `GET` | `/api/billing/bills/` | List bills (scoped + filterable) |
| `POST` | `/api/billing/bills/from-order/{order_id}/` | Create bill from confirmed order |
| `GET` | `/api/billing/bills/{id}/` | Bill detail |
| `GET` | `/api/billing/bills/{id}/calculate/` | Recalculate / preview totals |
| `POST` | `/api/billing/bills/{id}/discount/` | Apply discount |
| `DELETE` | `/api/billing/bills/{id}/discount/` | Remove discount |
| `POST` | `/api/billing/bills/{id}/finalize/` | Finalize bill |
| `POST` | `/api/billing/bills/{id}/cancel/` | Cancel bill |
| `POST` | `/api/billing/bills/{id}/void/` | Void bill (escalated) |
| `GET` | `/api/billing/bills/{id}/receipt/` | Receipt data (JSON) |
| `POST` | `/api/billing/bills/{id}/corrections/` | Request correction |
| `GET` | `/api/billing/bill-corrections/` | List corrections |
| `GET` | `/api/billing/bill-corrections/{id}/` | Correction detail |
| `POST` | `/api/billing/bill-corrections/{id}/approve/` | Approve correction |
| `POST` | `/api/billing/bill-corrections/{id}/reject/` | Reject correction |
| `POST` | `/api/billing/bill-corrections/{id}/cancel/` | Cancel correction |

---

## Database Models

### Bill
- `id` — UUID PK
- `order` — OneToOne → `orders.Order` (PROTECT)
- `branch` — FK → `organizations.Branch` (PROTECT)
- `bill_number` — unique, immutable (e.g. `B-2026-000001`)
- `status` — DRAFT / FINALIZED / CANCELLED / VOID
- `discount_type` — PERCENTAGE / FIXED_AMOUNT / null
- `discount_value` — Decimal input value
- `subtotal`, `discount_amount`, `taxable_amount`, `tax_amount`, `rounding_amount`, `grand_total` — all Decimal(12,2)
- `tax_breakdown` — JSON
- `created_by`, `finalized_by`, `cancelled_by` — FK → User
- `finalized_at`, `cancelled_at`, `cancellation_reason`

### BillItem
- `id` — UUID PK
- `bill` — FK → Bill (CASCADE)
- `order_item` — OneToOne → `orders.OrderItem` (PROTECT)
- `menu_item` — FK → `menu.MenuItem` (PROTECT)
- Snapshot fields: `item_name_snapshot`, `sku_snapshot`, `quantity`, `unit_price`
- Computed fields: `gross_amount`, `discount_amount`, `taxable_amount`, `tax_amount`, `total_amount`
- Tax fields: `tax_rate` (Decimal 6,3), `tax_code`

### BillSequence
- `branch` — FK (PROTECT)
- `year_key` — 4-char string (e.g. `"2026"`)
- `last_sequence` — PositiveIntegerField, incremented atomically

### BillCorrectionRequest
- `bill` — FK → Bill (PROTECT)
- `requested_by`, `reviewed_by` — FK → User
- `correction_type`, `status`, `reason`, `requested_data` (JSON snapshot)
- `reviewed_at`, `review_note`

---

## Security

- All queryset access is scoped via `billing/access.py` — IDOR prevented
- `get_object()` returns 404 for unauthorized UUIDs (not 403)
- Frontend totals are never trusted — backend recalculates everything
- Self-approval of corrections is blocked in `services.py`
- Finalized bills cannot be directly edited
- Large discounts require elevated permission

---

## Frontend Pages

| Route | Page |
|-------|------|
| `/billing` | `BillingDashboard` — stats + recent bills + quick actions |
| `/billing/bills` | `BillListPage` — filterable bill list |
| `/billing/bills/:id` | `BillDetailPage` — full detail + actions |
| `/billing/bills/:id/receipt` | `BillReceiptPage` — printable receipt |
| `/billing/corrections` | `BillCorrectionsPage` — correction approval queue |

### Reusable Components
- `BillStatusBadge` — status color badge
- `BillTotalsPanel` — subtotal / discount / tax / rounding / grand total
- `BillItemsTable` — line items with all financial columns
- `POSBillingPanel` — embedded POS billing flow (create → discount → finalize → print)

---

## Relationship with Other Phases

### Kitchen (Phase 7)
Billing reads the Order/Kitchen state but never modifies `KitchenOrder` status.
`Bill FINALIZED` ≠ `KitchenOrder READY`. They are separate domains.

### Counter (Phase 4)
Bills retain `counter` and `counter_session` references from the Order.
Phase 9 will connect `Bill → Payment → CounterSession` for cash reconciliation.

### Tables (Phase 6)
Dine-in bills retain `table` and `table_session` from the Order.
Table closure is not triggered by bill finalization.

### Payment (Phase 9 — NOT YET)
- No payment gateway
- No UPI / card / cash recording
- No refunds
- Receipt shows a placeholder for payment fields

---

## Concurrency Protection

| Operation | Protection |
|-----------|-----------|
| `create_bill_from_order` | `select_for_update()` on Order + `UniqueConstraint` on Bill.order |
| `finalize_bill` | `select_for_update()` on Bill |
| `apply_discount` | `select_for_update()` on Bill |
| `approve_correction` | `select_for_update()` on BillCorrectionRequest |
| `generate_bill_number` | `select_for_update()` on BillSequence |

All are wrapped in `transaction.atomic()`.

---

## Known Limitations / Future Work

1. **Split bills** — not implemented (Phase 9+)
2. **Merged bills** — not implemented
3. **Item-level discounts** — BillItem.discount_amount reserved but always 0 in Phase 8
4. **Coupon / loyalty** — not implemented
5. **Restaurant-specific max discount config** — uses permission tiers for now
6. **Correction replacement bill** — Phase 8 only marks the bill VOID for CANCELLATION corrections; full replacement-bill workflow is Phase 9+

---

## Recommended Next Phase

**Phase 9 — Payments + Payment Methods + Receipts + Refunds + Payment Reconciliation**

Phase 9 will:
- Add payment recording linked to finalized Bills
- Support cash, card, UPI payment methods
- Counter session cash reconciliation (expected_cash += bill payments)
- Refund processing
- Printable receipt with payment details
