# =============================================================================
# RestaurantFlow — Security & Isolation Tests
# Phase 12
#
# Tests that verify:
#   - Cross-company isolation
#   - Cross-restaurant isolation
#   - Permission enforcement
#   - Unauthenticated access blocked
#   - IDOR prevention via 404 (not 403) for unauthorized UUIDs
# =============================================================================

from decimal import Decimal

from financials.models import Payable
from financials.tests.base import FinancialTestBase


class CrossRestaurantIsolationTests(FinancialTestBase):
    """Restaurant A cannot see/act on Restaurant B's data."""

    def test_expense_uuid_returns_404_for_wrong_restaurant(self):
        expense = self._create_expense(restaurant=self.restaurant)
        # other_user is scoped to other_restaurant only
        response = self.other_client.get(f"/api/financials/expenses/{expense.pk}/")
        # Must be 404, NOT 403 — no information leakage
        self.assertEqual(response.status_code, 404)

    def test_expense_list_never_leaks_other_restaurants_data(self):
        self._create_expense(
            user=self.manager,
            restaurant=self.restaurant,
            title="Restaurant A Expense",
        )
        self._create_expense(
            user=self.other_user,
            restaurant=self.other_restaurant,
            category=self.other_category,
            title="Restaurant B Expense",
        )
        response = self.owner_client.get("/api/financials/expenses/")
        self.assertEqual(response.status_code, 200)
        for exp in response.json()["results"]:
            self.assertNotEqual(exp["title"], "Restaurant B Expense")

    def test_category_list_scoped_to_restaurant(self):
        response = self.owner_client.get(
            f"/api/financials/expense-categories/?restaurant={self.restaurant.pk}"
        )
        self.assertEqual(response.status_code, 200)
        for cat in response.json():
            self.assertEqual(cat["restaurant"], str(self.restaurant.pk))

    def test_submit_foreign_expense_returns_404(self):
        expense = self._create_expense(restaurant=self.restaurant)
        # Escalate to SUBMITTED so we can test the submit endpoint
        from financials.services import ExpenseService
        expense = ExpenseService.submit_expense(expense, self.manager)
        response = self.other_client.post(
            f"/api/financials/expenses/{expense.pk}/approve/",
            data={"approval_note": "Hacked"},
            format="json",
        )
        # other_client can't even see this expense
        self.assertEqual(response.status_code, 404)

    def test_payable_uuid_returns_404_for_wrong_restaurant(self):
        expense = self._create_expense(status="APPROVED")
        payable = Payable.objects.get(expense=expense)
        response = self.other_client.get(f"/api/financials/payables/{payable.pk}/")
        self.assertEqual(response.status_code, 404)

    def test_supplier_invoice_scoped_to_restaurant(self):
        invoice = self._create_supplier_invoice()
        response = self.other_client.get(f"/api/financials/supplier-invoices/{invoice.pk}/")
        self.assertEqual(response.status_code, 404)

    def test_correction_request_scoped_to_restaurant(self):
        from financials.services import ExpenseCorrectionService
        expense = self._create_expense(status="APPROVED")
        correction = ExpenseCorrectionService.request_correction(
            expense=expense,
            user=self.manager,
            correction_type="OTHER",
            requested_data={},
            reason="This is a legitimate correction reason for testing.",
        )
        response = self.other_client.get(
            f"/api/financials/expense-corrections/{correction.pk}/"
        )
        self.assertEqual(response.status_code, 404)


class UnauthenticatedAccessTests(FinancialTestBase):
    """All financial endpoints require authentication."""

    ENDPOINTS = [
        ("GET",  "/api/financials/expenses/"),
        ("GET",  "/api/financials/expense-categories/"),
        ("GET",  "/api/financials/recurring-expenses/"),
        ("GET",  "/api/financials/supplier-invoices/"),
        ("GET",  "/api/financials/payables/"),
        ("GET",  "/api/financials/dashboard/"),
    ]

    def test_unauthenticated_gets_401(self):
        for method, url in self.ENDPOINTS:
            with self.subTest(url=url, method=method):
                response = getattr(self.anon_client, method.lower())(url)
                self.assertEqual(
                    response.status_code, 401,
                    f"Expected 401 for {method} {url}, got {response.status_code}",
                )


