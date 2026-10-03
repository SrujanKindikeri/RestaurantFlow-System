# =============================================================================
# RestaurantFlow — Orders Initial Migration
# Phase 6
# Generated manually; equivalent to what `python manage.py makemigrations orders` produces.
# =============================================================================

import uuid
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("organizations", "0001_initial"),
        ("counters",      "0001_initial"),
        # menu app uses auto-migrations (no named initial migration file);
        # Django resolves the FK to menu.MenuItem at DB level via the app registry.
        # If menu gets a named migration in future, add ("menu", "0001_initial") here.
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # =====================================================================
        # DiningTable
        # =====================================================================
        migrations.CreateModel(
            name="DiningTable",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
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
                    "branch",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="dining_tables",
                        to="organizations.branch",
                    ),
                ),
                ("table_number", models.CharField(db_index=True, max_length=20)),
                ("name", models.CharField(blank=True, max_length=150)),
                ("capacity", models.PositiveIntegerField(default=2)),
                (
                    "section",
                    models.CharField(blank=True, db_index=True, max_length=100),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[("ACTIVE", "Active"), ("INACTIVE", "Inactive")],
                        db_index=True,
                        default="ACTIVE",
                        max_length=20,
                    ),
                ),
                ("display_order", models.PositiveIntegerField(db_index=True, default=0)),
            ],
            options={
                "verbose_name": "Dining Table",
                "verbose_name_plural": "Dining Tables",
                "ordering": ["display_order", "table_number"],
            },
        ),
        migrations.AddConstraint(
            model_name="diningtable",
            constraint=models.UniqueConstraint(
                fields=["branch", "table_number"],
                name="unique_table_number_per_branch",
            ),
        ),
        migrations.AddIndex(
            model_name="diningtable",
            index=models.Index(
                fields=["branch", "status"], name="orders_dini_branch__status_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="diningtable",
            index=models.Index(
                fields=["branch", "section"], name="orders_dini_branch__section_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="diningtable",
            index=models.Index(
                fields=["branch", "display_order"],
                name="orders_dini_branch__display_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="diningtable",
            index=models.Index(
                fields=["branch", "table_number"],
                name="orders_dini_branch__tblnum_idx",
            ),
        ),
        # =====================================================================
        # TableSession
        # =====================================================================
        migrations.CreateModel(
            name="TableSession",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
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
                    "table",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="sessions",
                        to="orders.diningtable",
                    ),
                ),
                (
                    "opened_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="opened_table_sessions",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "closed_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="closed_table_sessions",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                ("opened_at", models.DateTimeField(auto_now_add=True)),
                ("closed_at", models.DateTimeField(blank=True, null=True)),
                (
                    "status",
                    models.CharField(
                        choices=[("OPEN", "Open"), ("CLOSED", "Closed")],
                        db_index=True,
                        default="OPEN",
                        max_length=20,
                    ),
                ),
                ("guest_count", models.PositiveIntegerField(default=1)),
                ("notes", models.TextField(blank=True)),
            ],
            options={
                "verbose_name": "Table Session",
                "verbose_name_plural": "Table Sessions",
                "ordering": ["-opened_at"],
            },
        ),
        migrations.AddConstraint(
            model_name="tablesession",
            constraint=models.UniqueConstraint(
                condition=models.Q(status="OPEN"),
                fields=["table"],
                name="unique_open_session_per_table",
            ),
        ),
        migrations.AddIndex(
            model_name="tablesession",
            index=models.Index(
                fields=["table", "status"], name="orders_tabl_table_status_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="tablesession",
            index=models.Index(
                fields=["opened_by", "status"], name="orders_tabl_openby_status_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="tablesession",
            index=models.Index(
                fields=["table", "opened_at"], name="orders_tabl_table_openat_idx"
            ),
        ),
        # =====================================================================
        # OrderSequence
        # =====================================================================
        migrations.CreateModel(
            name="OrderSequence",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
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
                    "scope_type",
                    models.CharField(
                        choices=[("counter", "Counter"), ("branch", "Branch")],
                        db_index=True,
                        max_length=20,
                    ),
                ),
                ("scope_id", models.CharField(db_index=True, max_length=50)),
                ("date_key", models.CharField(db_index=True, max_length=8)),
                ("last_sequence", models.PositiveIntegerField(default=0)),
            ],
            options={
                "verbose_name": "Order Sequence",
                "verbose_name_plural": "Order Sequences",
                "ordering": ["scope_type", "scope_id", "date_key"],
            },
        ),
        migrations.AddConstraint(
            model_name="ordersequence",
            constraint=models.UniqueConstraint(
                fields=["scope_type", "scope_id", "date_key"],
                name="unique_order_sequence",
            ),
        ),
        migrations.AddIndex(
            model_name="ordersequence",
            index=models.Index(
                fields=["scope_type", "scope_id", "date_key"],
                name="orders_seq_scope_date_idx",
            ),
        ),
        # =====================================================================
        # Order
        # =====================================================================
        migrations.CreateModel(
            name="Order",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
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
                    "branch",
                    models.ForeignKey(
                        db_index=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="orders",
                        to="organizations.branch",
                    ),
                ),
                ("order_number", models.CharField(db_index=True, max_length=50)),
                (
                    "order_type",
                    models.CharField(
                        choices=[
                            ("DINE_IN", "Dine In"),
                            ("TAKEAWAY", "Takeaway"),
                            ("COUNTER", "Counter"),
                        ],
                        db_index=True,
                        default="DINE_IN",
                        max_length=20,
                    ),
                ),
                (
                    "table",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="orders",
                        to="orders.diningtable",
                    ),
                ),
                (
                    "table_session",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="orders",
                        to="orders.tablesession",
                    ),
                ),
                (
                    "counter",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="orders",
                        to="counters.counter",
                    ),
                ),
                (
                    "counter_session",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="orders",
                        to="counters.countersession",
                    ),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="created_orders",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "assigned_waiter",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="assigned_orders",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                ("guest_count", models.PositiveIntegerField(blank=True, null=True)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("DRAFT", "Draft"),
                            ("CONFIRMED", "Confirmed"),
                            ("CANCELLED", "Cancelled"),
                        ],
                        db_index=True,
                        default="DRAFT",
                        max_length=20,
                    ),
                ),
                ("notes", models.TextField(blank=True)),
                ("confirmed_at", models.DateTimeField(blank=True, null=True)),
                ("cancelled_at", models.DateTimeField(blank=True, null=True)),
                (
                    "cancelled_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="cancelled_orders",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                ("cancellation_reason", models.TextField(blank=True)),
            ],
            options={
                "verbose_name": "Order",
                "verbose_name_plural": "Orders",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="order",
            index=models.Index(
                fields=["branch", "status"], name="orders_ord_branch_status_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="order",
            index=models.Index(
                fields=["branch", "order_type"], name="orders_ord_branch_type_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="order",
            index=models.Index(
                fields=["branch", "created_at"], name="orders_ord_branch_creat_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="order",
            index=models.Index(
                fields=["order_number"], name="orders_ord_ordnum_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="order",
            index=models.Index(
                fields=["table", "status"], name="orders_ord_table_status_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="order",
            index=models.Index(
                fields=["counter", "status"], name="orders_ord_counter_status_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="order",
            index=models.Index(
                fields=["assigned_waiter", "status"],
                name="orders_ord_waiter_status_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="order",
            index=models.Index(
                fields=["created_by", "status"], name="orders_ord_createdby_status_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="order",
            index=models.Index(
                fields=["status", "created_at"], name="orders_ord_status_creat_idx"
            ),
        ),
        # =====================================================================
        # OrderItem
        # =====================================================================
        migrations.CreateModel(
            name="OrderItem",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
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
                    "order",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="items",
                        to="orders.order",
                    ),
                ),
                (
                    "menu_item",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="order_items",
                        to="menu.menuitem",
                    ),
                ),
                ("item_name_snapshot", models.CharField(max_length=200)),
                ("sku_snapshot", models.CharField(blank=True, max_length=100)),
                (
                    "unit_price_snapshot",
                    models.DecimalField(decimal_places=2, max_digits=12),
                ),
                (
                    "tax_rate_snapshot",
                    models.DecimalField(
                        decimal_places=3, default="0.000", max_digits=6
                    ),
                ),
                ("tax_code_snapshot", models.CharField(blank=True, max_length=50)),
                (
                    "quantity",
                    models.DecimalField(decimal_places=3, max_digits=7),
                ),
                ("notes", models.TextField(blank=True)),
            ],
            options={
                "verbose_name": "Order Item",
                "verbose_name_plural": "Order Items",
                "ordering": ["created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="orderitem",
            index=models.Index(
                fields=["order", "menu_item"], name="orders_item_order_item_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="orderitem",
            index=models.Index(
                fields=["menu_item"], name="orders_item_menuitem_idx"
            ),
        ),
    ]
