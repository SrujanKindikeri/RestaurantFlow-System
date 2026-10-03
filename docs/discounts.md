# Discounts — RestaurantFlow

## Types

| Type | Description |
|------|-------------|
| `PERCENTAGE` | e.g. `10.00` = 10% off subtotal |
| `FIXED_AMOUNT` | e.g. `50.00` = ₹50 off subtotal |

## Validation Rules

| Rule | Detail |
|------|--------|
| Percentage ≥ 0 | Cannot be negative |
| Percentage ≤ 100 | Cannot exceed 100% |
| Percentage ≤ user_max | Enforced by permission tier |
| Fixed ≥ 0 | Cannot be negative |
| Fixed ≤ subtotal | Discount cannot exceed what is owed |

## Permission Tiers

```python
# In billing/views.py → _get_max_discount_pct()
if has_permission(user, "discount.apply_large"):
    return Decimal("100")   # Manager / Owner tier
return Decimal("10")        # Default cashier tier
```

Roles do **not** have hard-coded names in discount logic. The check is purely permission-code based.

## Discount Application

Discounts are applied at the **bill level**, not per item.
The proportional effect on each BillItem is calculated when `calculate_bill()` runs:

```
discount_ratio = discount_amount / subtotal
item_discount  = item.gross_amount × discount_ratio
item_taxable   = item.gross_amount − item_discount
```

## Idempotency

Calling `apply_discount()` twice with the same value **replaces** the discount, not stacks it.

## Immutability

Discounts cannot be applied to or removed from a **FINALIZED** bill.
Any post-finalization discount change requires a `BillCorrectionRequest`.
