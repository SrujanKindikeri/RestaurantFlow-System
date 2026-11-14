# =============================================================================
# RestaurantFlow — Orders Composite Index
# Phase 22: Performance, Caching & Scalability Engineering
#
# Adds composite index on Order(branch, status, created_at).
#
# Uses SeparateDatabaseAndState with CREATE INDEX CONCURRENTLY so that the
# index builds without holding an exclusive table lock in production.
# =============================================================================

from django.db import migrations, models


class Migration(migrations.Migration):

    atomic = False  # required for CONCURRENTLY

    dependencies = [
        ('orders', '0004_remove_order_order_branch_type_status_date_idx_and_more'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql=(
                        "CREATE INDEX CONCURRENTLY IF NOT EXISTS "
                        "order_branch_status_created_at "
                        "ON orders_order (branch_id, status, created_at);"
                    ),
                    reverse_sql=(
                        "DROP INDEX CONCURRENTLY IF EXISTS order_branch_status_created_at;"
                    ),
                ),
            ],
            state_operations=[
                migrations.AddIndex(
                    model_name='order',
                    index=models.Index(
                        fields=['branch', 'status', 'created_at'],
                        name='order_branch_status_created_at',
                    ),
                ),
            ],
        ),
    ]
