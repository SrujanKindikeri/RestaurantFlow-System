# =============================================================================
# RestaurantFlow — CRM Loyalty Tests
# Phase 17
# =============================================================================

from decimal import Decimal
from django.test import TestCase
from django.db import transaction as db_transaction

from crm.loyalty_services import LoyaltyService, RewardService
from crm.exceptions import InsufficientLoyaltyPoints, RewardUnavailable, RewardExpired
from crm.tests.base import CRMTestBase


class LoyaltyAccountTests(CRMTestBase):

    def test_get_or_create_account(self):
        c = self.make_customer(phone="+910001000001")
        program = self.make_loyalty_program()
        account = LoyaltyService.get_or_create_account(c, program)
        self.assertEqual(account.points_balance, 0)
        self.assertEqual(account.loyalty_program, program)

    def test_idempotent_account_creation(self):
        c = self.make_customer(phone="+910001000002")
        program = self.make_loyalty_program()
        acc1 = LoyaltyService.get_or_create_account(c, program)
        acc2 = LoyaltyService.get_or_create_account(c, program)
        self.assertEqual(acc1.pk, acc2.pk)


class LoyaltyEarningTests(CRMTestBase):

    def _make_finalized_bill(self, customer, amount="500.00"):
        """Helper: create a finalized bill linked to a customer's order."""
        from orders.models import Order, OrderType, OrderStatus
        from billing.models import Bill, BillStatus

        order = Order.objects.create(
            branch=self.branch,
            order_number=f"ORD-{Order.objects.count():06d}",
            order_type=OrderType.COUNTER,
            status=OrderStatus.CONFIRMED,
            created_by=self.cashier_user,
            customer=customer,
        )
        bill = Bill.objects.create(
            order=order,
            branch=self.branch,
            bill_number=f"B-2026-{Bill.objects.count():06d}",
            status=BillStatus.FINALIZED,
            subtotal=Decimal(amount),
            grand_total=Decimal(amount),
            created_by=self.cashier_user,
        )
        return bill

    def test_earn_points_for_bill(self):
        c = self.make_customer(phone="+910001000003")
        program = self.make_loyalty_program(points_per_unit="1.0000")
        account = LoyaltyService.get_or_create_account(c, program)
        bill = self._make_finalized_bill(c, "500.00")

        txn = LoyaltyService.earn_points_for_bill(bill, loyalty_program=program)
        self.assertIsNotNone(txn)
        self.assertEqual(txn.points, 500)
        self.assertEqual(txn.transaction_type, "EARN")

        account.refresh_from_db()
        self.assertEqual(account.points_balance, 500)

    def test_earn_points_idempotent(self):
        """Same bill cannot earn points twice."""
        c = self.make_customer(phone="+910001000004")
        program = self.make_loyalty_program()
        bill = self._make_finalized_bill(c, "300.00")

        txn1 = LoyaltyService.earn_points_for_bill(bill, loyalty_program=program)
        txn2 = LoyaltyService.earn_points_for_bill(bill, loyalty_program=program)

        self.assertEqual(txn1.pk, txn2.pk)
        account = LoyaltyService.get_or_create_account(c, program)
        self.assertEqual(account.points_balance, 300)

    def test_no_points_for_non_finalized_bill(self):
        from billing.models import Bill, BillStatus
        from orders.models import Order, OrderType, OrderStatus

        c = self.make_customer(phone="+910001000005")
        program = self.make_loyalty_program()
        order = Order.objects.create(
            branch=self.branch, order_number="ORD-DRAFT",
            order_type=OrderType.COUNTER,
            status=OrderStatus.CONFIRMED,
            created_by=self.cashier_user, customer=c,
        )
        bill = Bill.objects.create(
            order=order, branch=self.branch,
            bill_number="B-DRAFT-001",
            status=BillStatus.DRAFT,
            grand_total=Decimal("200.00"),
            created_by=self.cashier_user,
        )
        result = LoyaltyService.earn_points_for_bill(bill, loyalty_program=program)
        self.assertIsNone(result)

    def test_no_points_for_anonymous_order(self):
        from billing.models import Bill, BillStatus
        from orders.models import Order, OrderType, OrderStatus

        program = self.make_loyalty_program()
        order = Order.objects.create(
            branch=self.branch, order_number="ORD-ANON",
            order_type=OrderType.COUNTER,
            status=OrderStatus.CONFIRMED,
            created_by=self.cashier_user,
            customer=None,
        )
        bill = Bill.objects.create(
            order=order, branch=self.branch,
            bill_number="B-ANON-001",
            status=BillStatus.FINALIZED,
            grand_total=Decimal("200.00"),
            created_by=self.cashier_user,
        )
        result = LoyaltyService.earn_points_for_bill(bill, loyalty_program=program)
        self.assertIsNone(result)


