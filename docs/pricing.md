# Pricing Architecture — RestaurantFlow Phase 5

## Design Decision: No Single Price on MenuItem

The `MenuItem` model does **not** have a `price` field. This is intentional.

### Rationale

Restaurant chains operate branches in different locations with different cost structures, local market conditions, and competitive pricing. A single global price per item is operationally incorrect for multi-branch operations.

```
Chicken Biryani

  LPU Campus     → ₹220  (student market)
  City Center    → ₹260  (commercial area)
  Airport        → ₹280  (captive market)
```

### Solution: MenuItemPrice

`MenuItemPrice` stores one price record per `(menu_item, branch)` combination.

---

## Price History

Historical prices are **never deleted or overwritten**. When a price needs to change:

1. The existing active price record is **deactivated** (`is_active = False`)
2. A new price record is **created** with the updated price
3. Both records remain in the database

```
Chicken Biryani — LPU Campus

  ₹220   01 Oct → 15 Oct   is_active=False  (historical)
  ₹240   16 Oct → current  is_active=True   (current)
```

This approach ensures that future billing can always reconstruct "what was the price of this item on this date at this branch" by querying `MenuItemPrice` with the transaction timestamp.

### Why this matters for billing (Phase 6+)

When an order is created, the bill must capture a **snapshot** of the price at that moment. If prices were overwritten in place, historical bills would silently reference the wrong amount. By preserving history, a Phase 6 bill can store the `MenuItemPrice.id` used and reconstruct the exact charge even years later.

---

## Active Price Rule

At any point in time, there should be at most one `is_active=True` price for a given `(menu_item, branch)` pair in any overlapping effective period.

The serializer enforces this at write time:

```python
# Rejected — active price already exists for this item+branch
POST /api/menu/prices/
{
  "menu_item": "uuid",
  "branch": "uuid",
  "price": "240.00",
  "is_active": true
}
# → 400 Bad Request: "An active price already exists..."
```

To update a price:
1. Call `POST /api/menu/prices/{id}/deactivate/` on the existing active price
2. Then `POST /api/menu/prices/` with the new price

---

## Effective Dates

`effective_from` and `effective_to` are optional datetime fields.

- Both NULL: the price is considered always applicable (until deactivated)
- `effective_from` set: price applies from that datetime
- `effective_to` set: price expires at that datetime
- Both set: price applies only within that window

Future reporting can use these fields to answer: "What was the price of item X at branch Y on date D?"

---

## Financial Safety

- `price` uses `DecimalField(max_digits=12, decimal_places=2)` — never `float`
- Minimum allowed price: `0.00` (complimentary items are valid)
- The backend calculates all tax amounts from the stored `TaxRate.rate` — the frontend never submits a computed tax figure as authoritative
- `cash_difference` on `CounterSession` is similarly calculated server-side

---

## API Reference

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/menu/prices/` | List prices (scoped, filterable by item/branch/status) |
| POST | `/api/menu/prices/` | Create new price record |
| GET | `/api/menu/prices/{id}/` | Retrieve price detail |
| PATCH | `/api/menu/prices/{id}/` | Update non-financial fields |
| POST | `/api/menu/prices/{id}/deactivate/` | Mark as historical |

### Filter parameters

| Parameter | Description |
|---|---|
| `menu_item` | UUID — filter by menu item |
| `branch` | UUID — filter by branch |
| `is_active` | true/false — active or historical |

### Example: Create a price

```json
POST /api/menu/prices/
{
  "menu_item": "550e8400-e29b-41d4-a716-446655440000",
  "branch": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
  "price": "220.00",
  "effective_from": "2026-10-01T00:00:00Z"
}
```

---

## Access Control

| Permission | Required for |
|---|---|
| `menu.price.view` | Reading price records |
| `menu.price.create` | Creating new prices |
| `menu.price.update` | Updating / deactivating prices |

Assigned by default to: Restaurant Owner, Restaurant Manager, Company Head, Central Admin.
Cashiers and Waiters get `menu.price.view` only.
