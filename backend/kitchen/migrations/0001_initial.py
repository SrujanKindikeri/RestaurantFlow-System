# =============================================================================
# RestaurantFlow — Kitchen Initial Migration
# Phase 7: KitchenOrder, KitchenOrderItem
# Generated manually (no Python interpreter on CI PATH).
# =============================================================================

import uuid
import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("orders", "0001_initial"),
        ("menu", "0001_initial"),
        ("organizations", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # ------------------------------------------------------------------
        # KitchenOrder
        # ------------------------------------------------------------------
        migrations.CreateModel(
            name="KitchenOrder",
            fields=[
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True),
                ),
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("NEW", "New"),
                            ("ACCEPTED", "Accepted"),
                            ("PREPARING", "Preparing"),
                            ("READY", "Ready"),
                            ("CANCELLED", "Cancelled"),
                        ],
                        db_index=True,
                        default="NEW",
                        max_length=20,
                    ),
                ),
                (
                    "priority",
                    models.CharField(
                        choices=[
                            ("NORMAL", "Normal"),
                            ("HIGH", "High"),
                            ("URGENT", "Urgent"),
                        ],
                        db_index=True,
                        default="NORMAL",
                        max_length=10,
                    ),
                ),
                (
                    "kitchen_note",
                    models.TextField(blank=True),
                ),
                (
                    "received_at",
                    models.DateTimeField(auto_now_add=True),
                ),
                (
                    "accepted_at",
                    models.DateTimeField(blank=True, null=True),
                ),
                (
                    "started_at",
                    models.DateTimeField(blank=True, null=True),
                ),
                (
                    "ready_at",
                    models.DateTimeField(blank=True, null=True),
                ),
                (
                    "cancelled_at",
                    models.DateTimeField(blank=True, null=True),
                ),
                (
                    "cancellation_reason",
                    models.TextField(blank=True),
                ),
                (
                    "accepted_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="kitchen_orders_accepted",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "branch",
                    models.ForeignKey(
                        db_index=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="kitchen_orders",
                        to="organizations.branch",
                    ),
                ),
                (
                    "cancelled_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="kitchen_orders_cancelled",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "completed_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="kitchen_orders_completed",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "order",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="kitchen_order",
                        to="orders.order",
                    ),
                ),
                (
                    "started_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="kitchen_orders_started",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Kitchen Order",
                "verbose_name_plural": "Kitchen Orders",
                "ordering": ["received_at"],
            },
        ),
        # ------------------------------------------------------------------
        # KitchenOrderItem
        # ------------------------------------------------------------------
        migrations.CreateModel(
            name="KitchenOrderItem",
            fields=[
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True),
                ),
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "item_name_snapshot",
                    models.CharField(max_length=200),
                ),
                (
                    "quantity",
                    models.DecimalField(decimal_places=3, max_digits=7),
                ),
                (
                    "notes",
                    models.TextField(blank=True),
                ),
                (
                    "food_type",
                    models.CharField(blank=True, max_length=10),
                ),
                (
                    "preparation_time_minutes",
                    models.PositiveIntegerField(default=0),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("NEW", "New"),
                            ("PREPARING", "Preparing"),
                            ("READY", "Ready"),
                            ("CANCELLED", "Cancelled"),
                        ],
                        db_index=True,
                        default="NEW",
                        max_length=20,
                    ),
                ),
                (
                    "station",
                    models.CharField(blank=True, max_length=100),
                ),
                (
                    "started_at",
                    models.DateTimeField(blank=True, null=True),
                ),
                (
                    "ready_at",
                    models.DateTimeField(blank=True, null=True),
                ),
                (
                    "cancelled_at",
                    models.DateTimeField(blank=True, null=True),
                ),
                (
                    "kitchen_order",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="items",
                        to="kitchen.kitchenorder",
                    ),
                ),
                (
                    "menu_item",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="kitchen_items",
                        to="menu.menuitem",
                    ),
                ),
                (
                    "order_item",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="kitchen_item",
                        to="orders.orderitem",
                    ),
                ),
            ],
            options={
                "verbose_name": "Kitchen Order Item",
                "verbose_name_plural": "Kitchen Order Items",
                "ordering": ["created_at"],
            },
        ),
        # ------------------------------------------------------------------
        # Indexes — KitchenOrder
        # ------------------------------------------------------------------
        migrations.AddIndex(
            model_name="kitchenorder",
            index=models.Index(
                fields=["branch", "status"],
                name="kitchen_kit_branch__idx",
            ),
        ),
        migrations.AddIndex(
            model_name="kitchenorder",
            index=models.Index(
                fields=["branch", "priority"],
                name="kitchen_kit_branch_priority_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="kitchenorder",
            index=models.Index(
                fields=["branch", "received_at"],
                name="kitchen_kit_branch_recv_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="kitchenorder",
            index=models.Index(
                fields=["status", "priority"],
                name="kitchen_kit_status_priority_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="kitchenorder",
            index=models.Index(
                fields=["status", "received_at"],
                name="kitchen_kit_status_recv_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="kitchenorder",
            index=models.Index(
                fields=["branch", "status", "received_at"],
                name="kitchen_kit_bsr_idx",
            ),
        ),
        # ------------------------------------------------------------------
        # Indexes — KitchenOrderItem
        # ------------------------------------------------------------------
        migrations.AddIndex(
            model_name="kitchenorderitem",
            index=models.Index(
                fields=["kitchen_order", "status"],
                name="kitchen_kititem_order_status_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="kitchenorderitem",
            index=models.Index(
                fields=["menu_item", "status"],
                name="kitchen_kititem_menu_status_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="kitchenorderitem",
            index=models.Index(
                fields=["status"],
                name="kitchen_kititem_status_idx",
            ),
        ),
    ]
