# =============================================================================
# RestaurantFlow — Orders Concurrency Tests
# Phase 6
#
# Tests that DB-level constraints and service-layer locks prevent race conditions.
# These run sequentially against the same test DB.
# =============================================================================

from django.test import TestCase, TransactionTestCase
from django.db import IntegrityError, transaction

from orders.models import (
    DiningTable, TableSession, OrderSequence,
    TableStatus, TableSessionStatus,
)
from orders import services
from orders.tests.test_tables import (
    make_org, make_restaurant, make_branch, make_user, make_table, make_waiter_user,
)


# =============================================================================
# Table Session Concurrency
# =============================================================================

class TableSessionConcurrencyTests(TransactionTestCase):
    """
    TransactionTestCase (not TestCase) so that DB-level constraint violations
    are raised properly (TestCase wraps everything in a transaction which
    suppresses IntegrityError propagation in some cases).
    """

    def test_db_constraint_prevents_two_open_sessions(self):
        """
        Inserting two OPEN sessions for the same table directly at the DB level
        should raise IntegrityError — the partial unique constraint is enforced.
        """
        org = make_org("Conc Org")
        rest = make_restaurant(org, "Conc Rest")
        branch = make_branch(rest)
        table = make_table(branch, number="TC01")
        user = make_user(email="conc@test.com")

        # First session — succeeds
        TableSession.objects.create(
            table=table, opened_by=user, status=TableSessionStatus.OPEN, guest_count=2
        )

        # Second session — must fail at DB level
        with self.assertRaises(IntegrityError):
            TableSession.objects.create(
                table=table, opened_by=user, status=TableSessionStatus.OPEN, guest_count=3
            )

    def test_second_closed_session_allowed(self):
        """Two CLOSED sessions for the same table are allowed."""
        org = make_org("Conc Org 2")
        rest = make_restaurant(org, "Conc Rest 2")
        branch = make_branch(rest, code="CC2")
        table = make_table(branch, number="TC02")
        user = make_user(email="conc2@test.com")

        s1 = TableSession.objects.create(
            table=table, opened_by=user, status=TableSessionStatus.CLOSED, guest_count=2
        )
        s2 = TableSession.objects.create(
            table=table, opened_by=user, status=TableSessionStatus.CLOSED, guest_count=3
        )
        self.assertNotEqual(s1.pk, s2.pk)


# =============================================================================
# Order Sequence Concurrency
# =============================================================================

class OrderSequenceConcurrencyTests(TestCase):
    """
    Verify that the sequence generation service is safe against simple
    sequential calls.  True concurrent tests require threads and are left
    to load testing tools.
    """

    def setUp(self):
        self.org = make_org("Seq Org")
        self.restaurant = make_restaurant(self.org, "Seq Rest")
        self.branch = make_branch(self.restaurant, code="SB")

    def test_sequential_sequence_generation_no_duplicates(self):
        """Generate 10 order numbers in a loop — all must be unique."""
        numbers = set()
        for _ in range(10):
            with transaction.atomic():
                num = services.generate_order_number(
                    branch=self.branch, order_type="DINE_IN"
                )
            numbers.add(num)
        self.assertEqual(len(numbers), 10)

    def test_sequence_resets_across_different_date_keys(self):
        """Manually insert a sequence for yesterday; today's must start fresh."""
        import datetime
        yesterday = (datetime.date.today() - datetime.timedelta(days=1)).strftime("%Y%m%d")
        OrderSequence.objects.create(
            scope_type=OrderSequence.SCOPE_BRANCH,
            scope_id=str(self.branch.pk),
            date_key=yesterday,
            last_sequence=999,
        )
        # Today's sequence should start at 0001 not 1000
        with transaction.atomic():
            num = services.generate_order_number(
                branch=self.branch, order_type="DINE_IN"
            )
        seq = int(num.split("-")[-1])
        self.assertEqual(seq, 1)

    def test_db_unique_constraint_on_sequence(self):
        """Duplicate scope+date_key entries are rejected by DB."""
        today = services._local_date_key(self.branch)
        OrderSequence.objects.create(
            scope_type=OrderSequence.SCOPE_BRANCH,
            scope_id=str(self.branch.pk),
            date_key=today,
            last_sequence=5,
        )
        with self.assertRaises(IntegrityError):
            OrderSequence.objects.create(
                scope_type=OrderSequence.SCOPE_BRANCH,
                scope_id=str(self.branch.pk),
                date_key=today,
                last_sequence=6,
            )


# =============================================================================
# Table Number Uniqueness Concurrency
# =============================================================================

class TableNumberUniquenessTests(TransactionTestCase):
    def test_db_constraint_prevents_duplicate_table_number_in_same_branch(self):
        org = make_org("TN Org")
        rest = make_restaurant(org, "TN Rest")
        branch = make_branch(rest)
        DiningTable.objects.create(
            branch=branch,
            table_number="T99",
            capacity=4,
            status=TableStatus.ACTIVE,
        )
        with self.assertRaises(IntegrityError):
            DiningTable.objects.create(
                branch=branch,
                table_number="T99",
                capacity=2,
                status=TableStatus.ACTIVE,
            )

    def test_same_table_number_in_different_branches_allowed(self):
        org = make_org("TN Org 2")
        rest = make_restaurant(org, "TN Rest 2")
        b1 = make_branch(rest, name="B1", code="B1")
        b2 = make_branch(rest, name="B2", code="B2")
        t1 = DiningTable.objects.create(
            branch=b1, table_number="T99", capacity=4, status=TableStatus.ACTIVE
        )
        t2 = DiningTable.objects.create(
            branch=b2, table_number="T99", capacity=6, status=TableStatus.ACTIVE
        )
        self.assertNotEqual(t1.pk, t2.pk)
