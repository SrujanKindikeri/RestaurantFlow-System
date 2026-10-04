# =============================================================================
# RestaurantFlow — Recurring Expense Tests
# Phase 12
# =============================================================================

from datetime import date
from decimal import Decimal

from financials.models import RecurringExpense, Expense
from financials.services import RecurringExpenseService
from financials.tests.base import FinancialTestBase


class RecurringExpenseTemplateTests(FinancialTestBase):
    """Template creation and management."""

    def test_create_template(self):
        template = RecurringExpenseService.create_template(
            restaurant=self.restaurant,
            category=self.category,
            title="Monthly Rent",
            amount=Decimal("25000.00"),
            frequency="MONTHLY",
            start_date=date(2026, 10, 1),
            user=self.manager,
        )
        self.assertEqual(template.frequency, "MONTHLY")
        self.assertEqual(template.amount, Decimal("25000.00"))
        self.assertTrue(template.is_active)
        self.assertEqual(template.next_run_date, date(2026, 10, 1))

    def test_end_date_before_start_date_rejected_by_serializer(self):
        from financials.serializers import CreateRecurringExpenseSerializer
        serializer = CreateRecurringExpenseSerializer(data={
            "restaurant": str(self.restaurant.pk),
            "category": str(self.category.pk),
            "title": "Bad Dates",
            "amount": "1000.00",
            "frequency": "MONTHLY",
            "start_date": "2026-10-01",
            "end_date": "2026-09-01",  # before start
        })
        self.assertFalse(serializer.is_valid())
        self.assertIn("end_date", serializer.errors)

    def test_disable_template(self):
        template = RecurringExpenseService.create_template(
            restaurant=self.restaurant,
            category=self.category,
            title="Internet Bill",
            amount=Decimal("2000.00"),
            frequency="MONTHLY",
            start_date=date(2026, 10, 1),
            user=self.manager,
        )
        disabled = RecurringExpenseService.disable_template(template, self.manager)
        self.assertFalse(disabled.is_active)

    def test_disabled_template_not_generated(self):
        template = RecurringExpenseService.create_template(
            restaurant=self.restaurant,
            category=self.category,
            title="Water Bill",
            amount=Decimal("500.00"),
            frequency="MONTHLY",
            start_date=date(2026, 9, 1),
            user=self.manager,
        )
        RecurringExpenseService.disable_template(template, self.manager)
        initial_count = Expense.objects.filter(restaurant=self.restaurant).count()
        RecurringExpenseService.generate_due_expenses(today=date(2026, 10, 1))
        final_count = Expense.objects.filter(restaurant=self.restaurant).count()
        self.assertEqual(initial_count, final_count)


