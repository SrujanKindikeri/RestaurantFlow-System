# =============================================================================
# RestaurantFlow — Inventory Initial Migration
# Phase 10
#
# Generated manually (Python not available in shell environment).
# Covers all 15 inventory models.
# =============================================================================

from decimal import Decimal
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
        # InventoryCategory
        # =====================================================================
        migrations.CreateModel(
            name="InventoryCategory",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=100)),
                ("description", models.TextField(blank=True)),
                ("is_active", models.BooleanField(db_index=True, default=True)),
                (
                    "restaurant",
                    models.ForeignKey(
                        db_index=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="inventory_categories",
                        to="organizations.restaurant",
                    ),
                ),
            ],
            options={
                "verbose_name": "Inventory Category",
                "verbose_name_plural": "Inventory Categories",
                "ordering": ["name"],
            },
        ),
        migrations.AddConstraint(
            model_name="inventorycategory",
            constraint=models.UniqueConstraint(
                fields=["restaurant", "name"],
                name="unique_inventory_category_per_restaurant",
            ),
        ),
        migrations.AddIndex(
            model_name="inventorycategory",
            index=models.Index(fields=["restaurant", "is_active"], name="inv_cat_rest_active_idx"),
        ),
        migrations.AddIndex(
            model_name="inventorycategory",
            index=models.Index(fields=["restaurant", "name"], name="inv_cat_rest_name_idx"),
        ),

        # =====================================================================
        # InventoryItem
        # =====================================================================
        migrations.CreateModel(
            name="InventoryItem",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("name", models.CharField(db_index=True, max_length=150)),
                ("sku", models.CharField(db_index=True, max_length=50, help_text="Stock Keeping Unit — unique within the restaurant.")),
                ("description", models.TextField(blank=True)),
                ("default_unit", models.CharField(
                    choices=[
                        ("KG", "Kilogram (KG)"), ("GRAM", "Gram (g)"), ("LITRE", "Litre (L)"),
                        ("MILLILITRE", "Millilitre (mL)"), ("PIECE", "Piece"), ("PACK", "Pack"),
                        ("BOX", "Box"), ("BOTTLE", "Bottle"), ("DOZEN", "Dozen"),
                    ],
                    db_index=True, max_length=15,
                )),
                ("minimum_stock", models.DecimalField(decimal_places=3, default="0.000", max_digits=14)),
                ("reorder_level", models.DecimalField(decimal_places=3, default="0.000", max_digits=14)),
                ("maximum_stock", models.DecimalField(decimal_places=3, default="0.000", max_digits=14)),
                ("average_cost", models.DecimalField(decimal_places=2, default="0.00", max_digits=14)),
                ("is_active", models.BooleanField(db_index=True, default=True)),
                (
                    "restaurant",
                    models.ForeignKey(
                        db_index=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="inventory_items",
                        to="organizations.restaurant",
                    ),
                ),
                (
                    "category",
                    models.ForeignKey(
                        blank=True,
                        db_index=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="items",
                        to="inventory.inventorycategory",
                    ),
                ),
            ],
            options={
                "verbose_name": "Inventory Item",
                "verbose_name_plural": "Inventory Items",
                "ordering": ["name"],
            },
        ),
        migrations.AddConstraint(
            model_name="inventoryitem",
            constraint=models.UniqueConstraint(
                fields=["restaurant", "sku"],
                name="unique_inventory_sku_per_restaurant",
            ),
        ),
        migrations.AddIndex(
            model_name="inventoryitem",
            index=models.Index(fields=["restaurant", "is_active"], name="inv_item_rest_active_idx"),
        ),
        migrations.AddIndex(
            model_name="inventoryitem",
            index=models.Index(fields=["restaurant", "category"], name="inv_item_rest_cat_idx"),
        ),
        migrations.AddIndex(
            model_name="inventoryitem",
            index=models.Index(fields=["restaurant", "sku"], name="inv_item_rest_sku_idx"),
        ),
        migrations.AddIndex(
            model_name="inventoryitem",
            index=models.Index(fields=["name"], name="inv_item_name_idx"),
        ),

        # =====================================================================
        # StorageLocation
        # =====================================================================
        migrations.CreateModel(
            name="StorageLocation",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=100)),
                ("code", models.CharField(db_index=True, max_length=20)),
                ("location_type", models.CharField(
                    choices=[
                        ("MAIN_STORE", "Main Store"), ("KITCHEN", "Kitchen Store"),
                        ("COLD_STORAGE", "Cold Storage"), ("FREEZER", "Freezer"),
                        ("BAR", "Bar Store"), ("DRY_STORE", "Dry Store"), ("OTHER", "Other"),
                    ],
                    db_index=True, max_length=20,
                )),
                ("description", models.TextField(blank=True)),
                ("is_active", models.BooleanField(db_index=True, default=True)),
                (
                    "branch",
                    models.ForeignKey(
                        db_index=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="storage_locations",
                        to="organizations.branch",
                    ),
                ),
            ],
            options={
                "verbose_name": "Storage Location",
                "verbose_name_plural": "Storage Locations",
                "ordering": ["branch", "name"],
            },
        ),
        migrations.AddConstraint(
            model_name="storagelocation",
            constraint=models.UniqueConstraint(
                fields=["branch", "code"],
                name="unique_storage_location_code_per_branch",
            ),
        ),
        migrations.AddIndex(
            model_name="storagelocation",
            index=models.Index(fields=["branch", "is_active"], name="inv_loc_branch_active_idx"),
        ),
        migrations.AddIndex(
            model_name="storagelocation",
            index=models.Index(fields=["branch", "location_type"], name="inv_loc_branch_type_idx"),
        ),

        # =====================================================================
        # StockBalance
        # =====================================================================
        migrations.CreateModel(
            name="StockBalance",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("quantity", models.DecimalField(decimal_places=3, default="0.000", max_digits=14)),
                ("reserved_quantity", models.DecimalField(decimal_places=3, default="0.000", max_digits=14)),
                ("average_cost", models.DecimalField(decimal_places=2, default="0.00", max_digits=14)),
                ("last_movement_at", models.DateTimeField(blank=True, null=True)),
                (
                    "inventory_item",
                    models.ForeignKey(
                        db_index=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="stock_balances",
                        to="inventory.inventoryitem",
                    ),
                ),
                (
                    "storage_location",
                    models.ForeignKey(
                        db_index=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="stock_balances",
                        to="inventory.storagelocation",
                    ),
                ),
            ],
            options={
                "verbose_name": "Stock Balance",
                "verbose_name_plural": "Stock Balances",
                "ordering": ["inventory_item", "storage_location"],
            },
        ),
        migrations.AddConstraint(
            model_name="stockbalance",
            constraint=models.UniqueConstraint(
                fields=["inventory_item", "storage_location"],
                name="unique_stock_balance_per_item_location",
            ),
        ),
        migrations.AddIndex(
            model_name="stockbalance",
            index=models.Index(fields=["inventory_item", "storage_location"], name="inv_bal_item_loc_idx"),
        ),
        migrations.AddIndex(
            model_name="stockbalance",
            index=models.Index(fields=["storage_location"], name="inv_bal_loc_idx"),
        ),
        migrations.AddIndex(
            model_name="stockbalance",
            index=models.Index(fields=["inventory_item"], name="inv_bal_item_idx"),
        ),

        # =====================================================================
        # StockMovement
        # =====================================================================
        migrations.CreateModel(
            name="StockMovement",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("movement_type", models.CharField(
                    choices=[
                        ("PURCHASE", "Purchase"), ("PURCHASE_RETURN", "Purchase Return"),
                        ("TRANSFER_IN", "Transfer In"), ("TRANSFER_OUT", "Transfer Out"),
                        ("WASTAGE", "Wastage"), ("ADJUSTMENT_IN", "Adjustment In"),
                        ("ADJUSTMENT_OUT", "Adjustment Out"), ("CONSUMPTION", "Consumption"),
                        ("OPENING_STOCK", "Opening Stock"), ("CORRECTION", "Correction"),
                    ],
                    db_index=True, max_length=25,
                )),
                ("quantity", models.DecimalField(decimal_places=3, max_digits=14)),
                ("unit_cost", models.DecimalField(decimal_places=2, default="0.00", max_digits=14)),
                ("total_cost", models.DecimalField(decimal_places=2, default="0.00", max_digits=16)),
                ("reference_type", models.CharField(blank=True, db_index=True, max_length=30)),
                ("reference_id", models.UUIDField(blank=True, db_index=True, null=True)),
                ("reason", models.TextField(blank=True)),
                (
                    "inventory_item",
                    models.ForeignKey(
                        db_index=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="stock_movements",
                        to="inventory.inventoryitem",
                    ),
                ),
                (
                    "storage_location",
                    models.ForeignKey(
                        db_index=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="stock_movements",
                        to="inventory.storagelocation",
                    ),
                ),
                (
                    "performed_by",
                    models.ForeignKey(
                        db_index=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="stock_movements",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Stock Movement",
                "verbose_name_plural": "Stock Movements",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="stockmovement",
            index=models.Index(fields=["inventory_item", "created_at"], name="inv_mov_item_date_idx"),
        ),
        migrations.AddIndex(
            model_name="stockmovement",
            index=models.Index(fields=["storage_location", "created_at"], name="inv_mov_loc_date_idx"),
        ),
        migrations.AddIndex(
            model_name="stockmovement",
            index=models.Index(fields=["movement_type", "created_at"], name="inv_mov_type_date_idx"),
        ),
        migrations.AddIndex(
            model_name="stockmovement",
            index=models.Index(fields=["reference_type", "reference_id"], name="inv_mov_ref_idx"),
        ),
        migrations.AddIndex(
            model_name="stockmovement",
            index=models.Index(fields=["performed_by", "created_at"], name="inv_mov_user_date_idx"),
        ),
        migrations.AddIndex(
            model_name="stockmovement",
            index=models.Index(fields=["created_at"], name="inv_mov_date_idx"),
        ),

        # =====================================================================
        # Supplier
        # =====================================================================
        migrations.CreateModel(
            name="Supplier",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("name", models.CharField(db_index=True, max_length=150)),
                ("code", models.CharField(db_index=True, max_length=30)),
                ("contact_person", models.CharField(blank=True, max_length=100)),
                ("phone", models.CharField(blank=True, max_length=30)),
                ("email", models.EmailField(blank=True)),
                ("address", models.TextField(blank=True)),
                ("tax_identifier", models.CharField(blank=True, max_length=50)),
                ("notes", models.TextField(blank=True)),
                ("is_active", models.BooleanField(db_index=True, default=True)),
                (
                    "restaurant",
                    models.ForeignKey(
                        db_index=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="suppliers",
                        to="organizations.restaurant",
                    ),
                ),
            ],
            options={
                "verbose_name": "Supplier",
                "verbose_name_plural": "Suppliers",
                "ordering": ["name"],
            },
        ),
        migrations.AddConstraint(
            model_name="supplier",
            constraint=models.UniqueConstraint(
                fields=["restaurant", "code"],
                name="unique_supplier_code_per_restaurant",
            ),
        ),
        migrations.AddIndex(
            model_name="supplier",
            index=models.Index(fields=["restaurant", "is_active"], name="inv_sup_rest_active_idx"),
        ),
        migrations.AddIndex(
            model_name="supplier",
            index=models.Index(fields=["restaurant", "code"], name="inv_sup_rest_code_idx"),
        ),

        # =====================================================================
        # PurchaseSequence
        # =====================================================================
        migrations.CreateModel(
            name="PurchaseSequence",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("last_sequence", models.PositiveIntegerField(default=0)),
                (
                    "restaurant",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="purchase_sequence",
                        to="organizations.restaurant",
                    ),
                ),
            ],
            options={
                "verbose_name": "Purchase Sequence",
                "verbose_name_plural": "Purchase Sequences",
            },
        ),

        # =====================================================================
        # PurchaseOrder
        # =====================================================================
        migrations.CreateModel(
            name="PurchaseOrder",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("purchase_number", models.CharField(db_index=True, max_length=20, unique=True)),
                ("status", models.CharField(
                    choices=[
                        ("DRAFT", "Draft"), ("SUBMITTED", "Submitted"), ("APPROVED", "Approved"),
                        ("PARTIALLY_RECEIVED", "Partially Received"), ("RECEIVED", "Received"),
                        ("CANCELLED", "Cancelled"),
                    ],
                    db_index=True, default="DRAFT", max_length=25,
                )),
                ("order_date", models.DateField(blank=True, null=True)),
                ("expected_date", models.DateField(blank=True, null=True)),
                ("subtotal", models.DecimalField(decimal_places=2, default="0.00", max_digits=14)),
                ("tax_amount", models.DecimalField(decimal_places=2, default="0.00", max_digits=14)),
                ("discount_amount", models.DecimalField(decimal_places=2, default="0.00", max_digits=14)),
                ("total_amount", models.DecimalField(decimal_places=2, default="0.00", max_digits=14)),
                ("notes", models.TextField(blank=True)),
                ("approved_at", models.DateTimeField(blank=True, null=True)),
                ("received_at", models.DateTimeField(blank=True, null=True)),
                (
                    "restaurant",
                    models.ForeignKey(
                        db_index=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="purchase_orders",
                        to="organizations.restaurant",
                    ),
                ),
                (
                    "branch",
                    models.ForeignKey(
                        db_index=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="purchase_orders",
                        to="organizations.branch",
                    ),
                ),
                (
                    "supplier",
                    models.ForeignKey(
                        db_index=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="purchase_orders",
                        to="inventory.supplier",
                    ),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="created_purchase_orders",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "approved_by",
                    models.ForeignKey(
                        blank=True, null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="approved_purchase_orders",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "received_by",
                    models.ForeignKey(
                        blank=True, null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="received_purchase_orders",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Purchase Order",
                "verbose_name_plural": "Purchase Orders",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="purchaseorder",
            index=models.Index(fields=["restaurant", "status"], name="inv_po_rest_status_idx"),
        ),
        migrations.AddIndex(
            model_name="purchaseorder",
            index=models.Index(fields=["branch", "status"], name="inv_po_branch_status_idx"),
        ),
        migrations.AddIndex(
            model_name="purchaseorder",
            index=models.Index(fields=["supplier", "status"], name="inv_po_sup_status_idx"),
        ),
        migrations.AddIndex(
            model_name="purchaseorder",
            index=models.Index(fields=["purchase_number"], name="inv_po_number_idx"),
        ),
        migrations.AddIndex(
            model_name="purchaseorder",
            index=models.Index(fields=["status", "created_at"], name="inv_po_status_date_idx"),
        ),
        migrations.AddIndex(
            model_name="purchaseorder",
            index=models.Index(fields=["created_at"], name="inv_po_date_idx"),
        ),

        # =====================================================================
        # PurchaseOrderItem
        # =====================================================================
        migrations.CreateModel(
            name="PurchaseOrderItem",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("quantity", models.DecimalField(decimal_places=3, max_digits=14)),
                ("unit", models.CharField(
                    choices=[
                        ("KG", "Kilogram (KG)"), ("GRAM", "Gram (g)"), ("LITRE", "Litre (L)"),
                        ("MILLILITRE", "Millilitre (mL)"), ("PIECE", "Piece"), ("PACK", "Pack"),
                        ("BOX", "Box"), ("BOTTLE", "Bottle"), ("DOZEN", "Dozen"),
                    ],
                    max_length=15,
                )),
                ("unit_cost", models.DecimalField(decimal_places=2, max_digits=14)),
                ("tax_rate", models.DecimalField(decimal_places=3, default="0.000", max_digits=6)),
                ("discount_amount", models.DecimalField(decimal_places=2, default="0.00", max_digits=14)),
                ("total_amount", models.DecimalField(decimal_places=2, default="0.00", max_digits=14)),
                ("received_quantity", models.DecimalField(decimal_places=3, default="0.000", max_digits=14)),
                ("notes", models.TextField(blank=True)),
                (
                    "purchase_order",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="items",
                        to="inventory.purchaseorder",
                    ),
                ),
                (
                    "inventory_item",
                    models.ForeignKey(
                        db_index=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="purchase_order_items",
                        to="inventory.inventoryitem",
                    ),
                ),
            ],
            options={
                "verbose_name": "Purchase Order Item",
                "verbose_name_plural": "Purchase Order Items",
                "ordering": ["created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="purchaseorderitem",
            index=models.Index(fields=["purchase_order", "inventory_item"], name="inv_poi_po_item_idx"),
        ),
        migrations.AddIndex(
            model_name="purchaseorderitem",
            index=models.Index(fields=["inventory_item"], name="inv_poi_item_idx"),
        ),

        # =====================================================================
        # PurchaseReceipt
        # =====================================================================
        migrations.CreateModel(
            name="PurchaseReceipt",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("received_at", models.DateTimeField(auto_now_add=True)),
                ("notes", models.TextField(blank=True)),
                (
                    "purchase_order",
                    models.ForeignKey(
                        db_index=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="receipts",
                        to="inventory.purchaseorder",
                    ),
                ),
                (
                    "received_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="purchase_receipts",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "storage_location",
                    models.ForeignKey(
                        db_index=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="purchase_receipts",
                        to="inventory.storagelocation",
                    ),
                ),
            ],
            options={
                "verbose_name": "Purchase Receipt",
                "verbose_name_plural": "Purchase Receipts",
                "ordering": ["-received_at"],
            },
        ),
        migrations.AddIndex(
            model_name="purchasereceipt",
            index=models.Index(fields=["purchase_order", "received_at"], name="inv_pr_po_date_idx"),
        ),
        migrations.AddIndex(
            model_name="purchasereceipt",
            index=models.Index(fields=["storage_location", "received_at"], name="inv_pr_loc_date_idx"),
        ),

        # =====================================================================
        # PurchaseReceiptItem
        # =====================================================================
        migrations.CreateModel(
            name="PurchaseReceiptItem",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("quantity_received", models.DecimalField(decimal_places=3, max_digits=14)),
                ("unit_cost", models.DecimalField(decimal_places=2, max_digits=14)),
                (
                    "receipt",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="items",
                        to="inventory.purchasereceipt",
                    ),
                ),
                (
                    "purchase_order_item",
                    models.ForeignKey(
                        db_index=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="receipt_items",
                        to="inventory.purchaseorderitem",
                    ),
                ),
            ],
            options={
                "verbose_name": "Purchase Receipt Item",
                "verbose_name_plural": "Purchase Receipt Items",
            },
        ),
        migrations.AddIndex(
            model_name="purchasereceiptitem",
            index=models.Index(fields=["receipt", "purchase_order_item"], name="inv_pri_receipt_item_idx"),
        ),

        # =====================================================================
        # TransferSequence
        # =====================================================================
        migrations.CreateModel(
            name="TransferSequence",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("last_sequence", models.PositiveIntegerField(default=0)),
                (
                    "restaurant",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="transfer_sequence",
                        to="organizations.restaurant",
                    ),
                ),
            ],
            options={
                "verbose_name": "Transfer Sequence",
                "verbose_name_plural": "Transfer Sequences",
            },
        ),

        # =====================================================================
        # StockTransfer
        # =====================================================================
        migrations.CreateModel(
            name="StockTransfer",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("transfer_number", models.CharField(db_index=True, max_length=20, unique=True)),
                ("status", models.CharField(
                    choices=[
                        ("DRAFT", "Draft"), ("REQUESTED", "Requested"),
                        ("APPROVED", "Approved"), ("COMPLETED", "Completed"),
                        ("CANCELLED", "Cancelled"),
                    ],
                    db_index=True, default="DRAFT", max_length=15,
                )),
                ("notes", models.TextField(blank=True)),
                ("requested_at", models.DateTimeField(blank=True, null=True)),
                ("approved_at", models.DateTimeField(blank=True, null=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                (
                    "restaurant",
                    models.ForeignKey(
                        db_index=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="stock_transfers",
                        to="organizations.restaurant",
                    ),
                ),
                (
                    "source_location",
                    models.ForeignKey(
                        db_index=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="outgoing_transfers",
                        to="inventory.storagelocation",
                    ),
                ),
                (
                    "destination_location",
                    models.ForeignKey(
                        db_index=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="incoming_transfers",
                        to="inventory.storagelocation",
                    ),
                ),
                (
                    "requested_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="requested_transfers",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "approved_by",
                    models.ForeignKey(
                        blank=True, null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="approved_transfers",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "completed_by",
                    models.ForeignKey(
                        blank=True, null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="completed_transfers",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Stock Transfer",
                "verbose_name_plural": "Stock Transfers",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="stocktransfer",
            index=models.Index(fields=["restaurant", "status"], name="inv_tr_rest_status_idx"),
        ),
        migrations.AddIndex(
            model_name="stocktransfer",
            index=models.Index(fields=["source_location", "status"], name="inv_tr_src_status_idx"),
        ),
        migrations.AddIndex(
            model_name="stocktransfer",
            index=models.Index(fields=["destination_location", "status"], name="inv_tr_dst_status_idx"),
        ),
        migrations.AddIndex(
            model_name="stocktransfer",
            index=models.Index(fields=["transfer_number"], name="inv_tr_number_idx"),
        ),
        migrations.AddIndex(
            model_name="stocktransfer",
            index=models.Index(fields=["status", "created_at"], name="inv_tr_status_date_idx"),
        ),

        # =====================================================================
        # StockTransferItem
        # =====================================================================
        migrations.CreateModel(
            name="StockTransferItem",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("quantity", models.DecimalField(decimal_places=3, max_digits=14)),
                ("unit", models.CharField(
                    choices=[
                        ("KG", "Kilogram (KG)"), ("GRAM", "Gram (g)"), ("LITRE", "Litre (L)"),
                        ("MILLILITRE", "Millilitre (mL)"), ("PIECE", "Piece"), ("PACK", "Pack"),
                        ("BOX", "Box"), ("BOTTLE", "Bottle"), ("DOZEN", "Dozen"),
                    ],
                    max_length=15,
                )),
                (
                    "transfer",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="items",
                        to="inventory.stocktransfer",
                    ),
                ),
                (
                    "inventory_item",
                    models.ForeignKey(
                        db_index=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="transfer_items",
                        to="inventory.inventoryitem",
                    ),
                ),
            ],
            options={
                "verbose_name": "Stock Transfer Item",
                "verbose_name_plural": "Stock Transfer Items",
            },
        ),
        migrations.AddIndex(
            model_name="stocktransferitem",
            index=models.Index(fields=["transfer", "inventory_item"], name="inv_tri_tr_item_idx"),
        ),

        # =====================================================================
        # StockWastage
        # =====================================================================
        migrations.CreateModel(
            name="StockWastage",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("quantity", models.DecimalField(decimal_places=3, max_digits=14)),
                ("unit", models.CharField(
                    choices=[
                        ("KG", "Kilogram (KG)"), ("GRAM", "Gram (g)"), ("LITRE", "Litre (L)"),
                        ("MILLILITRE", "Millilitre (mL)"), ("PIECE", "Piece"), ("PACK", "Pack"),
                        ("BOX", "Box"), ("BOTTLE", "Bottle"), ("DOZEN", "Dozen"),
                    ],
                    max_length=15,
                )),
                ("wastage_type", models.CharField(
                    choices=[
                        ("SPOILED", "Spoiled"), ("DAMAGED", "Damaged"), ("EXPIRED", "Expired"),
                        ("PREPARATION_LOSS", "Preparation Loss"), ("OTHER", "Other"),
                    ],
                    db_index=True, max_length=20,
                )),
                ("reason", models.TextField()),
                ("estimated_cost", models.DecimalField(decimal_places=2, default="0.00", max_digits=14)),
                ("status", models.CharField(
                    choices=[
                        ("PENDING", "Pending"), ("APPROVED", "Approved"),
                        ("REJECTED", "Rejected"), ("RECORDED", "Recorded"),
                    ],
                    db_index=True, default="PENDING", max_length=10,
                )),
                ("approved_at", models.DateTimeField(blank=True, null=True)),
                ("rejection_reason", models.TextField(blank=True)),
                (
                    "inventory_item",
                    models.ForeignKey(
                        db_index=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="wastage_records",
                        to="inventory.inventoryitem",
                    ),
                ),
                (
                    "storage_location",
                    models.ForeignKey(
                        db_index=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="wastage_records",
                        to="inventory.storagelocation",
                    ),
                ),
                (
                    "recorded_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="recorded_wastages",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "approved_by",
                    models.ForeignKey(
                        blank=True, null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="approved_wastages",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Stock Wastage",
                "verbose_name_plural": "Stock Wastages",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="stockwastage",
            index=models.Index(fields=["inventory_item", "status"], name="inv_wst_item_status_idx"),
        ),
        migrations.AddIndex(
            model_name="stockwastage",
            index=models.Index(fields=["storage_location", "status"], name="inv_wst_loc_status_idx"),
        ),
        migrations.AddIndex(
            model_name="stockwastage",
            index=models.Index(fields=["status", "created_at"], name="inv_wst_status_date_idx"),
        ),
        migrations.AddIndex(
            model_name="stockwastage",
            index=models.Index(fields=["recorded_by", "created_at"], name="inv_wst_user_date_idx"),
        ),

        # =====================================================================
        # StockAdjustment
        # =====================================================================
        migrations.CreateModel(
            name="StockAdjustment",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("quantity_before", models.DecimalField(decimal_places=3, max_digits=14)),
                ("quantity_physical", models.DecimalField(decimal_places=3, max_digits=14)),
                ("quantity_difference", models.DecimalField(decimal_places=3, max_digits=14)),
                ("unit", models.CharField(
                    choices=[
                        ("KG", "Kilogram (KG)"), ("GRAM", "Gram (g)"), ("LITRE", "Litre (L)"),
                        ("MILLILITRE", "Millilitre (mL)"), ("PIECE", "Piece"), ("PACK", "Pack"),
                        ("BOX", "Box"), ("BOTTLE", "Bottle"), ("DOZEN", "Dozen"),
                    ],
                    max_length=15,
                )),
                ("reason", models.TextField()),
                (
                    "inventory_item",
                    models.ForeignKey(
                        db_index=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="adjustments",
                        to="inventory.inventoryitem",
                    ),
                ),
                (
                    "storage_location",
                    models.ForeignKey(
                        db_index=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="adjustments",
                        to="inventory.storagelocation",
                    ),
                ),
                (
                    "adjusted_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="stock_adjustments",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "stock_movement",
                    models.OneToOneField(
                        blank=True, null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="adjustment",
                        to="inventory.stockmovement",
                    ),
                ),
            ],
            options={
                "verbose_name": "Stock Adjustment",
                "verbose_name_plural": "Stock Adjustments",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="stockadjustment",
            index=models.Index(fields=["inventory_item", "created_at"], name="inv_adj_item_date_idx"),
        ),
        migrations.AddIndex(
            model_name="stockadjustment",
            index=models.Index(fields=["storage_location", "created_at"], name="inv_adj_loc_date_idx"),
        ),
        migrations.AddIndex(
            model_name="stockadjustment",
            index=models.Index(fields=["adjusted_by", "created_at"], name="inv_adj_user_date_idx"),
        ),
    ]
