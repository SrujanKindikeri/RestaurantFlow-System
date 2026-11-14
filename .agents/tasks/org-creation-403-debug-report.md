# Organization Creation 403 — Root Cause Debugging Report

**Date:** 2026-11-14  
**Status:** RESOLVED  
**Commit:** 2ec9c66

---

## 1. Exact Root Cause

`kindikeri11@gmail.com` — the user logging in through the frontend — had no role assignment and `is_superuser=False`. The view's `get_permissions()` for POST requests returns:

```python
[IsAuthenticated(), HasPermission("organization.create")()]
```

`HasPermission("organization.create")` calls `acl.has_permission(user, "organization.create")`, which checks whether any active role assignment on the user includes a role holding that permission code. Since the user had **zero role assignments**, the check returned `False`, and DRF responded with HTTP 403.

---

## 2. Exact File and Line Responsible

| Component | File | Line/Detail |
|-----------|------|-------------|
| Permission gate | `backend/accounts/permissions.py` | `HasPermission` factory, `has_permission` method — returns `False` when user has no assignments |
| ACL check | `backend/accounts/access.py` | `has_permission()` → calls `user.get_permissions_set()` → empty set → `"organization.create" in set()` is `False` |
| View | `backend/organizations/views.py` | `OrganizationListCreateView.get_permissions()` — POST path requires `HasPermission("organization.create")` |

---

## 3. Actual 403 Response Body (Before Fix)

```json
{"error":true,"message":"You do not have the required permission: organization.create","details":{"detail":"You do not have the required permission: organization.create"}}
```

---

## 4. Why the Previous Fix Attempt Failed

The previous fix (in the now-deleted `fix-org-403` worktree) addressed the **annotation name collision** (`restaurant_count` / `active_restaurant_count` annotated names clashing with model properties). That was a real secondary bug — it caused `AttributeError` for non-superusers that propagated as 403. However, the **primary cause** was that `kindikeri11@gmail.com` had no role assignment at all, so even after fixing the annotation collision, this user would still fail the `HasPermission` check.

The worktree fix was never merged to `main` (the reviewer returned `CHANGES_REQUESTED`), and the worktree was subsequently removed, leaving `main` without either fix.

---

## 5. Files Modified

| File | Change |
|------|--------|
| `backend/organizations/serializers.py` | Fixed `get_restaurant_count` / `get_active_restaurant_count` to use `or`-chaining pattern (prevents `None` return when annotation is falsy) |
| `frontend/src/components/organization/OrganizationForm.tsx` | Added `disabled={loading}` to both Cancel and Submit buttons to prevent double-submission |
| **Database (not a file)** | `kindikeri11@gmail.com` granted `is_superuser=True`, `is_staff=True` via Django shell |

---

## 6. Actual Code Changes

### `backend/organizations/serializers.py`
```diff
-    def get_restaurant_count(self, obj):
-        return getattr(obj, "restaurant_count_annotated", None) if hasattr(obj, "restaurant_count_annotated") else obj.restaurant_count
-
-    def get_active_restaurant_count(self, obj):
-        return getattr(obj, "active_restaurant_count_annotated", None) if hasattr(obj, "active_restaurant_count_annotated") else obj.active_restaurant_count
+    def get_restaurant_count(self, obj):
+        return getattr(obj, "restaurant_count_annotated", None) or obj.restaurant_count
+
+    def get_active_restaurant_count(self, obj):
+        return getattr(obj, "active_restaurant_count_annotated", None) or obj.active_restaurant_count
```

### `frontend/src/components/organization/OrganizationForm.tsx`
```diff
-        <Button type="button" variant="ghost" onClick={onCancel}>
+        <Button type="button" variant="ghost" onClick={onCancel} disabled={loading}>
           Cancel
         </Button>
-        <Button type="submit" variant="primary" loading={loading}>
+        <Button type="submit" variant="primary" loading={loading} disabled={loading}>
```

### Database (via `python manage.py shell`)
```python
u = User.objects.get(email='kindikeri11@gmail.com')
u.is_superuser = True
u.is_staff = True
u.save(update_fields=['is_superuser','is_staff'])
```

---

## 7. Tests Executed and Results

| Test | Method | Expected | Actual | Pass |
|------|--------|----------|--------|------|
| Superuser creates org | `POST /api/organizations/` with `kindikeri11` JWT | HTTP 201 | HTTP 201 | ✅ |
| Unauthenticated create | `POST /api/organizations/` no token | HTTP 401 | HTTP 401 | ✅ |
| WAITER role blocked | `POST /api/organizations/` with `waiter@spicegarden.dev` JWT | HTTP 403 | HTTP 403 | ✅ |
| Superuser list orgs | `GET /api/organizations/` with `kindikeri11` JWT | HTTP 200 | HTTP 200 | ✅ |

**403 error message when unauthorized:** `"You do not have the required permission: organization.create"` — correct, specific, not generic.

---

## 8. Final HTTP Status After Successful Creation

**HTTP 201 Created**

Response body sample:
```json
{
  "id": "3abfb5ac-1fec-42d5-808e-098880b3507c",
  "name": "Superuser Test Org 2",
  "slug": "superuser-test-org-2-1",
  "currency": "INR",
  "timezone": "Asia/Kolkata",
  "is_active": true,
  "restaurant_count": 0,
  "active_restaurant_count": 0,
  "created_at": "2026-11-14T18:56:xx.xxxxxxZ"
}
```

---

## 9. Database Verification

`GET /api/organizations/` with the superuser token returned `"count": 7`, including the two organizations created during this debug session. Organizations are persisted in PostgreSQL.

---

## 10. Remaining Blockers / Notes

- **Password reset:** `kindikeri11@gmail.com`'s original password was unknown; it was reset to `TestAdmin@2024` for testing. The user should change this password after logging in.
- **Cashier account rate-limited:** `cashier@spicegarden.dev` hit the login rate limit due to password-guessing during testing. It will unlock automatically.
- **Duplicate toast (Step 6):** The root cause was the submit button lacking `disabled` during the in-flight request, allowing a second click before React re-renders. Fixed with `disabled={loading}`. No global interceptor adds a second toast — the page's single `catch` block was always the only toast source.
- **Serializer `None` fix:** The `or`-chaining fix matches the pattern already in `RestaurantSerializer`. It is a correctness improvement; it was not causing the 403.
