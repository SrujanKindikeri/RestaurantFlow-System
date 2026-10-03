# =============================================================================
# RestaurantFlow — Seed Phase 6 Order/Table Permissions + Demo Tables
#
# Usage:
#   python manage.py seed_order_data
#   python manage.py seed_order_data --branch <code>
#   python manage.py seed_order_data --permissions-only
#
# Creates:
#   - Phase 6 permission records (table.*, order.*)
#   - Assigns permissions to system roles
#   - Demo dining tables (T01–T05) split across Indoor / Outdoor sections
#     (only if branches exist and --permissions-only is NOT set)
#
# Safe to run multiple times (get_or_create / update_or_create throughout).
# Does NOT touch Phase 1–5 data.
# Demo data is clearly marked — do NOT use in production without review.
# =============================================================================

import logging
from django.core.management.base import BaseCommand

logger = logging.getLogger("orders")


# ---------------------------------------------------------------------------
# Permission definitions
# ---------------------------------------------------------------------------

ORDER_PERMISSIONS = [
    # Tables
    ("table.view",           "View Dining Tables",             "table",   "view"),
    ("table.create",         "Create Dining Tables",           "table",   "create"),
    ("table.update",         "Update Dining Tables",           "table",   "update"),
    ("table.disable",        "Disable Dining Tables",          "table",   "disable"),
    # Table sessions
    ("table.session.view",   "View Table Sessions",            "table",   "session.view"),
    ("table.session.open",   "Open Table Sessions",            "table",   "session.open"),
    ("table.session.close",  "Close Table Sessions",           "table",   "session.close"),
    # Order — viewing
    ("order.view.own",       "View Own Orders",                "order",   "view.own"),
    ("order.view.branch",    "View Branch Orders",             "order",   "view.branch"),
    # Order — creation by type
    ("order.create.dine_in",  "Create Dine-In Orders",         "order",   "create.dine_in"),
    ("order.create.counter",  "Create Counter Orders",         "order",   "create.counter"),
    ("order.create.takeaway", "Create Takeaway Orders",        "order",   "create.takeaway"),
    # Order — lifecycle
    ("order.update",          "Update Draft Orders",           "order",   "update"),
    ("order.confirm",         "Confirm Orders",                "order",   "confirm"),
    ("order.cancel",          "Cancel Draft Orders",           "order",   "cancel"),
    ("order.cancel.confirmed","Cancel Confirmed Orders",       "order",   "cancel.confirmed"),
    # Order items
    ("order.item.add",        "Add Order Items",               "order",   "item.add"),
    ("order.item.update",     "Update Order Items",            "order",   "item.update"),
    ("order.item.remove",     "Remove Order Items",            "order",   "item.remove"),
    # Waiter assignment
    ("order.reassign_waiter", "Reassign Waiter on Order",      "order",   "reassign_waiter"),
]

# Permissions per system role
ROLE_PERMISSIONS = {
    "COMPANY_HEAD": [p[0] for p in ORDER_PERMISSIONS],
    "CENTRAL_ADMIN": [p[0] for p in ORDER_PERMISSIONS],
    "RESTAURANT_OWNER": [p[0] for p in ORDER_PERMISSIONS],
    "RESTAURANT_MANAGER": [
        "table.view", "table.create", "table.update", "table.disable",
        "table.session.view", "table.session.open", "table.session.close",
        "order.view.branch",
        "order.create.dine_in", "order.create.counter", "order.create.takeaway",
        "order.update", "order.confirm",
        "order.cancel", "order.cancel.confirmed",
        "order.item.add", "order.item.update", "order.item.remove",
        "order.reassign_waiter",
    ],
    "CASHIER": [
        "table.view",
        "table.session.view",
        "order.view.own",
        "order.create.counter", "order.create.takeaway",
        "order.update", "order.confirm",
        "order.cancel",
        "order.item.add", "order.item.update", "order.item.remove",
    ],
    "WAITER": [
        "table.view",
        "table.session.view", "table.session.open", "table.session.close",
        "order.view.own",
        "order.create.dine_in",
        "order.update", "order.confirm",
        "order.cancel",
        "order.item.add", "order.item.update", "order.item.remove",
    ],
    "KITCHEN_STAFF": [
        "order.view.branch",
    ],
    "INVENTORY_STAFF": [],
    "ACCOUNTANT": [
        "order.view.branch",
        "table.view",
    ],
}

