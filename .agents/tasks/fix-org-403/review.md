# HTTP 403 fix for POST /api/organizations/

The 403 was caused by two distinct problems. The annotation names `restaurant_count` and `active_restaurant_count` on the queryset collided with same-name model properties, triggering an `AttributeError` during queryset evaluation for non-superusers; this was silently swallowed and surfaced as a 403. The fix renames the annotations to `restaurant_count_annotated` / `active_restaurant_count_annotated`, adds `SerializerMethodField` wrappers that prefer the annotation and fall back to the model property, wraps `perform_create` in `@transaction.atomic`, appends a `SecurityAuditLog` entry, and replaces the frontend's single-catch block with per-status-code error messages. The existing `HasPermission("organization.create")` permission gate is correctly in place and was not bypassed.

**Watch for:**
- Audit log event reuse (confirmed): `EVENT_USER_CREATED` is used to record `organization_created`; this mismatches the event semantics stored in the log.
- Three required test scenarios missing (confirmed): "Restaurant Owner without required permission → 403", "audit log entry written on success", and "atomic rollback on partial failure" are absent from `OrganizationPermissionTests`.
- Serializer fallback returns `None` instead of `0` (confirmed): when neither annotation nor property is available the `get_restaurant_count` fallback silently passes through `None`.

**Verdict**: NEEDS_CHANGES

---

## High-level view

The annotation name collision was the mechanical root of the 403. Superusers bypassed the broken queryset path, so CRUD tests passed before this fix; non-superusers hit the collision and the error propagated as a permission failure. Renaming the annotations and adding `SerializerMethodField` wrappers resolves this without changing the access-control logic.

The permission gate for POST is `IsAuthenticated` + `HasPermission("organization.create")`, evaluated via `get_permissions()`. The `HasPermission` factory returns a class and the view instantiates it correctly with `()`. Superusers short-circuit at `acl.has_permission` via the `is_superuser` fast path, and COMPANY_HEAD users reach it through a role assignment carrying `organization.create`. Both paths are tested.

The audit log wires into the existing `record_security_event` / `SecurityAuditLog` infrastructure, but the event chosen (`EVENT_USER_CREATED`) is a semantic mismatch — there is no `EVENT_ORGANIZATION_CREATED` constant in `SecurityAuditLog.EVENT_CHOICES`, and the metadata `"action": "organization_created"` only partially compensates because anything querying the log by event type will conflate organization creations with user creations.

The frontend error handler now dispatches on HTTP status (400 → field errors, 403 → permission denied, 401 → session expired, 409 → conflict, else → generic retry). The `catch` branch is entered at most once per submission, so the repeated-toast problem is resolved.

The test suite grows from the existing 31 tests to 40 tests (9 new in `OrganizationPermissionTests`). The new tests cover superuser create, COMPANY_HEAD create, unauthenticated 401, unauthorized 403, invalid data 400, first-org bootstrap, full-field persistence, duplicate-name slug disambiguation, and cross-company queryset scoping. Three scenarios from the brief's required list of 12 are absent.

---

<details>
<summary>Issues (7)</summary>

1. **Audit log event mismatch** — `EVENT_USER_CREATED` is used to record organization creation. This conflates org-creation events with user-creation events in any audit log query filtered by event type. Use `EVENT_SECURITY_ALERT` with a descriptive `metadata["action"]`, or add an `EVENT_ORGANIZATION_CREATED` constant, until a proper domain event exists.

2. **Missing test: Restaurant Owner → 403** — The brief requires a test that a Restaurant Owner without `organization.create` receives 403. No such test exists in `OrganizationPermissionTests`. Add `test_restaurant_owner_without_permission_receives_403` using a user with `CODE_RESTAURANT_OWNER` role but no `organization.create` permission.

3. **Missing test: audit log written on success** — The brief requires verifying the audit record is created. Add a test that calls POST as a superuser and asserts `SecurityAuditLog.objects.filter(metadata__action="organization_created").exists()`.

4. **Missing test: atomic rollback** — The brief requires verifying that a failure inside `perform_create` after `serializer.save()` does not leave a partial record. No test covers the `@transaction.atomic` guarantee added in this diff.

5. **Serializer fallback returns `None`** — `get_restaurant_count` returns `getattr(obj, "restaurant_count_annotated", None) if hasattr(obj, "restaurant_count_annotated") else obj.restaurant_count`. When `restaurant_count_annotated` is present but `None` (edge case in some ORM paths), the method returns `None` rather than `0`. The `RestaurantSerializer` sibling uses `or` chaining (`getattr(...) or obj.branch_count`) which handles `None`/`0` correctly; `OrganizationSerializer` should follow the same pattern.

6. **Soft test assertion on restaurant-list isolation** — `test_restaurant_list_for_org_a_returns_org_a_restaurants_only` now accepts `(200, 404)` for `user_b`. Scoped querysets should deterministically 404 when the organization isn't in scope; accepting 200 leaves a path where `user_b` sees an empty list for `org_a` without the test catching it. Harden to assert only `HTTP_404_NOT_FOUND`.

