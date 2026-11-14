# RestaurantFlow — Known Issues
## Phase 26 — Pre-Release Issue Register

**Last Updated:** Phase 26 Final QA Run  

---

## Open Issues

### KI-001: Nginx Configuration Absent from Repository
**Severity:** Major (Deployment Blocker)  
**Category:** Deployment  
**Description:** No Nginx configuration file exists in the repository. Without a production-ready Nginx config, the system cannot handle SSL termination, reverse proxy, rate limiting at the web server layer, or static file serving.  
**Impact:** Cannot deploy to production without manual Nginx setup.  
**Workaround:** Configure Nginx manually from the template in `production_operations_manual.md`.  
**Resolution Required Before:** Production deployment.

---

### KI-002: Backup Execution Scripts Absent
**Severity:** Major (Operational Risk)  
**Category:** Backup and Recovery  
**Description:** The `backup_management` Django app exists and has models, but the actual shell scripts or cron job templates for automated database backup execution are not present in the repository.  
**Impact:** No automated backup unless manually configured.  
**Workaround:** Use the manual backup commands in `production_operations_manual.md`.  
**Resolution Required Before:** Production deployment.

---

### KI-003: No Content-Security-Policy Header
**Severity:** Major (Security)  
**Category:** Security  
**Description:** The application does not set a `Content-Security-Policy` HTTP response header. This exposes the frontend to potential XSS attacks that a CSP could mitigate.  
**Detection:** Confirmed via `config/settings.py` inspection — no `CONTENT_SECURITY_POLICY` or `django-csp` configuration present.  
**Workaround:** Add `django-csp` package and configure CSP rules, or configure CSP via Nginx.  
**Resolution Required Before:** Production deployment (security hardening phase).

---

### KI-004: No Playwright/Browser Integration Tests
**Severity:** Minor (Test Coverage)  
**Category:** Testing  
**Description:** No end-to-end browser tests using Playwright or Selenium are implemented. The E2E test suite tests the backend service layer only. Full UI flows are not programmatically tested.  
**Impact:** Frontend regressions may not be caught by automated tests.  
**Workaround:** Manual UAT per `docs/user_acceptance_testing.md`.  
**Resolution Required Before:** Next major release.

---

### KI-005: Performance Benchmarks Not Re-Run
**Severity:** Minor (Performance)  
**Category:** Performance  
**Description:** Database query performance, API response times, and load test results have not been measured in Phase 26. The database indexes added in Phases 10–25 are assumed to be functional but have not been benchmarked.  
**Impact:** Unknown production performance characteristics under load.  
**Workaround:** None — benchmark before production launch.  
**Resolution Required Before:** Production launch.

---

### KI-006: DEBUG=True in Default Config
**Severity:** Critical (Security)  
**Category:** Security  
**Description:** `config/settings.py` has `DEBUG = True` as its configured value. This must be overridden via the `DEBUG` environment variable before production deployment.  
**Detection:** Confirmed via settings inspection: `DEBUG: True`.  
**Impact:** Exposes stack traces, internal error details, and may disable security features.  
**Resolution:** Set `DEBUG=False` via environment variable in production.  
**Resolution Required Before:** Production deployment (must be verified before go-live).

---

### KI-007: Rate Limiting Not Configured
**Severity:** Major (Security)  
**Category:** Security  
**Description:** `REST_FRAMEWORK['DEFAULT_THROTTLE_CLASSES']` is empty. No API rate limiting is enforced. The system is vulnerable to brute-force login attacks, API abuse, and resource exhaustion.  
**Detection:** Confirmed via settings inspection: `throttle classes: []`.  
**Workaround:** Implement throttle classes in `config/settings.py` or use Nginx rate limiting.  
**Resolution Required Before:** Production deployment.

---

### KI-008: SESSION_COOKIE_SECURE and CSRF_COOKIE_SECURE are False
**Severity:** Major (Security)  
**Category:** Security  
**Description:** Both `SESSION_COOKIE_SECURE` and `CSRF_COOKIE_SECURE` are set to `False`. This allows session and CSRF tokens to be transmitted over unencrypted HTTP, enabling theft.  
**Detection:** Confirmed via settings inspection.  
**Resolution:** Set both to `True` via environment variable in production when HTTPS is enforced.  
**Resolution Required Before:** Production deployment.

---

### KI-009: Pre-Existing E2E Test Failures (Workflows A and B)
**Severity:** Minor (Test Coverage)  
**Category:** Testing  
**Description:** 9 tests in the pre-existing E2E test files (`test_workflow_a_onboarding.py` and `test_workflow_b_pos_order.py`) fail because they reference service API names (`complete_payment`, `create_kitchen_order`, `initiated_by` parameter) that do not match the actual service layer implementations.  
- `complete_payment` does not exist — `create_payment` returns a completed payment directly.
- `create_kitchen_order` is not an exported function from `kitchen.services`.
- `POST /api/restaurants/` returns 405 (endpoint is read-only list view).  
**Impact:** Test failures are not system bugs — the tests have incorrect expectations. These tests were delivered as "done" in Phase 26 Step 1.  
**Workaround:** Tests skip gracefully in most cases. Full service verification requires manual testing or service API name correction.  
**Resolution Required Before:** Next test maintenance cycle.

---

### KI-010: Safety Vulnerability Scan Not Run
**Severity:** Minor (Security)  
**Category:** Security  
**Description:** The `safety` package for Python dependency vulnerability scanning is not installed in the development/CI environment. Dependency vulnerabilities have not been checked.  
**Resolution:** Install `safety` and run `safety check` before production deployment.  
**Resolution Required Before:** Production deployment.

---

## Closed Issues (from Previous Phases)

| Issue | Description | Resolved In |
|---|---|---|
| Missing migrations (backup_management/0002, central_control/0003, notifications/0005) | 3 missing migrations blocked `makemigrations --check` | Phase 26 Step 2 (commit e491801) |
