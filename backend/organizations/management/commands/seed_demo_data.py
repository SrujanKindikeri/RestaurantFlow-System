# =============================================================================
# RestaurantFlow — Demo Data Seed Command
# Phase 3: Roles + Permissions + Users + Role Assignments
#
# Usage:
#   python manage.py seed_demo_data
#   python manage.py seed_demo_data --reset   # clears existing demo data first
#
# ⚠️  FOR DEVELOPMENT AND TESTING ONLY.
#     Do NOT run this in a production environment.
#     Default demo password is set via DEMO_PASSWORD env var (default: Demo@1234).
# =============================================================================

import logging
import os
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from organizations.models import (
    Organization,
    Restaurant,
    Branch,
    RestaurantSettings,
    BranchSettings,
)
from accounts.models import Permission, Role, UserProfile, UserRoleAssignment

logger = logging.getLogger("organizations")
User = get_user_model()

DEMO_SLUG = "restaurantflow-foods-demo"
DEMO_PASSWORD = os.getenv("DEMO_PASSWORD", "Demo@1234")

# =============================================================================
# Permission definitions
# =============================================================================

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
    {"code": "role.view",         "name": "View Roles",        "module": "role", "action": "view"},
    {"code": "role.manage",       "name": "Manage Role Assignments", "module": "role", "action": "manage"},
    {"code": "permission.view",   "name": "View Permissions",  "module": "permission", "action": "view"},
    {"code": "permission.manage", "name": "Manage Permissions","module": "permission", "action": "manage"},
    # Orders (future)
    {"code": "order.view",   "name": "View Orders",   "module": "order", "action": "view"},
    {"code": "order.create", "name": "Create Order",  "module": "order", "action": "create"},
    {"code": "order.update", "name": "Update Order",  "module": "order", "action": "update"},
    {"code": "order.cancel", "name": "Cancel Order",  "module": "order", "action": "cancel"},
    # Bills (future)
    {"code": "bill.view",         "name": "View Bills",           "module": "bill", "action": "view"},
    {"code": "bill.create",       "name": "Create Bill",          "module": "bill", "action": "create"},
    {"code": "bill.print",        "name": "Print Bill",           "module": "bill", "action": "print"},
    {"code": "bill.cancel",       "name": "Cancel Bill",          "module": "bill", "action": "cancel"},
    {"code": "bill.edit.request", "name": "Request Bill Edit",    "module": "bill", "action": "edit.request"},
    {"code": "bill.edit.approve", "name": "Approve Bill Edit",    "module": "bill", "action": "edit.approve"},
    # Payments (Phase 9)
    {"code": "payment.view",            "name": "View Payments",         "module": "payment", "action": "view"},
    {"code": "payment.create",          "name": "Create Payment",        "module": "payment", "action": "create"},
    {"code": "payment.cancel",          "name": "Cancel Payment",        "module": "payment", "action": "cancel"},
    {"code": "payment.refund.request",  "name": "Request Refund",        "module": "payment", "action": "refund.request"},
    {"code": "payment.refund.approve",  "name": "Approve Refund",        "module": "payment", "action": "refund.approve"},
    {"code": "payment.refund.process",  "name": "Process Refund",        "module": "payment", "action": "refund.process"},
    {"code": "payment.history.view",    "name": "View Payment History",  "module": "payment", "action": "history.view"},
    {"code": "payment.receipt.print",   "name": "Print Payment Receipt", "module": "payment", "action": "receipt.print"},
    # Inventory (future)
    {"code": "inventory.view",    "name": "View Inventory",   "module": "inventory", "action": "view"},
    {"code": "inventory.adjust",  "name": "Adjust Inventory", "module": "inventory", "action": "adjust"},
    {"code": "inventory.wastage", "name": "Record Wastage",   "module": "inventory", "action": "wastage"},
    {"code": "inventory.receive", "name": "Receive Stock",    "module": "inventory", "action": "receive"},
    # Expenses (future)
    {"code": "expense.view",    "name": "View Expenses",   "module": "expense", "action": "view"},
    {"code": "expense.create",  "name": "Create Expense",  "module": "expense", "action": "create"},
    {"code": "expense.approve", "name": "Approve Expense", "module": "expense", "action": "approve"},
    # Reports (future)
    {"code": "report.sales.view",    "name": "View Sales Reports",    "module": "report", "action": "sales.view"},
    {"code": "report.accounts.view", "name": "View Account Reports",  "module": "report", "action": "accounts.view"},
    {"code": "report.profit.view",   "name": "View Profit Reports",   "module": "report", "action": "profit.view"},
    # Kitchen (future)
    {"code": "kitchen.order.view",   "name": "View Kitchen Orders",   "module": "kitchen", "action": "order.view"},
    {"code": "kitchen.order.update", "name": "Update Kitchen Orders", "module": "kitchen", "action": "order.update"},
    # Issues (future)
    {"code": "issue.view",    "name": "View Issues",    "module": "issue", "action": "view"},
    {"code": "issue.create",  "name": "Create Issue",   "module": "issue", "action": "create"},
    {"code": "issue.resolve", "name": "Resolve Issues", "module": "issue", "action": "resolve"},
    # Phase 4 — Counters
    {"code": "counter.view",                  "name": "View Counters",              "module": "counter", "action": "view"},
    {"code": "counter.create",                "name": "Create Counter",             "module": "counter", "action": "create"},
    {"code": "counter.update",                "name": "Update Counter",             "module": "counter", "action": "update"},
    {"code": "counter.disable",               "name": "Disable Counter",            "module": "counter", "action": "disable"},
    {"code": "counter.assign",                "name": "Assign Counter",             "module": "counter", "action": "assign"},
    {"code": "counter.unassign",              "name": "Unassign Counter",           "module": "counter", "action": "unassign"},
    {"code": "counter.session.view",          "name": "View Counter Sessions",      "module": "counter", "action": "session.view"},
    {"code": "counter.session.open",          "name": "Open Counter Session",       "module": "counter", "action": "session.open"},
    {"code": "counter.session.close",         "name": "Close Counter Session",      "module": "counter", "action": "session.close"},
    {"code": "counter.session.force_close",   "name": "Force-Close Counter Session","module": "counter", "action": "session.force_close"},
    {"code": "counter.reconcile",             "name": "Reconcile Counter Cash",     "module": "counter", "action": "reconcile"},
    # Phase 4 — Shifts
    {"code": "shift.view",   "name": "View Shifts",   "module": "shift", "action": "view"},
    {"code": "shift.manage", "name": "Manage Shifts", "module": "shift", "action": "manage"},
]


