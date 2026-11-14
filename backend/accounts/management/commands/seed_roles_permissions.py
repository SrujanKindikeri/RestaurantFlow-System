# =============================================================================
# RestaurantFlow — Seed Roles and Permissions Management Command
#
# Usage:
#   python manage.py seed_roles_permissions
#
# Idempotent — safe to run repeatedly. Creates missing roles/permissions and
# updates existing ones. Does NOT delete anything.
#
# This command seeds only the authorization schema (Roles + Permissions +
# Role-Permission mappings). It does NOT create users or demo data.
# Use seed_demo_data for a complete development dataset.
# =============================================================================

import logging
from django.core.management.base import BaseCommand
from django.db import transaction

from accounts.models import Permission, Role

logger = logging.getLogger("accounts")

# ---------------------------------------------------------------------------
# Permission definitions — single source of truth for all permission codes
# ---------------------------------------------------------------------------

PERMISSIONS = [
    # Organization
    {"code": "organization.view",    "name": "View Organization",    "module": "organization", "action": "view"},
    {"code": "organization.create",  "name": "Create Organization",  "module": "organization", "action": "create"},
    {"code": "organization.update",  "name": "Update Organization",  "module": "organization", "action": "update"},
    {"code": "organization.disable", "name": "Disable Organization", "module": "organization", "action": "disable"},
    # Restaurant
    {"code": "restaurant.view",    "name": "View Restaurant",    "module": "restaurant", "action": "view"},
    {"code": "restaurant.create",  "name": "Create Restaurant",  "module": "restaurant", "action": "create"},
    {"code": "restaurant.update",  "name": "Update Restaurant",  "module": "restaurant", "action": "update"},
    {"code": "restaurant.disable", "name": "Disable Restaurant", "module": "restaurant", "action": "disable"},
    # Branch
    {"code": "branch.view",    "name": "View Branch",    "module": "branch", "action": "view"},
    {"code": "branch.create",  "name": "Create Branch",  "module": "branch", "action": "create"},
    {"code": "branch.update",  "name": "Update Branch",  "module": "branch", "action": "update"},
    {"code": "branch.disable", "name": "Disable Branch", "module": "branch", "action": "disable"},
    # User management
    {"code": "user.view",    "name": "View User",    "module": "user", "action": "view"},
    {"code": "user.create",  "name": "Create User",  "module": "user", "action": "create"},
    {"code": "user.update",  "name": "Update User",  "module": "user", "action": "update"},
    {"code": "user.disable", "name": "Disable User", "module": "user", "action": "disable"},
    # Role + Permission management
    {"code": "role.view",         "name": "View Roles",             "module": "role", "action": "view"},
    {"code": "role.manage",       "name": "Manage Role Assignments", "module": "role", "action": "manage"},
    {"code": "permission.view",   "name": "View Permissions",       "module": "permission", "action": "view"},
    {"code": "permission.manage", "name": "Manage Permissions",     "module": "permission", "action": "manage"},
    # Orders
    {"code": "order.view",   "name": "View Orders",   "module": "order", "action": "view"},
    {"code": "order.create", "name": "Create Order",  "module": "order", "action": "create"},
    {"code": "order.update", "name": "Update Order",  "module": "order", "action": "update"},
    {"code": "order.cancel", "name": "Cancel Order",  "module": "order", "action": "cancel"},
    # Bills
    {"code": "bill.view",         "name": "View Bills",           "module": "bill", "action": "view"},
    {"code": "bill.create",       "name": "Create Bill",          "module": "bill", "action": "create"},
    {"code": "bill.print",        "name": "Print Bill",           "module": "bill", "action": "print"},
    {"code": "bill.cancel",       "name": "Cancel Bill",          "module": "bill", "action": "cancel"},
    {"code": "bill.edit.request", "name": "Request Bill Edit",    "module": "bill", "action": "edit.request"},
    {"code": "bill.edit.approve", "name": "Approve Bill Edit",    "module": "bill", "action": "edit.approve"},
    # Payments
    {"code": "payment.view",           "name": "View Payments",         "module": "payment", "action": "view"},
    {"code": "payment.create",         "name": "Create Payment",        "module": "payment", "action": "create"},
    {"code": "payment.cancel",         "name": "Cancel Payment",        "module": "payment", "action": "cancel"},
    {"code": "payment.refund.request", "name": "Request Refund",        "module": "payment", "action": "refund.request"},
    {"code": "payment.refund.approve", "name": "Approve Refund",        "module": "payment", "action": "refund.approve"},
    {"code": "payment.refund.process", "name": "Process Refund",        "module": "payment", "action": "refund.process"},
    {"code": "payment.history.view",   "name": "View Payment History",  "module": "payment", "action": "history.view"},
    {"code": "payment.receipt.print",  "name": "Print Payment Receipt", "module": "payment", "action": "receipt.print"},
    # Inventory
    {"code": "inventory.view",    "name": "View Inventory",   "module": "inventory", "action": "view"},
    {"code": "inventory.adjust",  "name": "Adjust Inventory", "module": "inventory", "action": "adjust"},
    {"code": "inventory.wastage", "name": "Record Wastage",   "module": "inventory", "action": "wastage"},
    {"code": "inventory.receive", "name": "Receive Stock",    "module": "inventory", "action": "receive"},
    # Expenses
    {"code": "expense.view",    "name": "View Expenses",   "module": "expense", "action": "view"},
    {"code": "expense.create",  "name": "Create Expense",  "module": "expense", "action": "create"},
    {"code": "expense.approve", "name": "Approve Expense", "module": "expense", "action": "approve"},
    # Reports
    {"code": "report.sales.view",    "name": "View Sales Reports",   "module": "report", "action": "sales.view"},
    {"code": "report.accounts.view", "name": "View Account Reports", "module": "report", "action": "accounts.view"},
    {"code": "report.profit.view",   "name": "View Profit Reports",  "module": "report", "action": "profit.view"},
    # Kitchen
    {"code": "kitchen.order.view",   "name": "View Kitchen Orders",   "module": "kitchen", "action": "order.view"},
    {"code": "kitchen.order.update", "name": "Update Kitchen Orders", "module": "kitchen", "action": "order.update"},
    # Issues
    {"code": "issue.view",    "name": "View Issues",    "module": "issue", "action": "view"},
    {"code": "issue.create",  "name": "Create Issue",   "module": "issue", "action": "create"},
    {"code": "issue.resolve", "name": "Resolve Issues", "module": "issue", "action": "resolve"},
    # Counters
    {"code": "counter.view",                "name": "View Counters",               "module": "counter", "action": "view"},
    {"code": "counter.create",              "name": "Create Counter",              "module": "counter", "action": "create"},
    {"code": "counter.update",              "name": "Update Counter",              "module": "counter", "action": "update"},
    {"code": "counter.disable",             "name": "Disable Counter",             "module": "counter", "action": "disable"},
    {"code": "counter.assign",              "name": "Assign Counter",              "module": "counter", "action": "assign"},
    {"code": "counter.unassign",            "name": "Unassign Counter",            "module": "counter", "action": "unassign"},
    {"code": "counter.session.view",        "name": "View Counter Sessions",       "module": "counter", "action": "session.view"},
    {"code": "counter.session.open",        "name": "Open Counter Session",        "module": "counter", "action": "session.open"},
    {"code": "counter.session.close",       "name": "Close Counter Session",       "module": "counter", "action": "session.close"},
    {"code": "counter.session.force_close", "name": "Force-Close Counter Session", "module": "counter", "action": "session.force_close"},
    {"code": "counter.reconcile",           "name": "Reconcile Counter Cash",      "module": "counter", "action": "reconcile"},
    # Shifts
    {"code": "shift.view",   "name": "View Shifts",   "module": "shift", "action": "view"},
    {"code": "shift.manage", "name": "Manage Shifts", "module": "shift", "action": "manage"},
    # Security
    {"code": "security.audit.view", "name": "View Security Audit Log", "module": "security", "action": "audit.view"},
]

