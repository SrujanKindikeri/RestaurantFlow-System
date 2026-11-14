# Investigation Report: "Failed to create organization" Error

## Summary

The most likely cause of the error is a **missing `organization.create` permission** on the logged-in user's role. The `POST /api/organizations/` endpoint requires the `HasPermission("organization.create")` check to pass before the request reaches the database. When it fails, the backend returns HTTP 403 with a DRF JSON error body. The frontend catches that rejection but discards the server's error details entirely — the `catch {}` block in `OrganizationsListPage.tsx` takes no parameter and shows a hardcoded toast: `'Failed to create organization.'`.

Three failure scenarios can produce this error. They are ordered by likelihood:

1. **Permission denied (most likely)** — the authenticated user does not have `organization.create` in their role's permission set. HTTP 403.
2. **Slug uniqueness collision** — an organization with the same name already exists and its auto-generated slug conflicts. HTTP 400.
3. **Unexpected server error** — unhandled exception or DB connectivity issue. HTTP 500.

---

## Evidence

### 1. API endpoint and routing

**File:** `backend/organizations/urls.py`

```
POST /api/organizations/   →   OrganizationListCreateView
```

Mounted at `path("api/", include("organizations.urls"))` in `backend/config/urls.py`.

The frontend service calls:

```typescript
// frontend/src/services/organizations.ts
export const createOrganization = (data: OrganizationCreatePayload) =>
  post<Organization>(BASE + '/', data)   // BASE = '/organizations'
```

Base URL: `VITE_API_URL ?? 'http://localhost:8000/api'` (from `frontend/src/services/api.ts`). Full URL therefore resolves to `http://localhost:8000/api/organizations/`.

---

### 2. Backend permission gate — the primary suspect

**File:** `backend/organizations/views.py`, lines 155–159

```python
class OrganizationListCreateView(generics.ListCreateAPIView):
    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated(), HasPermission("organization.create")()]
        return [IsAuthenticated()]
```

The `HasPermission` factory (`backend/accounts/permissions.py`) creates a DRF permission class. When `.has_permission()` returns `False` on the `HasPermission("organization.create")` instance, DRF raises `PermissionDenied` before `perform_create` is ever called. DRF returns HTTP 403.

The permission check path (`backend/accounts/access.py` → `has_permission()`):

1. Superusers always pass.
2. For normal users, the function calls `CacheService.get_secure(cache_key)`.
   - If Redis is up: looks up cached permission set from Redis.
   - If cache is cold (first call): queries the DB and caches the result.
   - If Redis is **down**: returns `CACHE_MISS_SENTINEL`, falls back to `user.has_perm_code(code)` (direct DB query).
3. The user must have an active `UserRoleAssignment` → active `Role` → `Permission(code="organization.create", is_active=True)`.

**The seed data** (`backend/organizations/management/commands/seed_demo_data.py`) shows that only the `COMPANY_HEAD` role has `organization.create`:

```python
ROLES = [
    {
        "code": "COMPANY_HEAD",
        "permissions": [
            "organization.view", "organization.create", ...  # line 138
        ]
    },
    {
        "code": "CENTRAL_ADMIN",
        "permissions": [
            "organization.view",   # NO organization.create
            ...
        ]
    },
    # All other roles: Restaurant Owner, Manager, Cashier, etc.
    # None of them have organization.create
]
```

A user logged in as `CENTRAL_ADMIN`, `RESTAURANT_OWNER`, or any branch-level role **will be denied**.

---

### 3. What validations could fail in the serializer

**File:** `backend/organizations/serializers.py`

`OrganizationSerializer` has only one custom validator:

```python
def validate_name(self, value):
    value = value.strip()
    if not value:
        raise serializers.ValidationError("Organization name cannot be blank.")
    return value
```

All other fields (`legal_name`, `email`, `phone`, etc.) are `blank=True` at the model level (`backend/organizations/models.py`). The only model-level constraint that could cause a DB-level failure on creation is:

```python
slug = models.SlugField(max_length=255, unique=True)
```

The `Organization.save()` method auto-generates a unique slug by appending a counter, so a collision would only fail if the loop is somehow broken. This is not a known issue.

The `tax_id` field has `max_length=100, blank=True` — it is entirely optional and the placeholder `29AABCT1332L1ZD` being visible means the field was **left empty**, which is fine.

---

### 4. What the frontend error handler does

**File:** `frontend/src/pages/organizations/OrganizationsListPage.tsx`, lines 33–40

```typescript
async function handleCreate(payload) {
  try {
    await createOrg.mutateAsync(payload)
    setShowCreate(false)
    toast('Organization created.', 'success')
  } catch {              // ← bare catch, no error parameter
    toast('Failed to create organization.', 'error')
  }
}
```

