# =============================================================================
# RestaurantFlow — CRM Performance Indexes
# Phase 22: Performance, Caching & Scalability Engineering
#
# Adds composite indexes that were missing from 0001_initial to accelerate
# high-traffic CRM queries.
#
# Uses SeparateDatabaseAndState with CREATE INDEX CONCURRENTLY so that the
# index builds without holding an exclusive table lock in production.
#
# All indexes added are verified as non-duplicate by reviewing 0001_initial.py.
# Corresponding entries are declared in Customer.Meta.indexes and
# LoyaltyAccount.Meta.indexes so that makemigrations --check stays clean.
#
# 0001 already has:
#   Customer: (company, restaurant), (restaurant, is_active), (phone), (email),
#             (last_order_at), (last_visit_at)
#   LoyaltyAccount: unique_loyalty_account_per_program constraint
# =============================================================================

from django.db import migrations, models


class Migration(migrations.Migration):

    atomic = False  # required for CONCURRENTLY

    dependencies = [
        ("crm", "0001_initial"),
    ]

    operations = [
        # ----------------------------------------------------------------
        # Customer — (restaurant, is_active, created_at)
        # Supports: "get all active customers for restaurant X ordered by join date"
        # 0001 has (restaurant, is_active) but not + created_at
        # ----------------------------------------------------------------
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql=(
                        "CREATE INDEX CONCURRENTLY IF NOT EXISTS "
                        "crm_cust_rest_active_crtd_idx "
                        "ON crm_customer (restaurant_id, is_active, created_at);"
                    ),
                    reverse_sql=(
                        "DROP INDEX CONCURRENTLY IF EXISTS crm_cust_rest_active_crtd_idx;"
                    ),
                ),
            ],
            state_operations=[
                migrations.AddIndex(
                    model_name="customer",
                    index=models.Index(
                        fields=["restaurant", "is_active", "created_at"],
                        name="crm_cust_rest_active_crtd_idx",
                    ),
                ),
            ],
        ),

        # ----------------------------------------------------------------
        # LoyaltyAccount — (loyalty_program, points_balance)
        # Supports: "get top earners / rank accounts by points for a program"
        # 0001 has individual db_index on loyalty_program and points_balance fields
        # but not a composite index
        # ----------------------------------------------------------------
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql=(
                        "CREATE INDEX CONCURRENTLY IF NOT EXISTS "
                        "crm_loyalty_prog_balance_idx "
                        "ON crm_loyaltyaccount (loyalty_program_id, points_balance);"
                    ),
                    reverse_sql=(
                        "DROP INDEX CONCURRENTLY IF EXISTS crm_loyalty_prog_balance_idx;"
                    ),
                ),
            ],
            state_operations=[
                migrations.AddIndex(
                    model_name="loyaltyaccount",
                    index=models.Index(
                        fields=["loyalty_program", "points_balance"],
                        name="crm_loyalty_prog_balance_idx",
                    ),
                ),
            ],
        ),
    ]
