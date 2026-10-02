# RestaurantFlow — Development Roadmap

## Overview

RestaurantFlow is built in structured phases. Each phase builds on the
foundation of the previous one. No phase skips ahead or assumes future
infrastructure exists.

---

## Phase 1 — Foundation ✅

**Goal:** Clean, scalable technical foundation.

- Django + DRF + PostgreSQL + Redis
- React + TypeScript + Vite + Tailwind
- Custom User model (email-based)
- JWT authentication foundation
- Health check API endpoint
- Docker Compose for infrastructure
- Logging, CORS, security defaults
- Full project documentation
- Git repository initialized

---

## Phase 2 — Companies, Restaurants & Branches ✅

**Goal:** Introduce the core multi-tenant business hierarchy.

- `Organization` model (company / head office)
- `Restaurant` model (belongs to organization)
- `Branch` model (belongs to restaurant)
- CRUD API endpoints for all three
- Ownership and access relationship foundation
- Frontend: Organization and restaurant management screens

---

## Phase 3 — Users, Roles & Permissions ✅

**Goal:** Role-based access control across the tenant hierarchy.

- Extend `User` model with role and tenant assignment
- Roles: Company Head, Central Admin, Restaurant Owner, Restaurant Manager, Cashier, Waiter, Kitchen Staff, Inventory Staff, Accountant
- `Permission` model with granular codes (e.g. `restaurant.view`, `branch.create`)
- `UserRoleAssignment` — scoped role assignment (org / restaurant / branch level)
- Full RBAC enforcement on all API views
- Scoped querysets — users only see resources within their scope
- IDOR protection — out-of-scope resources return 404
- Frontend: User management, role listing, assignment UI

---

## Phase 4 — Counters & Cash Sessions ✅

**Goal:** Model the physical POS counter infrastructure and daily cash sessions.

- `Counter` model (belongs to branch, unique code per branch)
- `CounterStatus`: ACTIVE / INACTIVE / MAINTENANCE
- `CounterAssignment` model (cashier ↔ counter link with full history)
- `Shift` model (schedule configuration per branch)
- `CounterSession` model (full cash lifecycle: open → close / force-close)
- `SessionStatus`: OPEN / CLOSED / FORCE_CLOSED
- Cash reconciliation: `cash_difference = actual_cash − expected_cash`
- Concurrency protection via `select_for_update()` + DB partial unique constraint
- Force-close permission for managers
- All monetary fields use `DecimalField` — never float
- 13 new counter permissions integrated into all existing roles
- API: counters, sessions, assignments, shifts, dashboard
- Frontend: Counter Dashboard, Counter List, Counter Detail, Sessions page
- ~35 tests covering model, service, concurrency, API security
- Documentation: `docs/counters.md`, `docs/cash-sessions.md`, `docs/phase-4.md`

---

## Phase 5 — Menu, Categories, Branch Pricing, Availability & Tax ✅

**Goal:** Build the full restaurant menu catalog with branch-aware pricing and availability.

- `TaxRate` model — restaurant-scoped, named tax configuration (never hard-coded)
- `Category` model — ordered categories with slug uniqueness per restaurant
- `MenuItem` model — full catalog item with food type, SKU, prep time, image
- `MenuItemPrice` model — branch-specific pricing with full history preservation
- `MenuItemBranch` model — branch availability with time-of-day windows
- `is_menu_item_available()` service — availability check respecting restaurant timezone
- Branch catalog API — read-optimized POS endpoint with price + tax
- Menu dashboard API — summary stats per restaurant/branch
- 15 new permissions integrated into all existing roles
- All price fields use `DecimalField` — never float
- Cross-restaurant isolation enforced at serializer + queryset level
- Price history preserved — never overwritten
- API: tax rates, categories, items, prices, availability, catalog, dashboard
- Frontend: Menu Dashboard, Categories, Menu Items, Pricing, Availability, Tax Rates
- 12 test classes, ~70 test methods covering all spec acceptance criteria
- Documentation: `docs/menu.md`, `docs/pricing.md`, `docs/tax.md`, `docs/phase-5.md`

---

## Phase 6 — Tables, Orders & POS

**Goal:** The core POS workflow — take orders, manage tables.

- `Table` model (belongs to branch, with QR code support)
- `Order` model (dine-in, takeaway, delivery)
- `OrderItem` model
- Order status flow: `pending → in_kitchen → ready → served → billed`
- Frontend: POS order entry interface, table map

---

## Phase 7 — Kitchen Display System

**Goal:** Real-time kitchen ticket management.

- Kitchen display view (WebSocket via Django Channels)
- Ticket status: `received → preparing → ready`
- Per-station routing (grill, cold, drinks)
- Frontend: Kitchen Display Screen (KDS)

---

## Phase 8 — Billing & Payments

**Goal:** Generate bills and record payments.

- `Bill` model (linked to order, immutable once issued)
- `Payment` model (cash, card, split payments)
- Tax calculation
- Discount application (with approval flow)
- Receipt generation
- Frontend: Billing screen, payment UI

---

## Phase 9 — Approvals, Audit & Issue Tracking

**Goal:** Manager oversight and audit trail.

- Approval workflow for discounts, voids, refunds
- `AuditLog` model (every sensitive action logged)
- Issue tracking for operational problems
- Frontend: Manager approval screens, audit log viewer

---

## Phase 10 — Inventory Management

**Goal:** Track stock levels and consumption.

- `InventoryItem` model
- `StockMovement` model (purchase, consumption, adjustment, waste)
- Low-stock alerts
- Menu item ↔ ingredient linkage
- Frontend: Inventory screens

---

## Phase 11 — Accounts (Financial Accounting)

**Goal:** Basic accounting and financial records.

- `Account` model (chart of accounts)
- `JournalEntry` model (double-entry bookkeeping foundation)
- Cash flow summary
- Expense recording
- Frontend: Accounting overview screens

---

## Phase 12 — Restaurant Analytics

**Goal:** Per-restaurant reporting and insights.

- Sales reports (daily, weekly, monthly)
- Top-selling items
- Revenue by branch / counter / cashier
- Kitchen performance metrics
- Frontend: Analytics dashboard

---

## Phase 13 — Central Control Center

**Goal:** Cross-restaurant overview for company heads.

- Multi-restaurant dashboard
- Aggregate sales across branches
- Comparative reporting
- Real-time status of all branches
- Frontend: Central Control Center screens

---

## Phase 14 — Security, Monitoring & Notifications

**Goal:** Production-grade security and observability.

- Two-factor authentication
- Session management and device tracking
- Rate limiting
- Anomaly detection (unusual sales, void patterns)
- Push / email notifications
- Sentry integration for error tracking
- Structured logging for external log aggregation

---

## Phase 15 — Production Deployment

**Goal:** Deploy to AWS in a production-ready configuration.

- Dockerfile for backend and frontend
- Nginx reverse proxy configuration
- Gunicorn / Daphne (ASGI) configuration
- AWS infrastructure (EC2/ECS, RDS PostgreSQL, ElastiCache Redis)
- SSL / HTTPS with Let's Encrypt or ACM
- Environment-based configuration for production
- CI/CD pipeline (GitHub Actions)
- Backup strategy for database
- Health monitoring and alerting

---

## Timeline Note

Each phase is a discrete, testable milestone. Phase N is not started until
Phase N-1 passes all acceptance criteria and is reviewed.
