# Menu Architecture — RestaurantFlow Phase 5

## Overview

Phase 5 introduces the restaurant menu system. A menu belongs to a restaurant and is shared across all of its branches. Branches do not have independent menus — they control **availability** and **pricing** of items from the restaurant's shared catalog.

```
Restaurant
    │
    └── Menu
          │
          ├── TaxRate           (restaurant-scoped tax configuration)
          ├── Category          (Veg, Non-Veg, Snacks, Beverages, Desserts)
          └── MenuItem          (individual dish / product)
                ├── MenuItemPrice     (branch-specific selling price + history)
                └── MenuItemBranch    (branch availability + time windows)
```

---

## Why MenuItem ≠ Price

A restaurant chain often operates multiple branches with different pricing strategies:

```
Spice Garden — Chicken Biryani

  LPU Campus branch    → ₹220
  City Center branch   → ₹260
  Airport branch       → ₹280
```

Putting a single `price` field on `MenuItem` would require either duplicating the item record per branch (data redundancy) or accepting that all branches share one price (operationally incorrect for most restaurant chains).

The `MenuItemPrice` model solves this by keeping price records separate, one per `(menu_item, branch)` combination. Each price record also carries `effective_from` / `effective_to` timestamps so the system can reconstruct the exact price charged on any historical date.

---

## Why MenuItem ≠ Branch Availability

A menu item can be:

- **Active** in the restaurant's catalog (`MenuItem.is_active = True`) but not yet set up at a branch.
- **Available** at one branch but temporarily unavailable at another (e.g. ingredient shortage, breakfast-only items).
- **Available only during certain hours** (e.g. Lunch Combo: 12:00–16:00).

These are three distinct concepts and must not be conflated:

| Field | Model | Meaning |
|---|---|---|
| `is_active` | `MenuItem` | Item exists in the restaurant's catalog |
| `is_available` | `MenuItem` | Restaurant-level default |
| `is_available` | `MenuItemBranch` | This specific branch currently offers it |
| `available_from/to` | `MenuItemBranch` | Time-of-day window for this branch |

---

## Models

### TaxRate

Tax configuration record scoped to a restaurant.

| Field | Type | Notes |
|---|---|---|
| `id` | UUID | Primary key |
| `restaurant` | FK → Restaurant | PROTECT |
| `name` | CharField | Human-readable (e.g. "GST Standard") |
| `code` | CharField | Internal code (e.g. "GST_STANDARD") — unique per restaurant |
| `rate` | DecimalField(6,3) | Percentage (e.g. 5.000 = 5%) |
| `description` | TextField | Optional notes |
| `is_active` | Boolean | Soft disable |

**Uniqueness:** `(restaurant, code)`

### Category

A menu category (e.g. Veg, Non-Veg, Beverages) belonging to a restaurant.

| Field | Type | Notes |
|---|---|---|
| `id` | UUID | Primary key |
| `restaurant` | FK → Restaurant | PROTECT |
| `name` | CharField | Display name |
| `slug` | SlugField | Auto-generated from name — unique per restaurant |
| `description` | TextField | Optional |
| `image` | ImageField | Uploaded to `menu/categories/` |
| `display_order` | PositiveIntegerField | Controls catalog ordering |
| `is_active` | Boolean | Soft disable |

**Uniqueness:** `(restaurant, slug)`

### MenuItem

An individual dish or product in the restaurant's catalog.

| Field | Type | Notes |
|---|---|---|
| `id` | UUID | Primary key |
| `restaurant` | FK → Restaurant | PROTECT |
| `category` | FK → Category | PROTECT — must be same restaurant |
| `tax_rate` | FK → TaxRate | SET_NULL — must be same restaurant if set |
| `name` | CharField | Display name |
| `slug` | SlugField | Auto-generated — unique per restaurant |
| `sku` | CharField | Internal code — unique per restaurant |
| `description` | TextField | Full description |
| `short_description` | CharField(300) | Shown in POS catalog |
| `image` | ImageField | Uploaded to `menu/items/` |
| `food_type` | Choices | VEG, NON_VEG, EGG, VEGAN, OTHER |
| `display_order` | PositiveIntegerField | Controls catalog ordering |
| `is_active` | Boolean | Item exists in catalog |
| `is_available` | Boolean | Restaurant-level default |
| `preparation_time_minutes` | PositiveIntegerField | Used by KDS (Phase 7+) |

**Uniqueness:** `(restaurant, slug)` and `(restaurant, sku)` (sku via serializer validation)

**Cross-model validation:**
- `category.restaurant == menu_item.restaurant`
- `tax_rate.restaurant == menu_item.restaurant` (when provided)

### MenuItemPrice

Branch-specific pricing with full history preservation.

| Field | Type | Notes |
|---|---|---|
| `id` | UUID | Primary key |
| `menu_item` | FK → MenuItem | PROTECT |
| `branch` | FK → Branch | PROTECT — must be same restaurant as item |
| `price` | DecimalField(12,2) | >= 0 |
| `effective_from` | DateTimeField | Optional start of validity |
| `effective_to` | DateTimeField | Optional end of validity (NULL = still current) |
| `is_active` | Boolean | Is this the current active price? |

**Price history rule:** Never delete price records. When a price changes, deactivate the old record and create a new one. Historical records are retained for billing reconstruction.

**Overlap prevention:** Serializer rejects creating a new `is_active=True` price for a `(menu_item, branch)` pair if an active price already exists for an overlapping time window.

### MenuItemBranch

Controls whether a menu item is available at a specific branch.

| Field | Type | Notes |
|---|---|---|
| `id` | UUID | Primary key |
| `menu_item` | FK → MenuItem | PROTECT |
| `branch` | FK → Branch | PROTECT — must be same restaurant |
| `is_available` | Boolean | Branch currently offers this item |
| `available_from` | TimeField | Start of daily time window (restaurant timezone) |
| `available_to` | TimeField | End of daily time window |

**Uniqueness:** `(menu_item, branch)` — one record per item+branch pair.

**Time windows:** Both `available_from` and `available_to` being NULL means available all day. The time-of-day check uses the restaurant's configured timezone (from `RestaurantSettings.timezone` or `Organization.timezone`), falling back to `Asia/Kolkata`.

---

## Availability Logic

```python
is_menu_item_available(menu_item, branch, current_time=None) → bool
```

Phase 5 checks (in order):

1. `menu_item.is_active` — item exists in catalog
2. `branch.is_active` — branch is operational
3. `MenuItemBranch` record exists for this `(menu_item, branch)` pair
4. `MenuItemBranch.is_available = True`
5. `current_time` falls within `available_from` → `available_to` (if set)

Phase 7+ will add: inventory stock check.

---

## Food Type

Controlled vocabulary — never free text:

| Value | Label |
|---|---|
| `VEG` | Vegetarian |
| `NON_VEG` | Non-Vegetarian |
| `EGG` | Egg |
| `VEGAN` | Vegan |
| `OTHER` | Other |

---

## Catalog API

`GET /api/menu/branches/{branch_id}/catalog/`

Returns only items that are:
- In an active category
- `is_active = True` on the MenuItem
- Have a `MenuItemBranch` record with `is_available = True` for this branch
- Within the availability time window (if set)

Includes branch-specific price and tax rate. Intended for POS consumption. Does **not** expose cost prices, margins, or supplier information.

---

## Demo Seed Data

Run `python manage.py seed_menu_data` to create:

- Phase 5 permissions assigned to all system roles
- For each active restaurant: demo tax rates, 5 categories, 10 menu items with pricing and availability per branch

Demo tax rates are for development only and do not constitute legal or tax advice.