class LoyaltyRedemptionTests(CRMTestBase):

    def test_redeem_deducts_balance(self):
        c = self.make_customer(phone="+910001000010")
        program = self.make_loyalty_program()
        account = LoyaltyService.get_or_create_account(c, program)
        LoyaltyService.adjust_points(account, 500, reason="Seeded for test", actor=self.manager_user)

        txn = LoyaltyService.redeem_points(account, 200, reason="Test redeem")
        self.assertEqual(txn.points, -200)
        account.refresh_from_db()
        self.assertEqual(account.points_balance, 300)

    def test_redeem_insufficient_raises(self):
        c = self.make_customer(phone="+910001000011")
        program = self.make_loyalty_program()
        account = LoyaltyService.get_or_create_account(c, program)
        LoyaltyService.adjust_points(account, 50, reason="Seeded", actor=self.manager_user)

        with self.assertRaises(InsufficientLoyaltyPoints):
            LoyaltyService.redeem_points(account, 100, reason="Over-redeem")

    def test_balance_never_negative(self):
        c = self.make_customer(phone="+910001000012")
        program = self.make_loyalty_program()
        account = LoyaltyService.get_or_create_account(c, program)
        LoyaltyService.adjust_points(account, 100, reason="Seeded", actor=self.manager_user)

        with self.assertRaises(InsufficientLoyaltyPoints):
            LoyaltyService.redeem_points(account, 150)
        account.refresh_from_db()
        self.assertEqual(account.points_balance, 100)

    def test_concurrent_redemptions(self):
        """
        Simulates two concurrent redemptions — only one should succeed
        when total points < combined redemption amount.
        Uses DB-level select_for_update.
        """
        from threading import Thread
        from crm.models import LoyaltyAccount

        c = self.make_customer(phone="+910001000013")
        program = self.make_loyalty_program()
        account = LoyaltyService.get_or_create_account(c, program)
        LoyaltyService.adjust_points(account, 100, reason="Seeded", actor=self.manager_user)

        results = []

        def attempt_redeem():
            try:
                with db_transaction.atomic():
                    acc = LoyaltyAccount.objects.select_for_update().get(pk=account.pk)
                    LoyaltyService.redeem_points(acc, 80, reason="Thread redeem")
                    results.append("success")
            except InsufficientLoyaltyPoints:
                results.append("insufficient")
            except Exception as e:
                results.append(f"error: {e}")

        t1 = Thread(target=attempt_redeem)
        t2 = Thread(target=attempt_redeem)
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        success_count = results.count("success")
        account.refresh_from_db()
        # Only one thread should have succeeded; balance must be non-negative
        self.assertGreaterEqual(account.points_balance, 0)
        self.assertLessEqual(success_count, 1)


class LoyaltyAdjustmentTests(CRMTestBase):

    def test_positive_adjustment(self):
        c = self.make_customer(phone="+910001000020")
        program = self.make_loyalty_program()
        account = LoyaltyService.get_or_create_account(c, program)
        LoyaltyService.adjust_points(account, 200, reason="Welcome bonus", actor=self.manager_user)
        account.refresh_from_db()
        self.assertEqual(account.points_balance, 200)

    def test_negative_adjustment_fails_without_balance(self):
        c = self.make_customer(phone="+910001000021")
        program = self.make_loyalty_program()
        account = LoyaltyService.get_or_create_account(c, program)
        with self.assertRaises(InsufficientLoyaltyPoints):
            LoyaltyService.adjust_points(account, -100, reason="Over-adjustment", actor=self.manager_user)

    def test_adjustment_requires_reason(self):
        c = self.make_customer(phone="+910001000022")
        program = self.make_loyalty_program()
        account = LoyaltyService.get_or_create_account(c, program)
        with self.assertRaises(Exception):
            LoyaltyService.adjust_points(account, 100, reason="", actor=self.manager_user)


class LoyaltyReversalTests(CRMTestBase):

    def _make_finalized_bill(self, customer, amount="400.00"):
        from orders.models import Order, OrderType, OrderStatus
        from billing.models import Bill, BillStatus
        order = Order.objects.create(
            branch=self.branch,
            order_number=f"ORD-REV-{Order.objects.count():04d}",
            order_type=OrderType.COUNTER,
            status=OrderStatus.CONFIRMED,
            created_by=self.cashier_user,
            customer=customer,
        )
        bill = Bill.objects.create(
            order=order, branch=self.branch,
            bill_number=f"B-REV-{Bill.objects.count():04d}",
            status=BillStatus.FINALIZED,
            grand_total=Decimal(amount),
            created_by=self.cashier_user,
        )
        return bill

    def test_reversal_reduces_balance(self):
        c = self.make_customer(phone="+910001000030")
        program = self.make_loyalty_program()
        account = LoyaltyService.get_or_create_account(c, program)
        bill = self._make_finalized_bill(c, "400.00")
        LoyaltyService.earn_points_for_bill(bill, loyalty_program=program)

        account.refresh_from_db()
        self.assertEqual(account.points_balance, 400)

        LoyaltyService.reverse_points_for_bill(bill, reason="Refund test")
        account.refresh_from_db()
        self.assertEqual(account.points_balance, 0)

    def test_reversal_is_idempotent(self):
        c = self.make_customer(phone="+910001000031")
        program = self.make_loyalty_program()
        account = LoyaltyService.get_or_create_account(c, program)
        bill = self._make_finalized_bill(c, "300.00")
        LoyaltyService.earn_points_for_bill(bill, loyalty_program=program)

        txn1 = LoyaltyService.reverse_points_for_bill(bill)
        txn2 = LoyaltyService.reverse_points_for_bill(bill)
        self.assertEqual(txn1.pk, txn2.pk)

    def test_reversal_safe_when_points_already_spent(self):
        """Reversal should not make balance negative even if points were spent."""
        c = self.make_customer(phone="+910001000032")
        program = self.make_loyalty_program()
        account = LoyaltyService.get_or_create_account(c, program)
        bill = self._make_finalized_bill(c, "200.00")
        LoyaltyService.earn_points_for_bill(bill, loyalty_program=program)

        # Spend the points
        account.refresh_from_db()
        LoyaltyService.redeem_points(account, 200, reason="Spent before reversal")

        # Now reverse — should not error and should not go negative
        LoyaltyService.reverse_points_for_bill(bill, reason="Safe reversal")
        account.refresh_from_db()
        self.assertGreaterEqual(account.points_balance, 0)


