# Phase 5 — Menu, Categories, Branch Pricing, Availability & Tax

## Summary

Phase 5 adds the complete restaurant menu system to RestaurantFlow. It builds on the organization → restaurant → branch hierarchy established in Phases 1–4 and provides the data foundation for all future POS, order, kitchen, billing, and analytics phases.

---

## What Was Built

### Backend (`backend/menu/`)

| File | Purpose |
|---|---|
| `models.py` | `TaxRate`, `Category`, `MenuItem`, `MenuItemPrice`, `MenuItemBranch` |
| `serializers.py` | Full validation: cross-restaurant checks, price overlap, SKU uniqueness |
| `views.py` | 18 endpoints: list/create/retrieve/update/disable/enable per resource + catalog + dashboard |
| `urls.py` | URL routing under `/api/menu/` |
| `access.py` | Scoped querysets (mirrors `accounts.access` pattern) |
| `permissions.py` | Object-level DRF permission classes |
| `services.py` | `is_menu_item_available()`, `get_branch_catalog()`, lifecycle helpers |
| `filters.py` | django-filter classes for all resources |
| `admin.py` | Django admin registration with search, filters, readonly timestamps |
| `tests.py` | 12 test classes, ~70 test methods |
| `management/commands/seed_menu_data.py` | Permission seeding + demo data |

### Settings & URLs

| Change | File |
|---|---|
| Added `"menu"` to `LOCAL_APPS` | `backend/config/settings.py` |
| Added `path("api/", include("menu.urls"))` | `backend/config/urls.py` |

### Frontend (`frontend/src/`)

| File | Purpose |
|---|---|
| `types/index.ts` | Phase 5 TypeScript interfaces appended |
| `services/menu.ts` | All menu API calls via central axios client |
| `hooks/useMenu.ts` | TanStack Query hooks with typed query key factories |
| `pages/menu/MenuDashboard.tsx` | Summary stats + quick navigation |
| `pages/menu/Categories.tsx` | Category CRUD with disable/enable |
| `pages/menu/MenuItems.tsx` | Item list with search, multi-filter, disable/enable |
| `pages/menu/MenuItemForm.tsx` | Reusable create/edit form for menu items |
| `pages/menu/Pricing.tsx` | Branch-specific price management with history |
| `pages/menu/Availability.tsx` | Branch availability toggle grid |
| `pages/menu/TaxRates.tsx` | Tax rate CRUD |
| `App.tsx` | 6 new routes added under `/menu/*` |
| `layouts/MainLayout.tsx` | Menu section added to sidebar nav |

---

## New API Endpoints

```
GET    /api/menu/tax-rates/
POST   /api/menu/tax-rates/
GET    /api/menu/tax-rates/{id}/
PATCH  /api/menu/tax-rates/{id}/
POST   /api/menu/tax-rates/{id}/disable/
POST   /api/menu/tax-rates/{id}/enable/

GET    /api/menu/categories/
POST   /api/menu/categories/
GET    /api/menu/categories/{id}/
PATCH  /api/menu/categories/{id}/
POST   /api/menu/categories/{id}/disable/
POST   /api/menu/categories/{id}/enable/

GET    /api/menu/items/
POST   /api/menu/items/
GET    /api/menu/items/{id}/
PATCH  /api/menu/items/{id}/
POST   /api/menu/items/{id}/disable/
POST   /api/menu/items/{id}/enable/

GET    /api/menu/prices/
POST   /api/menu/prices/
GET    /api/menu/prices/{id}/
PATCH  /api/menu/prices/{id}/
POST   /api/menu/prices/{id}/deactivate/

GET    /api/menu/availability/
POST   /api/menu/availability/
GET    /api/menu/availability/{id}/
PATCH  /api/menu/availability/{id}/

GET    /api/menu/branches/{id}/catalog/
GET    /api/menu/dashboard/
```

---

## New Permissions (15 total)