class PermissionEnforcementTests(FinancialTestBase):
    """Cashier has no financial management permissions."""

    def test_cashier_cannot_create_expense(self):
        response = self.cashier_client.post(
            "/api/financials/expenses/",
            data={
                "restaurant": str(self.restaurant.pk),
                "category": str(self.category.pk),
                "title": "Cashier attempt",
                "amount": "100.00",
                "expense_date": "2026-10-01",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 403)

    def test_cashier_cannot_create_expense_category(self):
        response = self.cashier_client.post(
            "/api/financials/expense-categories/",
            data={
                "restaurant": str(self.restaurant.pk),
                "name": "Hacked",
                "code": "HACK",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 403)

    def test_cashier_cannot_approve_expense(self):
        expense = self._create_expense(status="SUBMITTED")
        response = self.cashier_client.post(
            f"/api/financials/expenses/{expense.pk}/approve/",
            data={"approval_note": "ok"},
            format="json",
        )
        self.assertEqual(response.status_code, 403)

    def test_cashier_cannot_manage_payables(self):
        expense = self._create_expense(status="APPROVED")
        payable = Payable.objects.get(expense=expense)
        response = self.cashier_client.post(
            f"/api/financials/payables/{payable.pk}/record-payment/",
            data={"payment_amount": "100.00"},
            format="json",
        )
        self.assertEqual(response.status_code, 403)

    def test_cashier_cannot_approve_supplier_invoice(self):
        invoice = self._create_supplier_invoice()
        from financials.services import SupplierInvoiceService
        SupplierInvoiceService.submit_invoice(invoice, self.owner)
        invoice.refresh_from_db()
        response = self.cashier_client.post(
            f"/api/financials/supplier-invoices/{invoice.pk}/approve/",
            data={},
            format="json",
        )
        self.assertEqual(response.status_code, 403)

    def test_manager_cannot_approve_supplier_invoice(self):
        """Manager can submit but not approve invoices."""
        invoice = self._create_supplier_invoice()
        from financials.services import SupplierInvoiceService
        SupplierInvoiceService.submit_invoice(invoice, self.owner)
        invoice.refresh_from_db()
        response = self.manager_client.post(
            f"/api/financials/supplier-invoices/{invoice.pk}/approve/",
            data={},
            format="json",
        )
        self.assertEqual(response.status_code, 403)

    def test_manager_cannot_view_dashboard(self):
        """Manager role in test fixture does not have dashboard.view."""
        response = self.manager_client.get("/api/financials/dashboard/")
        self.assertEqual(response.status_code, 403)

    def test_owner_can_view_dashboard(self):
        response = self.owner_client.get("/api/financials/dashboard/")
        self.assertEqual(response.status_code, 200)


class AuditLogImmutabilityTests(FinancialTestBase):
    """Audit log records cannot be modified after creation."""

    def test_audit_log_cannot_be_updated(self):
        from financials.models import FinancialAuditLog
        expense = self._create_expense(status="APPROVED")
        log = FinancialAuditLog.objects.filter(entity_id=expense.pk).first()
        self.assertIsNotNone(log)
        with self.assertRaises(ValueError):
            log.old_status = "HACKED"
            log.save()

    def test_audit_log_is_written_on_every_transition(self):
        from financials.models import FinancialAuditLog
        expense = self._create_expense()       # CREATED
        from financials.services import ExpenseService
        ExpenseService.submit_expense(expense, self.manager)   # SUBMITTED
        expense.refresh_from_db()
        ExpenseService.approve_expense(expense, self.accountant)  # APPROVED

        logs = FinancialAuditLog.objects.filter(entity_id=expense.pk)
        actions = set(logs.values_list("action", flat=True))
        self.assertIn("EXPENSE_CREATED", actions)
        self.assertIn("EXPENSE_SUBMITTED", actions)
        self.assertIn("EXPENSE_APPROVED", actions)


class FinancialDashboardTests(FinancialTestBase):
    """Dashboard endpoint returns correct aggregates."""

    def test_dashboard_response_shape(self):
        response = self.owner_client.get("/api/financials/dashboard/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        required_keys = [
            "total_expenses", "pending_approval", "approved_expenses",
            "rejected_expenses", "unpaid_expenses", "partially_paid",
            "overdue_payables", "total_payable_amount", "total_paid_amount",
            "total_remaining_amount", "category_summary", "branch_summary",
            "recent_expenses",
        ]
        for key in required_keys:
            self.assertIn(key, data, f"Missing key: {key}")

    def test_dashboard_counts_correctly(self):
        self._create_expense(status="DRAFT")
        self._create_expense(status="SUBMITTED")
        self._create_expense(status="APPROVED")
        response = self.owner_client.get(
            f"/api/financials/dashboard/?restaurant={self.restaurant.pk}"
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertGreaterEqual(data["total_expenses"], 3)
        self.assertGreaterEqual(data["pending_approval"], 1)
        self.assertGreaterEqual(data["approved_expenses"], 1)
