# =============================================================================
# RestaurantFlow — Financials Reporting Indexes
# Phase 14
# =============================================================================

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("financials", "0002_expensecategory_expense_account"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="expense",
            index=models.Index(
                fields=["branch", "status", "expense_date"],
                name="expense_branch_status_date_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="payable",
            index=models.Index(
                fields=["branch", "status", "due_date"],
                name="payable_branch_status_due_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="payable",
            index=models.Index(
                fields=["restaurant", "status"],
                name="payable_restaurant_status_idx",
            ),
        ),
    ]
