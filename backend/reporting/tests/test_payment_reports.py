# =============================================================================
# RestaurantFlow — Payment Report Tests
# Phase 14
# =============================================================================

from decimal import Decimal
from datetime import date

from reporting.tests.base import ReportingTestBase
from reporting import aggregations as agg
from accounts import access as acl


class PaymentSummaryTests(ReportingTestBase):

    def test_completed_payment_counted(self):
        bill = self._make_finalized_bill()
        self._make_payment(bill, amount=Decimal("525.00"), method="CASH", status="COMPLETED")
        branches = acl.get_accessible_branches(self.manager_a)
        result = agg.aggregate_payment_summary(branches, date.today(), date.today())
        self.assertEqual(result["payment_count"], 1)
        self.assertEqual(result["total_paid"], Decimal("525.00"))

    def test_pending_payment_excluded(self):
        bill = self._make_finalized_bill()
        self._make_payment(bill, status="PENDING")
        branches = acl.get_accessible_branches(self.manager_a)
        result = agg.aggregate_payment_summary(branches, date.today(), date.today())
        self.assertEqual(result["payment_count"], 0)
        self.assertEqual(result["total_paid"], Decimal("0.00"))

    def test_failed_payment_excluded(self):
        bill = self._make_finalized_bill()
        self._make_payment(bill, status="FAILED")
        branches = acl.get_accessible_branches(self.manager_a)
        result = agg.aggregate_payment_summary(branches, date.today(), date.today())
        self.assertEqual(result["payment_count"], 0)

    def test_cancelled_payment_excluded(self):
        bill = self._make_finalized_bill()
        self._make_payment(bill, status="CANCELLED")
        branches = acl.get_accessible_branches(self.manager_a)
        result = agg.aggregate_payment_summary(branches, date.today(), date.today())
        self.assertEqual(result["payment_count"], 0)

    def test_cash_field_correct(self):
        bill = self._make_finalized_bill()
        self._make_payment(bill, amount=Decimal("525.00"), method="CASH")
        branches = acl.get_accessible_branches(self.manager_a)
        result = agg.aggregate_payment_summary(branches, date.today(), date.today())
        self.assertEqual(result["cash"], Decimal("525.00"))
        self.assertEqual(result["upi"], Decimal("0.00"))

    def test_upi_field_correct(self):
        bill = self._make_finalized_bill()
        self._make_payment(bill, amount=Decimal("525.00"), method="UPI")
        branches = acl.get_accessible_branches(self.manager_a)
        result = agg.aggregate_payment_summary(branches, date.today(), date.today())
        self.assertEqual(result["upi"], Decimal("525.00"))
        self.assertEqual(result["cash"], Decimal("0.00"))

    def test_isolation_between_orgs(self):
        bill = self._make_finalized_bill()
        self._make_payment(bill)
        branches_b = acl.get_accessible_branches(self.manager_b)
        result = agg.aggregate_payment_summary(branches_b, date.today(), date.today())
        self.assertEqual(result["payment_count"], 0)

    def test_payment_methods_distribution(self):
        bill1 = self._make_finalized_bill()
        bill2 = self._make_finalized_bill()
        self._make_payment(bill1, method="CASH")
        self._make_payment(bill2, method="UPI")
        branches = acl.get_accessible_branches(self.manager_a)
        result = agg.aggregate_payment_methods(branches, date.today(), date.today())
        methods = [r["payment_method"] for r in result]
        self.assertIn("CASH", methods)
        self.assertIn("UPI", methods)

    def test_payment_methods_percentages_sum_to_100(self):
        bill1 = self._make_finalized_bill()
        bill2 = self._make_finalized_bill()
        self._make_payment(bill1, method="CASH")
        self._make_payment(bill2, method="UPI")
        branches = acl.get_accessible_branches(self.manager_a)
        result = agg.aggregate_payment_methods(branches, date.today(), date.today())
        total_pct = sum(r["percentage"] for r in result)
        self.assertAlmostEqual(float(total_pct), 100.0, places=1)


class RefundTests(ReportingTestBase):

    def _make_processed_refund(self, payment, amount=None):
        from payments.models import PaymentRefund, RefundStatus
        from django.utils import timezone as tz
        ts = tz.now().strftime("%Y%m%d%H%M%S%f")
        return PaymentRefund.objects.create(
            payment=payment,
            refund_number=f"REF-{ts}",
            amount=amount or payment.amount,
            status=RefundStatus.PROCESSED,
            reason="Customer request",
            requested_by=self.manager_a,
            processed_by=self.manager_a,
            processed_at=tz.now(),
        )

    def test_processed_refund_counted(self):
        bill = self._make_finalized_bill()
        payment = self._make_payment(bill)
        self._make_processed_refund(payment, amount=Decimal("100.00"))
        branches = acl.get_accessible_branches(self.manager_a)
        result = agg.aggregate_refunds(branches, date.today(), date.today())
        self.assertEqual(result["refund_count"], 1)
        self.assertEqual(result["refund_amount"], Decimal("100.00"))

    def test_requested_refund_not_counted(self):
        from payments.models import PaymentRefund, RefundStatus
        from django.utils import timezone as tz
        bill = self._make_finalized_bill()
        payment = self._make_payment(bill)
        ts = tz.now().strftime("%Y%m%d%H%M%S%f")
        PaymentRefund.objects.create(
            payment=payment, refund_number=f"REF-{ts}",
            amount=Decimal("100.00"), status=RefundStatus.REQUESTED,
            reason="Customer request", requested_by=self.manager_a,
        )
        branches = acl.get_accessible_branches(self.manager_a)
        result = agg.aggregate_refunds(branches, date.today(), date.today())
        self.assertEqual(result["refund_count"], 0)

    def test_refund_percentage_of_sales(self):
        bill = self._make_finalized_bill(grand_total=Decimal("1000.00"))
        payment = self._make_payment(bill, amount=Decimal("1000.00"))
        self._make_processed_refund(payment, amount=Decimal("100.00"))
        branches = acl.get_accessible_branches(self.manager_a)
        result = agg.aggregate_refunds(branches, date.today(), date.today())
        # 100 refund / 1000 sales * 100 = 10%
        self.assertIsNotNone(result["percentage_of_sales"])
        self.assertAlmostEqual(float(result["percentage_of_sales"]), 10.0, places=1)