# ---------------------------------------------------------------------------
# Role definitions with permission code lists
# ---------------------------------------------------------------------------

ROLES = [
    {
        "name": "Company Head",
        "code": Role.CODE_COMPANY_HEAD,
        "scope": Role.SCOPE_ORGANIZATION,
        "description": "Full access to the entire organization including all restaurants and branches.",
        "is_system_role": True,
        "permissions": [
            "organization.view", "organization.create", "organization.update", "organization.disable",
            "restaurant.view", "restaurant.create", "restaurant.update", "restaurant.disable",
            "branch.view", "branch.create", "branch.update", "branch.disable",
            "user.view", "user.create", "user.update", "user.disable",
            "role.view", "role.manage", "permission.view",
            "security.audit.view",
            "expense.view", "expense.create", "expense.approve",
            "report.sales.view", "report.accounts.view", "report.profit.view",
            "issue.view", "issue.create", "issue.resolve",
            "counter.view", "counter.create", "counter.update", "counter.disable",
            "counter.assign", "counter.unassign",
            "counter.session.view", "counter.session.open", "counter.session.close",
            "counter.session.force_close", "counter.reconcile",
            "shift.view", "shift.manage",
        ],
    },
    {
        "name": "Central Admin",
        "code": Role.CODE_CENTRAL_ADMIN,
        "scope": Role.SCOPE_ORGANIZATION,
        "description": "Administrative/technical oversight across the organization.",
        "is_system_role": True,
        "permissions": [
            "organization.view",
            "restaurant.view", "restaurant.update",
            "branch.view", "branch.update",
            "user.view", "user.create", "user.update", "user.disable",
            "role.view", "role.manage", "permission.view",
            "security.audit.view",
            "issue.view", "issue.create", "issue.resolve",
            "counter.view", "counter.create", "counter.update", "counter.disable",
            "counter.assign", "counter.unassign",
            "counter.session.view", "counter.session.open", "counter.session.close",
            "counter.session.force_close", "counter.reconcile",
            "shift.view", "shift.manage",
        ],
    },
    {
        "name": "Restaurant Owner",
        "code": Role.CODE_RESTAURANT_OWNER,
        "scope": Role.SCOPE_RESTAURANT,
        "description": "Full control over an assigned restaurant and its branches.",
        "is_system_role": True,
        "permissions": [
            "restaurant.view", "restaurant.update",
            "branch.view", "branch.create", "branch.update", "branch.disable",
            "user.view", "user.create", "user.update", "user.disable",
            "role.view", "role.manage",
            "order.view", "order.create", "order.update", "order.cancel",
            "bill.view", "bill.create", "bill.print", "bill.cancel",
            "bill.edit.request", "bill.edit.approve",
            "payment.view", "payment.create", "payment.cancel",
            "payment.refund.request", "payment.refund.approve", "payment.refund.process",
            "payment.history.view", "payment.receipt.print",
            "inventory.view", "inventory.adjust", "inventory.wastage", "inventory.receive",
            "expense.view", "expense.create", "expense.approve",
            "report.sales.view", "report.accounts.view", "report.profit.view",
            "issue.view", "issue.create", "issue.resolve",
            "counter.view", "counter.create", "counter.update", "counter.disable",
            "counter.assign", "counter.unassign",
            "counter.session.view", "counter.session.open", "counter.session.close",
            "counter.session.force_close", "counter.reconcile",
            "shift.view", "shift.manage",
        ],
    },
    {
        "name": "Restaurant Manager",
        "code": Role.CODE_RESTAURANT_MANAGER,
        "scope": Role.SCOPE_BRANCH,
        "description": "Day-to-day operations management for a restaurant or branch.",
        "is_system_role": True,
        "permissions": [
            "restaurant.view", "branch.view", "branch.update",
            "user.view", "role.view",
            "order.view", "order.create", "order.update", "order.cancel",
            "bill.view", "bill.create", "bill.print",
            "bill.edit.request", "bill.edit.approve",
            "payment.view", "payment.create", "payment.cancel",
            "payment.refund.request", "payment.refund.approve", "payment.refund.process",
            "payment.history.view", "payment.receipt.print",
            "inventory.view", "inventory.adjust", "inventory.wastage",
            "expense.view", "expense.create", "report.sales.view",
            "issue.view", "issue.create", "issue.resolve",
            "counter.view", "counter.create", "counter.update",
            "counter.assign", "counter.unassign",
            "counter.session.view", "counter.session.open", "counter.session.close",
            "counter.session.force_close", "counter.reconcile",
            "shift.view", "shift.manage",
        ],
    },
    {
        "name": "Cashier",
        "code": Role.CODE_CASHIER,
        "scope": Role.SCOPE_BRANCH,
        "description": "POS operations — orders, bills, and payments at a counter.",
        "is_system_role": True,
        "permissions": [
            "order.view", "order.create",
            "bill.view", "bill.create", "bill.print",
            "payment.view", "payment.create", "payment.cancel", "payment.receipt.print",
            "counter.view", "counter.session.view", "counter.session.open", "counter.session.close",
        ],
    },
    {
        "name": "Waiter",
        "code": Role.CODE_WAITER,
        "scope": Role.SCOPE_BRANCH,
        "description": "Table service — order taking and table management.",
        "is_system_role": True,
        "permissions": ["order.view", "order.create"],
    },
    {
        "name": "Kitchen Staff",
        "code": Role.CODE_KITCHEN_STAFF,
        "scope": Role.SCOPE_BRANCH,
        "description": "Kitchen order display and status updates.",
        "is_system_role": True,
        "permissions": ["kitchen.order.view", "kitchen.order.update"],
    },
    {
        "name": "Inventory Staff",
        "code": Role.CODE_INVENTORY_STAFF,
        "scope": Role.SCOPE_BRANCH,
        "description": "Stock management — receiving, adjustments, and wastage.",
        "is_system_role": True,
        "permissions": ["inventory.view", "inventory.receive", "inventory.adjust", "inventory.wastage"],
    },
    {
        "name": "Accountant",
        "code": Role.CODE_ACCOUNTANT,
        "scope": Role.SCOPE_BRANCH,
        "description": "Financial operations — expenses and financial reports.",
        "is_system_role": True,
        "permissions": [
            "expense.view", "expense.create",
            "report.accounts.view", "report.profit.view",
            "payment.view", "payment.history.view", "payment.receipt.print",
        ],
    },
]


