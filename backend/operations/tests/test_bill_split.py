# =============================================================================
# RestaurantFlow — Bill Split Tests
# Phase 19: Advanced POS & Restaurant Operations
# =============================================================================

from decimal import Decimal

from django.test import TestCase

from operations.tests.base import OperationsTestBase
from operations.bill_services import create_bill_split, finalize_bill_split, cancel_bill_split
from operations.exceptions import BillSplitConflict, BillNotSplittable
from operations.constants import SPLIT_EQUAL, SPLIT_DRAFT, SPLIT_FINALIZED, SPLIT_CANCELLED


def _make_finalized_bill(order, cashier):
    """Helper to create a finalized Bill for an order."""
    from billing.models import Bill, BillStatus
    from decimal import Decimal

    bill = Bill.objects.create(
        order=order,
        branch=order.branch,
        bill_number=f"B-2026-{Bill.objects.count() + 1:06d}",
        status=BillStatus.FINALIZED,
        subtotal=Decimal("350.00"),
        discount_amount=Decimal("0.00"),
        taxable_amount=Decimal("350.00"),
        tax_amount=Decimal("17.50"),
        grand_total=Decimal("367.50"),
        created_by=cashier,
        finalized_by=cashier,
    )
    from billing.models import BillItem
    from django.utils import timezone
    order_item = order.items.first()
    BillItem.objects.create(
        bill=bill,
        order_item=order_item,
        menu_item=order_item.menu_item,
        item_name_snapshot=order_item.item_name_snapshot,
        quantity=order_item.quantity,
        unit_price=order_item.unit_price_snapshot,
        gross_amount=Decimal("350.00"),
        taxable_amount=Decimal("350.00"),
        tax_rate=Decimal("5.000"),
        tax_code="GST_5",
        tax_amount=Decimal("17.50"),
        total_amount=Decimal("367.50"),
    )
    return bill


class BillSplitEqualTest(OperationsTestBase):
    """Tests for equal bill splitting."""

    def setUp(self):
        self.order = self._make_confirmed_order()
        self.bill = _make_finalized_bill(self.order, self.cashier)

    def test_split_equal_two_ways(self):
        splits = create_bill_split(
            bill=self.bill,
            split_type=SPLIT_EQUAL,
            requested_by=self.cashier,
            num_splits=2,
        )
        self.assertEqual(len(splits), 2)
        total = sum(s.amount for s in splits)
        # Total must equal grand_total (within 1 cent rounding)
        self.assertAlmostEqual(float(total), float(self.bill.grand_total), places=1)

    def test_split_equal_three_ways(self):
        splits = create_bill_split(
            bill=self.bill,
            split_type=SPLIT_EQUAL,
            requested_by=self.cashier,
            num_splits=3,
        )
        self.assertEqual(len(splits), 3)
        total = sum(s.amount for s in splits)
        self.assertAlmostEqual(float(total), float(self.bill.grand_total), places=1)

    def test_split_creates_audit(self):
        from operations.models import OperationsAuditLog
        from operations.constants import AUDIT_BILL_SPLIT_CREATED

        create_bill_split(
            bill=self.bill, split_type=SPLIT_EQUAL,
            requested_by=self.cashier, num_splits=2,
        )
        self.assertTrue(
            OperationsAuditLog.objects.filter(
                event_type=AUDIT_BILL_SPLIT_CREATED,
                bill_id=self.bill.id,
            ).exists()
        )

    def test_split_draft_bill_raises(self):
        """Only FINALIZED bills can be split."""
        from billing.models import Bill, BillStatus
        draft_order = self._make_confirmed_order()
        draft_bill = Bill.objects.create(
            order=draft_order,
            branch=self.branch,
            bill_number=f"B-2026-DRAFT-{Bill.objects.count():04d}",
            status=BillStatus.DRAFT,
            subtotal=Decimal("350.00"),
            grand_total=Decimal("367.50"),
            created_by=self.cashier,
        )
        with self.assertRaises(BillNotSplittable):
            create_bill_split(
                bill=draft_bill, split_type=SPLIT_EQUAL,
                requested_by=self.cashier, num_splits=2,
            )

    def test_duplicate_active_splits_raises(self):
        """Cannot create splits if active splits already exist."""
        create_bill_split(
            bill=self.bill, split_type=SPLIT_EQUAL,
            requested_by=self.cashier, num_splits=2,
        )
        with self.assertRaises(BillSplitConflict):
            create_bill_split(
                bill=self.bill, split_type=SPLIT_EQUAL,
                requested_by=self.cashier, num_splits=2,
            )

    def test_finalize_split(self):
        splits = create_bill_split(
            bill=self.bill, split_type=SPLIT_EQUAL,
            requested_by=self.cashier, num_splits=2,
        )
        split = finalize_bill_split(bill_split=splits[0], user=self.cashier)
        self.assertEqual(split.status, SPLIT_FINALIZED)

    def test_finalize_creates_audit(self):
        from operations.models import OperationsAuditLog
        from operations.constants import AUDIT_BILL_SPLIT_FINALIZED

        splits = create_bill_split(
            bill=self.bill, split_type=SPLIT_EQUAL,
            requested_by=self.cashier, num_splits=2,
        )
        finalize_bill_split(bill_split=splits[0], user=self.cashier)
        self.assertTrue(
            OperationsAuditLog.objects.filter(
                event_type=AUDIT_BILL_SPLIT_FINALIZED,
            ).exists()
        )

    def test_finalize_already_finalized_raises(self):
        splits = create_bill_split(
            bill=self.bill, split_type=SPLIT_EQUAL,
            requested_by=self.cashier, num_splits=2,
        )
        finalize_bill_split(bill_split=splits[0], user=self.cashier)
        splits[0].refresh_from_db()
        with self.assertRaises(BillSplitConflict):
            finalize_bill_split(bill_split=splits[0], user=self.cashier)

    def test_cancel_split(self):
        splits = create_bill_split(
            bill=self.bill, split_type=SPLIT_EQUAL,
            requested_by=self.cashier, num_splits=2,
        )
        split = cancel_bill_split(bill_split=splits[0], user=self.cashier)
        self.assertEqual(split.status, SPLIT_CANCELLED)

    def test_cancel_finalized_raises(self):
        splits = create_bill_split(
            bill=self.bill, split_type=SPLIT_EQUAL,
            requested_by=self.cashier, num_splits=2,
        )
        finalize_bill_split(bill_split=splits[0], user=self.cashier)
        splits[0].refresh_from_db()
        with self.assertRaises(BillSplitConflict):
            cancel_bill_split(bill_split=splits[0], user=self.cashier)