# =============================================================================
# Role definitions with permission assignments
# =============================================================================

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
            "role.view", "role.manage",
            "permission.view",
            "expense.view", "expense.create", "expense.approve",
            "report.sales.view", "report.accounts.view", "report.profit.view",
            "issue.view", "issue.create", "issue.resolve",
            # Phase 4 — Counters
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
            "role.view", "role.manage",
            "permission.view",
            "issue.view", "issue.create", "issue.resolve",
            # Phase 4 — Counters
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
            # Phase 4 — Counters
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
            "restaurant.view",
            "branch.view", "branch.update",
            "user.view",
            "role.view",
            "order.view", "order.create", "order.update", "order.cancel",
            "bill.view", "bill.create", "bill.print",
            "bill.edit.request", "bill.edit.approve",
            "payment.view", "payment.create", "payment.cancel",
            "payment.refund.request", "payment.refund.approve", "payment.refund.process",
            "payment.history.view", "payment.receipt.print",
            "inventory.view", "inventory.adjust", "inventory.wastage",
            "expense.view", "expense.create",
            "report.sales.view",
            "issue.view", "issue.create", "issue.resolve",
            # Phase 4 — Counters
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
            "payment.view", "payment.create", "payment.cancel",
            "payment.receipt.print",
            # Phase 4 — Counters (cashier subset)
            "counter.view",
            "counter.session.view", "counter.session.open", "counter.session.close",
        ],
    },
    {
        "name": "Waiter",
        "code": Role.CODE_WAITER,
        "scope": Role.SCOPE_BRANCH,
        "description": "Table service — order taking and table management.",
        "is_system_role": True,
        "permissions": [
            "order.view", "order.create",
        ],
    },
    {
        "name": "Kitchen Staff",
        "code": Role.CODE_KITCHEN_STAFF,
        "scope": Role.SCOPE_BRANCH,
        "description": "Kitchen order display and status updates.",
        "is_system_role": True,
        "permissions": [
            "kitchen.order.view", "kitchen.order.update",
        ],
    },
    {
        "name": "Inventory Staff",
        "code": Role.CODE_INVENTORY_STAFF,
        "scope": Role.SCOPE_BRANCH,
        "description": "Stock management — receiving, adjustments, and wastage.",
        "is_system_role": True,
        "permissions": [
            "inventory.view", "inventory.receive", "inventory.adjust", "inventory.wastage",
        ],
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


# =============================================================================
# Organization / Restaurant / Branch demo data (carried from Phase 2)
# =============================================================================

DEMO_DATA = {
    "organization": {
        "name": "RestaurantFlow Foods",
        "legal_name": "RestaurantFlow Foods Pvt Ltd",
        "slug": DEMO_SLUG,
        "email": "admin@restaurantflow.dev",
        "phone": "+91-9000000001",
        "address": "12 Tech Park, Sector 5",
        "city": "Bangalore",
        "state": "Karnataka",
        "country": "India",
        "postal_code": "560001",
        "tax_id": "29AABCT1332L1ZD",
        "currency": "INR",
        "timezone": "Asia/Kolkata",
    },
    "restaurants": [
        {
            "name": "Spice Garden",
            "code": "SPICE-001",
            "description": "Authentic South Indian cuisine with a modern twist.",
            "phone": "+91-9000000002",
            "email": "spicegarden@restaurantflow.dev",
            "city": "Bangalore",
            "state": "Karnataka",
            "country": "India",
            "settings": {
                "currency": "INR",
                "timezone": "Asia/Kolkata",
                "tax_enabled": True,
                "default_tax_rate": 5.00,
                "order_prefix": "SG",
            },
            "branches": [
                {
                    "name": "LPU Campus",
                    "code": "SG-LPU",
                    "address": "LPU Campus, Phagwara",
                    "city": "Phagwara",
                    "state": "Punjab",
                    "country": "India",
                    "postal_code": "144411",
                    "phone": "+91-9000000010",
                    "settings": {"opening_time": "08:00:00", "closing_time": "22:00:00", "default_order_type": "dine_in"},
                },
                {
                    "name": "Main Market",
                    "code": "SG-MKT",
                    "address": "42 Main Market Road",
                    "city": "Bangalore",
                    "state": "Karnataka",
                    "country": "India",
                    "postal_code": "560002",
                    "phone": "+91-9000000011",
                    "settings": {"opening_time": "09:00:00", "closing_time": "23:00:00", "default_order_type": "takeaway"},
                },
                {
                    "name": "City Center",
                    "code": "SG-CITY",
                    "address": "City Center Mall, 3rd Floor",
                    "city": "Bangalore",
                    "state": "Karnataka",
                    "country": "India",
                    "postal_code": "560003",
                    "phone": "+91-9000000012",
                    "settings": {"opening_time": "10:00:00", "closing_time": "22:00:00", "default_order_type": "dine_in"},
                },
            ],
        },
        {
            "name": "Urban Bites",
            "code": "URBAN-001",
            "description": "Contemporary street food and fusion snacks.",
            "phone": "+91-9000000003",
            "email": "urbanbites@restaurantflow.dev",
            "city": "Mumbai",
            "state": "Maharashtra",
            "country": "India",
            "settings": {
                "currency": "INR",
                "timezone": "Asia/Kolkata",
                "tax_enabled": True,
                "default_tax_rate": 5.00,
                "order_prefix": "UB",
            },
            "branches": [
                {
                    "name": "Downtown",
                    "code": "UB-DT",
                    "address": "88 Downtown Avenue",
                    "city": "Mumbai",
                    "state": "Maharashtra",
                    "country": "India",
                    "postal_code": "400001",
                    "phone": "+91-9000000020",
                    "settings": {"opening_time": "11:00:00", "closing_time": "23:00:00", "default_order_type": "takeaway"},
                },
                {
                    "name": "Airport Terminal 2",
                    "code": "UB-AIR",
                    "address": "CSIA Terminal 2, Airside",
                    "city": "Mumbai",
                    "state": "Maharashtra",
                    "country": "India",
                    "postal_code": "400099",
                    "phone": "+91-9000000021",
                    "settings": {"opening_time": "05:00:00", "closing_time": "23:59:00", "default_order_type": "takeaway"},
                },
            ],
        },
        {
            "name": "Royal Kitchen",
            "code": "ROYAL-001",
            "description": "Traditional Mughlai and North Indian cuisine.",
            "phone": "+91-9000000004",
            "email": "royalkitchen@restaurantflow.dev",
            "city": "Delhi",
            "state": "Delhi",
            "country": "India",
            "settings": {
                "currency": "INR",
                "timezone": "Asia/Kolkata",
                "tax_enabled": True,
                "default_tax_rate": 5.00,
                "order_prefix": "RK",
            },
            "branches": [
                {
                    "name": "Main Branch",
                    "code": "RK-MAIN",
                    "address": "1 Connaught Place",
                    "city": "New Delhi",
                    "state": "Delhi",
                    "country": "India",
                    "postal_code": "110001",
                    "phone": "+91-9000000030",
                    "settings": {"opening_time": "12:00:00", "closing_time": "23:00:00", "default_order_type": "dine_in"},
                },
                {
                    "name": "Lajpat Nagar",
                    "code": "RK-LN",
                    "address": "Central Market, Lajpat Nagar",
                    "city": "New Delhi",
                    "state": "Delhi",
                    "country": "India",
                    "postal_code": "110024",
                    "phone": "+91-9000000031",
                    "settings": {"opening_time": "11:00:00", "closing_time": "22:00:00", "default_order_type": "dine_in"},
                },
            ],
        },
    ],
}


# =============================================================================
# Demo users
# =============================================================================

DEMO_USERS = [
    {
        "email": "company@restaurantflow.dev",
        "first_name": "Srujan",
        "last_name": "Mehta",
        "phone": "+91-9000000100",
        "role_code": Role.CODE_COMPANY_HEAD,
        "scope": "organization",
        "employee_code": "EMP-0001",
        "display_name": "Srujan Mehta — Company Head",
    },
    {
        "email": "admin@restaurantflow.dev",
        "first_name": "Priya",
        "last_name": "Sharma",
        "phone": "+91-9000000101",
        "role_code": Role.CODE_CENTRAL_ADMIN,
        "scope": "organization",
        "employee_code": "EMP-0002",
        "display_name": "Priya Sharma — Central Admin",
    },
    {
        "email": "owner@spicegarden.dev",
        "first_name": "Arjun",
        "last_name": "Nair",
        "phone": "+91-9000000102",
        "role_code": Role.CODE_RESTAURANT_OWNER,
        "scope": "restaurant",
        "restaurant_code": "SPICE-001",
        "employee_code": "EMP-0003",
        "display_name": "Arjun Nair — Spice Garden Owner",
    },
    {
        "email": "manager@spicegarden.dev",
        "first_name": "Kavya",
        "last_name": "Reddy",
        "phone": "+91-9000000103",
        "role_code": Role.CODE_RESTAURANT_MANAGER,
        "scope": "branch",
        "restaurant_code": "SPICE-001",
        "branch_code": "SG-LPU",
        "employee_code": "EMP-0004",
        "display_name": "Kavya Reddy — LPU Manager",
    },
    {
        "email": "cashier@spicegarden.dev",
        "first_name": "Rohit",
        "last_name": "Verma",
        "phone": "+91-9000000104",
        "role_code": Role.CODE_CASHIER,
        "scope": "branch",
        "restaurant_code": "SPICE-001",
        "branch_code": "SG-LPU",
        "employee_code": "EMP-0005",
        "display_name": "Rohit Verma — Cashier",
    },
    {
        "email": "waiter@spicegarden.dev",
        "first_name": "Ananya",
        "last_name": "Singh",
        "phone": "+91-9000000105",
        "role_code": Role.CODE_WAITER,
        "scope": "branch",
        "restaurant_code": "SPICE-001",
        "branch_code": "SG-LPU",
        "employee_code": "EMP-0006",
        "display_name": "Ananya Singh — Waiter",
    },
    {
        "email": "kitchen@spicegarden.dev",
        "first_name": "Deepak",
        "last_name": "Rao",
        "phone": "+91-9000000106",
        "role_code": Role.CODE_KITCHEN_STAFF,
        "scope": "branch",
        "restaurant_code": "SPICE-001",
        "branch_code": "SG-LPU",
        "employee_code": "EMP-0007",
        "display_name": "Deepak Rao — Kitchen Staff",
    },
    {
        "email": "inventory@spicegarden.dev",
        "first_name": "Meera",
        "last_name": "Joshi",
        "phone": "+91-9000000107",
        "role_code": Role.CODE_INVENTORY_STAFF,
        "scope": "branch",
        "restaurant_code": "SPICE-001",
        "branch_code": "SG-LPU",
        "employee_code": "EMP-0008",
        "display_name": "Meera Joshi — Inventory Staff",
    },
    {
        "email": "accounts@spicegarden.dev",
        "first_name": "Vikram",
        "last_name": "Pillai",
        "phone": "+91-9000000108",
        "role_code": Role.CODE_ACCOUNTANT,
        "scope": "branch",
        "restaurant_code": "SPICE-001",
        "branch_code": "SG-LPU",
        "employee_code": "EMP-0009",
        "display_name": "Vikram Pillai — Accountant",
    },
]


# =============================================================================
# Command
# =============================================================================

class Command(BaseCommand):
    help = (
        "Seed the database with demo data: "
        "Organizations, Restaurants, Branches, Roles, Permissions, Users, Assignments. "
        "FOR DEVELOPMENT AND TESTING ONLY."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete the existing demo organization and users before re-seeding.",
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.WARNING(
                "\n⚠️  seed_demo_data — DEVELOPMENT ONLY\n"
                "   Do NOT run in production.\n"
                f"   Demo password: {DEMO_PASSWORD}\n"
            )
        )

        if options["reset"]:
            self._reset_demo_data()

        try:
            with transaction.atomic():
                # Step 1: Permissions
                perm_map = self._seed_permissions()

                # Step 2: Roles
                role_map = self._seed_roles(perm_map)

                # Step 3: Organization + restaurants + branches
                org = self._create_organization()
                restaurant_map = {}
                branch_map = {}
                for restaurant_data in DEMO_DATA["restaurants"]:
                    rest, branches = self._create_restaurant(org, restaurant_data)
                    restaurant_map[rest.code] = rest
                    for branch in branches:
                        branch_map[branch.code] = branch

                # Step 4: Demo users + role assignments
                self._seed_users(org, role_map, restaurant_map, branch_map)

            self.stdout.write(self.style.SUCCESS("\n✓ Demo data seeded successfully.\n"))
            self._print_summary(restaurant_map, branch_map)

        except Exception as exc:
            raise CommandError(f"Seeding failed: {exc}") from exc

    # -------------------------------------------------------------------------

    def _reset_demo_data(self):
        # Delete demo users
        demo_emails = [u["email"] for u in DEMO_USERS]
        deleted_users, _ = User.objects.filter(email__in=demo_emails).delete()
        if deleted_users:
            self.stdout.write(self.style.WARNING(f"  Deleted {deleted_users} demo users."))

        # Delete demo org (cascades to restaurants/branches via PROTECT — so we need to delete in order)
        try:
            org = Organization.objects.get(slug=DEMO_SLUG)
            # Assignments are CASCADE on user delete — branches/restaurants need explicit removal
            Branch.objects.filter(restaurant__organization=org).delete()
            Restaurant.objects.filter(organization=org).delete()
            org.delete()
            self.stdout.write(self.style.WARNING(f"  Deleted demo organization ({DEMO_SLUG})."))
        except Organization.DoesNotExist:
            pass

    def _seed_permissions(self):
        perm_map = {}
        created_count = 0
        for p in PERMISSIONS:
            perm, created = Permission.objects.get_or_create(
                code=p["code"],
                defaults={
                    "name": p["name"],
                    "module": p["module"],
                    "action": p["action"],
                    "is_active": True,
                },
            )
            perm_map[p["code"]] = perm
            if created:
                created_count += 1
        self.stdout.write(f"  Permissions: {created_count} created, {len(PERMISSIONS) - created_count} already existed.")
        return perm_map

    def _seed_roles(self, perm_map):
        role_map = {}
        created_count = 0
        for r in ROLES:
            role, created = Role.objects.get_or_create(
                code=r["code"],
                defaults={
                    "name": r["name"],
                    "scope": r["scope"],
                    "description": r["description"],
                    "is_system_role": r["is_system_role"],
                    "is_active": True,
                },
            )
            # Always sync permissions (in case they were reset)
            perm_objects = [perm_map[code] for code in r["permissions"] if code in perm_map]
            role.permissions.set(perm_objects)
            role_map[r["code"]] = role
            if created:
                created_count += 1
        self.stdout.write(f"  Roles: {created_count} created, {len(ROLES) - created_count} already existed.")
        return role_map

    def _create_organization(self):
        org, created = Organization.objects.get_or_create(
            slug=DEMO_SLUG,
            defaults=DEMO_DATA["organization"],
        )
        if created:
            self.stdout.write(f"  Created organization: {org.name}")
        else:
            self.stdout.write(self.style.NOTICE(f"  Organization already exists: {org.name}"))
        return org

    def _create_restaurant(self, org, restaurant_data):
        data = dict(restaurant_data)
        settings_data = data.pop("settings", {})
        branches_data = data.pop("branches", [])

        restaurant, created = Restaurant.objects.get_or_create(
            organization=org,
            code=data["code"],
            defaults={**data, "organization": org},
        )

        if created:
            self.stdout.write(f"    Created restaurant: {restaurant.name}")
            rs, _ = RestaurantSettings.objects.get_or_create(restaurant=restaurant)
            for key, val in settings_data.items():
                setattr(rs, key, val)
            rs.save()
        else:
            self.stdout.write(self.style.NOTICE(f"    Restaurant already exists: {restaurant.name}"))

        branches = []
        for branch_data in branches_data:
            branch = self._create_branch(restaurant, branch_data)
            branches.append(branch)

        return restaurant, branches

    def _create_branch(self, restaurant, branch_data):
        data = dict(branch_data)
        settings_data = data.pop("settings", {})

        branch, created = Branch.objects.get_or_create(
            restaurant=restaurant,
            code=data["code"],
            defaults={**data, "restaurant": restaurant},
        )

        if created:
            self.stdout.write(f"      Created branch: {branch.name}")
            bs, _ = BranchSettings.objects.get_or_create(branch=branch)
            for key, val in settings_data.items():
                setattr(bs, key, val)
            bs.save()
        else:
            self.stdout.write(self.style.NOTICE(f"      Branch already exists: {branch.name}"))

        return branch

    def _seed_users(self, org, role_map, restaurant_map, branch_map):
        created_count = 0
        for u in DEMO_USERS:
            user, created = User.objects.get_or_create(
                email=u["email"],
                defaults={
                    "first_name": u["first_name"],
                    "last_name": u["last_name"],
                    "phone": u["phone"],
                    "is_active": True,
                },
            )
            if created:
                user.set_password(DEMO_PASSWORD)
                user.save()
                created_count += 1
                self.stdout.write(f"    Created user: {user.email}")
            else:
                self.stdout.write(self.style.NOTICE(f"    User already exists: {user.email}"))

            # Ensure profile
            profile, _ = UserProfile.objects.get_or_create(user=user)
            profile.employee_code = u.get("employee_code", "")
            profile.display_name = u.get("display_name", "")
            profile.save()

            # Create role assignment if not already exists
            role = role_map.get(u["role_code"])
            if not role:
                continue

            scope = u["scope"]
            restaurant = restaurant_map.get(u.get("restaurant_code", ""))
            branch = branch_map.get(u.get("branch_code", ""))

            existing = UserRoleAssignment.objects.filter(
                user=user, role=role, is_active=True
            ).first()

            if not existing:
                # Build assignment kwargs based on scope
                assignment_kwargs = {
                    "user": user,
                    "role": role,
                    "organization": org,
                    "is_active": True,
                }
                if scope in ("restaurant", "branch") and restaurant:
                    assignment_kwargs["restaurant"] = restaurant
                if scope == "branch" and branch:
                    assignment_kwargs["branch"] = branch

                assignment = UserRoleAssignment(**assignment_kwargs)
                assignment.full_clean()
                assignment.save()
                self.stdout.write(f"      Assigned role {role.code} to {user.email}")

        self.stdout.write(f"  Users: {created_count} created.")

    def _print_summary(self, restaurant_map, branch_map):
        self.stdout.write("\n  Demo Credentials (DEVELOPMENT ONLY)")
        self.stdout.write("  " + "─" * 60)
        self.stdout.write(f"  {'Email':<40} {'Role':<20}")
        self.stdout.write("  " + "─" * 60)
        for u in DEMO_USERS:
            self.stdout.write(f"  {u['email']:<40} {u['role_code']:<20}")
        self.stdout.write("  " + "─" * 60)
        self.stdout.write(f"  Password for all: {DEMO_PASSWORD}")
        self.stdout.write("")
