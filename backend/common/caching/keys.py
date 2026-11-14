import hashlib
import json

PREFIX = "restaurantflow"

def make_params_hash(*args, **kwargs) -> str:
    """Create a short hash from query parameters for cache key uniqueness."""
    payload = json.dumps((list(args), kwargs), sort_keys=True, default=str)
    return hashlib.md5(payload.encode()).hexdigest()[:12]

def menu_catalog_key(branch_id, params_hash="") -> str:
    return f"{PREFIX}:branch:{branch_id}:menu_catalog:{params_hash}"

def branch_config_key(branch_id, key="") -> str:
    return f"{PREFIX}:branch:{branch_id}:config:{key}"

def user_permissions_key(user_id, branch_id="") -> str:
    return f"{PREFIX}:user:{user_id}:branch:{branch_id}:permissions"

def dashboard_kpi_key(user_id, restaurant_id, branch_id, date_str="") -> str:
    return f"{PREFIX}:user:{user_id}:restaurant:{restaurant_id}:branch:{branch_id}:dashboard_kpi:{date_str}"

def reporting_key(report_type, scope_hash, date_from, date_to) -> str:
    return f"{PREFIX}:report:{report_type}:{scope_hash}:{date_from}:{date_to}"

def inventory_availability_key(branch_id, item_id) -> str:
    return f"{PREFIX}:branch:{branch_id}:inventory:{item_id}"
