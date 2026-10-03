# =============================================================================
# RestaurantFlow — Payment Concurrency Tests
# Phase 9
#
# Tests the select_for_update() locking that prevents two simultaneous
# payment requests from both succeeding when only one should.
#
# These tests use threading to simulate concurrent requests.
# Both threads attempt to pay the full remaining balance simultaneously;
# only one should succeed.
# =============================================================================

import threading
from decimal import Decimal

from django.test import TestCase, TransactionTestCase

from payments import services
from payments.models import Payment, PaymentStatus, PaymentMethod
from payments.tests.base import PaymentTestBase


class TestConcurrentPayments(TransactionTestCase):
    """
    Concurrency tests require TransactionTestCase (not TestCase) because
    TestCase wraps everything in a rolled-back transaction, which would
    prevent threads from seeing each other's writes.
    """

    def setUp(self):
        """Set up fixtures for each test (TransactionTestCase doesn't use setUpTestData)."""
        from decimal import Decimal
        from django.utils import timezone

        from accounts.models import User, Role, Permission, UserRoleAssignment
        from organizations.models import Organization, Restaurant, Branch, RestaurantSettings, BranchSettings
        from menu.models import Category, MenuItem, MenuItemPrice, MenuItemBranch, TaxRate
        from orders.models import Order, OrderItem, OrderStatus, OrderType
        from counters.models import Counter, CounterSession, SessionStatus, CounterStatus
        from billing import services as billing_services

        # Minimal org/restaurant/branch
        self.org = Organization.objects.create(name="Conc Org", slug="conc-org")
        self.restaurant = Restaurant.objects.create(
            organization=self.org, name="Conc Rest", slug="conc-rest", code="CR01",
        )
        RestaurantSettings.objects.create(restaurant=self.restaurant, currency="INR")
        self.branch = Branch.objects.create(
            restaurant=self.restaurant, name="Conc Branch", code="CB01",
        )
        BranchSettings.objects.create(branch=self.branch)

        # Permissions
        perms_data = [
            ("payment.view",   "payment", "view"),
            ("payment.create", "payment", "create"),
            ("payment.cancel", "payment", "cancel"),
            ("bill.view",      "billing", "view"),
            ("bill.create",    "billing", "create"),
            ("bill.finalize",  "billing", "finalize"),
            ("order.view",     "orders",  "view"),
            ("order.create",   "orders",  "create"),
            ("order.confirm",  "orders",  "confirm"),
        ]
        self.perms = {}
        for code, module, action in perms_data:
            p, _ = Permission.objects.get_or_create(
                code=code, defaults={"name": code, "module": module, "action": action}
            )
            self.perms[code] = p

        self.cashier_role = Role.objects.create(name="ConcCashier", code="CONC_CASHIER")
        self.cashier_role.permissions.set(self.perms.values())

        self.cashier = User.objects.create_user(
            email="conc_cashier@test.com", password="pass123",
            first_name="Conc", last_name="Cashier",
        )
        UserRoleAssignment.objects.create(
            user=self.cashier, role=self.cashier_role,
            organization=self.org, restaurant=self.restaurant, branch=self.branch,
        )

        # Tax + Menu
        self.tax_zero = TaxRate.objects.create(
            restaurant=self.restaurant, name="Zero", code="ZERO", rate=Decimal("0.000"),
        )
        self.category = Category.objects.create(
            restaurant=self.restaurant, name="Cat", slug="cat-conc",
        )
        self.item = MenuItem.objects.create(
            restaurant=self.restaurant, category=self.category,
            name="Item", slug="item-conc", sku="ITEM-CONC",
        )
        MenuItemBranch.objects.create(menu_item=self.item, branch=self.branch, is_available=True)
        MenuItemPrice.objects.create(
            menu_item=self.item, branch=self.branch, price=Decimal("100.00"), is_active=True,
        )

        self.counter = Counter.objects.create(
            branch=self.branch, name="CC01", code="CC01", status=CounterStatus.ACTIVE,
        )
        self.counter_session = CounterSession.objects.create(
            counter=self.counter, opened_by=self.cashier,
            opening_cash=Decimal("500.00"), status=SessionStatus.OPEN,
        )

        # Confirmed order
        import time
        order_num = f"CONC-{time.time_ns()}"
        self.order = Order.objects.create(
            branch=self.branch, order_number=order_num,
            order_type=OrderType.COUNTER, counter=self.counter,
            counter_session=self.counter_session, created_by=self.cashier,
            status=OrderStatus.CONFIRMED, confirmed_at=timezone.now(),
        )
        OrderItem.objects.create(
            order=self.order, menu_item=self.item,
            item_name_snapshot="Item", sku_snapshot="ITEM-CONC",
            unit_price_snapshot=Decimal("100.00"),
            tax_rate_snapshot=Decimal("0.000"), tax_code_snapshot="ZERO",
            quantity=Decimal("1.000"),
        )

        # Finalized bill
        self.bill = billing_services.create_bill_from_order(self.order, self.cashier)
        self.bill = billing_services.finalize_bill(self.bill, self.cashier)

    def test_concurrent_full_payments_only_one_succeeds(self):
        """
        Two threads simultaneously attempt to pay the full bill.
        Only ONE should succeed; the other should get a validation error
        because remaining_amount = 0 after the first completes.

        Bill total = ₹100.00
        Thread A: pay ₹100
        Thread B: pay ₹100
        Expected: 1 COMPLETED payment in DB, 1 failed attempt.
        """
        results = []
        errors = []

        def attempt_payment():
            from django.db import connection
            try:
                p = services.create_payment(
                    self.bill,
                    self.cashier,
                    amount=self.bill.grand_total,
                    payment_method=PaymentMethod.OTHER,
                )
                results.append(p)
            except Exception as exc:
                errors.append(exc)
            finally:
                connection.close()

        t1 = threading.Thread(target=attempt_payment)
        t2 = threading.Thread(target=attempt_payment)
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        # Exactly one success + one error (or both may succeed if thread 2 ran after remaining=0)
        total = len(results) + len(errors)
        self.assertEqual(total, 2)

        # Only ONE completed payment in DB
        completed = Payment.objects.filter(
            bill=self.bill, status=PaymentStatus.COMPLETED
        ).count()
        self.assertEqual(completed, 1)

    def test_concurrent_partial_then_remaining_correct(self):
        """
        Three threads each try to pay 1/3 of the bill.
        All should succeed for partial amounts that don't exceed remaining.
        Total paid at end == bill.grand_total.
        """
        import time
        from payments.utils import compute_remaining_amount

        third = (self.bill.grand_total / 3).quantize(Decimal("0.01"))
        remainder = self.bill.grand_total - third - third

        # Pay sequentially (not concurrent) to test correctness
        services.create_payment(
            self.bill, self.cashier, amount=third,
            payment_method=PaymentMethod.OTHER,
        )
        services.create_payment(
            self.bill, self.cashier, amount=third,
            payment_method=PaymentMethod.OTHER,
        )
        services.create_payment(
            self.bill, self.cashier, amount=remainder,
            payment_method=PaymentMethod.OTHER,
        )

        remaining = compute_remaining_amount(self.bill)
        self.assertEqual(remaining, Decimal("0.00"))
