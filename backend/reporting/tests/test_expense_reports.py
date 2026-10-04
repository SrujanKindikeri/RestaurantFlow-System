# =============================================================================
# RestaurantFlow — Expense Report Tests
# Phase 14
# =============================================================================

from decimal import Decimal
from datetime import date

from reporting.tests.base import ReportingTestBase
from reporting import aggregations as agg
from accounts import access as acl
from financials.models import ExpenseCategory, Expense
from financials.constants import EXPENSE_APPROVED, EXPENSE_DRAFT, EXPENSE_REJECTED


class ExpenseReportTests(ReportingTestBase):

    def _make_expense_category(self):
        return ExpenseCategory.objects.create(
            restaurant=self.restaurant_a, name="Utilities", code="UTIL",
        )

    def _make_expense(self, status=EXPENSE_APPROVED, amount=Decimal("1000.00"),
                      branch=None):
        from django.utils import timezone as tz
        ts = tz.now().strftime("%Y%m%d%H%M%S%f")
        cat = self._make_expense_category()
        exp = Expense.objects.create(
            restaurant=self.restaurant_a,
            branch=branch or self.branch_a1,
            expense_number=f"EXP-{ts}",
            category=cat,
            title="Test Expense",
            amount=amount,
            tax_amount=Decimal("0.00"),
            total_amount=amount,
            expense_date=date.today(),
            status=status,
            created_by=self.manager_a,
        )
        return exp

    def test_approved_expense_included(self):
        self._make_expense(status=EXPENSE_APPROVED, amount=Decimal("1000.00"))
        branches = acl.get_accessible_branches(self.manager_a)
        result = agg.aggregate_expenses(branches, date.today(), date.today())
        self.assertEqual(result["approved_expenses"], Decimal("1000.00"))

    def test_draft_expense_excluded_from_approved(self):
        self._make_expense(status=EXPENSE_DRAFT)
        branches = acl.get_accessible_branches(self.manager_a)
        result = agg.aggregate_expenses(branches, date.today(), date.today())
        self.assertEqual(result["approved_expenses"], Decimal("0.00"))

    def test_rejected_expense_excluded_from_approved(self):
        self._make_expense(status=EXPENSE_REJECTED)
        branches = acl.get_accessible_branches(self.manager_a)
        result = agg.aggregate_expenses(branches, date.today(), date.today())
        self.assertEqual(result["approved_expenses"], Decimal("0.00"))

    def test_category_breakdown_returned(self):
        self._make_expense(status=EXPENSE_APPROVED, amount=Decimal("500.00"))
        branches = acl.get_accessible_branches(self.manager_a)
        result = agg.aggregate_expenses(branches, date.today(), date.today())
        self.assertIn("category_breakdown", result)
        self.assertGreater(len(result["category_breakdown"]), 0)

    def test_isolation_between_orgs(self):
        self._make_expense(status=EXPENSE_APPROVED)
        branches_b = acl.get_accessible_branches(self.manager_b)
        result = agg.aggregate_expenses(branches_b, date.today(), date.today())
        self.assertEqual(result["approved_expenses"], Decimal("0.00"))
