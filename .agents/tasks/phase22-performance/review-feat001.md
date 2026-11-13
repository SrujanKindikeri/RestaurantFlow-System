# Review: FEAT-001 DB Query Optimisation + Indexing + Docs

**Commit**: `8981632` — `feat: FEAT-001 DB query optimisation + indexing + docs`  
**Verdict**: CHANGES_REQUESTED

---

## Evidence Summary

### Verification Evidence (from commit message)
- `python manage.py check`: 0 issues ✓
- `python manage.py makemigrations --check`: No changes detected ✓
- `python manage.py test`: 65 tests, 2 pre-existing failures unrelated to FEAT-001 ✓

### Documents existence
- `docs/performance_assessment_phase22.md`: EXISTS ✓ (all required audit sections present: N+1 patterns, missing indexes, cache usage, pagination, WebSocket, Celery, frontend audit)
- `docs/database_optimization.md`: EXISTS ✓
- `docs/scalability_guide.md`: EXISTS ✓

### Settings changes
- `CONN_MAX_AGE=60` in `DATABASES['default']`: PRESENT ✓ (`backend/config/settings.py` line 150)
- `CELERY_TASK_TIME_LIMIT=300`: PRESENT ✓
- `CELERY_TASK_SOFT_TIME_LIMIT=240`: PRESENT ✓
- `CELERY_TASK_ROUTES` defined: PRESENT ✓

### View optimisations
- `billing/views.py` `BillListView`: `order__branch` added to `select_related` ✓
- `billing/views.py` `_get_bill_or_404`: `prefetch_related("items__menu_item", "items__order_item")` added ✓
- orders, payments, inventory, notifications, enterprise views: NO CHANGE in this commit — pre-existing optimisations correctly documented as "already in place" in `docs/database_optimization.md`

---

## Blockers

### BLOCKER 1 — Two of the five required performance-index migration files are absent

**Task requirement**: "5 migration files created (notifications, enterprise, crm, marketing, menu)"

**Actual state**:
- `backend/enterprise/migrations/0002_performance_indexes.py` — **DOES NOT EXIST**  
  The only enterprise migration in this commit is `0002_rename_enterprise_policy_co_type_idx...py`, which is a rename/sync migration with no `AddIndex` operations for the three performance indexes the task requires.
- `backend/marketing/migrations/0002_performance_indexes.py` — **DOES NOT EXIST**  
  The only marketing migration is `0002_alter_campaignapproval_options...py` with no `AddIndex` operations.

**Evidence**: `git diff HEAD~1..HEAD --name-only` lists no `enterprise/migrations/0002_performance_indexes.py` or `marketing/migrations/0002_performance_indexes.py`. Direct file listing of both migration directories confirms absence.

**Documentation impact**: `docs/database_optimization.md` sections 1.2 and 1.4 reference these non-existent files and claim three enterprise indexes (`EnterpriseConfiguration.(company,configuration_key,created_at)`, `StaffBranchAssignment.(user,branch,is_active)`, `MenuRollout.(restaurant,status,created_at)`) and two marketing indexes (`MarketingCampaign.(restaurant,status,start_at)`, `MarketingCampaign.(restaurant,status,end_at)`) were created. None were.

**Correction**: Create `enterprise/migrations/0002_performance_indexes.py` and `marketing/migrations/0002_performance_indexes.py` with the stated `AddIndex` operations, chaining them before the existing 0002 (now renumbered 0003) rename migration. Add the corresponding entries to each model's `Meta.indexes` so future `makemigrations --check` does not auto-remove them.

---

### BLOCKER 2 — Notifications performance indexes are created and immediately removed (net zero)

**File**: `backend/notifications/migrations/0002_performance_indexes.py` and `backend/notifications/migrations/0003_remove_notification_notif_company_type_created_idx_and_more.py`

**Issue**: `0002_performance_indexes.py` adds four composite indexes:
- `notif_company_type_created_idx` on `Notification.(company, notification_type, created_at)`
- `notif_rest_type_created_idx` on `Notification.(restaurant, notification_type, created_at)`
- `notif_branch_type_created_idx` on `Notification.(branch, notification_type, created_at)`
- `notif_recip_user_status_created_idx` on `NotificationRecipient.(user, delivery_status, created_at)`

