# =============================================================================
# RestaurantFlow — Enterprise Performance Indexes
# Phase 22: Performance, Caching & Scalability Engineering
#
# Adds composite indexes that were missing from 0001_initial to accelerate
# high-traffic enterprise queries.
#
# Uses SeparateDatabaseAndState with CREATE INDEX CONCURRENTLY so that the
# index builds without holding an exclusive table lock in production.
#
# All indexes added are verified as non-duplicate by reviewing 0001_initial.py.
# Corresponding entries are declared in MenuRollout.Meta.indexes and
# StaffBranchAssignment.Meta.indexes so that makemigrations --check stays clean.
#
# 0001 already has:
#   MenuRollout: (restaurant, status), (restaurant, menu_item, status),
#                (status, effective_from)
#   StaffBranchAssignment: (user, restaurant, is_active), (branch, is_active),
#                           (restaurant, is_active), (user, is_primary, is_active)
# =============================================================================

from django.db import migrations, models


class Migration(migrations.Migration):

    atomic = False  # required for CONCURRENTLY

    dependencies = [
        ("enterprise", "0001_initial"),
    ]

    operations = [
        # ----------------------------------------------------------------
        # MenuRollout — (restaurant, status, created_at)
        # Supports: "get recent rollouts by status for a restaurant"
        # 0001 has (restaurant, status) but not + created_at
        # ----------------------------------------------------------------
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql=(
                        "CREATE INDEX CONCURRENTLY IF NOT EXISTS "
                        "ent_rollout_rest_stat_crtd_idx "
                        "ON enterprise_menurollout (restaurant_id, status, created_at);"
                    ),
                    reverse_sql=(
                        "DROP INDEX CONCURRENTLY IF EXISTS ent_rollout_rest_stat_crtd_idx;"
                    ),
                ),
            ],
            state_operations=[
                migrations.AddIndex(
                    model_name="menurollout",
                    index=models.Index(
                        fields=["restaurant", "status", "created_at"],
                        name="ent_rollout_rest_stat_crtd_idx",
                    ),
                ),
            ],
        ),

        # ----------------------------------------------------------------
        # StaffBranchAssignment — (user, branch, is_active)
        # Supports: "is this user actively assigned to this specific branch?"
        # 0001 has (user, restaurant, is_active) but not + branch directly
        # ----------------------------------------------------------------
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql=(
                        "CREATE INDEX CONCURRENTLY IF NOT EXISTS "
                        "ent_staffassign_usr_br_act_idx "
                        "ON enterprise_staffbranchassignment (user_id, branch_id, is_active);"
                    ),
                    reverse_sql=(
                        "DROP INDEX CONCURRENTLY IF EXISTS ent_staffassign_usr_br_act_idx;"
                    ),
                ),
            ],
            state_operations=[
                migrations.AddIndex(
                    model_name="staffbranchassignment",
                    index=models.Index(
                        fields=["user", "branch", "is_active"],
                        name="ent_staffassign_usr_br_act_idx",
                    ),
                ),
            ],
        ),
    ]
