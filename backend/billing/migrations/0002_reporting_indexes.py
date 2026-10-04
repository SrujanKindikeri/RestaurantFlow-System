# =============================================================================
# RestaurantFlow — Billing Reporting Indexes
# Phase 14: Add indexes for reporting query performance
# =============================================================================

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("billing", "0001_initial"),
    ]

    operations = [
        # finalized_at is the primary timestamp used by all sales reports
        migrations.AddIndex(
            model_name="bill",
            index=models.Index(
                fields=["branch", "status", "finalized_at"],
                name="bill_branch_status_finalized_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="bill",
            index=models.Index(
                fields=["finalized_at"],
                name="bill_finalized_at_idx",
            ),
        ),
        # BillItem → menu_item aggregation
        migrations.AddIndex(
            model_name="billitem",
            index=models.Index(
                fields=["bill", "menu_item"],
                name="billitem_bill_menuitem_idx",
            ),
        ),
    ]
