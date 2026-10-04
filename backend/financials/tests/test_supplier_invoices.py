# =============================================================================
# RestaurantFlow — Supplier Invoice Tests
# Phase 12
# =============================================================================

from decimal import Decimal

from financials.models import SupplierInvoice, Payable
from financials.services import SupplierInvoiceService
from financials.exceptions import InvoiceSupplierMismatch, InvoiceRestaurantMismatch
from financials.tests.base import FinancialTestBase


class SupplierInvoiceCreationTests(FinancialTestBase):
    """Supplier invoice creation — field validation and PO linkage."""

    def _make_supplier(self, restaurant=None, code="SUP001"):
        from inventory.models import Supplier
        rest = restaurant or self.restaurant
        supplier, _ = Supplier.objects.get_or_create(
            restaurant=rest, code=code,
            defaults={"name": f"Supplier {code}"},
        )
        return supplier

    def test_creates_invoice_in_draft_status(self):
        from django.utils import timezone
        supplier = self._make_supplier()
        invoice = SupplierInvoiceService.create_invoice(
            restaurant=self.restaurant,
            supplier=supplier,
            invoice_date=timezone.now().date(),
            user=self.owner,
            subtotal=Decimal("10000.00"),
            tax_amount=Decimal("1800.00"),
        )
        self.assertEqual(invoice.status, "DRAFT")
        self.assertEqual(invoice.total_amount, Decimal("11800.00"))

    def test_invoice_number_is_generated(self):
        invoice = self._create_supplier_invoice()
        self.assertTrue(invoice.invoice_number.startswith("SINV-"))

    def test_supplier_must_belong_to_same_restaurant(self):
        from rest_framework.exceptions import ValidationError
        from inventory.models import Supplier
        from django.utils import timezone
        other_supplier = Supplier.objects.create(
            restaurant=self.other_restaurant,
            name="Wrong Supplier",
            code="WRONG01",
        )
        with self.assertRaises(ValidationError):
            SupplierInvoiceService.create_invoice(
                restaurant=self.restaurant,  # different restaurant
                supplier=other_supplier,     # belongs to other_restaurant
                invoice_date=timezone.now().date(),
                user=self.owner,
            )

    def test_purchase_order_restaurant_mismatch_raises(self):
        from django.utils import timezone
        from inventory.models import Supplier, PurchaseOrder
        supplier = self._make_supplier()
        other_supplier = self._make_supplier(restaurant=self.other_restaurant, code="OSUP")
        # Create a PO for the other restaurant
        other_po = PurchaseOrder.objects.create(
            restaurant=self.other_restaurant,
            branch=self.other_branch,
            supplier=other_supplier,
            purchase_number="PO-999999",
            created_by=self.other_user,
        )
        with self.assertRaises(InvoiceRestaurantMismatch):
            SupplierInvoiceService.create_invoice(
                restaurant=self.restaurant,
                supplier=supplier,
                invoice_date=timezone.now().date(),
                user=self.owner,
                purchase_order=other_po,  # wrong restaurant PO
            )

    def test_purchase_order_supplier_mismatch_raises(self):
        from django.utils import timezone
        from inventory.models import Supplier, PurchaseOrder
        supplier_a = self._make_supplier(code="SUPA")
        supplier_b = self._make_supplier(code="SUPB")
        po = PurchaseOrder.objects.create(
            restaurant=self.restaurant,
            branch=self.branch,
            supplier=supplier_a,          # PO is for supplier A
            purchase_number="PO-888888",
            created_by=self.owner,
        )
        with self.assertRaises(InvoiceSupplierMismatch):
            SupplierInvoiceService.create_invoice(
                restaurant=self.restaurant,
                supplier=supplier_b,          # invoice is for supplier B
                invoice_date=timezone.now().date(),
                user=self.owner,
                purchase_order=po,            # but PO belongs to supplier A
            )

    def test_cancelled_po_cannot_have_invoice(self):
        from rest_framework.exceptions import ValidationError
        from django.utils import timezone
        from inventory.models import Supplier, PurchaseOrder
        supplier = self._make_supplier()
        po = PurchaseOrder.objects.create(
            restaurant=self.restaurant,
            branch=self.branch,
            supplier=supplier,
            purchase_number="PO-777777",
            status="CANCELLED",
            created_by=self.owner,
        )
        with self.assertRaises(ValidationError) as ctx:
            SupplierInvoiceService.create_invoice(
                restaurant=self.restaurant,
                supplier=supplier,
                invoice_date=timezone.now().date(),
                user=self.owner,
                purchase_order=po,
            )
        self.assertIn("CANCELLED", str(ctx.exception.detail))

    def test_negative_total_raises_error(self):
        from rest_framework.exceptions import ValidationError
        from django.utils import timezone
        supplier = self._make_supplier()
        with self.assertRaises(ValidationError):
            SupplierInvoiceService.create_invoice(
                restaurant=self.restaurant,
                supplier=supplier,
                invoice_date=timezone.now().date(),
                user=self.owner,
                subtotal=Decimal("100.00"),
                tax_amount=Decimal("0.00"),
                discount_amount=Decimal("200.00"),  # discount > subtotal → negative total
            )


