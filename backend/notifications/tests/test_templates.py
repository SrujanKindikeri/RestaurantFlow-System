# =============================================================================
# RestaurantFlow — Notification Template Tests
# Phase 16
# =============================================================================

from notifications.tests.base import NotificationTestBase
from notifications.validators import (
    render_template,
    validate_template_variables,
)
from notifications.exceptions import InvalidTemplateVariable


class TemplateRendererTests(NotificationTestBase):

    def test_render_known_variable(self):
        result = render_template("Order {{order_number}} is ready.", {"order_number": "ORD-123"})
        self.assertEqual(result, "Order ORD-123 is ready.")

    def test_render_multiple_variables(self):
        result = render_template(
            "{{item_name}} is low at {{branch_name}}.",
            {"item_name": "Chicken", "branch_name": "Branch 01"},
        )
        self.assertEqual(result, "Chicken is low at Branch 01.")

    def test_unknown_variable_left_as_is(self):
        """Known unknown variable (not in safe list) raises during validation."""
        with self.assertRaises(InvalidTemplateVariable):
            render_template("Hello {{secret_key}}.", {})

    def test_no_eval_in_template(self):
        """Template system must never execute Python."""
        with self.assertRaises(InvalidTemplateVariable):
            render_template("{{__import__('os').system('rm -rf /')}}", {})

    def test_render_missing_context_variable_leaves_placeholder(self):
        """If context doesn't have a value, {{var}} stays in output."""
        result = render_template("Hello {{user_name}}.", {})
        self.assertIn("{{user_name}}", result)

    def test_validate_template_variables_returns_found_vars(self):
        found = validate_template_variables("Order {{order_number}} at {{branch_name}}.")
        self.assertIn("order_number", found)
        self.assertIn("branch_name", found)

    def test_validate_rejects_unsafe_var(self):
        with self.assertRaises(InvalidTemplateVariable):
            validate_template_variables("{{password}}")

    def test_template_with_no_variables_is_valid(self):
        """Plain text templates with no {{}} are always valid."""
        result = render_template("System alert detected.", {})
        self.assertEqual(result, "System alert detected.")

    def test_render_subject_and_body_together(self):
        subject = render_template("Alert: {{alert_title}}", {"alert_title": "Critical"})
        body    = render_template("Alert {{alert_title}} at {{branch_name}}.", {
            "alert_title": "Critical",
            "branch_name": "Branch 02",
        })
        self.assertEqual(subject, "Alert: Critical")
        self.assertEqual(body, "Alert Critical at Branch 02.")


class NotificationTemplateModelTests(NotificationTestBase):

    def test_template_creation_and_retrieval(self):
        from notifications.models import NotificationTemplate
        from notifications.constants import NOTIF_PAYMENT_FAILED, CHANNEL_EMAIL

        tmpl = NotificationTemplate.objects.create(
            company=self.company_a,
            notification_type=NOTIF_PAYMENT_FAILED,
            channel=CHANNEL_EMAIL,
            subject_template="Payment Failed",
            body_template="Your payment of {{payment_amount}} failed.",
            is_active=True,
        )
        self.assertEqual(tmpl.notification_type, NOTIF_PAYMENT_FAILED)
        self.assertEqual(tmpl.channel, CHANNEL_EMAIL)

    def test_selector_returns_company_specific_template_first(self):
        from notifications.models import NotificationTemplate
        from notifications.selectors import get_templates_for_type_channel
        from notifications.constants import NOTIF_PAYMENT_FAILED, CHANNEL_EMAIL

        # Global template
        NotificationTemplate.objects.create(
            notification_type=NOTIF_PAYMENT_FAILED,
            channel=CHANNEL_EMAIL,
            body_template="Global body",
            is_active=True,
        )
        # Company-specific template
        specific = NotificationTemplate.objects.create(
            company=self.company_a,
            notification_type=NOTIF_PAYMENT_FAILED,
            channel=CHANNEL_EMAIL,
            body_template="Company A specific body",
            is_active=True,
        )
        result = get_templates_for_type_channel(
            NOTIF_PAYMENT_FAILED, CHANNEL_EMAIL, self.company_a
        )
        self.assertEqual(result.pk, specific.pk)

    def test_selector_falls_back_to_global_when_no_company_template(self):
        from notifications.models import NotificationTemplate
        from notifications.selectors import get_templates_for_type_channel
        from notifications.constants import NOTIF_INVENTORY_LOW_STOCK, CHANNEL_EMAIL

        global_tmpl = NotificationTemplate.objects.create(
            notification_type=NOTIF_INVENTORY_LOW_STOCK,
            channel=CHANNEL_EMAIL,
            body_template="{{item_name}} is low.",
            is_active=True,
        )
        result = get_templates_for_type_channel(
            NOTIF_INVENTORY_LOW_STOCK, CHANNEL_EMAIL, self.company_a
        )
        self.assertEqual(result.pk, global_tmpl.pk)

    def test_inactive_template_not_returned(self):
        from notifications.models import NotificationTemplate
        from notifications.selectors import get_templates_for_type_channel
        from notifications.constants import NOTIF_REFUND_PROCESSED, CHANNEL_EMAIL

        NotificationTemplate.objects.create(
            notification_type=NOTIF_REFUND_PROCESSED,
            channel=CHANNEL_EMAIL,
            body_template="Refund body",
            is_active=False,
        )
        result = get_templates_for_type_channel(
            NOTIF_REFUND_PROCESSED, CHANNEL_EMAIL, self.company_a
        )
        self.assertIsNone(result)
