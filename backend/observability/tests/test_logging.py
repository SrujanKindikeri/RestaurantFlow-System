# =============================================================================
# RestaurantFlow — Observability Logging Tests
# Phase 24
# =============================================================================

import json
import logging
import io

from django.test import SimpleTestCase

from observability.logging_config import StructuredJsonFormatter, redact, _redact_string
from observability.context import LogContext, set_context, reset_context
from observability.constants import REQUEST_ID_INVALID


class StructuredLoggingTests(SimpleTestCase):

    def _make_record(self, **extra):
        record = logging.LogRecord(
            name="observability.test",
            level=logging.ERROR,
            pathname=__file__,
            lineno=1,
            msg="Bill finalization failed",
            args=None,
            exc_info=None,
        )
        for k, v in extra.items():
            setattr(record, k, v)
        return record

    def _format(self, record):
        stream = io.StringIO()
        handler = logging.StreamHandler(stream)
        handler.setFormatter(StructuredJsonFormatter())
        handler.emit(record)
        return stream.getvalue().strip()

    def test_json_formatter_emits_required_fields(self):
        record = self._make_record()
        out = self._format(record)
        payload = json.loads(out)
        for field in ("timestamp", "level", "service", "environment", "message"):
            self.assertIn(field, payload, f"missing {field} in {out}")
        self.assertEqual(payload["level"], "ERROR")
        self.assertEqual(payload["message"], "Bill finalization failed")
        self.assertEqual(payload["service"], "restaurantflow-api")

    def test_request_id_is_injected_from_context(self):
        token = set_context(LogContext(request_id="req-123", user_id="u-1"))
        try:
            record = self._make_record()
            out = self._format(record)
            payload = json.loads(out)
            self.assertEqual(payload["request_id"], "req-123")
            self.assertEqual(payload["user_id"], "u-1")
        finally:
            reset_context(token)

    def test_safe_tenant_context_included(self):
        token = set_context(LogContext(
            request_id="r", company_id="c", restaurant_id="rr", branch_id="b"
        ))
        try:
            payload = json.loads(self._format(self._make_record()))
            self.assertEqual(payload["company_id"], "c")
            self.assertEqual(payload["restaurant_id"], "rr")
            self.assertEqual(payload["branch_id"], "b")
        finally:
            reset_context(token)

    def test_sensitive_keys_are_redacted(self):
        record = self._make_record(
            password="s3cret", api_key="key-123", token="tok",
            card_number="4111111111111111", cvv="123",
        )
        payload = json.loads(self._format(record))
        self.assertEqual(payload["password"], "[REDACTED]")
        self.assertEqual(payload["api_key"], "[REDACTED]")
        self.assertEqual(payload["token"], "[REDACTED]")
        self.assertEqual(payload["card_number"], "[REDACTED]")
        self.assertEqual(payload["cvv"], "[REDACTED]")
        self.assertNotIn("s3cret", json.dumps(payload))
        self.assertNotIn("4111111111111111", json.dumps(payload))

    def test_authorization_header_value_masked(self):
        masked = _redact_string("Authorization: Bearer abc.def.ghi-secret")
        self.assertNotIn("abc.def.ghi-secret", masked)
        self.assertIn("[REDACTED]", masked)

    def test_exception_details_logged(self):
        try:
            raise ValueError("boom")
        except ValueError:
            import sys
            record = self._make_record()
            record.exc_info = sys.exc_info()
        payload = json.loads(self._format(record))
        self.assertEqual(payload["exception_type"], "ValueError")
        self.assertEqual(payload["exception_message"], "boom")
        self.assertIn("Traceback", payload["stack_trace"])
        # Stack trace must not contain local variable values from this frame.
        self.assertNotIn("s3cret", payload["stack_trace"])

    def test_invalid_request_id_dropped(self):
        token = set_context(LogContext(request_id=REQUEST_ID_INVALID))
        try:
            payload = json.loads(self._format(self._make_record()))
            self.assertIsNone(payload["request_id"])
        finally:
            reset_context(token)

    def test_redact_recursive(self):
        cleaned = redact({
            "ok": "visible",
            "password": "p",
            "nested": {"secret": "s", "safe": "ok", "token": "t"},
            "items": [{"authorization": "a"}],
        })
        self.assertEqual(cleaned["ok"], "visible")
        self.assertEqual(cleaned["password"], "[REDACTED]")
        self.assertEqual(cleaned["nested"]["safe"], "ok")
        self.assertEqual(cleaned["nested"]["secret"], "[REDACTED]")
        self.assertEqual(cleaned["items"][0]["authorization"], "[REDACTED]")
