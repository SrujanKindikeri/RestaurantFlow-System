# =============================================================================
# RestaurantFlow — Receipt Print Tests
# Phase 19: Advanced POS & Restaurant Operations
# =============================================================================

from decimal import Decimal

from django.test import TestCase

from operations.tests.base import OperationsTestBase
from operations.print_services import log_receipt_print, build_receipt_data
from operations.exceptions import ReceiptPrintNotAllowed
from operations.constants import PRINT_ORIGINAL, PRINT_REPRINT, PRINT_DUPLICATE


def _make_finalized_bill(order, cashier):
    """Create a finalized bill for testing."""
    from billing.models import Bill, BillStatus, BillItem
    bill = Bill.objects.create(
        order=order, branch=order.branch,
        bill_number=f"B-2026-{Bill.objects.count() + 1:06d}",
        status=BillStatus.FINALIZED,
        subtotal=Decimal("350.00"),
        discount_amount=Decimal("0.00"),
        taxable_amount=Decimal("350.00"),
        tax_amount=Decimal("17.50"),
        grand_total=Decimal("367.50"),
        created_by=cashier, finalized_by=cashier,
    )
    order_item = order.items.first()
    BillItem.objects.create(
        bill=bill, order_item=order_item,
        menu_item=order_item.menu_item,
        item_name_snapshot=order_item.item_name_snapshot,
        quantity=order_item.quantity,
        unit_price=order_item.unit_price_snapshot,
        gross_amount=Decimal("350.00"),
        taxable_amount=Decimal("350.00"),
        tax_rate=Decimal("5.000"), tax_code="GST_5",
        tax_amount=Decimal("17.50"), total_amount=Decimal("367.50"),
    )
    return bill


class ReceiptPrintLogTest(OperationsTestBase):
    """Tests for receipt print logging."""

    def setUp(self):
        self.order = self._make_confirmed_order()
        self.bill = _make_finalized_bill(self.order, self.cashier)

    def test_log_original_print(self):
        log = log_receipt_print(
            bill=self.bill, payment=None,
            printed_by=self.cashier, print_type=PRINT_ORIGINAL,
        )
        self.assertEqual(log.print_type, PRINT_ORIGINAL)
        self.assertEqual(log.printed_by, self.cashier)
        self.assertEqual(log.bill, self.bill)

    def test_log_reprint_requires_reason(self):
        with self.assertRaises(ReceiptPrintNotAllowed):
            log_receipt_print(
                bill=self.bill, payment=None,
                printed_by=self.cashier, print_type=PRINT_REPRINT,
                reason="",  # empty reason should raise
            )

    def test_log_reprint_with_reason_succeeds(self):
        log = log_receipt_print(
            bill=self.bill, payment=None,
            printed_by=self.cashier, print_type=PRINT_REPRINT,
            reason="Customer requested duplicate",
        )
        self.assertEqual(log.print_type, PRINT_REPRINT)
        self.assertEqual(log.reason, "Customer requested duplicate")

    def test_log_duplicate_requires_reason(self):
        with self.assertRaises(ReceiptPrintNotAllowed):
            log_receipt_print(
                bill=self.bill, payment=None,
                printed_by=self.cashier, print_type=PRINT_DUPLICATE,
                reason="",
            )

    def test_print_log_is_immutable(self):
        """ReceiptPrintLog records cannot be edited after creation."""
        log = log_receipt_print(
            bill=self.bill, payment=None,
            printed_by=self.cashier, print_type=PRINT_ORIGINAL,
        )
        log.reason = "tampered"
        with self.assertRaises(ValueError):
            log.save()

    def test_print_log_creates_audit(self):
        from operations.models import OperationsAuditLog
        from operations.constants import AUDIT_RECEIPT_PRINTED

        log_receipt_print(
            bill=self.bill, payment=None,
            printed_by=self.cashier, print_type=PRINT_ORIGINAL,
        )
        self.assertTrue(
            OperationsAuditLog.objects.filter(
                event_type=AUDIT_RECEIPT_PRINTED,
                bill_id=self.bill.id,
            ).exists()
        )

    def test_reprint_creates_reprint_audit(self):
        from operations.models import OperationsAuditLog
        from operations.constants import AUDIT_RECEIPT_REPRINTED

        log_receipt_print(
            bill=self.bill, payment=None,
            printed_by=self.cashier, print_type=PRINT_REPRINT,
            reason="Customer lost receipt",
        )
        self.assertTrue(
            OperationsAuditLog.objects.filter(
                event_type=AUDIT_RECEIPT_REPRINTED,
            ).exists()
        )


class ReceiptDataBuilderTest(OperationsTestBase):
    """Tests for build_receipt_data."""

    def setUp(self):
        self.order = self._make_confirmed_order()
        self.bill = _make_finalized_bill(self.order, self.cashier)

    def test_receipt_data_structure(self):
        data = build_receipt_data(self.bill)
        self.assertIn("bill_number", data)
        self.assertIn("order_number", data)
        self.assertIn("items", data)
        self.assertIn("grand_total", data)
        self.assertIn("branch", data)

    def test_receipt_data_uses_snapshot_prices(self):
        """Receipt uses snapshot prices — never live menu prices."""
        data = build_receipt_data(self.bill)
        item = data["items"][0]
        self.assertEqual(item["unit_price"], "350.00")

    def test_receipt_data_no_payment_credentials(self):
        """Receipt data never contains payment credentials."""
        data = build_receipt_data(self.bill)
        data_str = str(data)
        # Ensure no credential-like fields appear
        self.assertNotIn("card_number", data_str)
        self.assertNotIn("cvv", data_str)
        self.assertNotIn("upi_pin", data_str)

    def test_receipt_branch_info(self):
        data = build_receipt_data(self.bill)
        self.assertEqual(data["branch"]["name"], self.branch.name)
