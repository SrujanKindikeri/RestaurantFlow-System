# =============================================================================
# RestaurantFlow — Notifications Performance Indexes
# Phase 22: Performance, Caching & Scalability Engineering
#
# Adds composite indexes that were missing from 0001_initial to accelerate
# high-traffic notification queries.
#
# Uses SeparateDatabaseAndState with CREATE INDEX CONCURRENTLY so that the
# index builds without holding an exclusive table lock in production.
#
# All indexes added are verified as non-duplicate by reviewing 0001_initial.py.
# Corresponding entries are declared in Notification.Meta.indexes and
# NotificationRecipient.Meta.indexes so that makemigrations --check stays
# clean after this migration.
# =============================================================================

from django.db import migrations, models


class Migration(migrations.Migration):

    atomic = False  # required for CONCURRENTLY

    dependencies = [
        ("notifications", "0001_initial"),
    ]

    operations = [
        # ----------------------------------------------------------------
        # Notification — (company, notification_type, created_at)
        # Supports: "get latest N notifications of type X for company Y"
        # 0001 has (company, notification_type) but not + created_at
        # ----------------------------------------------------------------
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql=(
                        "CREATE INDEX CONCURRENTLY IF NOT EXISTS "
                        "notif_co_type_created_idx "
                        "ON notifications_notification (company_id, notification_type, created_at);"
                    ),
                    reverse_sql=(
                        "DROP INDEX CONCURRENTLY IF EXISTS notif_co_type_created_idx;"
                    ),
                ),
            ],
            state_operations=[
                migrations.AddIndex(
                    model_name="notification",
                    index=models.Index(
                        fields=["company", "notification_type", "created_at"],
                        name="notif_co_type_created_idx",
                    ),
                ),
            ],
        ),

        # ----------------------------------------------------------------
        # Notification — (restaurant, notification_type, created_at)
        # Supports: "get recent notifications of type X for a restaurant"
        # 0001 has (restaurant, created_at) but not + notification_type
        # ----------------------------------------------------------------
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql=(
                        "CREATE INDEX CONCURRENTLY IF NOT EXISTS "
                        "notif_rest_type_created_idx "
                        "ON notifications_notification (restaurant_id, notification_type, created_at);"
                    ),
                    reverse_sql=(
                        "DROP INDEX CONCURRENTLY IF EXISTS notif_rest_type_created_idx;"
                    ),
                ),
            ],
            state_operations=[
                migrations.AddIndex(
                    model_name="notification",
                    index=models.Index(
                        fields=["restaurant", "notification_type", "created_at"],
                        name="notif_rest_type_created_idx",
                    ),
                ),
            ],
        ),

        # ----------------------------------------------------------------
        # Notification — (branch, notification_type, created_at)
        # Supports: "get recent notifications of type X for branch Y"
        # 0001 has (branch, created_at) but not + notification_type
        # ----------------------------------------------------------------
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql=(
                        "CREATE INDEX CONCURRENTLY IF NOT EXISTS "
                        "notif_branch_type_created_idx "
                        "ON notifications_notification (branch_id, notification_type, created_at);"
                    ),
                    reverse_sql=(
                        "DROP INDEX CONCURRENTLY IF EXISTS notif_branch_type_created_idx;"
                    ),
                ),
            ],
            state_operations=[
                migrations.AddIndex(
                    model_name="notification",
                    index=models.Index(
                        fields=["branch", "notification_type", "created_at"],
                        name="notif_branch_type_created_idx",
                    ),
                ),
            ],
        ),

        # ----------------------------------------------------------------
        # NotificationRecipient — (user, delivery_status, created_at)
        # Supports: "get unread/pending notifications for user ordered by recency"
        # 0001 has (user, delivery_status) and (user, read_at) separately
        # but not the three-column composite with created_at.
        # ----------------------------------------------------------------
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql=(
                        "CREATE INDEX CONCURRENTLY IF NOT EXISTS "
                        "notif_recip_usr_stat_crtd_idx "
                        "ON notifications_notificationrecipient (user_id, delivery_status, created_at);"
                    ),
                    reverse_sql=(
                        "DROP INDEX CONCURRENTLY IF EXISTS notif_recip_usr_stat_crtd_idx;"
                    ),
                ),
            ],
            state_operations=[
                migrations.AddIndex(
                    model_name="notificationrecipient",
                    index=models.Index(
                        fields=["user", "delivery_status", "created_at"],
                        name="notif_recip_usr_stat_crtd_idx",
                    ),
                ),
            ],
        ),
    ]
