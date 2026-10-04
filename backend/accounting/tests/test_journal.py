# =============================================================================
# RestaurantFlow — Journal Entry Tests
# Phase 13
# =============================================================================

import uuid
from decimal import Decimal
from datetime import date

from django.test import TestCase
from rest_framework.exceptions import PermissionDenied, ValidationError

from accounting.tests.base import AccountingTestBase, ZERO
from accounting.services import JournalService
from accounting.exceptions import (
    JournalImbalanceError, ImmutableJournalError, JournalPostingError,
    ClosedPeriodError, AccountInactiveError, NonPostableAccountError,
    CrossRestaurantAccountError, DuplicateAccountingPostError,
)
from accounting.constants import (
    JE_DRAFT, JE_POSTED, JE_REVERSED, JE_VOID,
    SOURCE_BILL, SOURCE_MANUAL,
)


class JournalCreateTests(AccountingTestBase):

    def test_create_draft_entry(self):
        entry = JournalService.create_draft(
            restaurant=self.restaurant,
            period=self.period,
            entry_date=date.today(),
            description="Test draft",
            user=self.user,
        )
        self.assertEqual(entry.status, JE_DRAFT)
        self.assertEqual(entry.restaurant, self.restaurant)
        self.assertTrue(entry.entry_number.startswith("JE-"))

    def test_journal_number_unique_per_restaurant(self):
        e1 = JournalService.create_draft(
            restaurant=self.restaurant, period=self.period,
            entry_date=date.today(), description="E1", user=self.user,
        )
        e2 = JournalService.create_draft(
            restaurant=self.restaurant, period=self.period,
            entry_date=date.today(), description="E2", user=self.user,
        )
        self.assertNotEqual(e1.entry_number, e2.entry_number)

    def test_entry_number_format(self):
        entry = JournalService.create_draft(
            restaurant=self.restaurant, period=self.period,
            entry_date=date.today(), description="Format test", user=self.user,
        )
        import re
        self.assertRegex(entry.entry_number, r'^JE-\d{6}$')

    def test_add_line_debit(self):
        entry = JournalService.create_draft(
            restaurant=self.restaurant, period=self.period,
            entry_date=date.today(), description="Line test", user=self.user,
        )
        line = JournalService.add_line(
            entry, self.acct_cash,
            debit_amount=Decimal("500.00"), credit_amount=ZERO,
            user=self.user,
        )
        self.assertEqual(line.debit_amount, Decimal("500.00"))
        self.assertEqual(line.credit_amount, ZERO)

    def test_add_line_credit(self):
        entry = JournalService.create_draft(
            restaurant=self.restaurant, period=self.period,
            entry_date=date.today(), description="Credit test", user=self.user,
        )
        line = JournalService.add_line(
            entry, self.acct_sales,
            debit_amount=ZERO, credit_amount=Decimal("500.00"),
            user=self.user,
        )
        self.assertEqual(line.credit_amount, Decimal("500.00"))
        self.assertEqual(line.debit_amount, ZERO)

    def test_cannot_have_both_debit_and_credit_on_same_line(self):
        entry = JournalService.create_draft(
            restaurant=self.restaurant, period=self.period,
            entry_date=date.today(), description="XOR test", user=self.user,
        )
        with self.assertRaises(ValidationError):
            JournalService.add_line(
                entry, self.acct_cash,
                debit_amount=Decimal("100.00"),
                credit_amount=Decimal("100.00"),  # both set — invalid
                user=self.user,
            )

    def test_cannot_have_both_zero_on_same_line(self):
        entry = JournalService.create_draft(
            restaurant=self.restaurant, period=self.period,
            entry_date=date.today(), description="Zero test", user=self.user,
        )
        with self.assertRaises(ValidationError):
            JournalService.add_line(
                entry, self.acct_cash,
                debit_amount=ZERO, credit_amount=ZERO,  # both zero — invalid
                user=self.user,
            )

    def test_cannot_add_line_to_inactive_account(self):
        entry = JournalService.create_draft(
            restaurant=self.restaurant, period=self.period,
            entry_date=date.today(), description="Inactive test", user=self.user,
        )
        self.acct_cash.is_active = False
        self.acct_cash.save()
        try:
            with self.assertRaises(AccountInactiveError):
                JournalService.add_line(
                    entry, self.acct_cash,
                    debit_amount=Decimal("100.00"), credit_amount=ZERO,
                    user=self.user,
                )
        finally:
            self.acct_cash.is_active = True
            self.acct_cash.save()

    def test_cannot_add_line_to_non_postable_account(self):
        entry = JournalService.create_draft(
            restaurant=self.restaurant, period=self.period,
            entry_date=date.today(), description="Non-postable test", user=self.user,
        )
        with self.assertRaises(NonPostableAccountError):
            JournalService.add_line(
                entry, self.acct_assets_header,  # is_postable=False
                debit_amount=Decimal("100.00"), credit_amount=ZERO,
                user=self.user,
            )

    def test_cannot_add_line_to_posted_entry(self):
        entry = self._post_journal_entry()
        with self.assertRaises(ImmutableJournalError):
            JournalService.add_line(
                entry, self.acct_cash,
                debit_amount=Decimal("50.00"), credit_amount=ZERO,
                user=self.user,
            )


