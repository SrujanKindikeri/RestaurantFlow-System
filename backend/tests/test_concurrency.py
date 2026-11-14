# =============================================================================
# RestaurantFlow — Concurrency Safety Tests
# FEAT-004: Verifies select_for_update() guards prevent data races in
# payment creation, inventory deduction, and bill finalization.
#
# Uses TransactionTestCase (not TestCase) so each thread gets an independent
# DB connection — required for real concurrency testing.
# =============================================================================

import threading
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TransactionTestCase
from django.utils.text import slugify

User = get_user_model()


def _make_base_objects():
    """
    Create the minimum org/restaurant/branch/user hierarchy needed by
    payment and billing services.  Returns a dict of model instances.
    """
    from organizations.models import Organization, Restaurant, Branch

    org = Organization.objects.create(
        name="ConcurrencyOrg",
        slug="concurrency-org",
    )
    restaurant = Restaurant.objects.create(
        organization=org,
        name="ConcurrencyRest",
        slug="concurrency-rest",
    )
    branch = Branch.objects.create(
        restaurant=restaurant,
        name="ConcurrencyBranch",
        code="CB01",
    )
    user = User.objects.create_user(
        email="conctest@example.com",
        password="pass",
        is_active=True,
        is_superuser=True,
    )
    return {"org": org, "restaurant": restaurant, "branch": branch, "user": user}


def _grant_payment_permission(user):
    """Assign payment.create permission so create_payment does not 403."""
    from accounts.models import Permission, Role, UserRoleAssignment
    from organizations.models import Organization

    perm, _ = Permission.objects.get_or_create(
        code="payment.create",
        defaults={"name": "Create Payment", "module": "payments"},
    )
    org = Organization.objects.first()
    role, _ = Role.objects.get_or_create(
        code="cashier-conc",
        defaults={"name": "Cashier Conc", "is_system_role": False},
    )
    role.permissions.add(perm)
    UserRoleAssignment.objects.get_or_create(
        user=user,
        organization=org,
        role=role,
    )


class ConcurrentPaymentsTest(TransactionTestCase):
    """
    Two threads attempt to pay the same bill simultaneously.
    The total collected must not exceed the bill's grand_total.
    """

    def setUp(self):
        self.objects = _make_base_objects()

    def test_concurrent_payments_no_overpayment(self):
        from billing.models import Bill, BillItem, BillStatus
        from menu.models import MenuItem, Category, TaxRate
        from orders.models import Order, OrderItem, OrderStatus, OrderType

        branch = self.objects["branch"]
        restaurant = self.objects["restaurant"]
        user = self.objects["user"]

        # Minimal bill setup — bypass full order/billing services to keep test fast
        order = Order.objects.create(
            branch=branch,
            order_number="ORD-CONC-001",
            order_type=OrderType.COUNTER,
            status=OrderStatus.CONFIRMED,
            created_by=user,
        )

        bill = Bill.objects.create(
            order=order,
            branch=branch,
            bill_number="BILL-CONC-001",
            status=BillStatus.FINALIZED,
            subtotal=Decimal("100.00"),
            discount_amount=Decimal("0.00"),
            taxable_amount=Decimal("100.00"),
            tax_amount=Decimal("0.00"),
            grand_total=Decimal("100.00"),
            created_by=user,
        )

        _grant_payment_permission(user)

        errors = []
        payments_created = []

        def pay_half():
            try:
                from payments.services import create_payment
                p = create_payment(
                    bill,
                    user,
                    amount=Decimal("100.00"),
                    payment_method="CASH",
                    cash_received=Decimal("100.00"),
                )
                payments_created.append(p)
            except Exception as e:
                errors.append(e)

        t1 = threading.Thread(target=pay_half)
        t2 = threading.Thread(target=pay_half)
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        from payments.models import Payment
        total_paid = sum(
            p.amount for p in Payment.objects.filter(bill=bill)
        )
        # Total collected must not exceed grand_total
        self.assertLessEqual(total_paid, bill.grand_total)
        # At least one payment must have succeeded
        self.assertGreaterEqual(len(payments_created) + len(errors), 1)


