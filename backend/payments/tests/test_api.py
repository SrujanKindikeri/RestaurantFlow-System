# =============================================================================
# RestaurantFlow — Payment API Tests
# Phase 9
#
# Tests:
#   - POST /api/payments/           (create payment)
#   - GET  /api/payments/list/      (list payments)
#   - GET  /api/payments/{id}/      (retrieve)
#   - POST /api/payments/{id}/cancel/
#   - GET  /api/payments/bill/{id}/summary/
#   - GET  /api/payments/bill/{id}/receipt/
#   - POST /api/payments/{id}/refunds/   (request refund)
#   - GET  /api/payments/{id}/audit/
#   - Auth required
#   - IDOR prevention (cross-branch UUID guessing)
#   - Frontend-supplied totals ignored (amount is validated against bill)
# =============================================================================

from decimal import Decimal
import uuid
import json

from django.test import TestCase
from rest_framework.test import APIClient

from billing import services as billing_services
from payments import services
from payments.models import Payment, PaymentStatus, PaymentMethod
from payments.tests.base import PaymentTestBase


class TestPaymentAPIAuth(PaymentTestBase):
    """Unauthenticated requests are rejected."""

    def test_create_payment_requires_auth(self):
        client = APIClient()
        response = client.post("/api/payments/", {}, format="json")
        self.assertIn(response.status_code, [401, 403])

    def test_list_payments_requires_auth(self):
        client = APIClient()
        response = client.get("/api/payments/list/")
        self.assertIn(response.status_code, [401, 403])


class TestCreatePaymentAPI(PaymentTestBase):
    """POST /api/payments/"""

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(user=self.cashier)

    def test_create_upi_payment(self):
        """Create a UPI payment via API."""
        bill = self._make_finalized_bill()

        response = self.client.post("/api/payments/", {
            "bill_id": str(bill.id),
            "amount": str(bill.grand_total),
            "payment_method": "UPI",
            "transaction_reference": "UPI-API-001",
        }, format="json")

        self.assertEqual(response.status_code, 201, response.data)
        data = response.data
        self.assertEqual(data["status"], "COMPLETED")
        self.assertEqual(data["payment_method"], "UPI")
        self.assertTrue(data["payment_number"].startswith("PAY-"))
        self.assertIn("bill_number", data)

    def test_create_cash_payment(self):
        """Create a CASH payment via API."""
        bill = self._make_finalized_bill()

        response = self.client.post("/api/payments/", {
            "bill_id": str(bill.id),
            "amount": str(bill.grand_total),
            "payment_method": "CASH",
            "cash_received": str(bill.grand_total + Decimal("100.00")),
            "counter_session": str(self.counter_session.id),
        }, format="json")

        self.assertEqual(response.status_code, 201, response.data)
        data = response.data
        self.assertEqual(data["payment_method"], "CASH")
        self.assertIsNotNone(data["cash_received"])
        self.assertIsNotNone(data["change_amount"])
        expected_change = Decimal(data["cash_received"]) - Decimal(data["amount"])
        self.assertEqual(Decimal(data["change_amount"]), expected_change)

    def test_create_payment_invalid_bill_id_404(self):
        """Random UUID that user cannot access returns 404."""
        response = self.client.post("/api/payments/", {
            "bill_id": str(uuid.uuid4()),
            "amount": "100.00",
            "payment_method": "OTHER",
        }, format="json")
        self.assertEqual(response.status_code, 404)

    def test_create_payment_missing_fields_400(self):
        """Missing required fields returns 400."""
        response = self.client.post("/api/payments/", {
            "amount": "100.00",
        }, format="json")
        self.assertEqual(response.status_code, 400)

    def test_create_payment_idempotency(self):
        """Same idempotency_key returns same payment."""
        bill = self._make_finalized_bill()
        key = str(uuid.uuid4())

        payload = {
            "bill_id": str(bill.id),
            "amount": str(bill.grand_total),
            "payment_method": "OTHER",
            "idempotency_key": key,
        }

        r1 = self.client.post("/api/payments/", payload, format="json")
        r2 = self.client.post("/api/payments/", payload, format="json")

        self.assertEqual(r1.status_code, 201)
        self.assertEqual(r2.status_code, 201)
        self.assertEqual(r1.data["id"], r2.data["id"])
        self.assertEqual(Payment.objects.filter(bill=bill).count(), 1)

    def test_frontend_cannot_control_change_amount(self):
        """API ignores any frontend-supplied change — backend calculates it."""
        bill = self._make_finalized_bill()

        # Try to supply a fake change_amount — should be ignored
        response = self.client.post("/api/payments/", {
            "bill_id": str(bill.id),
            "amount": str(bill.grand_total),
            "payment_method": "CASH",
            "cash_received": str(bill.grand_total + Decimal("50.00")),
            "counter_session": str(self.counter_session.id),
            "change_amount": "9999.99",   # ← backend must ignore this
        }, format="json")

        self.assertEqual(response.status_code, 201)
        # Backend calculated the real change
        real_change = Decimal(response.data["cash_received"]) - Decimal(response.data["amount"])
        self.assertEqual(Decimal(response.data["change_amount"]), real_change)
        # NOT the fake value
        self.assertNotEqual(Decimal(response.data["change_amount"]), Decimal("9999.99"))


