# Bill Corrections — RestaurantFlow

## When to Use

A `BillCorrectionRequest` is needed when a **FINALIZED** bill requires any change.
Draft bills can be modified directly without a correction workflow.

## Workflow

```
1. Cashier notices an error in a finalized bill
2. Submits BillCorrectionRequest (correction_type + reason)
3. Manager reviews (approve or reject)
4. If APPROVED:
   - CANCELLATION type → Bill transitions to VOID
   - Other types → Bill remains FINALIZED + correction noted
5. If REJECTED → Bill unchanged, note recorded
```

## Correction Types

| Type | When to Use |
|------|-------------|
| `ITEM_CORRECTION` | Wrong quantity, wrong item, etc. |
| `DISCOUNT_CORRECTION` | Discount was wrong |
| `TAX_CORRECTION` | Tax code or rate was wrong |
| `CANCELLATION` | Full void of the finalized bill |

## Self-Approval Prevention

A user **cannot approve their own correction request**. This is enforced in `services.py`:

```python
validate_self_approval(correction.requested_by_id, reviewer.pk)
# Raises ValidationError if they are the same user
```

## Audit Trail

Every correction stores a snapshot of the bill's financial state at the time of the request:

```json
{
  "bill_number": "B-2026-000042",
  "grand_total": "645.00",
  "tax_amount": "25.00",
  "items": [...],
  "snapshot_at": "2026-10-03T12:30:00Z"
}
```

This `requested_data` JSON is immutable after creation.

## Permissions Required

| Action | Permission |
|--------|-----------|
| Request correction | `bill.correction.request` |
| Approve / Reject | `bill.correction.approve` |
| Cancel own request | Any authenticated user who is the requester |

## What Correction Approval Does NOT Do

- Does **not** mutate the original bill's financial fields (except CANCELLATION type → VOID)
- Does **not** create a replacement bill automatically (Phase 9+ concern)
- The full correction-replacement-bill chain with versioned bill numbers (B-001-R1) is future work

## Traceability

All corrections are linked to the original bill via FK and visible in:
- `Bill.correction_requests` reverse relation
- `BillDetailPage` frontend (correction count + pending indicator)
- `BillCorrectionsPage` approval queue
- Django admin `BillCorrectionRequest` list