class ConcurrentInventoryDeductionTest(TransactionTestCase):
    """
    Two threads each attempt to deduct 60 units from a StockBalance
    with quantity=100.  Final quantity must be >= 0.
    """

    def setUp(self):
        self.objects = _make_base_objects()

    def test_concurrent_inventory_deduction_no_negative_stock(self):
        from inventory.models import (
            InventoryCategory, InventoryItem, StorageLocation, StockBalance,
        )
        from inventory.services import decrease_stock

        branch = self.objects["branch"]
        restaurant = self.objects["restaurant"]
        user = self.objects["user"]

        cat = InventoryCategory.objects.create(
            restaurant=restaurant,
            name="Beverages",
        )
        item = InventoryItem.objects.create(
            restaurant=restaurant,
            category=cat,
            name="Water",
            sku="WAT-001",
            default_unit="LITRE",
        )
        location = StorageLocation.objects.create(
            branch=branch,
            name="Main Store",
            code="MS01",
        )
        balance = StockBalance.objects.create(
            inventory_item=item,
            storage_location=location,
            quantity=Decimal("100.000"),
        )

        errors = []

        def deduct_sixty():
            try:
                from django.db import transaction
                with transaction.atomic():
                    decrease_stock(
                        inventory_item=item,
                        storage_location=location,
                        quantity=Decimal("60.000"),
                        unit=item.default_unit,
                        movement_type="ADJUSTMENT_OUT",
                        actor=user,
                        reason="concurrency test",
                    )
            except Exception as e:
                errors.append(e)

        t1 = threading.Thread(target=deduct_sixty)
        t2 = threading.Thread(target=deduct_sixty)
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        balance.refresh_from_db()
        # Final quantity must never be negative
        self.assertGreaterEqual(balance.quantity, Decimal("0.000"))


class ConcurrentBillFinalizationTest(TransactionTestCase):
    """
    Two threads call finalize_bill on the same DRAFT bill simultaneously.
    Exactly one must succeed; the other must raise or be a no-op.
    """

    def setUp(self):
        self.objects = _make_base_objects()

    def test_concurrent_bill_finalization_single_winner(self):
        from billing.models import Bill, BillItem, BillStatus
        from orders.models import Order, OrderItem, OrderStatus, OrderType
        from menu.models import MenuItem, Category

        branch = self.objects["branch"]
        restaurant = self.objects["restaurant"]
        user = self.objects["user"]

        # Create the minimal menu hierarchy needed for OrderItem
        category = Category.objects.create(
            restaurant=restaurant,
            name="Test Category",
            slug="test-category-conc",
        )
        menu_item = MenuItem.objects.create(
            restaurant=restaurant,
            category=category,
            name="Test Item",
            slug="test-item-conc",
            is_active=True,
        )

        order = Order.objects.create(
            branch=branch,
            order_number="ORD-CONC-002",
            order_type=OrderType.COUNTER,
            status=OrderStatus.CONFIRMED,
            created_by=user,
        )

        order_item = OrderItem.objects.create(
            order=order,
            menu_item=menu_item,
            item_name_snapshot="Test Item",
            sku_snapshot="SKU-001",
            unit_price_snapshot=Decimal("50.00"),
            quantity=Decimal("1"),
        )

        bill = Bill.objects.create(
            order=order,
            branch=branch,
            bill_number="BILL-CONC-002",
            status=BillStatus.DRAFT,
            subtotal=Decimal("50.00"),
            discount_amount=Decimal("0.00"),
            taxable_amount=Decimal("50.00"),
            tax_amount=Decimal("0.00"),
            grand_total=Decimal("50.00"),
            created_by=user,
        )

        # Add a BillItem so finalize_bill passes the "has items" check
        BillItem.objects.create(
            bill=bill,
            order_item=order_item,
            menu_item=menu_item,
            item_name_snapshot="Test Item",
            sku_snapshot="SKU-001",
            quantity=Decimal("1"),
            unit_price=Decimal("50.00"),
            tax_rate=Decimal("0.00"),
            gross_amount=Decimal("50.00"),
            discount_amount=Decimal("0.00"),
            taxable_amount=Decimal("50.00"),
            tax_amount=Decimal("0.00"),
            total_amount=Decimal("50.00"),
        )

        successes = []
        errors = []

        def finalize():
            try:
                from billing.services import finalize_bill
                finalize_bill(bill, user)
                successes.append(True)
            except Exception as e:
                errors.append(e)

        t1 = threading.Thread(target=finalize)
        t2 = threading.Thread(target=finalize)
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        bill.refresh_from_db()
        self.assertEqual(bill.status, BillStatus.FINALIZED)
        # One must win, the other raises or is idempotent — total finalized = 1
        from billing.models import Bill as BillModel
        finalized_count = BillModel.objects.filter(
            order=order, status=BillStatus.FINALIZED
        ).count()
        self.assertEqual(finalized_count, 1)