# Demo tables per section
DEMO_TABLES = [
    # (table_number, name,             capacity, section,  display_order)
    ("T01", "Table 01",          2,  "Indoor",   1),
    ("T02", "Table 02",          4,  "Indoor",   2),
    ("T03", "Table 03",          4,  "Indoor",   3),
    ("T04", "Family Table",      6,  "Indoor",   4),
    ("T05", "Large Table",       8,  "Indoor",   5),
    ("T06", "Outdoor Table 01",  2,  "Outdoor",  6),
    ("T07", "Outdoor Table 02",  4,  "Outdoor",  7),
    ("T08", "Terrace Table 01",  4,  "Terrace",  8),
]


class Command(BaseCommand):
    help = "Seed Phase 6 order/table permissions and optional demo tables"

    def add_arguments(self, parser):
        parser.add_argument(
            "--branch",
            type=str,
            default=None,
            help="Branch code to seed demo tables for (default: all branches)",
        )
        parser.add_argument(
            "--permissions-only",
            action="store_true",
            default=False,
            help="Only seed permissions; skip demo table creation",
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING("=== Phase 6 Orders Seed ==="))

        self._seed_permissions()

        if not options["permissions_only"]:
            branch_code = options.get("branch")
            self._seed_demo_tables(branch_code)

        self.stdout.write(self.style.SUCCESS("Phase 6 seed complete."))

    # -------------------------------------------------------------------------
    # Permissions
    # -------------------------------------------------------------------------

    def _seed_permissions(self):
        from accounts.models import Permission, Role

        self.stdout.write("  Seeding Phase 6 permissions...")
        created_count = 0

        for code, name, module, action in ORDER_PERMISSIONS:
            _, created = Permission.objects.get_or_create(
                code=code,
                defaults={
                    "name": name,
                    "module": module,
                    "action": action,
                    "is_active": True,
                },
            )
            if created:
                created_count += 1

        self.stdout.write(
            f"    {created_count} new permissions created "
            f"({len(ORDER_PERMISSIONS) - created_count} already existed)."
        )

        self.stdout.write("  Assigning permissions to roles...")
        for role_code, perm_codes in ROLE_PERMISSIONS.items():
            try:
                role = Role.objects.get(code=role_code)
            except Role.DoesNotExist:
                self.stdout.write(
                    self.style.WARNING(f"    Role '{role_code}' not found — skipping.")
                )
                continue

            perms = Permission.objects.filter(code__in=perm_codes)
            role.permissions.add(*perms)
            self.stdout.write(
                f"    {role_code}: +{perms.count()} order/table permissions assigned."
            )

    # -------------------------------------------------------------------------
    # Demo tables
    # -------------------------------------------------------------------------

    def _seed_demo_tables(self, branch_code=None):
        from organizations.models import Branch
        from orders.models import DiningTable, TableStatus

        qs = Branch.objects.filter(is_active=True).select_related(
            "restaurant__organization"
        )
        if branch_code:
            qs = qs.filter(code__iexact=branch_code)

        if not qs.exists():
            self.stdout.write(
                self.style.WARNING(
                    "  No active branches found — skipping demo table creation."
                )
            )
            return

        for branch in qs:
            self.stdout.write(
                f"  Seeding demo tables for branch: {branch.name} ({branch.code})"
            )
            created_count = 0

            for table_number, name, capacity, section, display_order in DEMO_TABLES:
                _, created = DiningTable.objects.get_or_create(
                    branch=branch,
                    table_number=table_number,
                    defaults={
                        "name": name,
                        "capacity": capacity,
                        "section": section,
                        "display_order": display_order,
                        "status": TableStatus.ACTIVE,
                    },
                )
                if created:
                    created_count += 1

            self.stdout.write(
                f"    {created_count} new demo tables created "
                f"({len(DEMO_TABLES) - created_count} already existed)."
            )

        self.stdout.write(
            self.style.WARNING(
                "  NOTE: Demo tables are for development only. "
                "Review before using in production."
            )
        )
