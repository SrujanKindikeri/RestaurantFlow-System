# =============================================================================
# RestaurantFlow — Accounting Permission & Isolation Tests
# Phase 13
# =============================================================================

import uuid
from decimal import Decimal
from datetime import date

from django.test import TestCase
from rest_framework.exceptions import PermissionDenied
from rest_framework.test import APIClient

from accounting.tests.base import AccountingTestBase
from accounting.services import AccountService, JournalService, PeriodService
from accounting.constants import (
    ACCOUNT_TYPE_ASSET, NORMAL_BALANCE_DEBIT,
    PERM_ACCOUNT_VIEW, PERM_ACCOUNT_CREATE,
)


class RestaurantIsolationTests(AccountingTestBase):
    """
    Verify that Restaurant A cannot access Restaurant B's accounting data.
    """

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        # Create a second restaurant
        from organizations.models import Organization, Restaurant, Branch
        cls.org2 = Organization.objects.create(
            name="Other Corp",
            slug=f"other-corp-{uuid.uuid4().hex[:6]}",
        )
        cls.restaurant2 = Restaurant.objects.create(
            organization=cls.org2,
            name="Other Restaurant",
            slug=f"other-rest-{uuid.uuid4().hex[:6]}",
            code=f"OR{uuid.uuid4().hex[:4].upper()}",
        )
        cls.branch2 = Branch.objects.create(
            restaurant=cls.restaurant2,
            name="Other Branch",
            code=f"OB{uuid.uuid4().hex[:4].upper()}",
        )
        # Account in restaurant2
        from accounting.models import Account
        cls.acct_r2 = Account.objects.create(
            restaurant=cls.restaurant2,
            code="1100",
            name="Cash R2",
            account_type=ACCOUNT_TYPE_ASSET,
            normal_balance=NORMAL_BALANCE_DEBIT,
        )

    def test_cannot_use_other_restaurant_account_in_journal(self):
        """A line referencing another restaurant's account is rejected."""
        from accounting.exceptions import CrossRestaurantAccountError
        from accounting.validators import validate_accounts_same_restaurant

        with self.assertRaises(CrossRestaurantAccountError):
            validate_accounts_same_restaurant(self.restaurant, [self.acct_r2])

    def test_accessible_accounts_scoped_to_user_restaurant(self):
        """get_accessible_accounts returns only the accessible restaurant's accounts."""
        from accounting import access as accounting_access
        accounts = accounting_access.get_accessible_accounts(self.user)
        restaurant2_accounts = accounts.filter(restaurant=self.restaurant2)
        # Superuser sees all; non-superuser must not see other restaurant's
        # We test with a non-superuser
        from accounts.models import User
        limited_user = User.objects.create_user(
            email=f"limited-{uuid.uuid4().hex[:6]}@test.com",
            password="pass123",
        )
        limited_accounts = accounting_access.get_accessible_accounts(limited_user)
        self.assertEqual(limited_accounts.count(), 0)

    def test_can_access_own_restaurant_fiscal_year(self):
        from accounting import access as accounting_access
        self.assertTrue(
            accounting_access.can_access_fiscal_year(self.user, self.fiscal_year)
        )


class PermissionCodeTests(AccountingTestBase):
    """Test that permission codes block unauthorized access."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        from accounts.models import User, Role, Permission
        # Non-superuser with no permissions
        cls.no_perm_user = User.objects.create_user(
            email=f"noperm-{uuid.uuid4().hex[:6]}@test.com",
            password="pass123",
        )

    def test_create_account_requires_permission(self):
        with self.assertRaises(PermissionDenied):
            AccountService.create_account(
                restaurant=self.restaurant,
                code="9998",
                name="Unauthorized",
                account_type=ACCOUNT_TYPE_ASSET,
                normal_balance=NORMAL_BALANCE_DEBIT,
                user=self.no_perm_user,  # no permissions
            )

    def test_post_journal_requires_permission(self):
        entry = self._make_journal_entry()
        with self.assertRaises(PermissionDenied):
            JournalService.post_entry(entry, self.no_perm_user)

    def test_close_period_requires_permission(self):
        from datetime import timedelta
        today = date.today()
        nm = (today.replace(day=1) + timedelta(days=32)).replace(day=1)
        period = PeriodService.create_period(
            restaurant=self.restaurant, name="Perm Test",
            start_date=nm, end_date=nm + timedelta(days=27),
            user=self.user,
        )
        with self.assertRaises(PermissionDenied):
            PeriodService.close_period(period, self.no_perm_user)

    def test_unauthenticated_user_denied(self):
        """None user is always rejected."""
        with self.assertRaises(PermissionDenied):
            AccountService.create_account(
                restaurant=self.restaurant,
                code="9997",
                name="Anon",
                account_type=ACCOUNT_TYPE_ASSET,
                normal_balance=NORMAL_BALANCE_DEBIT,
                user=None,
            )


class AuditLogImmutabilityTests(AccountingTestBase):

    def test_audit_log_immutable(self):
        """AccountingAuditLog entries cannot be updated after creation."""
        from accounting.models import AccountingAuditLog
        log = AccountingAuditLog.objects.create(
            actor=self.user,
            action="JOURNAL_POSTED",
            entity_type="JournalEntry",
            entity_id=uuid.uuid4(),
            restaurant=self.restaurant,
        )
        # After creation, _state.adding is False — any save() call is an update
        # and must be rejected by the immutability guard.
        with self.assertRaises(ValueError):
            log.action = "TAMPERED"
            log.save()

    def test_audit_log_created_on_journal_post(self):
        from accounting.models import AccountingAuditLog
        from accounting.constants import AUDIT_JOURNAL_POSTED

        before_count = AccountingAuditLog.objects.filter(
            action=AUDIT_JOURNAL_POSTED,
            restaurant=self.restaurant,
        ).count()

        self._post_journal_entry()

        after_count = AccountingAuditLog.objects.filter(
            action=AUDIT_JOURNAL_POSTED,
            restaurant=self.restaurant,
        ).count()

        self.assertEqual(after_count, before_count + 1)

    def test_audit_log_created_on_account_creation(self):
        from accounting.models import AccountingAuditLog
        from accounting.constants import AUDIT_ACCOUNT_CREATED

        before = AccountingAuditLog.objects.filter(
            action=AUDIT_ACCOUNT_CREATED, restaurant=self.restaurant
        ).count()

        AccountService.create_account(
            restaurant=self.restaurant, code="8001",
            name="Audit Test Acct", account_type=ACCOUNT_TYPE_ASSET,
            normal_balance=NORMAL_BALANCE_DEBIT, user=self.user,
        )

        after = AccountingAuditLog.objects.filter(
            action=AUDIT_ACCOUNT_CREATED, restaurant=self.restaurant
        ).count()
        self.assertEqual(after, before + 1)