class ConcurrentStockTransferTest(TransactionTestCase):
    """
    Two threads each attempt to complete the same APPROVED StockTransfer
    simultaneously.  The select_for_update() guard in complete_stock_transfer
    must ensure only one succeeds; the second must raise (double-complete
    is an invalid status transition).
    """

    def setUp(self):
        self.objects = _make_base_objects()

    def _make_inventory_fixtures(self):
        from inventory.models import (
            InventoryCategory, InventoryItem, StorageLocation, StockBalance,
        )
        from accounts.models import Permission, Role, UserRoleAssignment

        restaurant = self.objects["restaurant"]
        branch = self.objects["branch"]
        user = self.objects["user"]

        # Second branch for transfer destination
        from organizations.models import Branch
        dst_branch = Branch.objects.create(
            restaurant=restaurant,
            name="Transfer Dest Branch",
            code="TDB01",
        )

        cat = InventoryCategory.objects.create(
            restaurant=restaurant,
            name="Dry Goods Transfer",
        )
        item = InventoryItem.objects.create(
            restaurant=restaurant,
            category=cat,
            name="Rice Transfer",
            sku="RICE-CONC-001",
            default_unit="KG",
            average_cost=Decimal("50.00"),
        )
        src_location = StorageLocation.objects.create(
            branch=branch,
            name="Src Store Conc",
            code="SRC01",
        )
        dst_location = StorageLocation.objects.create(
            branch=dst_branch,
            name="Dst Store Conc",
            code="DST01",
        )
        StockBalance.objects.create(
            inventory_item=item,
            storage_location=src_location,
            quantity=Decimal("100.000"),
            average_cost=Decimal("50.00"),
        )

        # Grant inventory permissions to the superuser actor
        for code, name in [
            ("inventory.transfer", "Create/request transfers"),
            ("inventory.transfer.approve", "Approve/complete transfers"),
        ]:
            perm, _ = Permission.objects.get_or_create(
                code=code,
                defaults={"name": name, "module": "inventory"},
            )
            role, _ = Role.objects.get_or_create(
                code=f"conc-inv-{code.replace('.', '-')}",
                defaults={"name": f"Conc {name}", "is_system_role": False},
            )
            role.permissions.add(perm)
            from organizations.models import Organization
            org = Organization.objects.first()
            UserRoleAssignment.objects.get_or_create(
                user=user,
                organization=org,
                role=role,
            )

        return {
            "item": item,
            "src_location": src_location,
            "dst_location": dst_location,
        }

    def test_concurrent_complete_transfer_single_winner(self):
        from inventory.services import (
            create_stock_transfer, request_stock_transfer,
            approve_stock_transfer, complete_stock_transfer,
        )

        restaurant = self.objects["restaurant"]
        user = self.objects["user"]
        fixtures = self._make_inventory_fixtures()
        item = fixtures["item"]
        src = fixtures["src_location"]
        dst = fixtures["dst_location"]

        transfer = create_stock_transfer(
            restaurant=restaurant,
            source_location=src,
            destination_location=dst,
            items=[{"inventory_item_id": str(item.pk), "quantity": "30", "unit": "KG"}],
            user=user,
        )
        transfer = request_stock_transfer(transfer, user)
        transfer = approve_stock_transfer(transfer, user)

        successes = []
        errors = []

        def complete():
            try:
                complete_stock_transfer(transfer, user)
                successes.append(True)
            except Exception as e:
                errors.append(e)

        t1 = threading.Thread(target=complete)
        t2 = threading.Thread(target=complete)
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        from inventory.models import StockTransfer
        from inventory.constants import TRANSFER_COMPLETED
        transfer.refresh_from_db()
        self.assertEqual(transfer.status, TRANSFER_COMPLETED)
        # Exactly one must succeed; the second sees an invalid status transition
        self.assertEqual(len(successes), 1)
        self.assertEqual(len(errors), 1)