class SupplierInvoiceWorkflowTests(FinancialTestBase):
    """Supplier invoice state machine: DRAFT → SUBMITTED → APPROVED → CANCELLED."""

    def test_submit_draft_invoice(self):
        invoice = self._create_supplier_invoice()
        submitted = SupplierInvoiceService.submit_invoice(invoice, self.owner)
        self.assertEqual(submitted.status, "SUBMITTED")

    def test_cannot_submit_already_submitted(self):
        from financials.exceptions import InvalidStatusTransition
        invoice = self._create_supplier_invoice()
        SupplierInvoiceService.submit_invoice(invoice, self.owner)
        invoice.refresh_from_db()
        with self.assertRaises(InvalidStatusTransition):
            SupplierInvoiceService.submit_invoice(invoice, self.owner)

    def test_approve_submitted_invoice(self):
        invoice = self._create_supplier_invoice()
        SupplierInvoiceService.submit_invoice(invoice, self.owner)
        invoice.refresh_from_db()
        approved = SupplierInvoiceService.approve_invoice(invoice, self.accountant)
        self.assertEqual(approved.status, "APPROVED")
        self.assertEqual(approved.approved_by, self.accountant)

    def test_approved_invoice_creates_payable(self):
        invoice = self._create_supplier_invoice()
        SupplierInvoiceService.submit_invoice(invoice, self.owner)
        invoice.refresh_from_db()
        SupplierInvoiceService.approve_invoice(invoice, self.accountant)
        self.assertTrue(Payable.objects.filter(supplier_invoice=invoice).exists())

    def test_cancel_draft_invoice(self):
        invoice = self._create_supplier_invoice()
        cancelled = SupplierInvoiceService.cancel_invoice(invoice, self.owner, reason="Error")
        self.assertEqual(cancelled.status, "CANCELLED")

    def test_cancel_also_cancels_payable(self):
        invoice = self._create_supplier_invoice()
        SupplierInvoiceService.submit_invoice(invoice, self.owner)
        invoice.refresh_from_db()
        SupplierInvoiceService.approve_invoice(invoice, self.accountant)
        invoice.refresh_from_db()
        # Now cancel the approved invoice
        SupplierInvoiceService.cancel_invoice(invoice, self.owner, reason="Test cancellation")
        payable = Payable.objects.get(supplier_invoice=invoice)
        self.assertEqual(payable.status, "CANCELLED")

    def test_duplicate_invoice_for_same_po_is_not_prevented_at_service_level(self):
        """
        Multiple invoices per PO are not prevented (partial invoicing is valid).
        The unique constraint is only on invoice_number itself.
        """
        invoice1 = self._create_supplier_invoice()
        invoice2 = self._create_supplier_invoice()
        self.assertNotEqual(invoice1.invoice_number, invoice2.invoice_number)

    def test_audit_log_on_approve(self):
        from financials.models import FinancialAuditLog
        invoice = self._create_supplier_invoice()
        SupplierInvoiceService.submit_invoice(invoice, self.owner)
        invoice.refresh_from_db()
        SupplierInvoiceService.approve_invoice(invoice, self.accountant)
        self.assertTrue(
            FinancialAuditLog.objects.filter(
                action="SUPPLIER_INVOICE_APPROVED",
                entity_id=invoice.pk,
            ).exists()
        )


class SupplierInvoiceAPITests(FinancialTestBase):
    """Supplier invoice API isolation tests."""

    def test_other_user_cannot_see_this_restaurants_invoice(self):
        invoice = self._create_supplier_invoice()
        response = self.other_client.get(f"/api/financials/supplier-invoices/{invoice.pk}/")
        self.assertEqual(response.status_code, 404)

    def test_unauthenticated_cannot_list_invoices(self):
        response = self.anon_client.get("/api/financials/supplier-invoices/")
        self.assertEqual(response.status_code, 401)

    def test_owner_can_list_own_invoices(self):
        self._create_supplier_invoice()
        response = self.owner_client.get("/api/financials/supplier-invoices/")
        self.assertEqual(response.status_code, 200)
        for inv in response.json()["results"]:
            self.assertEqual(inv["restaurant"], str(self.restaurant.pk))