`0003` (auto-generated sync migration) immediately removes all four of them via `RemoveIndex` operations. After both migrations run, the database has none of these indexes.

**Root cause**: The indexes were added as bare migration operations but were never declared in `Notification.Meta.indexes` or `NotificationRecipient.Meta.indexes` in `backend/notifications/models.py`. Django's auto-generated sync migration (`makemigrations`) correctly detected the mismatch and emitted the removal. The `Notification.Meta.indexes` currently only holds 7 indexes (company/created_at, company/type, company/severity, restaurant/created_at, branch/created_at, source, type/source) — none of the new composites.

**User-visible consequence**: The claimed N+1 mitigation and time-series query acceleration for notifications is not delivered.

**Correction**: Add all four index definitions to the respective `Meta.indexes` lists in `backend/notifications/models.py`, then regenerate the 0002/0003 pair so the net state delivers the indexes and `makemigrations --check` stays clean.

---

### BLOCKER 3 — CRM performance indexes are created and immediately removed (net zero)

**File**: `backend/crm/migrations/0002_performance_indexes.py` and `backend/crm/migrations/0003_alter_crmauditlog_options_and_more.py`

**Issue**: `0002_performance_indexes.py` adds:
- `crm_cust_rest_active_created_idx` on `Customer.(restaurant, is_active, created_at)`
- `crm_loyalty_prog_balance_idx` on `LoyaltyAccount.(loyalty_program, points_balance)`

`0003` removes both via `RemoveIndex` before proceeding with model sync operations.

**Root cause**: Same as BLOCKER 2 — these indexes were not declared in `Customer.Meta.indexes` or `LoyaltyAccount.Meta.indexes`. `Customer.Meta.indexes` has `(restaurant, is_active)` and `(restaurant, created_at)` separately but not the three-column composite. The auto-generated migration removed the orphaned indexes.

**User-visible consequence**: The active-customer-by-join-date query and loyalty program ranking query remain unoptimised.

**Correction**: Add `models.Index(fields=["restaurant", "is_active", "created_at"], name="crm_cust_rest_active_created_idx")` to `Customer.Meta.indexes` and `models.Index(fields=["loyalty_program", "points_balance"], name="crm_loyalty_prog_balance_idx")` to `LoyaltyAccount.Meta.indexes`. Regenerate migrations so 0002 and 0003 deliver a net positive index count.

---

### BLOCKER 4 — SeparateDatabaseAndState/CONCURRENTLY not used in any migration

**Task requirement**: "5 migration files created ... using SeparateDatabaseAndState/CONCURRENTLY for large tables"

**Actual state**: Zero migrations in the entire repository use `SeparateDatabaseAndState` or the PostgreSQL `CONCURRENTLY` index-creation pattern. `grep -r "SeparateDatabaseAndState" backend/` and `grep -r "CONCURRENTLY" backend/*/migrations/` return no results.

All five `0002_performance_indexes.py` files (notifications, crm, menu; enterprise and marketing are absent) use plain `migrations.AddIndex()`. On a live PostgreSQL database with millions of rows in the notifications or orders tables, this takes a full table lock for the duration of index creation, blocking writes.

**User-visible consequence**: Running `migrate` in production against a populated database will cause downtime or write-unavailability on the affected tables.

**Correction**: Replace each `AddIndex` in a performance-index migration with a `SeparateDatabaseAndState` block that runs `CREATE INDEX CONCURRENTLY` via `migrations.RunSQL` and uses a no-op `state_operations` list (or the equivalent `AddIndex` for state only). This is the standard Django pattern for zero-downtime index creation on large tables.

---

## Non-blocking observations (not blockers)

- Menu `0002` index (`menu_avail_branch_available_idx`) is correctly preserved after `0003` (which renames it to `menu_menuit_branch__534a94_idx`) — the net state delivers the branch+availability composite index. ✓
- The settings changes (CONN_MAX_AGE, CELERY routes/limits) are correct and free of duplicate or conflicting settings. ✓
- `docs/performance_assessment_phase22.md` covers all required audit sections. ✓
- Two pre-existing test failures in `OrganizationScopeTests` are outside FEAT-001 scope per commit message. ✓
