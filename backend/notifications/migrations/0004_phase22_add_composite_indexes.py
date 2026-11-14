# =============================================================================
# RestaurantFlow — Notifications Composite Index
# Phase 22: Performance, Caching & Scalability Engineering
#
# Adds composite index on Notification(company, branch, source_type,
# source_id, notification_type).
#
# Uses SeparateDatabaseAndState with CREATE INDEX CONCURRENTLY so that the
# index builds without holding an exclusive table lock in production.
# =============================================================================

from django.db import migrations, models


class Migration(migrations.Migration):

    atomic = False  # required for CONCURRENTLY

    dependencies = [
        ('notifications', '0003_remove_notification_notif_company_type_created_idx_and_more'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql=(
                        "CREATE INDEX CONCURRENTLY IF NOT EXISTS "
                        "notif_idempotency_check "
                        "ON notifications_notification "
                        "(company_id, branch_id, source_type, source_id, notification_type);"
                    ),
                    reverse_sql=(
                        "DROP INDEX CONCURRENTLY IF EXISTS notif_idempotency_check;"
                    ),
                ),
            ],
            state_operations=[
                migrations.AddIndex(
                    model_name='notification',
                    index=models.Index(
                        fields=['company', 'branch', 'source_type', 'source_id', 'notification_type'],
                        name='notif_idempotency_check',
                    ),
                ),
            ],
        ),
    ]
