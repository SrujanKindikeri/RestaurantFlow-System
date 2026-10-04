# =============================================================================
# RestaurantFlow — Notifications Initial Migration
# Phase 16: Notification & Communication Center
# Written manually — run: python manage.py migrate
# =============================================================================

import django.db.models.deletion
import django.utils.timezone
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("organizations", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [

        # =====================================================================
        # Notification
        # =====================================================================
        migrations.CreateModel(
            name="Notification",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("notification_type", models.CharField(
                    choices=[
                        ("ORDER_CONFIRMED", "Order Confirmed"),
                        ("ORDER_READY", "Order Ready"),
                        ("ORDER_CANCELLED", "Order Cancelled"),
                        ("KITCHEN_ORDER_READY", "Kitchen Order Ready"),
                        ("KITCHEN_ORDER_DELAYED", "Kitchen Order Delayed"),
                        ("KITCHEN_BACKLOG", "Kitchen Backlog"),
                        ("INVENTORY_LOW_STOCK", "Inventory Low Stock"),
                        ("INVENTORY_OUT_OF_STOCK", "Inventory Out of Stock"),
                        ("INVENTORY_PURCHASE_RECEIVED", "Purchase Received"),
                        ("INVENTORY_CONSUMPTION_FAILED", "Inventory Consumption Failed"),
                        ("PAYMENT_COMPLETED", "Payment Completed"),
                        ("PAYMENT_FAILED", "Payment Failed"),
                        ("REFUND_PROCESSED", "Refund Processed"),
                        ("EXPENSE_SUBMITTED", "Expense Submitted"),
                        ("EXPENSE_APPROVAL_REQUIRED", "Expense Approval Required"),
                        ("EXPENSE_APPROVED", "Expense Approved"),
                        ("EXPENSE_REJECTED", "Expense Rejected"),
                        ("PAYABLE_OVERDUE", "Payable Overdue"),
                        ("SUPPLIER_INVOICE_SUBMITTED", "Supplier Invoice Submitted"),
                        ("ACCOUNTING_POSTING_FAILED", "Accounting Posting Failed"),
                        ("ACCOUNTING_PERIOD_CLOSED", "Accounting Period Closed"),
                        ("CENTRAL_ALERT_CREATED", "Central Alert Created"),
                        ("CENTRAL_ALERT_RESOLVED", "Central Alert Resolved"),
                        ("CENTRAL_ISSUE_ASSIGNED", "Central Issue Assigned"),
                        ("CENTRAL_ISSUE_RESOLVED", "Central Issue Resolved"),
                        ("USER_ACCESS_GRANTED", "User Access Granted"),
                        ("USER_ACCESS_REVOKED", "User Access Revoked"),
                        ("COUNTER_SESSION_CLOSED", "Counter Session Closed"),
                        ("SYSTEM_HEALTH_DEGRADED", "System Health Degraded"),
                        ("NOTIFICATION_PROVIDER_FAILURE", "Notification Provider Failure"),
                    ],
                    db_index=True, max_length=60,
                )),
                ("severity", models.CharField(
                    choices=[
                        ("INFO", "Info"), ("LOW", "Low"), ("MEDIUM", "Medium"),
                        ("HIGH", "High"), ("CRITICAL", "Critical"),
                    ],
                    db_index=True, default="MEDIUM", max_length=20,
                )),
                ("title", models.CharField(max_length=200)),
                ("message", models.TextField()),
                ("source_type", models.CharField(
                    choices=[
                        ("ORDER", "Order"), ("KITCHEN_ORDER", "Kitchen Order"),
                        ("STOCK_BALANCE", "Stock Balance"), ("PAYMENT", "Payment"),
                        ("REFUND", "Refund"), ("EXPENSE", "Expense"),
                        ("PAYABLE", "Payable"), ("SUPPLIER_INVOICE", "Supplier Invoice"),
                        ("ACCOUNTING_POSTING", "Accounting Posting"),
                        ("CENTRAL_ALERT", "Central Alert"), ("CENTRAL_ISSUE", "Central Issue"),
                        ("USER", "User"), ("COUNTER_SESSION", "Counter Session"),
                        ("SYSTEM", "System"),
                    ],
                    db_index=True, max_length=60,
                )),
                ("source_id", models.CharField(blank=True, db_index=True, max_length=100)),
                ("action_url", models.CharField(blank=True, max_length=500)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("expires_at", models.DateTimeField(blank=True, null=True)),
                ("company", models.ForeignKey(
                    db_index=True,
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="notifications",
                    to="organizations.organization",
                )),
                ("restaurant", models.ForeignKey(
                    blank=True, db_index=True, null=True,
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="notifications",
                    to="organizations.restaurant",
                )),
                ("branch", models.ForeignKey(
                    blank=True, db_index=True, null=True,
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="notifications",
                    to="organizations.branch",
                )),
            ],
            options={"verbose_name": "Notification", "verbose_name_plural": "Notifications", "ordering": ["-created_at"]},
        ),
        migrations.AddIndex(
            model_name="notification",
            index=models.Index(fields=["company", "created_at"], name="notif_company_created_idx"),
        ),
        migrations.AddIndex(
            model_name="notification",
            index=models.Index(fields=["company", "notification_type"], name="notif_company_type_idx"),
        ),
        migrations.AddIndex(
            model_name="notification",
            index=models.Index(fields=["company", "severity"], name="notif_company_severity_idx"),
        ),
        migrations.AddIndex(
            model_name="notification",
            index=models.Index(fields=["restaurant", "created_at"], name="notif_restaurant_created_idx"),
        ),
        migrations.AddIndex(
            model_name="notification",
            index=models.Index(fields=["branch", "created_at"], name="notif_branch_created_idx"),
        ),
        migrations.AddIndex(
            model_name="notification",
            index=models.Index(fields=["source_type", "source_id"], name="notif_source_idx"),
        ),
        migrations.AddIndex(
            model_name="notification",
            index=models.Index(fields=["notification_type", "source_type", "source_id"], name="notif_type_source_idx"),
        ),

        # =====================================================================
        # NotificationRecipient
        # =====================================================================
        migrations.CreateModel(
            name="NotificationRecipient",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("delivery_status", models.CharField(
                    choices=[
                        ("PENDING", "Pending"), ("DELIVERED", "Delivered"),
                        ("FAILED", "Failed"), ("READ", "Read"),
                        ("ACKNOWLEDGED", "Acknowledged"),
                    ],
                    db_index=True, default="PENDING", max_length=20,
                )),
                ("read_at", models.DateTimeField(blank=True, db_index=True, null=True)),
                ("acknowledged_at", models.DateTimeField(blank=True, null=True)),
                ("delivered_at", models.DateTimeField(blank=True, null=True)),
                ("failed_at", models.DateTimeField(blank=True, null=True)),
                ("failure_reason", models.TextField(blank=True)),
                ("notification", models.ForeignKey(
                    db_index=True,
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="recipients",
                    to="notifications.notification",
                )),
                ("user", models.ForeignKey(
                    db_index=True,
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="notification_recipients",
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={"verbose_name": "Notification Recipient", "verbose_name_plural": "Notification Recipients", "ordering": ["-created_at"]},
        ),
        migrations.AlterUniqueTogether(
            name="notificationrecipient",
            unique_together={("notification", "user")},
        ),
        migrations.AddIndex(
            model_name="notificationrecipient",
            index=models.Index(fields=["user", "delivery_status"], name="notif_recip_user_status_idx"),
        ),
        migrations.AddIndex(
            model_name="notificationrecipient",
            index=models.Index(fields=["user", "notification"], name="notif_recip_user_notif_idx"),
        ),
        migrations.AddIndex(
            model_name="notificationrecipient",
            index=models.Index(fields=["notification", "delivery_status"], name="notif_recip_notif_status_idx"),
        ),
        migrations.AddIndex(
            model_name="notificationrecipient",
            index=models.Index(fields=["user", "read_at"], name="notif_recip_user_read_idx"),
        ),

        # =====================================================================
        # NotificationDelivery
        # =====================================================================
        migrations.CreateModel(
            name="NotificationDelivery",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("channel", models.CharField(
                    choices=[
                        ("IN_APP", "In-App"), ("WEBSOCKET", "WebSocket"),
                        ("EMAIL", "Email"), ("SMS", "SMS"),
                        ("WHATSAPP", "WhatsApp"), ("TELEGRAM", "Telegram"),
                    ],
                    db_index=True, max_length=20,
                )),
                ("provider", models.CharField(blank=True, default="", max_length=50)),
                ("status", models.CharField(
                    choices=[
                        ("PENDING", "Pending"), ("QUEUED", "Queued"),
                        ("SENT", "Sent"), ("DELIVERED", "Delivered"),
                        ("FAILED", "Failed"), ("CANCELLED", "Cancelled"),
                        ("NOT_CONFIGURED", "Not Configured"),
                    ],
                    db_index=True, default="PENDING", max_length=20,
                )),
                ("attempt_count", models.PositiveSmallIntegerField(default=0)),
                ("provider_message_id", models.CharField(blank=True, max_length=200)),
                ("queued_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("sent_at", models.DateTimeField(blank=True, null=True)),
                ("failed_at", models.DateTimeField(blank=True, null=True)),
                ("failure_reason", models.TextField(blank=True)),
                ("next_retry_at", models.DateTimeField(blank=True, db_index=True, null=True)),
                ("notification", models.ForeignKey(
                    db_index=True,
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="deliveries",
                    to="notifications.notification",
                )),
                ("recipient", models.ForeignKey(
                    db_index=True,
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="deliveries",
                    to="notifications.notificationrecipient",
                )),
            ],
            options={"verbose_name": "Notification Delivery", "verbose_name_plural": "Notification Deliveries", "ordering": ["-created_at"]},
        ),
        migrations.AddIndex(
            model_name="notificationdelivery",
            index=models.Index(fields=["notification", "channel"], name="notif_deliv_notif_channel_idx"),
        ),
        migrations.AddIndex(
            model_name="notificationdelivery",
            index=models.Index(fields=["recipient", "channel"], name="notif_deliv_recip_channel_idx"),
        ),
        migrations.AddIndex(
            model_name="notificationdelivery",
            index=models.Index(fields=["status", "next_retry_at"], name="notif_deliv_status_retry_idx"),
        ),
        migrations.AddIndex(
            model_name="notificationdelivery",
            index=models.Index(fields=["channel", "status"], name="notif_deliv_channel_status_idx"),
        ),
        migrations.AddIndex(
            model_name="notificationdelivery",
            index=models.Index(fields=["created_at"], name="notif_deliv_created_idx"),
        ),

        # =====================================================================
        # NotificationPreference
        # =====================================================================
        migrations.CreateModel(
            name="NotificationPreference",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("notification_type", models.CharField(
                    choices=[
                        ("ORDER_CONFIRMED", "Order Confirmed"),
                        ("ORDER_READY", "Order Ready"),
                        ("ORDER_CANCELLED", "Order Cancelled"),
                        ("KITCHEN_ORDER_READY", "Kitchen Order Ready"),
                        ("KITCHEN_ORDER_DELAYED", "Kitchen Order Delayed"),
                        ("KITCHEN_BACKLOG", "Kitchen Backlog"),
                        ("INVENTORY_LOW_STOCK", "Inventory Low Stock"),
                        ("INVENTORY_OUT_OF_STOCK", "Inventory Out of Stock"),
                        ("INVENTORY_PURCHASE_RECEIVED", "Purchase Received"),
                        ("INVENTORY_CONSUMPTION_FAILED", "Inventory Consumption Failed"),
                        ("PAYMENT_COMPLETED", "Payment Completed"),
                        ("PAYMENT_FAILED", "Payment Failed"),
                        ("REFUND_PROCESSED", "Refund Processed"),
                        ("EXPENSE_SUBMITTED", "Expense Submitted"),
                        ("EXPENSE_APPROVAL_REQUIRED", "Expense Approval Required"),
                        ("EXPENSE_APPROVED", "Expense Approved"),
                        ("EXPENSE_REJECTED", "Expense Rejected"),
                        ("PAYABLE_OVERDUE", "Payable Overdue"),
                        ("SUPPLIER_INVOICE_SUBMITTED", "Supplier Invoice Submitted"),
                        ("ACCOUNTING_POSTING_FAILED", "Accounting Posting Failed"),
                        ("ACCOUNTING_PERIOD_CLOSED", "Accounting Period Closed"),
                        ("CENTRAL_ALERT_CREATED", "Central Alert Created"),
                        ("CENTRAL_ALERT_RESOLVED", "Central Alert Resolved"),
                        ("CENTRAL_ISSUE_ASSIGNED", "Central Issue Assigned"),
                        ("CENTRAL_ISSUE_RESOLVED", "Central Issue Resolved"),
                        ("USER_ACCESS_GRANTED", "User Access Granted"),
                        ("USER_ACCESS_REVOKED", "User Access Revoked"),
                        ("COUNTER_SESSION_CLOSED", "Counter Session Closed"),
                        ("SYSTEM_HEALTH_DEGRADED", "System Health Degraded"),
                        ("NOTIFICATION_PROVIDER_FAILURE", "Notification Provider Failure"),
                    ],
                    db_index=True, max_length=60,
                )),
                ("channel", models.CharField(
                    choices=[
                        ("IN_APP", "In-App"), ("WEBSOCKET", "WebSocket"),
                        ("EMAIL", "Email"), ("SMS", "SMS"),
                        ("WHATSAPP", "WhatsApp"), ("TELEGRAM", "Telegram"),
                    ],
                    db_index=True, max_length=20,
                )),
                ("enabled", models.BooleanField(default=True)),
                ("user", models.ForeignKey(
                    db_index=True,
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="notification_preferences",
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={"verbose_name": "Notification Preference", "verbose_name_plural": "Notification Preferences", "ordering": ["notification_type", "channel"]},
        ),
        migrations.AlterUniqueTogether(
            name="notificationpreference",
            unique_together={("user", "notification_type", "channel")},
        ),
        migrations.AddIndex(
            model_name="notificationpreference",
            index=models.Index(fields=["user", "notification_type"], name="notif_pref_user_type_idx"),
        ),
        migrations.AddIndex(
            model_name="notificationpreference",
            index=models.Index(fields=["user", "channel"], name="notif_pref_user_channel_idx"),
        ),

        # =====================================================================
        # NotificationTemplate
        # =====================================================================
        migrations.CreateModel(
            name="NotificationTemplate",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("notification_type", models.CharField(
                    choices=[
                        ("ORDER_CONFIRMED", "Order Confirmed"),
                        ("ORDER_READY", "Order Ready"),
                        ("ORDER_CANCELLED", "Order Cancelled"),
                        ("KITCHEN_ORDER_READY", "Kitchen Order Ready"),
                        ("KITCHEN_ORDER_DELAYED", "Kitchen Order Delayed"),
                        ("KITCHEN_BACKLOG", "Kitchen Backlog"),
                        ("INVENTORY_LOW_STOCK", "Inventory Low Stock"),
                        ("INVENTORY_OUT_OF_STOCK", "Inventory Out of Stock"),
                        ("INVENTORY_PURCHASE_RECEIVED", "Purchase Received"),
                        ("INVENTORY_CONSUMPTION_FAILED", "Inventory Consumption Failed"),
                        ("PAYMENT_COMPLETED", "Payment Completed"),
                        ("PAYMENT_FAILED", "Payment Failed"),
                        ("REFUND_PROCESSED", "Refund Processed"),
                        ("EXPENSE_SUBMITTED", "Expense Submitted"),
                        ("EXPENSE_APPROVAL_REQUIRED", "Expense Approval Required"),
                        ("EXPENSE_APPROVED", "Expense Approved"),
                        ("EXPENSE_REJECTED", "Expense Rejected"),
                        ("PAYABLE_OVERDUE", "Payable Overdue"),
                        ("SUPPLIER_INVOICE_SUBMITTED", "Supplier Invoice Submitted"),
                        ("ACCOUNTING_POSTING_FAILED", "Accounting Posting Failed"),
                        ("ACCOUNTING_PERIOD_CLOSED", "Accounting Period Closed"),
                        ("CENTRAL_ALERT_CREATED", "Central Alert Created"),
                        ("CENTRAL_ALERT_RESOLVED", "Central Alert Resolved"),
                        ("CENTRAL_ISSUE_ASSIGNED", "Central Issue Assigned"),
                        ("CENTRAL_ISSUE_RESOLVED", "Central Issue Resolved"),
                        ("USER_ACCESS_GRANTED", "User Access Granted"),
                        ("USER_ACCESS_REVOKED", "User Access Revoked"),
                        ("COUNTER_SESSION_CLOSED", "Counter Session Closed"),
                        ("SYSTEM_HEALTH_DEGRADED", "System Health Degraded"),
                        ("NOTIFICATION_PROVIDER_FAILURE", "Notification Provider Failure"),
                    ],
                    db_index=True, max_length=60,
                )),
                ("channel", models.CharField(
                    choices=[
                        ("IN_APP", "In-App"), ("WEBSOCKET", "WebSocket"),
                        ("EMAIL", "Email"), ("SMS", "SMS"),
                        ("WHATSAPP", "WhatsApp"), ("TELEGRAM", "Telegram"),
                    ],
                    db_index=True, max_length=20,
                )),
                ("subject_template", models.CharField(blank=True, max_length=300)),
                ("body_template", models.TextField()),
                ("is_active", models.BooleanField(db_index=True, default=True)),
                ("company", models.ForeignKey(
                    blank=True, db_index=True, null=True,
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="notification_templates",
                    to="organizations.organization",
                )),
            ],
            options={"verbose_name": "Notification Template", "verbose_name_plural": "Notification Templates", "ordering": ["notification_type", "channel"]},
        ),
        migrations.AddIndex(
            model_name="notificationtemplate",
            index=models.Index(fields=["notification_type", "channel", "is_active"], name="notif_tmpl_type_channel_idx"),
        ),
        migrations.AddIndex(
            model_name="notificationtemplate",
            index=models.Index(fields=["company", "notification_type", "channel"], name="notif_tmpl_company_idx"),
        ),

        # =====================================================================
        # NotificationProviderConfig
        # =====================================================================
        migrations.CreateModel(
            name="NotificationProviderConfig",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("channel", models.CharField(
                    choices=[
                        ("IN_APP", "In-App"), ("WEBSOCKET", "WebSocket"),
                        ("EMAIL", "Email"), ("SMS", "SMS"),
                        ("WHATSAPP", "WhatsApp"), ("TELEGRAM", "Telegram"),
                    ],
                    db_index=True, max_length=20,
                )),
                ("provider", models.CharField(default="DJANGO_EMAIL", max_length=50)),
                ("is_enabled", models.BooleanField(default=False)),
                ("configuration_metadata", models.JSONField(blank=True, default=dict)),
                ("company", models.ForeignKey(
                    db_index=True,
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="notification_provider_configs",
                    to="organizations.organization",
                )),
            ],
            options={"verbose_name": "Notification Provider Config", "verbose_name_plural": "Notification Provider Configs"},
        ),
        migrations.AlterUniqueTogether(
            name="notificationproviderconfig",
            unique_together={("company", "channel")},
        ),
        migrations.AddIndex(
            model_name="notificationproviderconfig",
            index=models.Index(fields=["company", "channel", "is_enabled"], name="notif_prov_company_channel_idx"),
        ),
    ]
