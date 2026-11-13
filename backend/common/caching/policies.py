import random

# TTL constants (seconds)
MENU_CATALOG_TTL = 300          # 5 min
BRANCH_CONFIG_TTL = 600         # 10 min
USER_PERMISSIONS_TTL = 300      # 5 min
DASHBOARD_KPI_TTL = 120         # 2 min
REPORTING_SUMMARY_TTL = 300     # 5 min
INVENTORY_AVAILABILITY_TTL = 60 # 1 min

# Never cache payments or accounting balances as authoritative state
PAYMENTS_NO_CACHE = True
ACCOUNTING_NO_CACHE = True

JITTER_FACTOR = 0.15

def add_jitter(ttl: int) -> int:
    """Add ±15% random jitter to prevent cache stampede on simultaneous expiry."""
    jitter = int(ttl * JITTER_FACTOR)
    return ttl + random.randint(-jitter, jitter)
