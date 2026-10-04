# =============================================================================
# RestaurantFlow — Financials Migration 0002
# Phase 13: Add expense_account FK to ExpenseCategory
# =============================================================================

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounting", "0001_initial"),
        ("financials", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="expensecategory",
            name="expense_account",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="expense_categories",
                to="accounting.account",
                help_text=(
                    "The accounting expense account to debit when expenses "
                    "in this category are approved. "
                    "Must be an EXPENSE-type account from the same restaurant."
                ),
            ),
        ),
    ]
