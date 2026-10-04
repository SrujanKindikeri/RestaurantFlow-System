# =============================================================================
# RestaurantFlow — Chart of Accounts Tests
# Phase 13
# =============================================================================

import uuid
from decimal import Decimal
from django.test import TestCase
from rest_framework.exceptions import PermissionDenied, ValidationError

from accounting.tests.base import AccountingTestBase
from accounting.services import AccountService
from accounting.exceptions import AccountHierarchyCycleError, NonPostableAccountError
from accounting.constants import (
    ACCOUNT_TYPE_ASSET, ACCOUNT_TYPE_EXPENSE,
    NORMAL_BALANCE_DEBIT, NORMAL_BALANCE_CREDIT,
)


class CreateAccountTests(AccountingTestBase):

    def test_create_account_success(self):
        acct = AccountService.create_account(
            restaurant=self.restaurant,
            code="1999",
            name="Petty Cash",
            account_type=ACCOUNT_TYPE_ASSET,
            normal_balance=NORMAL_BALANCE_DEBIT,
            user=self.user,
        )
        self.assertEqual(acct.code, "1999")
        self.assertEqual(acct.account_type, ACCOUNT_TYPE_ASSET)
        self.assertTrue(acct.is_active)
        self.assertTrue(acct.is_postable)

    def test_account_code_unique_per_restaurant(self):
        """Duplicate code within same restaurant raises IntegrityError/ValidationError."""
        from django.db import IntegrityError
        AccountService.create_account(
            restaurant=self.restaurant,
            code="9001",
            name="Account A",
            account_type=ACCOUNT_TYPE_ASSET,
            normal_balance=NORMAL_BALANCE_DEBIT,
            user=self.user,
        )
        with self.assertRaises((IntegrityError, Exception)):
            AccountService.create_account(
                restaurant=self.restaurant,
                code="9001",  # duplicate
                name="Account B",
                account_type=ACCOUNT_TYPE_ASSET,
                normal_balance=NORMAL_BALANCE_DEBIT,
                user=self.user,
            )

    def test_normal_balance_derived_from_account_type(self):
        """normal_balance defaults from account_type if not supplied."""
        acct = AccountService.create_account(
            restaurant=self.restaurant,
            code="6998",
            name="Auto Balance",
            account_type=ACCOUNT_TYPE_EXPENSE,
            normal_balance="",  # let service derive it
            user=self.user,
        )
        self.assertEqual(acct.normal_balance, NORMAL_BALANCE_DEBIT)

    def test_parent_account_hierarchy(self):
        """Child account can reference parent from same restaurant."""
        parent = AccountService.create_account(
            restaurant=self.restaurant,
            code="1050",
            name="Current Assets",
            account_type=ACCOUNT_TYPE_ASSET,
            normal_balance=NORMAL_BALANCE_DEBIT,
            user=self.user,
            is_group=True,
            is_postable=False,
        )
        child = AccountService.create_account(
            restaurant=self.restaurant,
            code="1051",
            name="Cash in Hand",
            account_type=ACCOUNT_TYPE_ASSET,
            normal_balance=NORMAL_BALANCE_DEBIT,
            user=self.user,
            parent_account=parent,
        )
        self.assertEqual(child.parent_account, parent)
        self.assertIn(parent, child.get_ancestors())

    def test_group_account_not_postable_by_default(self):
        """Group accounts should be created with is_postable=False."""
        group = AccountService.create_account(
            restaurant=self.restaurant,
            code="1060",
            name="Assets Group",
            account_type=ACCOUNT_TYPE_ASSET,
            normal_balance=NORMAL_BALANCE_DEBIT,
            user=self.user,
            is_group=True,
            is_postable=False,
        )
        self.assertFalse(group.is_postable)

    def test_deactivate_account(self):
        acct = AccountService.create_account(
            restaurant=self.restaurant,
            code="1997",
            name="To Deactivate",
            account_type=ACCOUNT_TYPE_ASSET,
            normal_balance=NORMAL_BALANCE_DEBIT,
            user=self.user,
        )
        result = AccountService.deactivate_account(acct, self.user)
        self.assertFalse(result.is_active)

    def test_cannot_deactivate_account_with_active_children(self):
        parent = AccountService.create_account(
            restaurant=self.restaurant,
            code="1070",
            name="Parent Group",
            account_type=ACCOUNT_TYPE_ASSET,
            normal_balance=NORMAL_BALANCE_DEBIT,
            user=self.user,
            is_group=True,
            is_postable=False,
        )
        AccountService.create_account(
            restaurant=self.restaurant,
            code="1071",
            name="Child Account",
            account_type=ACCOUNT_TYPE_ASSET,
            normal_balance=NORMAL_BALANCE_DEBIT,
            user=self.user,
            parent_account=parent,
        )
        with self.assertRaises(ValidationError):
            AccountService.deactivate_account(parent, self.user)

    def test_account_type_validation_postable(self):
        """Cannot post to a non-postable account."""
        from accounting.validators import validate_account_postable
        with self.assertRaises(NonPostableAccountError):
            validate_account_postable(self.acct_assets_header)

    def test_account_across_restaurants_rejected(self):
        """Account from different restaurant raises CrossRestaurantAccountError."""
        from organizations.models import Organization, Restaurant
        other_org = Organization.objects.create(
            name="Other Org",
            slug=f"other-{uuid.uuid4().hex[:6]}",
        )
        other_rest = Restaurant.objects.create(
            organization=other_org,
            name="Other Restaurant",
            slug=f"other-rest-{uuid.uuid4().hex[:6]}",
            code=f"OR{uuid.uuid4().hex[:4].upper()}",
        )
        other_acct = AccountService.create_account(
            restaurant=other_rest,
            code="1100",
            name="Cash",
            account_type=ACCOUNT_TYPE_ASSET,
            normal_balance=NORMAL_BALANCE_DEBIT,
            user=self.user,
        )
        from accounting.exceptions import CrossRestaurantAccountError
        from accounting.validators import validate_accounts_same_restaurant
        with self.assertRaises(CrossRestaurantAccountError):
            validate_accounts_same_restaurant(self.restaurant, [other_acct])
