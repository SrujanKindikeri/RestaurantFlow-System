# =============================================================================
# RestaurantFlow — Alert Forwarding Tests
# Phase 24
#
# Verifies Alertmanager webhooks forward into the EXISTING CentralAlert model
# with deduplication, lifecycle (resolve), severity mapping, and a notification
# delivered via the EXISTING Phase 16 notification center.
# =============================================================================

import json

from django.test import TestCase, override_settings
from django.urls import reverse

from central_control.models import CentralAlert
from central_control.constants import ALERT_OPEN, ALERT_RESOLVED, SEVERITY_HIGH, SEVERITY_MEDIUM
from notifications.models import Notification
from observability.tests.base import make_org


AM_TOKEN = "am-secret-token"


def firing_alert(alertname="HighErrorRate", severity="high", instance="backend:8000"):
    return {
        "alerts": [
            {
                "status": "firing",
                "labels": {"alertname": alertname, "severity": severity, "instance": instance},
                "annotations": {"summary": f"{alertname} firing", "description": "threshold exceeded"},
            }
        ]
    }


@override_settings(ALERTMANAGER_WEBHOOK_TOKEN=AM_TOKEN)
class AlertmanagerWebhookTests(TestCase):

    def setUp(self):
        self.org = make_org("Alert Corp")
        self.url = reverse("observability_alertmanager_webhook")

    def _post(self, payload, token=AM_TOKEN):
        return self.client.post(
            self.url,
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_X_ALERTMANAGER_TOKEN=token,
        )

    def test_webhook_requires_token(self):
        resp = self.client.post(self.url, data=json.dumps(firing_alert()),
                               content_type="application/json")
        self.assertEqual(resp.status_code, 403)
        # wrong token
        resp = self._post(firing_alert(), token="wrong")
        self.assertEqual(resp.status_code, 403)

    def test_webhook_creates_central_alert(self):
        resp = self._post(firing_alert(severity="high"))
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["created"], 1)
        alerts = CentralAlert.objects.filter(organization=self.org, source_type="MONITORING")
        self.assertEqual(alerts.count(), 1)
        alert = alerts.first()
        self.assertEqual(alert.severity, SEVERITY_HIGH)
        self.assertEqual(alert.status, ALERT_OPEN)
        self.assertEqual(alert.alert_type, "SYSTEM_HEALTH")
        self.assertEqual(alert.detection_count, 1)

    def test_dedup_increments_detection_count(self):
        self._post(firing_alert())
        self._post(firing_alert())
        self._post(firing_alert())
        alerts = CentralAlert.objects.filter(organization=self.org, source_type="MONITORING")
        self.assertEqual(alerts.count(), 1)
        self.assertEqual(alerts.first().detection_count, 3)

    def test_severity_escalation_on_re_detection(self):
        self._post(firing_alert(severity="warning"))   # -> MEDIUM
        self._post(firing_alert(severity="critical"))  # -> CRITICAL
        alert = CentralAlert.objects.filter(organization=self.org, source_type="MONITORING").first()
        self.assertEqual(alert.severity, "CRITICAL")

    def test_resolved_status_resolves_alert(self):
        self._post(firing_alert())
        self.assertEqual(CentralAlert.objects.filter(status=ALERT_OPEN).count(), 1)
        resolved_payload = {
            "alerts": [
                {
                    "status": "resolved",
                    "labels": {"alertname": "HighErrorRate", "severity": "high", "instance": "backend:8000"},
                    "annotations": {"summary": "resolved"},
                }
            ]
        }
        self._post(resolved_payload)
        self.assertEqual(CentralAlert.objects.filter(status=ALERT_RESOLVED).count(), 1)
        self.assertEqual(CentralAlert.objects.filter(status=ALERT_OPEN).count(), 0)

    def test_high_severity_creates_notification(self):
        self._post(firing_alert(severity="high"))
        notifs = Notification.objects.filter(notification_type="monitoring_alert", company=self.org)
        self.assertEqual(notifs.count(), 1)
        self.assertEqual(notifs.first().severity, SEVERITY_HIGH)

    def test_medium_severity_does_not_notify(self):
        self._post(firing_alert(severity="warning"))  # -> MEDIUM
        notifs = Notification.objects.filter(notification_type="monitoring_alert", company=self.org)
        self.assertEqual(notifs.count(), 0)
        # but the alert still exists
        self.assertEqual(CentralAlert.objects.filter(source_type="MONITORING").count(), 1)

    def test_secret_labels_are_redacted(self):
        payload = {
            "alerts": [
                {
                    "status": "firing",
                    "labels": {"alertname": "DbDown", "severity": "critical",
                               "instance": "db:5432", "db_password": "hunter2"},
                    "annotations": {"summary": "DB down", "description": "auth token=abc123"},
                }
            ]
        }
        self._post(payload)
        alert = CentralAlert.objects.filter(organization=self.org, source_type="MONITORING").first()
        # The secret label value must not be persisted in the alert message/source.
        self.assertNotIn("hunter2", alert.message)
        self.assertNotIn("hunter2", alert.source_id)
        self.assertNotIn("abc123", alert.message)
