# =============================================================================
# RestaurantFlow — Menu Composite Index
# Phase 22: Performance, Caching & Scalability Engineering
#
# Adds composite index on MenuItem(restaurant, is_active, display_order).
#
# Uses SeparateDatabaseAndState with CREATE INDEX CONCURRENTLY so that the
# index builds without holding an exclusive table lock in production.
# =============================================================================

from django.db import migrations, models


class Migration(migrations.Migration):

    atomic = False  # required for CONCURRENTLY

    dependencies = [
        ('menu', '0003_rename_menu_catg_rest_active_idx_menu_catego_restaur_c97a7f_idx_and_more'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql=(
                        "CREATE INDEX CONCURRENTLY IF NOT EXISTS "
                        "menuitem_catalog_order "
                        "ON menu_menuitem (restaurant_id, is_active, display_order);"
                    ),
                    reverse_sql=(
                        "DROP INDEX CONCURRENTLY IF EXISTS menuitem_catalog_order;"
                    ),
                ),
            ],
            state_operations=[
                migrations.AddIndex(
                    model_name='menuitem',
                    index=models.Index(
                        fields=['restaurant', 'is_active', 'display_order'],
                        name='menuitem_catalog_order',
                    ),
                ),
            ],
        ),
    ]
