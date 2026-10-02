# Tax Configuration — RestaurantFlow Phase 5

> **Disclaimer:** Tax rates in this system are configurable values intended for demonstration and development purposes. They do not constitute legal, financial, or tax advice. Restaurant operators must consult qualified tax professionals to configure correct rates for their jurisdiction.

---

## Design

Tax rates are stored as named, versioned records in the `TaxRate` model rather than hard-coded constants. This approach means:

1. Different restaurants can use different tax codes/rates
2. Rates can be updated without code changes
3. Future billing can snapshot the exact rate applied at transaction time
4. Zero-tax and exemption scenarios are handled uniformly

---

## TaxRate Model

```
TaxRate
  id              UUID
  restaurant      FK → Restaurant   (PROTECT)
  name            "GST Standard"
  code            "GST_STANDARD"    (unique per restaurant)
  rate            5.000             (Decimal — percentage)
  description     "..."
  is_active       Boolean
```

**Code uniqueness** is scoped per restaurant: two restaurants may both define `GST_STANDARD` independently. Codes from one restaurant never pollute another's namespace.

---

## Example Tax Rates (Development Only)

The seed command creates these demo rates for each restaurant:

| Code | Name | Rate |
|---|---|---|
| `GST_STANDARD` | GST Standard | 5.000% |
| `GST_REDUCED` | GST Reduced | 2.500% |
| `ZERO_TAX` | Zero Tax | 0.000% |

These are placeholder values. Real GST rates and applicability depend on the item category, business type, turnover thresholds, and current regulations in your jurisdiction.

---

## Tax Assignment

Menu items reference a `TaxRate` via a foreign key:

```
MenuItem.tax_rate → TaxRate
```

This means:
- The tax code and percentage are never duplicated into the item record
- Changing a rate is a single row update on `TaxRate`
- The item always shows the current configured rate

**Cross-restaurant validation:** The serializer enforces that `tax_rate.restaurant == menu_item.restaurant`. You cannot assign a tax rate from Restaurant B to an item in Restaurant A.

---

## Tax in the Catalog

The branch catalog endpoint (`GET /api/menu/branches/{id}/catalog/`) includes tax information per item:

```json
{
  "id": "...",
  "name": "Chicken Biryani",
  "price": "220.00",
  "tax_rate_code": "GST_STANDARD",
  "tax_rate_name": "GST Standard",
  "tax_rate": "5.000"
}
```

The POS uses this data to show tax-inclusive or tax-exclusive prices as configured.

---

## Tax History for Billing (Phase 6+)

Phase 5 establishes the data structure; Phase 6 billing will use it as follows:

When an order is placed, the bill line item must store a **snapshot** of:
- `tax_rate_code` (e.g. `GST_STANDARD`)
- `tax_rate_value` (e.g. `5.000`)

This snapshot is stored directly on the bill/order line, not as a live FK. This ensures that if the `TaxRate.rate` is later changed (e.g. government changes the rate from 5% to 8%), all historical bills still show the correct rate that was applied at the time of the transaction.

**Never** use the current `TaxRate.rate` to reconstruct old bills. Always use the snapshotted value stored on the bill line.

---

## Disabling a Tax Rate

```
POST /api/menu/tax-rates/{id}/disable/
```

Disabling a `TaxRate` sets `is_active = False`. It does **not** remove the tax rate from existing items. Items referencing a disabled tax rate will show no tax in the catalog (the serializer checks `tax_rate.is_active`).

Before disabling a tax rate, consider reassigning affected menu items to an active rate.

---

## API Reference

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/menu/tax-rates/` | List tax rates (scoped to accessible restaurants) |
| POST | `/api/menu/tax-rates/` | Create tax rate (`tax.create` permission) |
| GET | `/api/menu/tax-rates/{id}/` | Retrieve |
| PATCH | `/api/menu/tax-rates/{id}/` | Update (`tax.update` permission) |
| POST | `/api/menu/tax-rates/{id}/disable/` | Soft disable |
| POST | `/api/menu/tax-rates/{id}/enable/` | Re-enable |

### Access Control

| Permission | Roles with default access |
|---|---|
| `tax.view` | All roles |
| `tax.create` | Restaurant Owner, Manager, Company Head, Central Admin |
| `tax.update` | Restaurant Owner, Manager, Company Head, Central Admin |

Cashiers and Waiters have `tax.view` only. Accountants have `tax.view` for reporting.
