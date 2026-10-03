# Tax Calculation — RestaurantFlow

## Overview

Tax in RestaurantFlow is:
- **Configurable** — via `TaxRate` model (Phase 5), never hard-coded
- **Snapshotted** — frozen at order-item creation (`OrderItem.tax_rate_snapshot`)
- **Proportional** — when a bill-level discount is applied, tax is recalculated on the discounted taxable amount
- **Deterministic** — same inputs always produce the same result (Decimal, ROUND_HALF_UP)

## Data Flow

```
TaxRate (restaurant config)
    ↓ at order item creation
OrderItem.tax_rate_snapshot (frozen)
    ↓ at bill creation
BillItem.tax_rate (copied from snapshot)
    ↓ calculate_bill()
BillItem.tax_amount = item_taxable × tax_rate / 100
    ↓
Bill.tax_amount = sum(item_tax_amounts)
    ↓
Bill.tax_breakdown = {code: amount, …}
```

## Tax Rounding

All tax amounts are rounded to 2 decimal places using `ROUND_HALF_UP`.

```python
from decimal import Decimal, ROUND_HALF_UP

def compute_tax(taxable_amount, tax_rate_pct):
    tax = taxable_amount * tax_rate_pct / Decimal("100")
    return tax.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
```

## Tax Breakdown JSON

The `Bill.tax_breakdown` field aggregates tax by code:
```json
{
  "GST_5": "25.00",
  "ZERO_TAX": "0.00",
  "GST_18": "18.00"
}
```

This supports multi-component Indian GST (CGST + SGST) without hard-coding tax names.
When restaurant settings provide CGST/SGST as separate `TaxRate` codes, they appear separately.

## Tax Snapshot Protection

If a restaurant changes `TaxRate.rate` from 5% to 18% tomorrow:
- **New orders** will use 18%
- **Existing OrderItems** still have `tax_rate_snapshot = 5.000`
- **Existing Bills** still show tax calculated at 5%

Historical transactions are protected.

## Zero Tax

Items with `tax_rate_snapshot = 0.000` produce `tax_amount = 0.00`.
They still appear in `tax_breakdown` under their `tax_code` with value `"0.00"`.

## Missing Tax Snapshot (Legacy Data)

If `OrderItem.tax_rate_snapshot` is `0.000` and `tax_code_snapshot` is empty,
the billing service treats the item as zero-taxed. It does **not** silently assume a default rate.