7. **Frontend error type cast suppresses future safety** — The `catch` block casts `err` to `{ response?: { status?: number; data?: Record<string, unknown> } }`. If a middleware returns a plain string error body, `Object.entries(data)` on a non-object silently produces an empty list, falling back to the generic message. Replace with Axios's `isAxiosError` guard and `AxiosError<Record<string, unknown>>` to retain type safety as the error surface grows.

</details>

---

<details>
<summary>Details</summary>

## Annotation collision and the false 403

Before this fix, `get_organization_queryset` annotated the queryset with `restaurant_count` and `active_restaurant_count` — the same names as model properties on `Organization`. DRF's `IntegerField(read_only=True)` on the serializer expected the annotation to exist on the queryset object; the collision caused `AttributeError` during queryset evaluation for non-superusers, which propagated as 403 rather than 500. The fix gives annotations distinct names (`_annotated` suffix) and replaces the two `IntegerField` declarations with `SerializerMethodField`, resolving the collision. `RestaurantSerializer` already used this pattern (documented as "Phase 21 fix"), so this brings `OrganizationSerializer` in line.

## Atomic creation and audit log

`@transaction.atomic` is added to `perform_create`. The audit log write is in a `try/except Exception` block outside any savepoint, which means an audit log failure logs a warning but does not roll back the organization. This is the correct trade-off (org creation should not fail because of a secondary log write), but the brief asks for a test verifying the rollback when creation itself fails — that test is absent.

The audit log uses `SecurityAuditLog.EVENT_USER_CREATED` with `metadata["action"] = "organization_created"`. `EVENT_USER_CREATED` is a valid constant in `SecurityAuditLog.EVENT_CHOICES`, so the write will not raise an `IntegrityError`, but the semantics are wrong: the event type describes a user being created, not an organization. Any query or alert rule filtering on `event=EVENT_USER_CREATED` will now include false positives from org creation events. The intent is documented in a comment, but that doesn't fix the query-time confusion.

## Test coverage gaps against the 12-scenario brief

`OrganizationPermissionTests` delivers 9 of the 12 required scenarios. Covered: superuser creates (scenario 1), COMPANY_HEAD creates (scenario 2), unauthenticated 401 (scenario 3), unauthorized 403 (scenario 4), invalid data 400 (scenario 6), first-org bootstrap (scenario 8), full-field persistence (scenario 9 / "atomic creation"), duplicate handling (scenario 7), cross-company scoping (scenario 10).

Missing:
- Scenario 5: Restaurant Owner without `organization.create` → 403. The generic `test_authenticated_without_permission_receives_403` uses a plain user with no role, not a Restaurant Owner. This matters because `IsOrganizationAdmin` grants org-admins a fast path; a Restaurant Owner could theoretically match that check without holding `organization.create`. A dedicated test is needed.
- Scenario 11: Audit log entry written on successful creation.
- Scenario 12: Atomic rollback on failure mid-creation.

## CrossOrganizationSecurityTests behavioral change

The diff changes `test_organization_detail_is_accessible_phase2` from asserting `HTTP_200_OK` to `HTTP_404_NOT_FOUND`, and softens `test_restaurant_list_for_org_a_returns_org_a_restaurants_only` to accept either 200 or 404. These reflect Phase 3 scoped-queryset behavior and are consistent with the access control design — a user with no role assignment gets an empty queryset, so a direct-UUID lookup returns 404 rather than 403, preventing existence leakage. The soft assertion on the restaurant-list test (`assertIn(response.status_code, (200, 404))`) is pragmatic but reduces test specificity. The behavior should be deterministic: if `user_b` has no scope to `org_a`, the view should consistently return 404, not sometimes 200.

## Frontend error handling

The error type is cast as `{ response?: { status?: number; data?: Record<string, unknown> } }` rather than through Axios's typed `AxiosError<T>`. That's a narrower type than Axios provides, so if the response body shape ever diverges from `Record<string, unknown>` (e.g., a plain string error from a middleware), `Object.entries(data)` on a non-object will silently produce an empty field message list and fall through to the generic "Invalid data" text. The commit confirms `tsc --noEmit` passes so no type errors are introduced now, but the cast suppresses future type-safety at this call site.

</details>

---

<details>
<summary>File map</summary>

- `backend/organizations/views.py` — renamed annotations to `_annotated` suffix; added `@transaction.atomic` to `perform_create`; added `SecurityAuditLog` write via `record_security_event`.
- `backend/organizations/serializers.py` — replaced `IntegerField(read_only=True)` with `SerializerMethodField` for `restaurant_count` and `active_restaurant_count` on `OrganizationSerializer`.
- `backend/organizations/tests.py` — added `make_superuser` and `make_company_head_user` helpers; upgraded existing test classes to use superuser; added `organization` FK to restaurant/branch payloads; updated `CrossOrganizationSecurityTests` for Phase 3 scoped-queryset semantics; added `OrganizationPermissionTests` with 9 scenarios.
- `frontend/src/pages/organizations/OrganizationsListPage.tsx` — replaced single-catch generic toast with per-HTTP-status error messages (400 field errors, 403 permission denied, 401 session expired, 409 conflict, else generic retry).

Full diff: `git -C c:\Users\kindi\OneDrive\Documents\RestaurantFlow-System\.worktrees\fix-org-403 diff HEAD~1...HEAD`

</details>
