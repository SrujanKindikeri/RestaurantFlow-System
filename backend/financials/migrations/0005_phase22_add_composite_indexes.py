# =============================================================================
# RestaurantFlow — Financials Composite Index
# Phase 22: Performance, Caching & Scalability Engineering
#
# Adds composite index on Expense(branch, status, expense_date).
#
# Uses SeparateDatabaseAndState with CREATE INDEX CONCURRENTLY so that the
# index builds without holding an exclusive table lock in production.
# =============================================================================

from django.db import migrations, models


class Migration(migrations.Migration):

    atomic = False  # required for CONCURRENTLY

    dependencies = [
        ('financials', '0004_remove_expense_expense_branch_status_date_idx_and_more'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql=(
                        "CREATE INDEX CONCURRENTLY IF NOT EXISTS "
                        "expense_branch_status_date "
                        "ON financials_expense (branch_id, status, expense_date);"
                    ),
                    reverse_sql=(
                        "DROP INDEX CONCURRENTLY IF EXISTS expense_branch_status_date;"
                    ),
                ),
            ],
            state_operations=[
                migrations.AddIndex(
                    model_name='expense',
                    index=models.Index(
                        fields=['branch', 'status', 'expense_date'],
                        name='expense_branch_status_date',
                    ),
                ),
            ],
        ),
    ]
