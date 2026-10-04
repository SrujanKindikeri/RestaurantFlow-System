# =============================================================================
# RestaurantFlow — Orders Reporting Indexes
# Phase 14
# =============================================================================

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0001_initial"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="order",
            index=models.Index(
                fields=["branch", "order_type", "status", "created_at"],
                name="order_branch_type_status_date_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="order",
            index=models.Index(
                fields=["assigned_waiter", "created_at"],
                name="order_waiter_date_idx",
            ),
        ),
    ]