class LoyaltyExpiryTests(CRMTestBase):

    def test_expire_points(self):
        c = self.make_customer(phone="+910001000040")
        program = self.make_loyalty_program()
        account = LoyaltyService.get_or_create_account(c, program)
        LoyaltyService.adjust_points(account, 300, reason="Seed", actor=self.manager_user)

        account.refresh_from_db()
        LoyaltyService.expire_points(account, 300, reason="Expiry test")
        account.refresh_from_db()
        self.assertEqual(account.points_balance, 0)

    def test_expiry_is_idempotent(self):
        c = self.make_customer(phone="+910001000041")
        program = self.make_loyalty_program()
        account = LoyaltyService.get_or_create_account(c, program)
        LoyaltyService.adjust_points(account, 100, reason="Seed", actor=self.manager_user)

        txn1 = LoyaltyService.expire_points(account, 100, reason="Expiry")
        txn2 = LoyaltyService.expire_points(account, 100, reason="Expiry")
        self.assertEqual(txn1.pk, txn2.pk)


class LoyaltyTransactionImmutabilityTest(CRMTestBase):

    def test_cannot_update_loyalty_transaction(self):
        from crm.models import LoyaltyTransaction
        c = self.make_customer(phone="+910001000050")
        program = self.make_loyalty_program()
        account = LoyaltyService.get_or_create_account(c, program)
        LoyaltyService.adjust_points(account, 100, reason="Seed", actor=self.manager_user)

        txn = account.transactions.first()
        txn.reason = "Tampered"
        with self.assertRaises(ValueError):
            txn.save()


class RewardServiceTests(CRMTestBase):

    def test_redeem_reward_deducts_points(self):
        c = self.make_customer(phone="+910001000060")
        program = self.make_loyalty_program()
        account = LoyaltyService.get_or_create_account(c, program)
        LoyaltyService.adjust_points(account, 500, reason="Seed", actor=self.manager_user)

        reward = self.make_reward(points_required=200)
        redemption = RewardService.redeem_reward(c, reward, account, actor=self.cashier_user)

        self.assertEqual(redemption.status, "CONFIRMED")
        self.assertEqual(redemption.points_used, 200)
        account.refresh_from_db()
        self.assertEqual(account.points_balance, 300)

    def test_redeem_insufficient_raises(self):
        c = self.make_customer(phone="+910001000061")
        program = self.make_loyalty_program()
        account = LoyaltyService.get_or_create_account(c, program)
        LoyaltyService.adjust_points(account, 50, reason="Seed", actor=self.manager_user)

        reward = self.make_reward(points_required=200)
        with self.assertRaises(InsufficientLoyaltyPoints):
            RewardService.redeem_reward(c, reward, account)

    def test_inactive_reward_raises(self):
        from crm.models import LoyaltyReward
        c = self.make_customer(phone="+910001000062")
        program = self.make_loyalty_program()
        account = LoyaltyService.get_or_create_account(c, program)
        LoyaltyService.adjust_points(account, 500, reason="Seed", actor=self.manager_user)

        reward = self.make_reward(points_required=100)
        reward.is_active = False
        reward.save()

        with self.assertRaises(RewardUnavailable):
            RewardService.redeem_reward(c, reward, account)

    def test_expired_reward_raises(self):
        from crm.models import LoyaltyReward
        from django.utils import timezone
        c = self.make_customer(phone="+910001000063")
        program = self.make_loyalty_program()
        account = LoyaltyService.get_or_create_account(c, program)
        LoyaltyService.adjust_points(account, 500, reason="Seed", actor=self.manager_user)

        reward = self.make_reward(points_required=100)
        reward.valid_until = timezone.now() - timezone.timedelta(days=1)
        reward.save()

        with self.assertRaises(RewardExpired):
            RewardService.redeem_reward(c, reward, account)