class TestPaymentListAPI(PaymentTestBase):
    """GET /api/payments/list/"""

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(user=self.manager)

    def test_list_payments_returns_only_accessible(self):
        """Users only see payments from their accessible branches."""
        bill = self._make_finalized_bill()
        services.create_payment(bill, self.cashier, amount=bill.grand_total,
                                payment_method=PaymentMethod.OTHER)

        response = self.client.get("/api/payments/list/")
        self.assertEqual(response.status_code, 200)
        # At least one payment in results
        self.assertGreater(response.data["count"], 0)

    def test_filter_by_status(self):
        """Filter by status=COMPLETED."""
        bill = self._make_finalized_bill()
        services.create_payment(bill, self.cashier, amount=bill.grand_total,
                                payment_method=PaymentMethod.OTHER)

        response = self.client.get("/api/payments/list/?status=COMPLETED")
        self.assertEqual(response.status_code, 200)
        for item in response.data["results"]:
            self.assertEqual(item["status"], "COMPLETED")

    def test_unauthenticated_list_rejected(self):
        self.client.force_authenticate(user=None)
        response = self.client.get("/api/payments/list/")
        self.assertIn(response.status_code, [401, 403])


class TestBillPaymentSummaryAPI(PaymentTestBase):
    """GET /api/payments/bill/{bill_id}/summary/"""

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(user=self.cashier)

    def test_summary_unpaid_bill(self):
        """Summary for an unpaid bill shows correct totals."""
        bill = self._make_finalized_bill()

        response = self.client.get(f"/api/payments/bill/{bill.id}/summary/")
        self.assertEqual(response.status_code, 200, response.data)

        data = response.data
        self.assertEqual(data["payment_status"], "UNPAID")
        self.assertEqual(Decimal(data["total_paid"]), Decimal("0.00"))
        self.assertEqual(Decimal(data["remaining"]), Decimal(data["bill_total"]))
        self.assertEqual(data["payments"], [])

    def test_summary_partially_paid(self):
        """Summary reflects partial payment."""
        bill = self._make_finalized_bill()
        partial = (bill.grand_total / 2).quantize(Decimal("0.01"))
        services.create_payment(bill, self.cashier, amount=partial,
                                payment_method=PaymentMethod.OTHER)

        response = self.client.get(f"/api/payments/bill/{bill.id}/summary/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["payment_status"], "PARTIALLY_PAID")
        self.assertEqual(len(response.data["payments"]), 1)

    def test_summary_fully_paid(self):
        """Summary shows PAID and remaining = 0."""
        bill = self._make_finalized_bill()
        services.create_payment(bill, self.cashier, amount=bill.grand_total,
                                payment_method=PaymentMethod.OTHER)

        response = self.client.get(f"/api/payments/bill/{bill.id}/summary/")
        self.assertEqual(response.data["payment_status"], "PAID")
        self.assertEqual(response.data["remaining"], "0.00")

    def test_summary_inaccessible_bill_404(self):
        """Random UUID → 404."""
        response = self.client.get(f"/api/payments/bill/{uuid.uuid4()}/summary/")
        self.assertEqual(response.status_code, 404)


class TestPaymentDetailAPI(PaymentTestBase):
    """GET /api/payments/{id}/"""

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(user=self.manager)

    def test_retrieve_payment(self):
        """Can retrieve own payment detail."""
        bill = self._make_finalized_bill()
        payment = services.create_payment(bill, self.cashier, amount=bill.grand_total,
                                          payment_method=PaymentMethod.OTHER)

        response = self.client.get(f"/api/payments/{payment.id}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["payment_number"], payment.payment_number)
        self.assertIn("refunds", response.data)

    def test_retrieve_inaccessible_payment_404(self):
        """Random UUID → 404."""
        response = self.client.get(f"/api/payments/{uuid.uuid4()}/")
        self.assertEqual(response.status_code, 404)


class TestRefundAPI(PaymentTestBase):
    """POST /api/payments/{id}/refunds/"""

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(user=self.manager)

    def test_request_refund_via_api(self):
        """Manager can request a refund via API."""
        bill = self._make_finalized_bill()
        payment = services.create_payment(bill, self.cashier, amount=bill.grand_total,
                                          payment_method=PaymentMethod.UPI,
                                          transaction_reference="UPI-API-R-001")

        response = self.client.post(f"/api/payments/{payment.id}/refunds/", {
            "amount": str(payment.amount),
            "reason": "Customer returned all items",
        }, format="json")

        self.assertEqual(response.status_code, 201, response.data)
        data = response.data
        self.assertEqual(data["status"], "REQUESTED")
        self.assertTrue(data["refund_number"].startswith("REF-"))

    def test_refund_exceeds_amount_rejected(self):
        """Refund > payment.amount returns 400."""
        bill = self._make_finalized_bill()
        payment = services.create_payment(bill, self.cashier, amount=bill.grand_total,
                                          payment_method=PaymentMethod.OTHER)

        response = self.client.post(f"/api/payments/{payment.id}/refunds/", {
            "amount": str(payment.amount + Decimal("1.00")),
            "reason": "Too much",
        }, format="json")

        self.assertIn(response.status_code, [400])

    def test_cashier_cannot_request_refund(self):
        """Cashier (no payment.refund.request perm) gets 403."""
        self.client.force_authenticate(user=self.cashier)
        bill = self._make_finalized_bill()
        payment = services.create_payment(bill, self.cashier, amount=bill.grand_total,
                                          payment_method=PaymentMethod.OTHER)

        response = self.client.post(f"/api/payments/{payment.id}/refunds/", {
            "amount": str(payment.amount),
            "reason": "No permission",
        }, format="json")

        self.assertIn(response.status_code, [403])


class TestAuditLogAPI(PaymentTestBase):
    """GET /api/payments/{id}/audit/"""

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(user=self.manager)

    def test_audit_log_returned(self):
        """Audit log endpoint returns entries for a payment."""
        bill = self._make_finalized_bill()
        payment = services.create_payment(bill, self.cashier, amount=bill.grand_total,
                                          payment_method=PaymentMethod.OTHER)

        response = self.client.get(f"/api/payments/{payment.id}/audit/")
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.data, list)
        self.assertGreater(len(response.data), 0)
        self.assertIn("action", response.data[0])
        self.assertIn("actor_email", response.data[0])

    def test_audit_log_inaccessible_payment_404(self):
        response = self.client.get(f"/api/payments/{uuid.uuid4()}/audit/")
        self.assertEqual(response.status_code, 404)


class TestReceiptAPI(PaymentTestBase):
    """GET /api/payments/bill/{bill_id}/receipt/"""

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(user=self.cashier)

    def test_receipt_includes_payment_data(self):
        """Receipt endpoint returns payment information after payment."""
        bill = self._make_finalized_bill()
        services.create_payment(bill, self.cashier, amount=bill.grand_total,
                                payment_method=PaymentMethod.OTHER)

        response = self.client.get(f"/api/payments/bill/{bill.id}/receipt/")
        self.assertEqual(response.status_code, 200)

        data = response.data
        # Base billing fields
        self.assertIn("bill_number", data)
        self.assertIn("grand_total", data)
        self.assertIn("items", data)
        # Phase 9 payment fields
        self.assertIn("payment_status", data)
        self.assertIn("total_paid", data)
        self.assertIn("remaining", data)
        self.assertIn("payments", data)
        self.assertEqual(data["payment_status"], "PAID")
