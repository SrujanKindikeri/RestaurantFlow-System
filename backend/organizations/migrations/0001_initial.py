# =============================================================================
# RestaurantFlow — Organizations Initial Migration
# Phase 2: Organization → Restaurant → Branch hierarchy
# Generated manually (Python not available in CI path).
# =============================================================================

import uuid
import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        # =====================================================================
        # Organization
        # =====================================================================
        migrations.CreateModel(
            name="Organization",
            fields=[
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
                    "created_at",
                    models.DateTimeField(auto_now_add=True),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True),
                ),
                ("name", models.CharField(db_index=True, max_length=255)),
                ("legal_name", models.CharField(blank=True, max_length=255)),
                (
                    "slug",
                    models.SlugField(
                        db_index=True, max_length=255, unique=True
                    ),
                ),
                ("email", models.EmailField(blank=True, max_length=254)),
                ("phone", models.CharField(blank=True, max_length=30)),
                ("address", models.TextField(blank=True)),
                ("city", models.CharField(blank=True, max_length=100)),
                ("state", models.CharField(blank=True, max_length=100)),
                (
                    "country",
                    models.CharField(
                        blank=True, default="India", max_length=100
                    ),
                ),
                ("postal_code", models.CharField(blank=True, max_length=20)),
                ("tax_id", models.CharField(blank=True, max_length=100)),
                (
                    "currency",
                    models.CharField(default="INR", max_length=10),
                ),
                (
                    "timezone",
                    models.CharField(
                        default="Asia/Kolkata", max_length=50
                    ),
                ),
                (
                    "is_active",
                    models.BooleanField(db_index=True, default=True),
                ),
            ],
            options={
                "verbose_name": "Organization",
                "verbose_name_plural": "Organizations",
                "ordering": ["name"],
            },
        ),
        migrations.AddIndex(
            model_name="organization",
            index=models.Index(
                fields=["slug"], name="org_slug_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="organization",
            index=models.Index(
                fields=["is_active"], name="org_is_active_idx"
            ),
        ),
        # =====================================================================
        # Restaurant
        # =====================================================================
        migrations.CreateModel(
            name="Restaurant",
            fields=[
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
                    "created_at",
                    models.DateTimeField(auto_now_add=True),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True),
                ),
                (
                    "organization",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="restaurants",
                        to="organizations.organization",
                    ),
                ),
                ("name", models.CharField(db_index=True, max_length=255)),
                ("slug", models.SlugField(db_index=True, max_length=255)),
                ("code", models.CharField(db_index=True, max_length=50)),
                ("description", models.TextField(blank=True)),
                ("email", models.EmailField(blank=True, max_length=254)),
                ("phone", models.CharField(blank=True, max_length=30)),
                ("address", models.TextField(blank=True)),
                ("city", models.CharField(blank=True, max_length=100)),
                ("state", models.CharField(blank=True, max_length=100)),
                ("country", models.CharField(blank=True, max_length=100)),
                ("postal_code", models.CharField(blank=True, max_length=20)),
                (
                    "is_active",
                    models.BooleanField(db_index=True, default=True),
                ),
            ],
            options={
                "verbose_name": "Restaurant",
                "verbose_name_plural": "Restaurants",
                "ordering": ["name"],
            },
        ),
        migrations.AddConstraint(
            model_name="restaurant",
            constraint=models.UniqueConstraint(
                fields=["organization", "code"],
                name="unique_restaurant_code_per_org",
            ),
        ),
        migrations.AddConstraint(
            model_name="restaurant",
            constraint=models.UniqueConstraint(
                fields=["organization", "slug"],
                name="unique_restaurant_slug_per_org",
            ),
        ),
        migrations.AddIndex(
            model_name="restaurant",
            index=models.Index(
                fields=["organization", "is_active"],
                name="rest_org_active_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="restaurant",
            index=models.Index(
                fields=["organization", "code"],
                name="rest_org_code_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="restaurant",
            index=models.Index(
                fields=["organization", "slug"],
                name="rest_org_slug_idx",
            ),
        ),
        # =====================================================================
        # Branch
        # =====================================================================
        migrations.CreateModel(
            name="Branch",
            fields=[
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
                    "created_at",
                    models.DateTimeField(auto_now_add=True),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True),
                ),
                (
                    "restaurant",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="branches",
                        to="organizations.restaurant",
                    ),
                ),
                ("name", models.CharField(db_index=True, max_length=255)),
                ("code", models.CharField(db_index=True, max_length=50)),
                ("address", models.TextField(blank=True)),
                ("city", models.CharField(blank=True, max_length=100)),
                ("state", models.CharField(blank=True, max_length=100)),
                ("country", models.CharField(blank=True, max_length=100)),
                ("postal_code", models.CharField(blank=True, max_length=20)),
                ("phone", models.CharField(blank=True, max_length=30)),
                ("email", models.EmailField(blank=True, max_length=254)),
                (
                    "latitude",
                    models.DecimalField(
                        blank=True,
                        decimal_places=6,
                        max_digits=9,
                        null=True,
                    ),
                ),
                (
                    "longitude",
                    models.DecimalField(
                        blank=True,
                        decimal_places=6,
                        max_digits=9,
                        null=True,
                    ),
                ),
                (
                    "is_active",
                    models.BooleanField(db_index=True, default=True),
                ),
            ],
            options={
                "verbose_name": "Branch",
                "verbose_name_plural": "Branches",
                "ordering": ["name"],
            },
        ),
        migrations.AddConstraint(
            model_name="branch",
            constraint=models.UniqueConstraint(
                fields=["restaurant", "code"],
                name="unique_branch_code_per_restaurant",
            ),
        ),
        migrations.AddIndex(
            model_name="branch",
            index=models.Index(
                fields=["restaurant", "is_active"],
                name="branch_rest_active_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="branch",
            index=models.Index(
                fields=["restaurant", "code"],
                name="branch_rest_code_idx",
            ),
        ),
        # =====================================================================
        # RestaurantSettings
        # =====================================================================
        migrations.CreateModel(
            name="RestaurantSettings",
            fields=[
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
                    "created_at",
                    models.DateTimeField(auto_now_add=True),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True),
                ),
                (
                    "restaurant",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="settings",
                        to="organizations.restaurant",
                    ),
                ),
                ("currency", models.CharField(blank=True, default="", max_length=10)),
                ("timezone", models.CharField(blank=True, default="", max_length=50)),
                ("tax_enabled", models.BooleanField(default=True)),
                (
                    "default_tax_rate",
                    models.DecimalField(
                        decimal_places=2, default=0.0, max_digits=5
                    ),
                ),
                ("receipt_header", models.TextField(blank=True)),
                ("receipt_footer", models.TextField(blank=True)),
                ("allow_negative_stock", models.BooleanField(default=False)),
                (
                    "order_prefix",
                    models.CharField(default="ORD", max_length=20),
                ),
                ("is_active", models.BooleanField(default=True)),
            ],
            options={
                "verbose_name": "Restaurant Settings",
                "verbose_name_plural": "Restaurant Settings",
            },
        ),
        # =====================================================================
        # BranchSettings
        # =====================================================================
        migrations.CreateModel(
            name="BranchSettings",
            fields=[
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
                    "created_at",
                    models.DateTimeField(auto_now_add=True),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True),
                ),
                (
                    "branch",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="settings",
                        to="organizations.branch",
                    ),
                ),
                ("opening_time", models.TimeField(blank=True, null=True)),
                ("closing_time", models.TimeField(blank=True, null=True)),
                (
                    "default_order_type",
                    models.CharField(
                        choices=[
                            ("dine_in", "Dine In"),
                            ("takeaway", "Takeaway"),
                            ("delivery", "Delivery"),
                        ],
                        default="dine_in",
                        max_length=20,
                    ),
                ),
                ("receipt_footer", models.TextField(blank=True)),
                ("is_active", models.BooleanField(default=True)),
            ],
            options={
                "verbose_name": "Branch Settings",
                "verbose_name_plural": "Branch Settings",
            },
        ),
    ]
