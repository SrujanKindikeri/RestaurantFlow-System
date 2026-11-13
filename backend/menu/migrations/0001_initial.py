# =============================================================================
# RestaurantFlow — Menu Initial Migration
# Phase 5: TaxRate, Category, MenuItem, MenuItemPrice, MenuItemBranch
#
# This migration was missing from the repository, causing a broken migration
# graph (kitchen.0001_initial depends on ('menu', '0001_initial')).
# Reconstructed from the current model definitions.
# =============================================================================

import uuid

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
from django.utils.text import slugify


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("organizations", "0001_initial"),
    ]

    operations = [
        # ---------------------------------------------------------------------
        # TaxRate
        # ---------------------------------------------------------------------
        migrations.CreateModel(
            name="TaxRate",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=150)),
                ("code", models.CharField(db_index=True, max_length=50)),
                ("rate", models.DecimalField(decimal_places=3, help_text="Tax percentage, e.g. 5.000 = 5%.", max_digits=6)),
                ("description", models.TextField(blank=True)),
                ("is_active", models.BooleanField(db_index=True, default=True)),
                ("restaurant", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="tax_rates", to="organizations.restaurant")),
            ],
            options={
                "verbose_name": "Tax Rate",
                "verbose_name_plural": "Tax Rates",
                "ordering": ["restaurant", "code"],
                "constraints": [
                    models.UniqueConstraint(fields=["restaurant", "code"], name="unique_taxrate_code_per_restaurant"),
                ],
                "indexes": [
                    models.Index(fields=["restaurant", "is_active"], name="menu_taxrate_rest_active_idx"),
                    models.Index(fields=["restaurant", "code"], name="menu_taxrate_rest_code_idx"),
                ],
            },
        ),

        # ---------------------------------------------------------------------
        # Category
        # ---------------------------------------------------------------------
        migrations.CreateModel(
            name="Category",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("name", models.CharField(db_index=True, max_length=150)),
                ("slug", models.SlugField(db_index=True, max_length=150)),
                ("description", models.TextField(blank=True)),
                ("image", models.ImageField(blank=True, null=True, upload_to="menu/categories/")),
                ("display_order", models.PositiveIntegerField(db_index=True, default=0)),
                ("is_active", models.BooleanField(db_index=True, default=True)),
                ("restaurant", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="menu_categories", to="organizations.restaurant")),
            ],
            options={
                "verbose_name": "Category",
                "verbose_name_plural": "Categories",
                "ordering": ["display_order", "name"],
                "constraints": [
                    models.UniqueConstraint(fields=["restaurant", "slug"], name="unique_category_slug_per_restaurant"),
                ],
                "indexes": [
                    models.Index(fields=["restaurant", "is_active"], name="menu_catg_rest_active_idx"),
                    models.Index(fields=["restaurant", "display_order"], name="menu_catg_rest_order_idx"),
                    models.Index(fields=["restaurant", "slug"], name="menu_catg_rest_slug_idx"),
                ],
            },
        ),

        # ---------------------------------------------------------------------
        # MenuItem
        # ---------------------------------------------------------------------
        migrations.CreateModel(
            name="MenuItem",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("name", models.CharField(db_index=True, max_length=200)),
                ("slug", models.SlugField(db_index=True, max_length=200)),
                ("sku", models.CharField(blank=True, db_index=True, max_length=100)),
                ("description", models.TextField(blank=True)),
                ("short_description", models.CharField(blank=True, max_length=300)),
                ("image", models.ImageField(blank=True, null=True, upload_to="menu/items/")),
                ("food_type", models.CharField(choices=[("VEG", "Vegetarian"), ("NON_VEG", "Non-Vegetarian"), ("EGG", "Egg"), ("VEGAN", "Vegan"), ("OTHER", "Other")], db_index=True, default="VEG", max_length=10)),
                ("display_order", models.PositiveIntegerField(db_index=True, default=0)),
                ("is_active", models.BooleanField(db_index=True, default=True)),
                ("is_available", models.BooleanField(db_index=True, default=True)),
                ("preparation_time_minutes", models.PositiveIntegerField(default=0, help_text="Estimated preparation time in minutes.")),
                ("category", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="items", to="menu.category")),
                ("restaurant", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="menu_items", to="organizations.restaurant")),
                ("tax_rate", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="menu_items", to="menu.taxrate")),
            ],
            options={
                "verbose_name": "Menu Item",
                "verbose_name_plural": "Menu Items",
                "ordering": ["category__display_order", "display_order", "name"],
                "constraints": [
                    models.UniqueConstraint(fields=["restaurant", "slug"], name="unique_menuitem_slug_per_restaurant"),
                ],
                "indexes": [
                    models.Index(fields=["restaurant", "is_active"], name="menu_item_rest_active_idx"),
                    models.Index(fields=["restaurant", "category"], name="menu_item_rest_catg_idx"),
                    models.Index(fields=["restaurant", "food_type"], name="menu_item_rest_food_idx"),
                    models.Index(fields=["restaurant", "slug"], name="menu_item_rest_slug_idx"),
                    models.Index(fields=["restaurant", "sku"], name="menu_item_rest_sku_idx"),
                ],
            },
        ),

        # ---------------------------------------------------------------------
        # MenuItemPrice
        # ---------------------------------------------------------------------
        migrations.CreateModel(
            name="MenuItemPrice",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("price", models.DecimalField(decimal_places=2, help_text="Selling price in restaurant's currency. Must be >= 0.", max_digits=12)),
                ("effective_from", models.DateTimeField(blank=True, db_index=True, help_text="When this price record becomes effective (inclusive).", null=True)),
                ("effective_to", models.DateTimeField(blank=True, db_index=True, help_text="When this price record expires (exclusive). NULL = still active.", null=True)),
                ("is_active", models.BooleanField(db_index=True, default=True, help_text="Is this the currently active price for this item+branch?")),
                ("branch", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="menu_item_prices", to="organizations.branch")),
                ("menu_item", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="prices", to="menu.menuitem")),
            ],
            options={
                "verbose_name": "Menu Item Price",
                "verbose_name_plural": "Menu Item Prices",
                "ordering": ["-effective_from", "-created_at"],
                "indexes": [
                    models.Index(fields=["menu_item", "branch", "is_active"], name="menu_price_item_active_idx"),
                    models.Index(fields=["menu_item", "branch", "effective_from"], name="menu_price_item_from_idx"),
                    models.Index(fields=["branch", "is_active"], name="menu_price_branch_active_idx"),
                ],
            },
        ),

        # ---------------------------------------------------------------------
        # MenuItemBranch
        # ---------------------------------------------------------------------
        migrations.CreateModel(
            name="MenuItemBranch",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("is_available", models.BooleanField(db_index=True, default=True, help_text="Is this item currently available at this branch?")),
                ("available_from", models.TimeField(blank=True, help_text="Start of daily availability window (restaurant timezone). NULL = all day.", null=True)),
                ("available_to", models.TimeField(blank=True, help_text="End of daily availability window (restaurant timezone). NULL = all day.", null=True)),
                ("branch", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="menu_item_availability", to="organizations.branch")),
                ("menu_item", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="branch_availability", to="menu.menuitem")),
            ],
            options={
                "verbose_name": "Menu Item Branch Availability",
                "verbose_name_plural": "Menu Item Branch Availabilities",
                "ordering": ["menu_item", "branch"],
                "constraints": [
                    models.UniqueConstraint(fields=["menu_item", "branch"], name="unique_menuitem_branch_availability"),
                ],
            },
        ),
    ]
