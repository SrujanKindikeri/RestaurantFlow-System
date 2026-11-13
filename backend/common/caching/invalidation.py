from django.db import transaction
from .services import CacheService
from .keys import (
    menu_catalog_key, branch_config_key, user_permissions_key,
    dashboard_kpi_key, inventory_availability_key, reporting_key
)

PREFIX = "restaurantflow"


def invalidate_menu_catalog(branch_id):
    """Invalidate all menu catalog cache keys for a branch. Best-effort: Redis failure never rolls back DB."""
    def _do():
        pattern = f"{PREFIX}:branch:{branch_id}:menu_catalog:*"
        CacheService.delete_pattern(pattern)
    transaction.on_commit(_do)


def invalidate_branch_config(branch_id, key=""):
    """Invalidate branch config cache. Best-effort."""
    def _do():
        if key:
            CacheService.delete(branch_config_key(branch_id, key))
        else:
            CacheService.delete_pattern(f"{PREFIX}:branch:{branch_id}:config:*")
    transaction.on_commit(_do)


def invalidate_user_permissions(user_id, branch_id=""):
    """Invalidate user permissions cache. Best-effort."""
    def _do():
        if branch_id:
            CacheService.delete(user_permissions_key(user_id, branch_id))
        else:
            CacheService.delete_pattern(f"{PREFIX}:user:{user_id}:branch:*:permissions")
    transaction.on_commit(_do)


def invalidate_dashboard_kpis(restaurant_id, branch_id):
    """Invalidate dashboard KPI cache for a restaurant/branch. Best-effort."""
    def _do():
        pattern = f"{PREFIX}:restaurant:{restaurant_id}:branch:{branch_id}:dashboard_kpi:*"
        CacheService.delete_pattern(pattern)
    transaction.on_commit(_do)


def invalidate_inventory_availability(branch_id, item_id):
    """Invalidate inventory availability cache. Best-effort."""
    def _do():
        CacheService.delete(inventory_availability_key(branch_id, item_id))
    transaction.on_commit(_do)


def invalidate_reporting_cache(report_type="", scope_hash=""):
    """Invalidate reporting summary cache. Best-effort."""
    def _do():
        if report_type and scope_hash:
            pattern = f"{PREFIX}:report:{report_type}:{scope_hash}:*"
        elif report_type:
            pattern = f"{PREFIX}:report:{report_type}:*"
        else:
            pattern = f"{PREFIX}:report:*"
        CacheService.delete_pattern(pattern)
    transaction.on_commit(_do)
