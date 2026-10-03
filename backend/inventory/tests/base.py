# =============================================================================
# RestaurantFlow — Inventory Test Base
# Phase 10
#
# Shared fixture setup for all inventory integration tests.
# All test classes that need DB access should inherit from InventoryTestBase.
#
# Fixture hierarchy:
#   Organization → Restaurant → Branch (main + other)
#   Users: inventory_staff, manager, owner, other_user
#   Permissions: all inventory permissions
#   Roles: INVENTORY_ROLE, MANAGER_ROLE
#   InventoryCategory: dry_goods, dairy
#   InventoryItem: rice (KG), milk (LITRE)
#   StorageLocation: main_store, kitchen_store (branch); other_store (other_branch)
#   Supplier: supplier_a
#
# setUpTestData runs ONCE per test class — individual tests must not mutate cls.*
# =============================================================================

from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from accounts.models import User, Role, Permission, UserRoleAssignment
from organizations.models import Organization, Restaurant, Branch, RestaurantSettings, BranchSettings
from inventory.models import (
    InventoryCategory, InventoryItem, StorageLocation, Supplier,
    StockBalance,
)


class InventoryTestBase(TestCase):
    """
    Base test class providing a full fixture stack for inventory tests.

    setUpTestData runs ONCE per test class.
    Individual tests that mutate state must use setUp() instead and
    copy what they need, or use transaction.atomic savepoints.
    """

    @classmethod
    def setUpTestData(cls):
        # -----------------------------------------------------------------
        # Organization / Restaurant / Branch
        # -----------------------------------------------------------------
        cls.org = Organization.objects.create(
            name="Test Org",
            slug="test-org",
            currency="INR",
            tax_id="GSTIN12345",
        )
        cls.restaurant = Restaurant.objects.create(
            organization=cls.org,
            name="Test Restaurant",
            slug="test-restaurant",
            code="TR01",
        )
        RestaurantSettings.objects.create(
            restaurant=cls.restaurant,
            currency="INR",
            tax_enabled=True,
            default_tax_rate=Decimal("5.00"),
        )
        cls.branch = Branch.objects.create(
            restaurant=cls.restaurant,
            name="Main Branch",
            code="MB01",
            address="123 Main Street",
            city="Test City",
            state="Test State",
            postal_code="110001",
            phone="9999999999",
        )
        BranchSettings.objects.create(branch=cls.branch)

        cls.other_branch = Branch.objects.create(
            restaurant=cls.restaurant,
            name="Other Branch",
            code="OB01",
        )
        BranchSettings.objects.create(branch=cls.other_branch)

        # -----------------------------------------------------------------
        # Users
        # -----------------------------------------------------------------
        cls.inventory_staff = User.objects.create_user(
            email="inventory@test.com",
            password="pass123",
            first_name="Inventory",
            last_name="Staff",
        )
        cls.manager = User.objects.create_user(
            email="manager@test.com",
            password="pass123",
            first_name="Branch",
            last_name="Manager",
        )
        cls.owner = User.objects.create_user(
            email="owner@test.com",
            password="pass123",
            first_name="Restaurant",
            last_name="Owner",
        )
        cls.other_user = User.objects.create_user(
            email="other@test.com",
            password="pass123",
            first_name="Other",
            last_name="User",
        )

        # -----------------------------------------------------------------
        # Permissions
        # -----------------------------------------------------------------
        perm_data = [
            ("inventory.view",              "Inventory", "View inventory",                  "inventory", "view"),
            ("inventory.create",            "Inventory", "Create inventory items",          "inventory", "create"),
            ("inventory.update",            "Inventory", "Update inventory items",          "inventory", "update"),
            ("inventory.adjust",            "Inventory", "Adjust stock",                    "inventory", "adjust"),
            ("inventory.transfer",          "Inventory", "Create/request transfers",        "inventory", "transfer"),
            ("inventory.transfer.approve",  "Inventory", "Approve/complete transfers",      "inventory", "transfer_approve"),
            ("inventory.wastage.create",    "Inventory", "Record wastage",                  "inventory", "wastage_create"),
            ("inventory.wastage.approve",   "Inventory", "Approve wastage",                 "inventory", "wastage_approve"),
            ("supplier.view",               "Inventory", "View suppliers",                  "inventory", "supplier_view"),
            ("supplier.create",             "Inventory", "Create suppliers",                "inventory", "supplier_create"),
            ("supplier.update",             "Inventory", "Update suppliers",                "inventory", "supplier_update"),
            ("purchase.view",               "Inventory", "View purchases",                  "inventory", "purchase_view"),
            ("purchase.create",             "Inventory", "Create purchase orders",          "inventory", "purchase_create"),
            ("purchase.submit",             "Inventory", "Submit purchase orders",          "inventory", "purchase_submit"),
            ("purchase.approve",            "Inventory", "Approve purchase orders",         "inventory", "purchase_approve"),
            ("purchase.receive",            "Inventory", "Receive goods",                   "inventory", "purchase_receive"),
            ("purchase.cancel",             "Inventory", "Cancel purchase orders",          "inventory", "purchase_cancel"),
            ("stock.movement.view",         "Inventory", "View stock movements",            "inventory", "movement_view"),
        ]
        cls.perms = {}
        for code, name, desc, module, action in perm_data:
            p, _ = Permission.objects.get_or_create(
                code=code,
                defaults={"name": name, "description": desc, "module": module, "action": action},
            )
            cls.perms[code] = p

        # -----------------------------------------------------------------
        # Roles
        # -----------------------------------------------------------------
        cls.inventory_role = Role.objects.create(
            name="Inventory Staff Test",
            code="INVENTORY_STAFF_TEST",
            scope=Role.SCOPE_BRANCH,
        )
        inventory_perm_codes = [
            "inventory.view", "inventory.create", "inventory.update",
            "inventory.wastage.create", "inventory.transfer",
            "supplier.view", "purchase.view", "purchase.create",
            "purchase.submit", "purchase.receive",
            "stock.movement.view",
        ]
        cls.inventory_role.permissions.set([cls.perms[c] for c in inventory_perm_codes])

        cls.manager_role = Role.objects.create(
            name="Manager Test",
            code="MANAGER_TEST_INV",
            scope=Role.SCOPE_BRANCH,
        )
        cls.manager_role.permissions.set(list(cls.perms.values()))

        cls.owner_role = Role.objects.create(
            name="Owner Test",
            code="OWNER_TEST_INV",
            scope=Role.SCOPE_RESTAURANT,
        )
        cls.owner_role.permissions.set(list(cls.perms.values()))

        # -----------------------------------------------------------------
        # Role assignments
        # -----------------------------------------------------------------
        UserRoleAssignment.objects.create(
            user=cls.inventory_staff,
            role=cls.inventory_role,
            organization=cls.org,
            restaurant=cls.restaurant,
            branch=cls.branch,
        )
        UserRoleAssignment.objects.create(
            user=cls.manager,
            role=cls.manager_role,
            organization=cls.org,
            restaurant=cls.restaurant,
            branch=cls.branch,
        )
        UserRoleAssignment.objects.create(
            user=cls.owner,
            role=cls.owner_role,
            organization=cls.org,
            restaurant=cls.restaurant,
        )
        # other_user has NO role assignment

        # -----------------------------------------------------------------
        # Inventory Categories
        # -----------------------------------------------------------------
        cls.cat_dry = InventoryCategory.objects.create(
            restaurant=cls.restaurant,
            name="Dry Goods",
            description="Rice, flour, etc.",
        )
        cls.cat_dairy = InventoryCategory.objects.create(
            restaurant=cls.restaurant,
            name="Dairy",
            description="Milk, cheese, etc.",
        )

        # -----------------------------------------------------------------
        # Inventory Items
        # -----------------------------------------------------------------
        cls.item_rice = InventoryItem.objects.create(
            restaurant=cls.restaurant,
            category=cls.cat_dry,
            name="Rice",
            sku="RICE-001",
            default_unit="KG",
            minimum_stock=Decimal("5.000"),
            reorder_level=Decimal("10.000"),
            maximum_stock=Decimal("500.000"),
            average_cost=Decimal("50.00"),
        )
        cls.item_milk = InventoryItem.objects.create(
            restaurant=cls.restaurant,
            category=cls.cat_dairy,
            name="Milk",
            sku="MILK-001",
            default_unit="LITRE",
            minimum_stock=Decimal("2.000"),
            reorder_level=Decimal("5.000"),
            maximum_stock=Decimal("100.000"),
            average_cost=Decimal("30.00"),
        )

        # -----------------------------------------------------------------
        # Storage Locations
        # -----------------------------------------------------------------
        cls.main_store = StorageLocation.objects.create(
            branch=cls.branch,
            name="Main Store",
            code="MAIN",
            location_type="MAIN_STORE",
        )
        cls.kitchen_store = StorageLocation.objects.create(
            branch=cls.branch,
            name="Kitchen Store",
            code="KITCH",
            location_type="KITCHEN",
        )
        cls.other_store = StorageLocation.objects.create(
            branch=cls.other_branch,
            name="Other Store",
            code="OTHER",
            location_type="MAIN_STORE",
        )

        # -----------------------------------------------------------------
        # Supplier
        # -----------------------------------------------------------------
        cls.supplier_a = Supplier.objects.create(
            restaurant=cls.restaurant,
            name="Quality Grains Co.",
            code="QGC-001",
            contact_person="Raj Kumar",
            phone="9876543210",
            email="raj@qgc.com",
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _seed_balance(self, item, location, quantity: Decimal, avg_cost: Decimal = None) -> StockBalance:
        """
        Directly seed a StockBalance for testing.
        Does NOT create StockMovements (use for test setup only).
        """
        cost = avg_cost if avg_cost is not None else item.average_cost
        balance, _ = StockBalance.objects.get_or_create(
            inventory_item=item,
            storage_location=location,
            defaults={"quantity": quantity, "average_cost": cost},
        )
        if _:
            return balance
        # Already exists — update
        balance.quantity = quantity
        balance.average_cost = cost
        balance.save(update_fields=["quantity", "average_cost", "updated_at"])
        return balance