| Code | Description |
|---|---|
| `menu.view` | View menu items |
| `menu.create` | Create menu items |
| `menu.update` | Update menu items |
| `menu.disable` | Disable menu items |
| `category.view` | View categories |
| `category.create` | Create categories |
| `category.update` | Update categories |
| `category.disable` | Disable categories |
| `menu.price.view` | View prices |
| `menu.price.create` | Create prices |
| `menu.price.update` | Update/deactivate prices |
| `menu.availability.view` | View branch availability |
| `menu.availability.update` | Update branch availability |
| `tax.view` | View tax rates |
| `tax.create` | Create tax rates |
| `tax.update` | Update/disable tax rates |

---

## Running the Backend (Docker)

Docker Desktop must be running.

```bash
# Start PostgreSQL and Redis
docker compose up -d

# From backend/ directory (or via docker exec if Django runs in Docker):
python manage.py makemigrations menu
python manage.py migrate
python manage.py check
python manage.py test menu

# Seed demo data (optional)
python manage.py seed_menu_data
```

> **Note:** Python is not installed directly on the host machine — it runs inside Docker or a virtual environment. The frontend was verified with `npm run build` (passes with 0 TypeScript errors, 214 modules).

---

## Architecture After Phase 5

```
Organization
    │
    └── Restaurant
          │
          ├── Branch
          │    ├── Counters
          │    │     └── Sessions
          │    │
          │    └── [Tables — Phase 6]
          │
          └── Menu
               ├── TaxRate
               ├── Category
               │     └── MenuItem
               │           ├── MenuItemPrice   (per branch)
               │           └── MenuItemBranch  (per branch)
               └── [future: Modifiers, Combos]
```

---

## Future Compatibility

Phase 5 was designed so future phases can use the menu data without schema changes:

### Phase 6 (Orders)
- `MenuItem.id`, `name`, `sku`, `food_type`, `preparation_time_minutes` → order line item
- `MenuItemPrice.price` → base price at order time (snapshot, not live FK)
- `TaxRate.code`, `rate` → tax snapshot on order line

### Phase 7 (Kitchen)
- `MenuItem.preparation_time_minutes` → KDS timer

### Phase 8 (Billing)
- `MenuItemPrice` history → reconstruct historical bill with correct prices
- `TaxRate` snapshot → correct historical tax amount

### Phase 9 (Analytics)
- Category, food_type, SKU → sales breakdown
- Branch pricing → revenue by location

---

## Test Coverage

```
TaxRateModelTests       — create, update, duplicate rejected, negative rate, isolation
CategoryModelTests      — create, slug generation, update, disable, duplicate, cross-restaurant
MenuItemModelTests      — create, slug, update, disable, SKU uniqueness, category mismatch,
                          tax mismatch, restaurant isolation
MenuItemPriceTests      — create, negative price, zero price, wrong branch, history preserved,
                          overlap rejected, Decimal precision, multiple historical
MenuItemBranchTests     — create, unavailable excluded, available included, inactive item/branch,
                          no record means unavailable, time window (in/out), wrong branch, duplicate
CategoryAPITests        — unauthenticated rejected, list, create, cashier blocked,
                          disable/enable, cross-restaurant 404
MenuItemAPITests        — create, cashier blocked, duplicate SKU, category mismatch,
                          disable/enable, cross-restaurant 404
PricingAPITests         — create, negative rejected, wrong branch, deactivate, history preserved
AvailabilityAPITests    — create, update, cross-restaurant 404
TaxRateAPITests         — create, update, duplicate, isolation
BranchCatalogAPITests   — 200, active items only, unavailable excluded, inactive categories excluded,
                          correct price, correct tax, unauthorized 403/404, ordering
SecurityTests           — cross-restaurant category/item blocked, wrong-branch price blocked,
                          unauthenticated catalog/dashboard blocked, scoped item list
```

---

## Next Phase

**Phase 6: Tables + Dine-In Management + Order Foundation + Order Types**

```
Branch
  └── Table
         └── Order
               └── OrderLine → MenuItem + MenuItemPrice snapshot
```
