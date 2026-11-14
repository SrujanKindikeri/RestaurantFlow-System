# Logging Strategy — Phase 24

## Format

- **Default (`LOG_FORMAT=text`):** existing human-readable format (dev/test).
- **Production (`LOG_FORMAT=json`):** the `console` handler uses
  `observability.logging_config.StructuredJsonFormatter`, emitting one JSON
  object per line for log aggregation (Loki/Promtail or any JSON collector).

## JSON schema (base fields)

```json
{
  "timestamp": "2026-11-14T10:30:00.123456+00:00",
  "level": "ERROR",
  "service": "restaurantflow-api",
  "environment": "production",
  "request_id": "a1b2...hex",
  "user_id": "<uuid or null>",
  "company_id": "<uuid or null>",
  "restaurant_id": "<uuid or null>",
  "branch_id": "<uuid or null>",
  "module": "billing",
  "event": "bill.finalization.failed",
  "message": "Bill finalization failed",
  "duration_ms": 240,
  "error_code": "BILL_VALIDATION_ERROR",
  "exception_type": "ValueError",
  "exception_message": "...",
  "stack_trace": "Traceback ..."
}
```

`timestamp` is ISO-8601 UTC; `level` is the LogRecord `levelname`; `service`
and `environment` come from `OBSERVABILITY_SERVICE_NAME` /
`OBSERVABILITY_ENVIRONMENT`. Non-standard `extra=...` kwargs are merged and
**redacted**. Base fields present-but-null are kept for stable indexing.

## Request correlation

- `X-Request-ID` is validated against `^[A-Za-z0-9._\-]{1,128}$`. Invalid or
  missing ids are replaced with a generated UUID hex.
- The id is stored in a contextvar (`observability.context`) so every log
  line during the request carries it, and it is propagated into Celery task
  context where present.
- The id is echoed on the response (`X-Request-ID` header).
- The client-supplied id is **never** used for authorization.

## Sensitive data

`observability.logging_config.SENSITIVE_LOG_KEYS` (password, token,
authorization, api_key, secret, db_password, redis_password, card_number,
pan, cvv, upi_pin, session_key, private_key, …) are redacted to `[REDACTED]`
in any dict key. Strings containing `Authorization: Bearer …`-style values
are masked to end-of-line. Redaction never raises.

**Never log:** passwords, session tokens, API keys, secret keys, DB/Redis
passwords, card numbers, CVVs, UPI credentials, authentication headers,
provider credentials, or unnecessary personal information. Application logs
are **not** the financial audit trail — the existing audit system remains
authoritative.

## Rotation & retention

- `RotatingFileHandler`: 10 MB per file × 5 backups for `general.log`,
  `errors.log`, `security.log` (kept from Phase 1–23).
- `LOG_LEVEL` defaults to INFO (DEBUG in dev).
- Set operational retention at the log-aggregation layer (Loki retention) or
  via logrotate on the host for the rotating files. Avoid unlimited retention.
- Do not treat application logs as the official audit trail.

## Frontend errors

`POST /api/observability/frontend-errors` accepts only safe diagnostic
fields (`type`, `message` (truncated), `url`, `line`, `column`, `severity`,
`app_version`, `request_id`). No payloads/bodies are recorded. Rate-limited
(`THROTTLE_FRONTEND_ERRORS`, default 120/min per IP). Front-end must never
display stack traces to ordinary users.
