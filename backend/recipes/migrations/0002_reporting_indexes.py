# =============================================================================
# RestaurantFlow — Recipes Reporting Indexes
# Phase 14
# =============================================================================

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("recipes", "0001_initial"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="stockconsumption",
            index=models.Index(
                fields=["branch", "status", "consumed_at"],
                name="sc_branch_status_consumed_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="stockconsumption",
            index=models.Index(
                fields=["inventory_item", "consumed_at"],
                name="sc_item_consumed_date_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="stockconsumption",
            index=models.Index(
                fields=["order_item", "inventory_item"],
                name="sc_orderitem_item_idx",
            ),
        ),
    ]