class RecurringExpenseGenerationTests(FinancialTestBase):
    """Due expense generation from templates."""

    def test_generates_expense_when_due(self):
        template = RecurringExpenseService.create_template(
            restaurant=self.restaurant,
            category=self.category,
            title="Electricity",
            amount=Decimal("3000.00"),
            frequency="MONTHLY",
            start_date=date(2026, 9, 1),
            user=self.manager,
        )
        count_before = Expense.objects.filter(restaurant=self.restaurant).count()
        created = RecurringExpenseService.generate_due_expenses(today=date(2026, 9, 1))
        self.assertEqual(len(created), 1)
        self.assertEqual(Expense.objects.filter(restaurant=self.restaurant).count(), count_before + 1)

    def test_generated_expense_is_in_draft(self):
        RecurringExpenseService.create_template(
            restaurant=self.restaurant,
            category=self.category,
            title="Cleaning",
            amount=Decimal("1000.00"),
            frequency="MONTHLY",
            start_date=date(2026, 9, 2),
            user=self.manager,
        )
        created = RecurringExpenseService.generate_due_expenses(today=date(2026, 9, 2))
        self.assertEqual(created[0].status, "DRAFT")

    def test_next_run_date_advances_after_generation(self):
        template = RecurringExpenseService.create_template(
            restaurant=self.restaurant,
            category=self.category,
            title="Security",
            amount=Decimal("500.00"),
            frequency="MONTHLY",
            start_date=date(2026, 9, 15),
            user=self.manager,
        )
        RecurringExpenseService.generate_due_expenses(today=date(2026, 9, 15))
        template.refresh_from_db()
        self.assertEqual(template.next_run_date, date(2026, 10, 15))

    def test_no_generation_if_not_yet_due(self):
        RecurringExpenseService.create_template(
            restaurant=self.restaurant,
            category=self.category,
            title="Not Yet Due",
            amount=Decimal("1000.00"),
            frequency="MONTHLY",
            start_date=date(2026, 11, 1),  # future date
            user=self.manager,
        )
        count_before = Expense.objects.filter(restaurant=self.restaurant).count()
        RecurringExpenseService.generate_due_expenses(today=date(2026, 10, 1))
        self.assertEqual(Expense.objects.filter(restaurant=self.restaurant).count(), count_before)

    def test_idempotent_generation(self):
        """Calling generate_due_expenses twice on same day should not double-generate."""
        template = RecurringExpenseService.create_template(
            restaurant=self.restaurant,
            category=self.category,
            title="Idempotent Test",
            amount=Decimal("800.00"),
            frequency="MONTHLY",
            start_date=date(2026, 9, 10),
            user=self.manager,
        )
        RecurringExpenseService.generate_due_expenses(today=date(2026, 9, 10))
        template.refresh_from_db()
        count_after_first = Expense.objects.filter(restaurant=self.restaurant).count()
        # next_run_date is now 2026-10-10; calling again on same day should not re-generate
        RecurringExpenseService.generate_due_expenses(today=date(2026, 9, 10))
        count_after_second = Expense.objects.filter(restaurant=self.restaurant).count()
        self.assertEqual(count_after_first, count_after_second)

    def test_no_generation_after_end_date(self):
        RecurringExpenseService.create_template(
            restaurant=self.restaurant,
            category=self.category,
            title="Expired Template",
            amount=Decimal("2000.00"),
            frequency="MONTHLY",
            start_date=date(2026, 7, 1),
            end_date=date(2026, 8, 31),  # ended before our run date
            user=self.manager,
        )
        count_before = Expense.objects.filter(restaurant=self.restaurant).count()
        RecurringExpenseService.generate_due_expenses(today=date(2026, 10, 1))
        self.assertEqual(Expense.objects.filter(restaurant=self.restaurant).count(), count_before)


class NextRunDateCalculationTests(FinancialTestBase):
    """_calculate_next_run_date edge cases."""

    def test_weekly(self):
        result = RecurringExpenseService._calculate_next_run_date(date(2026, 10, 1), "WEEKLY")
        self.assertEqual(result, date(2026, 10, 8))

    def test_monthly(self):
        result = RecurringExpenseService._calculate_next_run_date(date(2026, 1, 31), "MONTHLY")
        # February doesn't have 31 days — should clamp to 28
        self.assertEqual(result, date(2026, 2, 28))

    def test_monthly_normal(self):
        result = RecurringExpenseService._calculate_next_run_date(date(2026, 10, 15), "MONTHLY")
        self.assertEqual(result, date(2026, 11, 15))

    def test_quarterly(self):
        result = RecurringExpenseService._calculate_next_run_date(date(2026, 10, 1), "QUARTERLY")
        self.assertEqual(result, date(2027, 1, 1))

    def test_yearly(self):
        result = RecurringExpenseService._calculate_next_run_date(date(2026, 10, 1), "YEARLY")
        self.assertEqual(result, date(2027, 10, 1))

    def test_yearly_leap_day_clamped(self):
        # Feb 29 on leap year → should clamp when target year is not leap
        result = RecurringExpenseService._calculate_next_run_date(date(2024, 2, 29), "YEARLY")
        self.assertEqual(result, date(2025, 2, 28))
