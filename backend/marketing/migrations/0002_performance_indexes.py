# =============================================================================
# RestaurantFlow — Marketing Performance Indexes
# Phase 22: Performance, Caching & Scalability Engineering
#
# Adds composite indexes that were missing from 0001_initial to accelerate
# high-traffic marketing campaign queries.
#
# Uses SeparateDatabaseAndState with CREATE INDEX CONCURRENTLY so that the
# index builds without holding an exclusive table lock in production.
#
# All indexes added are verified as non-duplicate by reviewing 0001_initial.py.
# Corresponding entries are declared in MarketingCampaign.Meta.indexes so that
# makemigrations --check stays clean.
#
# 0001 already has:
#   MarketingCampaign: (company, status), (restaurant, status),
#                      (status, start_at), (status, end_at)
# =============================================================================

from django.db import migrations, models


class Migration(migrations.Migration):

    atomic = False  # required for CONCURRENTLY

    dependencies = [
        ("marketing", "0001_initial"),
    ]

    operations = [
        # ----------------------------------------------------------------
        # MarketingCampaign — (restaurant, status, start_at)
        # Supports: "get running/scheduled campaigns for restaurant ordered by start"
        # 0001 has (restaurant, status) and (status, start_at) separately
        # but not the three-column composite for efficient restaurant + window queries
        # ----------------------------------------------------------------
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql=(
                        "CREATE INDEX CONCURRENTLY IF NOT EXISTS "
                        "mktg_camp_rest_stat_start_idx "
                        "ON marketing_marketingcampaign (restaurant_id, status, start_at);"
                    ),
                    reverse_sql=(
                        "DROP INDEX CONCURRENTLY IF EXISTS mktg_camp_rest_stat_start_idx;"
                    ),
                ),
            ],
            state_operations=[
                migrations.AddIndex(
                    model_name="marketingcampaign",
                    index=models.Index(
                        fields=["restaurant", "status", "start_at"],
                        name="mktg_camp_rest_stat_start_idx",
                    ),
                ),
            ],
        ),

        # ----------------------------------------------------------------
        # MarketingCampaign — (restaurant, status, end_at)
        # Supports: "find expiring campaigns for a restaurant"
        # Complements the start_at index above for time-window queries
        # ----------------------------------------------------------------
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql=(
                        "CREATE INDEX CONCURRENTLY IF NOT EXISTS "
                        "mktg_camp_rest_stat_end_idx "
                        "ON marketing_marketingcampaign (restaurant_id, status, end_at);"
                    ),
                    reverse_sql=(
                        "DROP INDEX CONCURRENTLY IF EXISTS mktg_camp_rest_stat_end_idx;"
                    ),
                ),
            ],
            state_operations=[
                migrations.AddIndex(
                    model_name="marketingcampaign",
                    index=models.Index(
                        fields=["restaurant", "status", "end_at"],
                        name="mktg_camp_rest_stat_end_idx",
                    ),
                ),
            ],
        ),
    ]
