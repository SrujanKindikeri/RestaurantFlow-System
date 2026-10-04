# =============================================================================
# RestaurantFlow — Kitchen Reporting Indexes
# Phase 14
# =============================================================================

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("kitchen", "0001_initial"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="kitchenorder",
            index=models.Index(
                fields=["branch", "status", "received_at"],
                name="ko_branch_status_received_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="kitchenorder",
            index=models.Index(
                fields=["started_at", "ready_at"],
                name="ko_started_ready_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="kitchenorderitem",
            index=models.Index(
                fields=["menu_item", "started_at", "ready_at"],
                name="koi_item_prep_times_idx",
            ),
        ),
    ]
