# =============================================================================
# RestaurantFlow — Notifications Performance Indexes
# Phase 22: Performance, Caching & Scalability Engineering
#
# Adds composite indexes that were missing from 0001_initial to accelerate
# high-traffic notification queries.
#
# All indexes added are verified as non-duplicate by reviewing 0001_initial.py.
# =============================================================================

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("notifications", "0001_initial"),
    ]

    operations = [
        # ----------------------------------------------------------------
        # Notification — composite index on (company, notification_type, created_at)
        # Supports: "get latest N notifications of type X for company Y"
        # Not a duplicate: 0001 has (company, notification_type) but not + created_at
        # ----------------------------------------------------------------
        migrations.AddIndex(
            model_name="notification",
            index=models.Index(
                fields=["company", "notification_type", "created_at"],
                name="notif_company_type_created_idx",
            ),
        ),

        # ----------------------------------------------------------------
        # Notification — composite index on (restaurant, status, created_at)
        # Supports: "get recent notifications by status for a restaurant"
        # Notification has severity not status; using severity field which is
        # the closest equivalent for restaurant-scoped filtering with time.
        # Using restaurant + notification_type + created_at as the meaningful
        # restaurant-scoped time-series pattern.
        # ----------------------------------------------------------------
        migrations.AddIndex(
            model_name="notification",
            index=models.Index(
                fields=["restaurant", "notification_type", "created_at"],
                name="notif_rest_type_created_idx",
            ),
        ),

        # ----------------------------------------------------------------
        # Notification — composite index on (branch, notification_type, created_at)
        # Supports: "get recent notifications of type X for branch Y"
        # Not a duplicate: 0001 has (branch, created_at) but not + notification_type
        # ----------------------------------------------------------------
        migrations.AddIndex(
            model_name="notification",
            index=models.Index(
                fields=["branch", "notification_type", "created_at"],
                name="notif_branch_type_created_idx",
            ),
        ),

        # ----------------------------------------------------------------
        # NotificationRecipient — composite index on (user, is_read, created_at)
        # Supports: "get unread notifications for user ordered by recency"
        # Note: is_read is represented as read_at IS NULL. Using (user, read_at)
        # but adding (user, delivery_status, created_at) for the status-time query.
        # Not a duplicate: 0001 has (user, delivery_status) and (user, read_at)
        # but not the three-column composite with created_at.
        # ----------------------------------------------------------------
        migrations.AddIndex(
            model_name="notificationrecipient",
            index=models.Index(
                fields=["user", "delivery_status", "created_at"],
                name="notif_recip_user_status_created_idx",
            ),
        ),
    ]
