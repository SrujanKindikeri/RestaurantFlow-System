# =============================================================================
# RestaurantFlow — Menu Performance Indexes
# Phase 22: Performance, Caching & Scalability Engineering
#
# Adds composite indexes that were missing from 0001_initial to accelerate
# high-traffic menu catalog queries.
#
# Uses SeparateDatabaseAndState with CREATE INDEX CONCURRENTLY so that the
# index builds without holding an exclusive table lock in production.
#
# All indexes added are verified as non-duplicate by reviewing 0001_initial.py.
#
# 0001 already declares as Meta.indexes (via CreateModel options):
#   MenuItemPrice: (menu_item, branch, is_active)       — menu_price_item_active_idx
#   MenuItemPrice: (menu_item, branch, effective_from)  — menu_price_item_from_idx
#   MenuItemPrice: (branch, is_active)                  — menu_price_branch_active_idx
#   MenuItemBranch: unique_menuitem_branch_availability — covers (menu_item, branch)
#
# New indexes added here:
#   MenuItemBranch: (branch, is_available) — not covered above
# =============================================================================

from django.db import migrations, models


class Migration(migrations.Migration):

    atomic = False  # required for CONCURRENTLY

    dependencies = [
        ("menu", "0001_initial"),
    ]

    operations = [
        # ----------------------------------------------------------------
        # MenuItemBranch — composite index on (branch, is_available)
        # Supports: "get all available menu items for a branch"
        # This is the primary catalog lookup for POS and ordering flows.
        # 0001 has individual db_index on is_available but no composite index
        # with branch for efficient branch-scoped catalog queries.
        # ----------------------------------------------------------------
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql=(
                        "CREATE INDEX CONCURRENTLY IF NOT EXISTS "
                        "menu_avail_branch_available_idx "
                        "ON menu_menuitembranch (branch_id, is_available);"
                    ),
                    reverse_sql=(
                        "DROP INDEX CONCURRENTLY IF EXISTS menu_avail_branch_available_idx;"
                    ),
                ),
            ],
            state_operations=[
                migrations.AddIndex(
                    model_name="menuitembranch",
                    index=models.Index(
                        fields=["branch", "is_available"],
                        name="menu_avail_branch_available_idx",
                    ),
                ),
            ],
        ),
    ]
