# =============================================================================
# RestaurantFlow — Operations Initial Migration
# Phase 19: Advanced POS & Restaurant Operations
# Generated manually (Python CLI unavailable in CI environment)
# =============================================================================

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("billing", "0002_reporting_indexes"),
        ("counters", "0001_initial"),
        ("menu", "0001_initial"),
        ("orders", "0001_initial"),
        ("organizations", "0001_initial"),
        ("payments", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # -------------------------------------------------------------------------
        # POSDevice
        # -------------------------------------------------------------------------
        migrations.CreateModel(
            name="POSDevice",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("device_name", models.CharField(max_length=150)),
                ("device_identifier", models.CharField(db_index=True, help_text="Browser fingerprint / device UUID — NEVER used for authorization.", max_length=200)),
                ("device_type", models.CharField(choices=[("DESKTOP", "Desktop"), ("LAPTOP", "Laptop"), ("TABLET", "Tablet"), ("POS_TERMINAL", "POS Terminal")], default="TABLET", max_length=20)),
                ("is_active", models.BooleanField(db_index=True, default=True)),
                ("last_seen_at", models.DateTimeField(blank=True, null=True)),
                ("branch", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="pos_devices", to="organizations.branch")),
                ("counter", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="pos_devices", to="counters.counter")),
                ("registered_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="registered_pos_devices", to=settings.AUTH_USER_MODEL)),
                ("restaurant", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="pos_devices", to="organizations.restaurant")),
            ],
            options={"verbose_name": "POS Device", "verbose_name_plural": "POS Devices", "ordering": ["-created_at"]},
        ),
        migrations.AddIndex(
            model_name="posdevice",
            index=models.Index(fields=["branch", "is_active"], name="ops_posdev_branch_active_idx"),
        ),
        migrations.AddIndex(
            model_name="posdevice",
            index=models.Index(fields=["device_identifier"], name="ops_posdev_identifier_idx"),
        ),

        # -------------------------------------------------------------------------
        # POSSession
        # -------------------------------------------------------------------------
        migrations.CreateModel(
            name="POSSession",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("device_identifier", models.CharField(blank=True, help_text="Browser/device fingerprint — metadata only, NOT used for auth.", max_length=200)),
                ("status", models.CharField(choices=[("ACTIVE", "Active"), ("PAUSED", "Paused"), ("ENDED", "Ended")], db_index=True, default="ACTIVE", max_length=10)),
                ("started_at", models.DateTimeField(auto_now_add=True)),
                ("ended_at", models.DateTimeField(blank=True, null=True)),
                ("last_activity_at", models.DateTimeField(blank=True, null=True)),
                ("branch", models.ForeignKey(db_index=True, help_text="Denormalized for efficient queries.", on_delete=django.db.models.deletion.PROTECT, related_name="pos_sessions", to="organizations.branch")),
                ("counter", models.ForeignKey(db_index=True, on_delete=django.db.models.deletion.PROTECT, related_name="pos_sessions", to="counters.counter")),
                ("counter_session", models.ForeignKey(db_index=True, help_text="The parent CounterSession this POS session belongs to.", on_delete=django.db.models.deletion.PROTECT, related_name="pos_sessions", to="counters.countersession")),
                ("user", models.ForeignKey(db_index=True, on_delete=django.db.models.deletion.PROTECT, related_name="pos_sessions", to=settings.AUTH_USER_MODEL)),
            ],
            options={"verbose_name": "POS Session", "verbose_name_plural": "POS Sessions", "ordering": ["-started_at"]},
        ),
        migrations.AddIndex(
            model_name="possession",
            index=models.Index(fields=["counter", "status"], name="ops_pos_counter_status_idx"),
        ),
        migrations.AddIndex(
            model_name="possession",
            index=models.Index(fields=["user", "status"], name="ops_pos_user_status_idx"),
        ),
        migrations.AddIndex(
            model_name="possession",
            index=models.Index(fields=["branch", "status"], name="ops_pos_branch_status_idx"),
        ),
        migrations.AddIndex(
            model_name="possession",
            index=models.Index(fields=["counter_session", "status"], name="ops_pos_session_status_idx"),
        ),
        migrations.AddConstraint(
            model_name="possession",
            constraint=models.UniqueConstraint(
                condition=models.Q(status="ACTIVE"),
                fields=["counter", "user"],
                name="unique_active_pos_session_per_counter_user",
            ),
        ),

        # -------------------------------------------------------------------------
        # MenuModifierGroup
        # -------------------------------------------------------------------------
        migrations.CreateModel(
            name="MenuModifierGroup",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=150)),
                ("description", models.TextField(blank=True)),
                ("is_required", models.BooleanField(default=False, help_text="If True, the customer MUST select at least min_selections options.")),
                ("min_selections", models.PositiveSmallIntegerField(default=0, help_text="Minimum number of options that must be selected.")),
                ("max_selections", models.PositiveSmallIntegerField(default=1, help_text="Maximum number of options that can be selected. 0 = unlimited.")),
                ("is_active", models.BooleanField(db_index=True, default=True)),
                ("menu_items", models.ManyToManyField(blank=True, help_text="Menu items that use this modifier group.", related_name="modifier_groups", to="menu.menuitem")),
                ("restaurant", models.ForeignKey(db_index=True, on_delete=django.db.models.deletion.PROTECT, related_name="modifier_groups", to="organizations.restaurant")),
            ],
            options={"verbose_name": "Menu Modifier Group", "verbose_name_plural": "Menu Modifier Groups", "ordering": ["restaurant", "name"]},
        ),
        migrations.AddIndex(
            model_name="menumodifiergroup",
            index=models.Index(fields=["restaurant", "is_active"], name="ops_modgrp_rest_active_idx"),
        ),

        # -------------------------------------------------------------------------
        # MenuModifierOption
        # -------------------------------------------------------------------------
        migrations.CreateModel(
            name="MenuModifierOption",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=150)),
                ("price_adjustment", models.DecimalField(decimal_places=2, default="0.00", help_text="Price change when this option is selected. Backend-authoritative — never trusted from frontend. 0.00 = no change. Positive = surcharge.", max_digits=10)),
                ("is_active", models.BooleanField(db_index=True, default=True)),
                ("modifier_group", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="options", to="operations.menumodifiergroup")),
            ],
            options={"verbose_name": "Menu Modifier Option", "verbose_name_plural": "Menu Modifier Options", "ordering": ["modifier_group", "name"]},
        ),
        migrations.AddIndex(
            model_name="menumodifieroption",
            index=models.Index(fields=["modifier_group", "is_active"], name="ops_modopt_grp_active_idx"),
        ),

        # -------------------------------------------------------------------------
        # OrderItemModifier
        # -------------------------------------------------------------------------
        migrations.CreateModel(
            name="OrderItemModifier",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("name", models.CharField(help_text="e.g. 'Spice Level'", max_length=150)),
                ("value", models.CharField(help_text="e.g. 'Less Spicy'", max_length=150)),
                ("price_adjustment", models.DecimalField(decimal_places=2, default="0.00", help_text="Copied from MenuModifierOption.price_adjustment. Backend-authoritative.", max_digits=10)),
                ("modifier_option", models.ForeignKey(blank=True, help_text="Source option. Null for free-text/special-request modifiers.", null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="applied_modifiers", to="operations.menumodifieroption")),
                ("order_item", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="modifiers", to="orders.orderitem")),
            ],
            options={"verbose_name": "Order Item Modifier", "verbose_name_plural": "Order Item Modifiers", "ordering": ["created_at"]},
        ),
        migrations.AddIndex(
            model_name="orderitemmodifier",
            index=models.Index(fields=["order_item"], name="ops_oimod_orderitem_idx"),
        ),

        # -------------------------------------------------------------------------
        # OrderFulfillmentStatus
        # -------------------------------------------------------------------------
        migrations.CreateModel(
            name="OrderFulfillmentStatus",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("status", models.CharField(choices=[("CONFIRMED", "Confirmed"), ("PREPARING", "Preparing"), ("READY", "Ready"), ("SERVED", "Served"), ("CANCELLED", "Cancelled")], db_index=True, default="CONFIRMED", max_length=20)),
                ("served_at", models.DateTimeField(blank=True, null=True)),
                ("notes", models.TextField(blank=True)),
                ("order", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="fulfillment_status", to="orders.order")),
                ("served_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="served_orders", to=settings.AUTH_USER_MODEL)),
            ],
            options={"verbose_name": "Order Fulfillment Status", "verbose_name_plural": "Order Fulfillment Statuses"},
        ),
        migrations.AddIndex(
            model_name="orderfulfillmentstatus",
            index=models.Index(fields=["order", "status"], name="ops_fulfill_order_status_idx"),
        ),
        migrations.AddIndex(
            model_name="orderfulfillmentstatus",
            index=models.Index(fields=["status"], name="ops_fulfill_status_idx"),
        ),

        # -------------------------------------------------------------------------
        # OrderChangeRequest
        # -------------------------------------------------------------------------
        migrations.CreateModel(
            name="OrderChangeRequest",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("change_type", models.CharField(choices=[("ADD_ITEM", "Add Item"), ("REMOVE_ITEM", "Remove Item"), ("CHANGE_QUANTITY", "Change Quantity"), ("CHANGE_NOTE", "Change Note"), ("CHANGE_TABLE", "Change Table"), ("CHANGE_WAITER", "Change Waiter"), ("CHANGE_CUSTOMER", "Change Customer")], db_index=True, max_length=30)),
                ("reason", models.TextField(help_text="Required reason for the change request.")),
                ("requested_data", models.JSONField(blank=True, default=dict, help_text="The proposed change data.")),
                ("status", models.CharField(choices=[("PENDING", "Pending"), ("APPROVED", "Approved"), ("REJECTED", "Rejected"), ("CANCELLED", "Cancelled")], db_index=True, default="PENDING", max_length=20)),
                ("approved_at", models.DateTimeField(blank=True, null=True)),
                ("rejected_at", models.DateTimeField(blank=True, null=True)),
                ("review_note", models.TextField(blank=True)),
                ("approved_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="approved_order_changes", to=settings.AUTH_USER_MODEL)),
                ("order", models.ForeignKey(db_index=True, on_delete=django.db.models.deletion.PROTECT, related_name="change_requests", to="orders.order")),
                ("requested_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="requested_order_changes", to=settings.AUTH_USER_MODEL)),
            ],
            options={"verbose_name": "Order Change Request", "verbose_name_plural": "Order Change Requests", "ordering": ["-created_at"]},
        ),
        migrations.AddIndex(
            model_name="orderchangerequest",
            index=models.Index(fields=["order", "status"], name="ops_chgreq_order_status_idx"),
        ),
        migrations.AddIndex(
            model_name="orderchangerequest",
            index=models.Index(fields=["status", "created_at"], name="ops_chgreq_status_created_idx"),
        ),
        migrations.AddIndex(
            model_name="orderchangerequest",
            index=models.Index(fields=["requested_by", "status"], name="ops_chgreq_user_status_idx"),
        ),

        # -------------------------------------------------------------------------
        # TableFloorPlan
        # -------------------------------------------------------------------------
        migrations.CreateModel(
            name="TableFloorPlan",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("position_x", models.FloatField(default=0.0)),
                ("position_y", models.FloatField(default=0.0)),
                ("width", models.FloatField(default=80.0)),
                ("height", models.FloatField(default=80.0)),
                ("rotation", models.FloatField(default=0.0, help_text="Degrees rotation.")),
                ("shape", models.CharField(choices=[("RECTANGLE", "Rectangle"), ("ROUND", "Round"), ("SQUARE", "Square")], default="RECTANGLE", max_length=20)),
                ("table", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="floor_plan", to="orders.diningtable")),
            ],
            options={"verbose_name": "Table Floor Plan", "verbose_name_plural": "Table Floor Plans"},
        ),

        # -------------------------------------------------------------------------
        # TableOperationalStatus
        # -------------------------------------------------------------------------
        migrations.CreateModel(
            name="TableOperationalStatus",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("status", models.CharField(choices=[("AVAILABLE", "Available"), ("OCCUPIED", "Occupied"), ("RESERVED", "Reserved"), ("BILL_PENDING", "Bill Pending"), ("CLEANING", "Cleaning"), ("OUT_OF_SERVICE", "Out of Service")], db_index=True, default="AVAILABLE", max_length=20)),
                ("notes", models.TextField(blank=True)),
                ("table", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="operational_status", to="orders.diningtable")),
                ("updated_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="updated_table_statuses", to=settings.AUTH_USER_MODEL)),
            ],
            options={"verbose_name": "Table Operational Status", "verbose_name_plural": "Table Operational Statuses"},
        ),
        migrations.AddIndex(
            model_name="tableoperationalstatus",
            index=models.Index(fields=["status"], name="ops_tableop_status_idx"),
        ),

        # -------------------------------------------------------------------------
        # TableTransfer
        # -------------------------------------------------------------------------
        migrations.CreateModel(
            name="TableTransfer",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("status", models.CharField(choices=[("REQUESTED", "Requested"), ("APPROVED", "Approved"), ("COMPLETED", "Completed"), ("REJECTED", "Rejected"), ("CANCELLED", "Cancelled")], db_index=True, default="REQUESTED", max_length=20)),
                ("reason", models.TextField(blank=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("approved_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="approved_table_transfers", to=settings.AUTH_USER_MODEL)),
                ("destination_table", models.ForeignKey(db_index=True, on_delete=django.db.models.deletion.PROTECT, related_name="incoming_transfers", to="orders.diningtable")),
                ("order", models.ForeignKey(db_index=True, on_delete=django.db.models.deletion.PROTECT, related_name="table_transfers", to="orders.order")),
                ("requested_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="requested_table_transfers", to=settings.AUTH_USER_MODEL)),
                ("source_table", models.ForeignKey(db_index=True, on_delete=django.db.models.deletion.PROTECT, related_name="outgoing_transfers", to="orders.diningtable")),
            ],
            options={"verbose_name": "Table Transfer", "verbose_name_plural": "Table Transfers", "ordering": ["-created_at"]},
        ),
        migrations.AddIndex(
            model_name="tabletransfer",
            index=models.Index(fields=["source_table", "status"], name="ops_tabxfer_src_status_idx"),
        ),
        migrations.AddIndex(
            model_name="tabletransfer",
            index=models.Index(fields=["destination_table", "status"], name="ops_tabxfer_dst_status_idx"),
        ),
        migrations.AddIndex(
            model_name="tabletransfer",
            index=models.Index(fields=["order", "status"], name="ops_tabxfer_order_status_idx"),
        ),
        migrations.AddIndex(
            model_name="tabletransfer",
            index=models.Index(fields=["status", "created_at"], name="ops_tabxfer_status_created_idx"),
        ),

        # -------------------------------------------------------------------------
        # TableMerge
        # -------------------------------------------------------------------------
        migrations.CreateModel(
            name="TableMerge",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("status", models.CharField(choices=[("REQUESTED", "Requested"), ("APPROVED", "Approved"), ("COMPLETED", "Completed"), ("REJECTED", "Rejected"), ("CANCELLED", "Cancelled")], db_index=True, default="REQUESTED", max_length=20)),
                ("reason", models.TextField(blank=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("approved_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="approved_table_merges", to=settings.AUTH_USER_MODEL)),
                ("branch", models.ForeignKey(db_index=True, on_delete=django.db.models.deletion.PROTECT, related_name="table_merges", to="organizations.branch")),
                ("destination_table", models.ForeignKey(help_text="Primary table — the merged group sits here.", on_delete=django.db.models.deletion.PROTECT, related_name="merge_destinations", to="orders.diningtable")),
                ("requested_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="requested_table_merges", to=settings.AUTH_USER_MODEL)),
                ("restaurant", models.ForeignKey(db_index=True, on_delete=django.db.models.deletion.PROTECT, related_name="table_merges", to="organizations.restaurant")),
                ("source_tables", models.ManyToManyField(help_text="All tables being merged together.", related_name="merge_sources", to="orders.diningtable")),
            ],
            options={"verbose_name": "Table Merge", "verbose_name_plural": "Table Merges", "ordering": ["-created_at"]},
        ),
        migrations.AddIndex(
            model_name="tablemerge",
            index=models.Index(fields=["branch", "status"], name="ops_tabmerge_branch_status_idx"),
        ),
        migrations.AddIndex(
            model_name="tablemerge",
            index=models.Index(fields=["status", "created_at"], name="ops_tabmerge_status_created_idx"),
        ),

        # -------------------------------------------------------------------------
        # OrderMergeRequest
        # -------------------------------------------------------------------------
        migrations.CreateModel(
            name="OrderMergeRequest",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("status", models.CharField(choices=[("PENDING", "Pending"), ("APPROVED", "Approved"), ("COMPLETED", "Completed"), ("REJECTED", "Rejected"), ("CANCELLED", "Cancelled")], db_index=True, default="PENDING", max_length=20)),
                ("reason", models.TextField(blank=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("approved_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="approved_order_merges", to=settings.AUTH_USER_MODEL)),
                ("destination_order", models.ForeignKey(help_text="The surviving order that receives all items.", on_delete=django.db.models.deletion.PROTECT, related_name="merge_destination", to="orders.order")),
                ("requested_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="requested_order_merges", to=settings.AUTH_USER_MODEL)),
                ("source_orders", models.ManyToManyField(help_text="Orders being merged (will be cancelled after merge completes).", related_name="merge_sources", to="orders.order")),
            ],
            options={"verbose_name": "Order Merge Request", "verbose_name_plural": "Order Merge Requests", "ordering": ["-created_at"]},
        ),
        migrations.AddIndex(
            model_name="ordermergerequest",
            index=models.Index(fields=["status", "created_at"], name="ops_ordmerge_status_created_idx"),
        ),
        migrations.AddIndex(
            model_name="ordermergerequest",
            index=models.Index(fields=["destination_order", "status"], name="ops_ordmerge_dest_status_idx"),
        ),

        # -------------------------------------------------------------------------
        # BillSplit
        # -------------------------------------------------------------------------
        migrations.CreateModel(
            name="BillSplit",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("split_number", models.PositiveSmallIntegerField(help_text="Sequential number within this bill (1, 2, 3, ...).")),
                ("split_type", models.CharField(choices=[("ITEM", "By Item"), ("QUANTITY", "By Quantity"), ("EQUAL", "Equal"), ("GUEST", "By Guest")], max_length=20)),
                ("amount", models.DecimalField(decimal_places=2, default="0.00", help_text="Amount allocated to this split. Backend-calculated.", max_digits=12)),
                ("status", models.CharField(choices=[("DRAFT", "Draft"), ("FINALIZED", "Finalized"), ("CANCELLED", "Cancelled")], db_index=True, default="DRAFT", max_length=20)),
                ("bill", models.ForeignKey(db_index=True, on_delete=django.db.models.deletion.PROTECT, related_name="splits", to="billing.bill")),
                ("created_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="created_bill_splits", to=settings.AUTH_USER_MODEL)),
            ],
            options={"verbose_name": "Bill Split", "verbose_name_plural": "Bill Splits", "ordering": ["bill", "split_number"]},
        ),
        migrations.AddIndex(
            model_name="billsplit",
            index=models.Index(fields=["bill", "status"], name="ops_billsplit_bill_status_idx"),
        ),
        migrations.AddConstraint(
            model_name="billsplit",
            constraint=models.UniqueConstraint(fields=["bill", "split_number"], name="unique_split_number_per_bill"),
        ),

        # -------------------------------------------------------------------------
        # BillSplitItem
        # -------------------------------------------------------------------------
        migrations.CreateModel(
            name="BillSplitItem",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("quantity", models.DecimalField(decimal_places=3, help_text="Quantity of this bill item allocated to this split.", max_digits=7)),
                ("amount", models.DecimalField(decimal_places=2, help_text="Amount for this allocation. Backend-calculated.", max_digits=12)),
                ("bill_item", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="split_allocations", to="billing.billitem")),
                ("bill_split", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="split_items", to="operations.billsplit")),
            ],
            options={"verbose_name": "Bill Split Item", "verbose_name_plural": "Bill Split Items", "ordering": ["bill_split", "created_at"]},
        ),
        migrations.AddIndex(
            model_name="billsplititem",
            index=models.Index(fields=["bill_split"], name="ops_splititem_split_idx"),
        ),
        migrations.AddIndex(
            model_name="billsplititem",
            index=models.Index(fields=["bill_item"], name="ops_splititem_billitem_idx"),
        ),

        # -------------------------------------------------------------------------
        # ReceiptPrintLog
        # -------------------------------------------------------------------------
        migrations.CreateModel(
            name="ReceiptPrintLog",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("print_type", models.CharField(choices=[("ORIGINAL", "Original"), ("REPRINT", "Reprint"), ("DUPLICATE", "Duplicate"), ("KITCHEN", "Kitchen Ticket")], db_index=True, default="ORIGINAL", max_length=20)),
                ("reason", models.TextField(blank=True, help_text="Required for REPRINT and DUPLICATE.")),
                ("printed_at", models.DateTimeField(auto_now_add=True)),
                ("bill", models.ForeignKey(db_index=True, on_delete=django.db.models.deletion.PROTECT, related_name="print_logs", to="billing.bill")),
                ("payment", models.ForeignKey(blank=True, help_text="Associated payment. Null for kitchen tickets.", null=True, on_delete=django.db.models.deletion.PROTECT, related_name="print_logs", to="payments.payment")),
                ("printed_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="receipt_prints", to=settings.AUTH_USER_MODEL)),
            ],
            options={"verbose_name": "Receipt Print Log", "verbose_name_plural": "Receipt Print Logs", "ordering": ["-printed_at"]},
        ),
        migrations.AddIndex(
            model_name="receiptprintlog",
            index=models.Index(fields=["bill", "print_type"], name="ops_printlog_bill_type_idx"),
        ),
        migrations.AddIndex(
            model_name="receiptprintlog",
            index=models.Index(fields=["printed_by", "printed_at"], name="ops_printlog_user_at_idx"),
        ),

        # -------------------------------------------------------------------------
        # OperationalShift
        # -------------------------------------------------------------------------
        migrations.CreateModel(
            name="OperationalShift",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("shift_type", models.CharField(choices=[("MORNING", "Morning"), ("AFTERNOON", "Afternoon"), ("EVENING", "Evening"), ("NIGHT", "Night"), ("CUSTOM", "Custom")], db_index=True, default="MORNING", max_length=20)),
                ("status", models.CharField(choices=[("OPEN", "Open"), ("CLOSED", "Closed")], db_index=True, default="OPEN", max_length=10)),
                ("started_at", models.DateTimeField(help_text="When this shift began.")),
                ("ended_at", models.DateTimeField(blank=True, help_text="When this shift ended.", null=True)),
                ("notes", models.TextField(blank=True)),
                ("branch", models.ForeignKey(db_index=True, on_delete=django.db.models.deletion.PROTECT, related_name="operational_shifts", to="organizations.branch")),
                ("closed_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="closed_operational_shifts", to=settings.AUTH_USER_MODEL)),
                ("opened_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="opened_operational_shifts", to=settings.AUTH_USER_MODEL)),
            ],
            options={"verbose_name": "Operational Shift", "verbose_name_plural": "Operational Shifts", "ordering": ["-started_at"]},
        ),
        migrations.AddIndex(
            model_name="operationalshift",
            index=models.Index(fields=["branch", "status"], name="ops_shift_branch_status_idx"),
        ),
        migrations.AddIndex(
            model_name="operationalshift",
            index=models.Index(fields=["branch", "started_at"], name="ops_shift_branch_started_idx"),
        ),
        migrations.AddIndex(
            model_name="operationalshift",
            index=models.Index(fields=["status", "started_at"], name="ops_shift_status_started_idx"),
        ),

        # -------------------------------------------------------------------------
        # ShiftHandoverNote
        # -------------------------------------------------------------------------
        migrations.CreateModel(
            name="ShiftHandoverNote",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("note_type", models.CharField(choices=[("GENERAL", "General"), ("KITCHEN", "Kitchen"), ("INVENTORY", "Inventory"), ("CUSTOMER", "Customer"), ("PAYMENT", "Payment"), ("EQUIPMENT", "Equipment"), ("STAFF", "Staff"), ("OTHER", "Other")], db_index=True, default="GENERAL", max_length=20)),
                ("content", models.TextField()),
                ("priority", models.CharField(choices=[("LOW", "Low"), ("NORMAL", "Normal"), ("HIGH", "High")], db_index=True, default="NORMAL", max_length=10)),
                ("created_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="shift_handover_notes", to=settings.AUTH_USER_MODEL)),
                ("shift", models.ForeignKey(db_index=True, on_delete=django.db.models.deletion.PROTECT, related_name="handover_notes", to="operations.operationalshift")),
            ],
            options={"verbose_name": "Shift Handover Note", "verbose_name_plural": "Shift Handover Notes", "ordering": ["-created_at"]},
        ),
        migrations.AddIndex(
            model_name="shifthandovernote",
            index=models.Index(fields=["shift", "note_type"], name="ops_handover_shift_type_idx"),
        ),
        migrations.AddIndex(
            model_name="shifthandovernote",
            index=models.Index(fields=["shift", "priority"], name="ops_handover_shift_priority_idx"),
        ),

        # -------------------------------------------------------------------------
        # OperationsAuditLog
        # -------------------------------------------------------------------------
        migrations.CreateModel(
            name="OperationsAuditLog",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("event_type", models.CharField(choices=[("POS_SESSION_STARTED", "POS Session Started"), ("POS_SESSION_PAUSED", "POS Session Paused"), ("POS_SESSION_ENDED", "POS Session Ended"), ("ORDER_HELD", "Order Held"), ("ORDER_RESUMED", "Order Resumed"), ("ORDER_PRIORITY_CHANGED", "Order Priority Changed"), ("ORDER_CHANGE_REQUESTED", "Order Change Requested"), ("ORDER_CHANGE_APPROVED", "Order Change Approved"), ("ORDER_CHANGE_REJECTED", "Order Change Rejected"), ("ORDER_MERGED", "Order Merged"), ("TABLE_TRANSFER_REQUESTED", "Table Transfer Requested"), ("TABLE_TRANSFER_COMPLETED", "Table Transfer Completed"), ("TABLE_MERGED", "Table Merged"), ("BILL_SPLIT_CREATED", "Bill Split Created"), ("BILL_SPLIT_FINALIZED", "Bill Split Finalized"), ("RECEIPT_PRINTED", "Receipt Printed"), ("RECEIPT_REPRINTED", "Receipt Reprinted"), ("SHIFT_CREATED", "Shift Created"), ("SHIFT_CLOSED", "Shift Closed"), ("SHIFT_HANDOVER_CREATED", "Shift Handover Created"), ("MODIFIER_ADDED", "Modifier Added"), ("MODIFIER_REMOVED", "Modifier Removed"), ("WAITER_ASSIGNED", "Waiter Assigned"), ("TABLE_OP_STATUS_CHANGED", "Table Operational Status Changed")], db_index=True, max_length=50)),
                ("order_id", models.UUIDField(blank=True, db_index=True, null=True)),
                ("bill_id", models.UUIDField(blank=True, db_index=True, null=True)),
                ("table_id", models.UUIDField(blank=True, db_index=True, null=True)),
                ("pos_session_id", models.UUIDField(blank=True, null=True)),
                ("shift_id", models.UUIDField(blank=True, null=True)),
                ("old_value", models.CharField(blank=True, max_length=100)),
                ("new_value", models.CharField(blank=True, max_length=100)),
                ("metadata", models.JSONField(blank=True, default=dict, help_text="Additional context for the event.")),
                ("occurred_at", models.DateTimeField(auto_now_add=True)),
                ("actor", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="operations_audit_logs", to=settings.AUTH_USER_MODEL)),
                ("branch", models.ForeignKey(blank=True, db_index=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="operations_audit_logs", to="organizations.branch")),
            ],
            options={"verbose_name": "Operations Audit Log", "verbose_name_plural": "Operations Audit Logs", "ordering": ["-occurred_at"]},
        ),
        migrations.AddIndex(
            model_name="operationsauditlog",
            index=models.Index(fields=["event_type", "occurred_at"], name="ops_audit_event_at_idx"),
        ),
        migrations.AddIndex(
            model_name="operationsauditlog",
            index=models.Index(fields=["actor", "occurred_at"], name="ops_audit_actor_at_idx"),
        ),
        migrations.AddIndex(
            model_name="operationsauditlog",
            index=models.Index(fields=["branch", "occurred_at"], name="ops_audit_branch_at_idx"),
        ),
        migrations.AddIndex(
            model_name="operationsauditlog",
            index=models.Index(fields=["order_id"], name="ops_audit_order_idx"),
        ),
        migrations.AddIndex(
            model_name="operationsauditlog",
            index=models.Index(fields=["bill_id"], name="ops_audit_bill_idx"),
        ),
    ]