class Command(BaseCommand):
    help = (
        "Seed roles and permissions into the database. "
        "Idempotent — safe to run multiple times. "
        "Creates missing entries; updates names/descriptions on existing ones."
    )

    def handle(self, *args, **options):
        with transaction.atomic():
            perm_map = self._seed_permissions()
            self._seed_roles(perm_map)
        self.stdout.write(self.style.SUCCESS("Roles and permissions seeded successfully."))

    def _seed_permissions(self):
        created = 0
        perm_map = {}
        for p in PERMISSIONS:
            obj, is_new = Permission.objects.update_or_create(
                code=p["code"],
                defaults={
                    "name": p["name"],
                    "module": p["module"],
                    "action": p["action"],
                    "is_active": True,
                },
            )
            perm_map[p["code"]] = obj
            if is_new:
                created += 1
        self.stdout.write(f"  Permissions: {created} created, {len(PERMISSIONS) - created} already existed.")
        return perm_map

    def _seed_roles(self, perm_map):
        created = 0
        for r in ROLES:
            obj, is_new = Role.objects.update_or_create(
                code=r["code"],
                defaults={
                    "name": r["name"],
                    "scope": r["scope"],
                    "description": r["description"],
                    "is_system_role": r["is_system_role"],
                    "is_active": True,
                },
            )
            # Set permissions (replace full set)
            perms = [perm_map[code] for code in r["permissions"] if code in perm_map]
            obj.permissions.set(perms)
            if is_new:
                created += 1
        self.stdout.write(f"  Roles: {created} created, {len(ROLES) - created} already existed.")
