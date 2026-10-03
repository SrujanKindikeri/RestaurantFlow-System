# Generated migration for Phase 11: Recipe and Ingredient Consumption
# Hand-authored because Python is not available in the CI environment.

import django.db.models.deletion
import django.utils.timezone
import uuid

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("inventory", "0001_initial"),
        ("menu", "0001_initial"),
        ("orders", "0001_initial"),
        ("organizations", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # ─────────────────────────────────────────────────────────────────────
        # BranchConsumptionConfig
        # ─────────────────────────────────────────────────────────────────────
        migrations.CreateModel(
            name="BranchConsumptionConfig",
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
                    "consumption_trigger",
                    models.CharField(
                        default="KITCHEN_COMPLETED",
                        help_text=(
                            "KITCHEN_STARTED = trigger on PREPARING transition. "
                            "KITCHEN_COMPLETED = trigger on READY transition (default)."
                        ),
                        max_length=25,
                    ),
                ),
                (
                    "branch",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="consumption_config",
                        to="organizations.branch",
                    ),
                ),
                (
                    "default_consumption_location",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="branch_consumption_configs",
                        to="inventory.storagelocation",
                        help_text=(
                            "The storage location from which stock is consumed for this branch."
                        ),
                    ),
                ),
            ],
            options={
                "verbose_name": "Branch Consumption Config",
                "verbose_name_plural": "Branch Consumption Configs",
            },
        ),
        # ─────────────────────────────────────────────────────────────────────
        # Recipe
        # ─────────────────────────────────────────────────────────────────────
        migrations.CreateModel(
            name="Recipe",
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
                ("name", models.CharField(max_length=200)),
                ("version", models.PositiveIntegerField(db_index=True, default=1)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("DRAFT", "Draft"),
                            ("ACTIVE", "Active"),
                            ("INACTIVE", "Inactive"),
                            ("ARCHIVED", "Archived"),
                        ],
                        db_index=True,
                        default="DRAFT",
                        max_length=10,
                    ),
                ),
                (
                    "yield_quantity",
                    models.DecimalField(
                        decimal_places=3,
                        default="1.000",
                        max_digits=10,
                    ),
                ),
                (
                    "yield_unit",
                    models.CharField(
                        default="PIECE",
                        max_length=15,
                    ),
                ),
                ("preparation_notes", models.TextField(blank=True)),
                (
                    "effective_from",
                    models.DateTimeField(blank=True, db_index=True, null=True),
                ),
                (
                    "effective_to",
                    models.DateTimeField(blank=True, db_index=True, null=True),
                ),
                ("approved_at", models.DateTimeField(blank=True, null=True)),
                (
                    "approved_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="approved_recipes",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="created_recipes",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "menu_item",
                    models.ForeignKey(
                        db_index=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="recipes",
                        to="menu.menuitem",
                    ),
                ),
                (
                    "restaurant",
                    models.ForeignKey(
                        db_index=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="recipes",
                        to="organizations.restaurant",
                    ),
                ),
            ],
            options={
                "verbose_name": "Recipe",
                "verbose_name_plural": "Recipes",
                "ordering": ["menu_item", "-version"],
            },
        ),
        migrations.AddIndex(
            model_name="recipe",
            index=models.Index(
                fields=["restaurant", "menu_item"], name="recipes_reci_restaur_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="recipe",
            index=models.Index(
                fields=["restaurant", "status"], name="recipes_reci_restaur_status_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="recipe",
            index=models.Index(
                fields=["menu_item", "status"], name="recipes_reci_menu_it_status_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="recipe",
            index=models.Index(
                fields=["menu_item", "version"], name="recipes_reci_menu_it_version_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="recipe",
            index=models.Index(
                fields=["status", "effective_from"],
                name="recipes_reci_status_eff_from_idx",
            ),
        ),
        migrations.AddConstraint(
            model_name="recipe",
            constraint=models.UniqueConstraint(
                condition=models.Q(status="ACTIVE"),
                fields=["menu_item"],
                name="unique_active_recipe_per_menu_item",
            ),
        ),
        # ─────────────────────────────────────────────────────────────────────
        # RecipeItem
        # ─────────────────────────────────────────────────────────────────────
        migrations.CreateModel(
            name="RecipeItem",
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
                    "quantity",
                    models.DecimalField(decimal_places=3, max_digits=14),
                ),
                ("unit", models.CharField(max_length=15)),
                (
                    "preparation_loss_percentage",
                    models.DecimalField(
                        decimal_places=3, default="0.000", max_digits=6
                    ),
                ),
                ("notes", models.TextField(blank=True)),
                (
                    "display_order",
                    models.PositiveIntegerField(db_index=True, default=0),
                ),
                (
                    "inventory_item",
                    models.ForeignKey(
                        db_index=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="recipe_items",
                        to="inventory.inventoryitem",
                    ),
                ),
                (
                    "recipe",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="items",
                        to="recipes.recipe",
                    ),
                ),
            ],
            options={
                "verbose_name": "Recipe Item",
                "verbose_name_plural": "Recipe Items",
                "ordering": ["display_order", "created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="recipeitem",
            index=models.Index(
                fields=["recipe", "display_order"],
                name="recipes_reci_recipe_disp_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="recipeitem",
            index=models.Index(
                fields=["inventory_item"], name="recipes_reci_inv_item_idx"
            ),
        ),
        migrations.AddConstraint(
            model_name="recipeitem",
            constraint=models.UniqueConstraint(
                fields=["recipe", "inventory_item"],
                name="unique_ingredient_per_recipe",
            ),
        ),
        # ─────────────────────────────────────────────────────────────────────
        # ConsumptionBatch
        # ─────────────────────────────────────────────────────────────────────
        migrations.CreateModel(
            name="ConsumptionBatch",
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
                    "idempotency_key",
                    models.CharField(db_index=True, max_length=100, unique=True),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("PENDING", "Pending"),
                            ("PROCESSING", "Processing"),
                            ("COMPLETED", "Completed"),
                            ("FAILED", "Failed"),
                            ("REVERSED", "Reversed"),
                        ],
                        db_index=True,
                        default="PENDING",
                        max_length=12,
                    ),
                ),
                (
                    "triggered_at",
                    models.DateTimeField(default=django.utils.timezone.now),
                ),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("failure_reason", models.TextField(blank=True)),
                (
                    "trigger",
                    models.CharField(default="KITCHEN_COMPLETED", max_length=25),
                ),
                (
                    "branch",
                    models.ForeignKey(
                        db_index=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="consumption_batches",
                        to="organizations.branch",
                    ),
                ),
                (
                    "order",
                    models.ForeignKey(
                        blank=True,
                        db_index=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="consumption_batches",
                        to="orders.order",
                    ),
                ),
                (
                    "triggered_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="triggered_consumption_batches",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Consumption Batch",
                "verbose_name_plural": "Consumption Batches",
                "ordering": ["-triggered_at"],
            },
        ),
        migrations.AddIndex(
            model_name="consumptionbatch",
            index=models.Index(
                fields=["order", "status"], name="recipes_cons_order_status_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="consumptionbatch",
            index=models.Index(
                fields=["branch", "status"], name="recipes_cons_branch_status_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="consumptionbatch",
            index=models.Index(
                fields=["triggered_at"], name="recipes_cons_trig_at_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="consumptionbatch",
            index=models.Index(
                fields=["idempotency_key"], name="recipes_cons_idempotency_idx"
            ),
        ),
        # ─────────────────────────────────────────────────────────────────────
        # StockConsumption
        # ─────────────────────────────────────────────────────────────────────
        migrations.CreateModel(
            name="StockConsumption",
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
                    "recipe_version",
                    models.PositiveIntegerField(blank=True, null=True),
                ),
                (
                    "quantity",
                    models.DecimalField(decimal_places=3, max_digits=14),
                ),
                ("unit", models.CharField(max_length=15)),
                (
                    "unit_cost",
                    models.DecimalField(
                        decimal_places=2, default="0.00", max_digits=14
                    ),
                ),
                (
                    "total_cost",
                    models.DecimalField(
                        decimal_places=2, default="0.00", max_digits=16
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("PENDING", "Pending"),
                            ("CONSUMED", "Consumed"),
                            ("FAILED", "Failed"),
                            ("REVERSED", "Reversed"),
                        ],
                        db_index=True,
                        default="PENDING",
                        max_length=12,
                    ),
                ),
                ("consumed_at", models.DateTimeField(blank=True, null=True)),
                (
                    "reference_type",
                    models.CharField(blank=True, db_index=True, max_length=30),
                ),
                (
                    "reference_id",
                    models.UUIDField(blank=True, db_index=True, null=True),
                ),
                (
                    "batch",
                    models.ForeignKey(
                        db_index=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="consumptions",
                        to="recipes.consumptionbatch",
                    ),
                ),
                (
                    "branch",
                    models.ForeignKey(
                        db_index=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="stock_consumptions",
                        to="organizations.branch",
                    ),
                ),
                (
                    "consumed_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="stock_consumptions",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "inventory_item",
                    models.ForeignKey(
                        db_index=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="stock_consumptions",
                        to="inventory.inventoryitem",
                    ),
                ),
                (
                    "order",
                    models.ForeignKey(
                        blank=True,
                        db_index=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="stock_consumptions",
                        to="orders.order",
                    ),
                ),
                (
                    "order_item",
                    models.ForeignKey(
                        blank=True,
                        db_index=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="stock_consumptions",
                        to="orders.orderitem",
                    ),
                ),
                (
                    "recipe",
                    models.ForeignKey(
                        blank=True,
                        db_index=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="stock_consumptions",
                        to="recipes.recipe",
                    ),
                ),
                (
                    "restaurant",
                    models.ForeignKey(
                        db_index=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="stock_consumptions",
                        to="organizations.restaurant",
                    ),
                ),
                (
                    "stock_movement",
                    models.OneToOneField(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="stock_consumption",
                        to="inventory.stockmovement",
                    ),
                ),
                (
                    "storage_location",
                    models.ForeignKey(
                        db_index=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="stock_consumptions",
                        to="inventory.storagelocation",
                    ),
                ),
            ],
            options={
                "verbose_name": "Stock Consumption",
                "verbose_name_plural": "Stock Consumptions",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="stockconsumption",
            index=models.Index(
                fields=["order", "status"], name="recipes_sc_order_status_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="stockconsumption",
            index=models.Index(
                fields=["order_item"], name="recipes_sc_order_item_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="stockconsumption",
            index=models.Index(
                fields=["batch"], name="recipes_sc_batch_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="stockconsumption",
            index=models.Index(
                fields=["inventory_item", "created_at"],
                name="recipes_sc_inv_item_created_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="stockconsumption",
            index=models.Index(
                fields=["branch", "created_at"],
                name="recipes_sc_branch_created_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="stockconsumption",
            index=models.Index(
                fields=["reference_type", "reference_id"],
                name="recipes_sc_ref_type_id_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="stockconsumption",
            index=models.Index(
                fields=["created_at"], name="recipes_sc_created_idx"
            ),
        ),
    ]