class JournalPostTests(AccountingTestBase):

    def test_post_balanced_entry(self):
        entry = self._make_journal_entry()
        entry = JournalService.post_entry(entry, self.user)
        self.assertEqual(entry.status, JE_POSTED)
        self.assertIsNotNone(entry.posted_at)
        self.assertEqual(entry.posted_by, self.user)

    def test_cannot_post_unbalanced_entry(self):
        entry = JournalService.create_draft(
            restaurant=self.restaurant, period=self.period,
            entry_date=date.today(), description="Unbalanced", user=self.user,
        )
        # Add only a debit line — no credit
        JournalService.add_line(
            entry, self.acct_cash,
            debit_amount=Decimal("100.00"), credit_amount=ZERO,
            user=self.user,
        )
        with self.assertRaises(JournalImbalanceError):
            JournalService.post_entry(entry, self.user)

    def test_cannot_post_entry_with_only_one_line(self):
        entry = JournalService.create_draft(
            restaurant=self.restaurant, period=self.period,
            entry_date=date.today(), description="One line", user=self.user,
        )
        JournalService.add_line(
            entry, self.acct_cash,
            debit_amount=Decimal("100.00"), credit_amount=ZERO,
            user=self.user,
        )
        with self.assertRaises(JournalImbalanceError):
            JournalService.post_entry(entry, self.user)

    def test_posted_entry_is_immutable(self):
        entry = self._post_journal_entry()
        with self.assertRaises(ImmutableJournalError):
            JournalService.validate_entry(entry)  # tries to validate as draft

    def test_cannot_post_already_posted_entry(self):
        entry = self._post_journal_entry()
        with self.assertRaises(ImmutableJournalError):
            JournalService.post_entry(entry, self.user)

    def test_cannot_post_to_closed_period(self):
        from datetime import timedelta
        from accounting.services import PeriodService
        today = date.today()
        next_month = (today.replace(day=1) + timedelta(days=32)).replace(day=1)
        closed_period = PeriodService.create_period(
            restaurant=self.restaurant,
            name="Closed For Test",
            start_date=next_month,
            end_date=next_month + timedelta(days=27),
            user=self.user,
        )
        PeriodService.close_period(closed_period, self.user)
        with self.assertRaises(ClosedPeriodError):
            JournalService.create_draft(
                restaurant=self.restaurant,
                period=closed_period,
                entry_date=next_month,
                description="Should fail",
                user=self.user,
            )

    def test_total_debits_equals_total_credits_invariant(self):
        """THE CENTRAL DOUBLE-ENTRY INVARIANT."""
        entry = self._post_journal_entry()
        self.assertTrue(entry.is_balanced())
        self.assertEqual(entry.get_total_debits(), entry.get_total_credits())


class JournalReverseTests(AccountingTestBase):

    def test_reverse_posted_entry(self):
        entry = self._post_journal_entry(self._make_journal_entry("Original"))
        reversal = JournalService.reverse_entry(entry, self.user, "Test reversal")

        # Reversal is posted
        self.assertEqual(reversal.status, JE_POSTED)
        self.assertEqual(reversal.reversal_of, entry)

        # Original is marked reversed
        entry.refresh_from_db()
        self.assertEqual(entry.status, JE_REVERSED)
        self.assertEqual(entry.reversed_by, self.user)

    def test_reversal_entry_is_balanced(self):
        entry = self._post_journal_entry()
        reversal = JournalService.reverse_entry(entry, self.user, "Reversal test")
        self.assertTrue(reversal.is_balanced())

    def test_reversal_swaps_debits_and_credits(self):
        entry = self._post_journal_entry()
        original_lines = list(entry.lines.all())
        reversal = JournalService.reverse_entry(entry, self.user, "Swap test")
        reversal_lines = {l.account_id: l for l in reversal.lines.all()}

        for orig_line in original_lines:
            rev_line = reversal_lines[orig_line.account_id]
            self.assertEqual(orig_line.debit_amount, rev_line.credit_amount)
            self.assertEqual(orig_line.credit_amount, rev_line.debit_amount)

    def test_cannot_reverse_draft_entry(self):
        entry = self._make_journal_entry()
        with self.assertRaises(JournalPostingError):
            JournalService.reverse_entry(entry, self.user, "Cannot reverse draft")

    def test_cannot_reverse_already_reversed_entry(self):
        entry = self._post_journal_entry()
        JournalService.reverse_entry(entry, self.user, "First reversal")
        entry.refresh_from_db()
        with self.assertRaises(JournalPostingError):
            JournalService.reverse_entry(entry, self.user, "Second reversal")

    def test_reverse_requires_reason(self):
        entry = self._post_journal_entry()
        with self.assertRaises(ValidationError):
            JournalService.reverse_entry(entry, self.user, "")  # empty reason

    def test_void_draft_entry(self):
        entry = self._make_journal_entry()
        entry = JournalService.void_entry(entry, self.user, "Testing void")
        self.assertEqual(entry.status, JE_VOID)

    def test_cannot_void_posted_entry(self):
        entry = self._post_journal_entry()
        with self.assertRaises(ImmutableJournalError):
            JournalService.void_entry(entry, self.user)


class JournalConcurrencyTests(AccountingTestBase):

    def test_duplicate_journal_number_prevented(self):
        """Two concurrent calls must not produce the same JE number."""
        import threading
        numbers = []
        errors = []

        def _create():
            try:
                entry = JournalService.create_draft(
                    restaurant=self.restaurant, period=self.period,
                    entry_date=date.today(), description="Concurrent",
                    user=self.user,
                )
                numbers.append(entry.entry_number)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=_create) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(errors), 0, f"Errors: {errors}")
        self.assertEqual(len(numbers), len(set(numbers)), "Duplicate journal numbers!")