The `catch` block has **no parameter** — the full Axios error (including `error.response.data`, status code, and the server's JSON body) is silently discarded. The user only ever sees the hardcoded string `'Failed to create organization.'`. There is no `console.error` call anywhere in this handler.

**What the server actually returns** on a 403:

The custom exception handler (`backend/core/exceptions.py`) wraps DRF errors into:

```json
{
  "error": true,
  "message": "You do not have the required permission: organization.create",
  "details": { "detail": "You do not have the required permission: organization.create" }
}
```

This body is never surfaced to the user or the console.

---

### 5. Recent changes

The two most recent commits touching organization-adjacent files are:

```
a35f74d  fix: correct performance index migrations to use CONCURRENTLY and fix model Meta.indexes
8981632  feat: FEAT-001 DB query optimisation + indexing + docs
```

Neither modifies `organizations/views.py`, `organizations/serializers.py`, the permission logic, or the frontend form. The organization creation flow itself has not changed recently. The most recent change to the forms/hooks/services is from at least several weeks prior. No regression was introduced here.

---

### 6. Backend error logging

`OrganizationListCreateView.perform_create()` logs success:

```python
def perform_create(self, serializer):
    org = serializer.save()
    logger.info("Organization created: %s ...", ...)
```

But on a 403, `perform_create` is never reached. The permission check log appears in `accounts/permissions.py`:

```python
logger.warning(
    "Permission denied: user=%s code=%s view=%s",
    request.user.email,
    self.required_code,
    view.__class__.__name__,
)
```

And in `core/exceptions.py`:

```python
logger.warning(
    "API error %s: %s | view=OrganizationListCreateView",
    403,
    str(exc),
)
```

Both entries land in the backend logs, but nothing is forwarded to the browser.

---

## Conclusions

### Root cause (most likely)

The logged-in user does not hold the `organization.create` permission. The backend returns HTTP 403. The frontend catches the error and shows the hardcoded toast without logging or surfacing the actual 403 response.

This is confirmed by the role matrix: only `COMPANY_HEAD` has `organization.create`. Any other role — including `CENTRAL_ADMIN` — is denied.

### Contributing issue

The `catch {}` block in `handleCreate` discards all error information, making it impossible for users or developers to self-diagnose the failure without reading backend logs or browser network traffic.

---

## Recommendations

### Fix 1 — Verify and correct the user's role

Log in as a superuser or as the `company@restaurantflow.dev` demo account (role: `COMPANY_HEAD`), which has the `organization.create` permission. If the failing user is a `CENTRAL_ADMIN`, assign them the `organization.create` permission or log in as `COMPANY_HEAD` to create organizations.

### Fix 2 — Surface the server error message in the frontend

Change `OrganizationsListPage.tsx` to capture and display the server's error message:

```typescript
// frontend/src/pages/organizations/OrganizationsListPage.tsx
import type { AxiosError } from 'axios'
import type { ApiError } from '@/types'

async function handleCreate(payload) {
  try {
    await createOrg.mutateAsync(payload)
    setShowCreate(false)
    toast('Organization created.', 'success')
  } catch (err) {
    const axiosErr = err as AxiosError<ApiError>
    const serverMessage = axiosErr.response?.data?.message
    toast(serverMessage ?? 'Failed to create organization.', 'error')
    console.error('[createOrganization]', axiosErr.response?.status, axiosErr.response?.data)
  }
}
```

This change would immediately show `"You do not have the required permission: organization.create"` to the user instead of the generic message.

### Fix 3 (optional) — Extend `CENTRAL_ADMIN` permissions

If it is intentional for `CENTRAL_ADMIN` to be able to create new organizations, add `organization.create` to the `CENTRAL_ADMIN` role in the seed command and update the database via Django admin or a migration/data fixture.

---

## Files Investigated

| File | Purpose |
|------|---------|
| `backend/organizations/views.py` | `OrganizationListCreateView` — POST handler with permission gate |
| `backend/organizations/serializers.py` | `OrganizationSerializer` — field validation |
| `backend/organizations/models.py` | `Organization` model — field constraints, slug generation |
| `backend/organizations/urls.py` | URL routing |
| `backend/accounts/permissions.py` | `HasPermission` factory |
| `backend/accounts/access.py` | `has_permission()` — permission resolution with Redis cache |
| `backend/accounts/models.py` | `Role`, `Permission`, `UserRoleAssignment` |
| `backend/organizations/management/commands/seed_demo_data.py` | Role/permission definitions |
| `backend/core/exceptions.py` | Custom DRF exception handler |
| `backend/common/caching/services.py` | `CacheService.get_secure()` — Redis fallback |
| `backend/config/urls.py` | Root URL config |
| `backend/config/settings.py` | `REST_FRAMEWORK` settings |
| `frontend/src/services/organizations.ts` | `createOrganization` API call |
| `frontend/src/hooks/useOrganizations.ts` | `useCreateOrganization` mutation |
| `frontend/src/pages/organizations/OrganizationsListPage.tsx` | Form submit handler and error toast |
| `frontend/src/components/organization/OrganizationForm.tsx` | Form fields and local validation |
| `frontend/src/services/api.ts` | Axios client, JWT interceptor |
| `frontend/src/types/index.ts` | `OrganizationCreatePayload` type |
