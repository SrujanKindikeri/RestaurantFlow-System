# =============================================================================
# RestaurantFlow — Inventory Concurrency Tests
# Phase 10
#
# Tests:
#   - Concurrent stock decrease: only one succeeds when stock is limited
#   - Stock never becomes negative under concurrent access
#   - Concurrent PO number generation produces unique numbers
#
# These tests use threading to simulate concurrent requests.
# TransactionTestCase is required (not TestCase) because threads need
# their own DB connections — TestCase wraps everything in a rolled-back
# transaction that threads cannot see.
# =============================================================================

import threading
from decimal import Decimal

from django.test import TransactionTestCase
from rest_framework.exceptions import ValidationError

from accounts.models import User, Role, Permission, UserRoleAssignment
from organizations.models import (
    Organization, Restaurant, Branch,
    RestaurantSettings, BranchSettings,
)
from inventory import services
from inventory.models import (
    InventoryCategory, InventoryItem, StorageLocation, StockBalance,
)
from inventory.constants import MOVEMENT_WASTAGE


class TestConcurrentStockDecrease(TransactionTestCase):
    """
    Spec scenario:
        Initial stock = 10 KG
        Request A: remove 7 KG
        Request B: remove 6 KG
        Expected: exactly ONE succeeds, the other fails with INSUFFICIENT_STOCK.
        Stock never goes below 0.
    """

    def setUp(self):
        self.org = Organization.objects.create(name="Concurrency Org", slug="conc-org", currency="INR")
        self.restaurant = Restaurant.objects.create(
            organization=self.org, name="Conc Restaurant", slug="conc-rest", code="CR01"
        )
        RestaurantSettings.objects.create(restaurant=self.restaurant)
        self.branch = Branch.objects.create(
            restaurant=self.restaurant, name="Conc Branch", code="CB01"
        )
        BranchSettings.objects.create(branch=self.branch)

        self.manager = User.objects.create_user(
            email="conc_manager@test.com", password="pass123",
            first_name="Conc", last_name="Manager",
        )
        mgr_role = Role.objects.create(name="Conc Manager", code="CONC_MGR", scope=Role.SCOPE_BRANCH)
        for code, name, mod, act in [
            ("inventory.adjust", "Adjust", "inventory", "adjust"),
            ("inventory.wastage.approve", "Wastage Approve", "inventory", "wastage_approve"),
        ]:
            p, _ = Permission.objects.get_or_create(
                code=code, defaults={"name": name, "module": mod, "action": act}
            )
            mgr_role.permissions.add(p)
        UserRoleAssignment.objects.create(
            user=self.manager, role=mgr_role,
            organization=self.org, restaurant=self.restaurant, branch=self.branch,
        )

        cat = InventoryCategory.objects.create(restaurant=self.restaurant, name="Grains")
        self.item = InventoryItem.objects.create(
            restaurant=self.restaurant, category=cat,
            name="Basmati Rice", sku="BSMT-001",
            default_unit="KG", average_cost=Decimal("50.00"),
        )
        self.location = StorageLocation.objects.create(
            branch=self.branch, name="Main Store", code="MAIN", location_type="MAIN_STORE"
        )
        # Seed exactly 10 KG
        StockBalance.objects.create(
            inventory_item=self.item,
            storage_location=self.location,
            quantity=Decimal("10.000"),
            average_cost=Decimal("50.00"),
        )

    def test_concurrent_decrease_only_one_succeeds(self):
        """
        Start: 10 KG
        Thread A: remove 7 KG
        Thread B: remove 6 KG
        Exactly one thread succeeds.
        Final balance is 3 KG (if A wins) or 4 KG (if B wins) — never negative.
        """
        results = {"success": 0, "failed": 0, "final_qty": None}
        lock = threading.Lock()

        def attempt_decrease(qty: Decimal):
            try:
                services.decrease_stock(
                    inventory_item=self.item,
                    storage_location=self.location,
                    quantity=qty,
                    movement_type=MOVEMENT_WASTAGE,
                    performed_by=self.manager,
                    reason="Concurrency test decrease",
                )
                with lock:
                    results["success"] += 1
            except ValidationError:
                with lock:
                    results["failed"] += 1

        thread_a = threading.Thread(target=attempt_decrease, args=(Decimal("7.000"),))
        thread_b = threading.Thread(target=attempt_decrease, args=(Decimal("6.000"),))

        thread_a.start()
        thread_b.start()
        thread_a.join()
        thread_b.join()

        # Exactly one must succeed
        self.assertEqual(results["success"], 1, "Expected exactly 1 successful decrease")
        self.assertEqual(results["failed"], 1, "Expected exactly 1 failed decrease")

        # Stock must never be negative
        balance = StockBalance.objects.get(inventory_item=self.item, storage_location=self.location)
        self.assertGreaterEqual(balance.quantity, Decimal("0.000"))

        # Stock is either 3 KG (A won) or 4 KG (B won)
        self.assertIn(balance.quantity, [Decimal("3.000"), Decimal("4.000")])

    def test_stock_never_negative_concurrent(self):
        """
        10 threads each try to remove 2 KG (total demand = 20 KG > stock = 10 KG).
        Final balance must be >= 0.
        Exactly 5 should succeed (5 × 2 = 10 KG).
        """
        results = {"success": 0, "failed": 0}
        lock = threading.Lock()

        def attempt():
            try:
                services.decrease_stock(
                    inventory_item=self.item,
                    storage_location=self.location,
                    quantity=Decimal("2.000"),
                    movement_type=MOVEMENT_WASTAGE,
                    performed_by=self.manager,
                    reason="Mass concurrency test",
                )
                with lock:
                    results["success"] += 1
            except ValidationError:
                with lock:
                    results["failed"] += 1

        threads = [threading.Thread(target=attempt) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        balance = StockBalance.objects.get(inventory_item=self.item, storage_location=self.location)
        # Stock must never be negative
        self.assertGreaterEqual(balance.quantity, Decimal("0.000"))
        # Exactly 5 should succeed (5 × 2 = 10)
        self.assertEqual(results["success"], 5)
        self.assertEqual(results["failed"], 5)
        self.assertEqual(balance.quantity, Decimal("0.000"))


class TestConcurrentPurchaseNumberGeneration(TransactionTestCase):
    """
    Concurrent PO number generation must produce unique, non-duplicated numbers.
    """

    def setUp(self):
        self.org = Organization.objects.create(name="Seq Org", slug="seq-org", currency="INR")
        self.restaurant = Restaurant.objects.create(
            organization=self.org, name="Seq Restaurant", slug="seq-rest", code="SR01"
        )
        RestaurantSettings.objects.create(restaurant=self.restaurant)

    def test_concurrent_po_numbers_are_unique(self):
        """
        10 threads concurrently generate PO numbers.
        All 10 numbers must be unique — no duplicates.
        """
        from django.db import transaction

        numbers = []
        lock = threading.Lock()

        def generate():
            try:
                with transaction.atomic():
                    number = services.generate_purchase_number(self.restaurant)
                with lock:
                    numbers.append(number)
            except Exception:
                pass

        threads = [threading.Thread(target=generate) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All successfully generated numbers must be unique
        self.assertEqual(len(numbers), len(set(numbers)), "Duplicate PO numbers detected")
        self.assertEqual(len(numbers), 10, "Not all threads generated a number")
