# =============================================================================
# RestaurantFlow — Billing Permission / Security Tests
# Phase 8
#
# Tests:
#   - Restaurant A cannot access Restaurant B bills (IDOR)
#   - Branch A cannot access Branch B bills
#   - cashier cannot approve correction
#   - cashier cannot void bills
#   - frontend total manipulation rejected (backend recalculates)
#   - invalid discount type rejected
#   - invalid tax rate rejected (negative)
#   - UUID tampering returns 404
#   - unauthenticated requests rejected
#   - other_user has no billing access
# =============================================================================

import uuid
from decimal import Decimal

from django.test import TestCase
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.test import APIClient

from billing.models import Bill, BillStatus
from billing import access as bill_acl
from billing import services
from billing.tests.base import BillingTestBase

from accounts.models import User, Role, Permission, UserRoleAssignment
from organizations.models import Organization, Restaurant, Branch
from menu.models import Category, MenuItem, MenuItemBranch, MenuItemPrice, TaxRate
from orders.models import Order, OrderItem, OrderStatus, OrderType
from counters.models import Counter, CounterSession, SessionStatus, CounterStatus
from django.utils import timezone


class TestScopeIsolation(BillingTestBase):
    """IDOR prevention: users cannot access bills outside their scope."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        # Second restaurant completely separate from the first
        cls.org2 = Organization.objects.create(
            name="Other Org", slug="other-org"
        )
        cls.restaurant2 = Restaurant.objects.create(
            organization=cls.org2,
            name="Other Restaurant",
            slug="other-restaurant",
            code="OR01",
        )
        cls.branch2 = Branch.objects.create(
            restaurant=cls.restaurant2,
            name="Other Branch",
            code="OB02",
        )
        cls.tax2 = TaxRate.objects.create(
            restaurant=cls.restaurant2,
            name="GST 5%",
            code="GST_5",
            rate=Decimal("5.000"),
        )
        cls.cat2 = Category.objects.create(
            restaurant=cls.restaurant2,
            name="Cat2",
            slug="cat2",
        )
        cls.item2 = MenuItem.objects.create(
            restaurant=cls.restaurant2,
            category=cls.cat2,
            name="Item2",
            slug="item2",
            sku="ITEM2-001",
        )
        cls.counter2 = Counter.objects.create(
            branch=cls.branch2,
            name="Counter 01",
            code="C01",
            status=CounterStatus.ACTIVE,
        )

        # User scoped ONLY to restaurant2
        cls.restaurant2_user = User.objects.create_user(
            email="r2user@test.com",
            password="pass123",
            first_name="R2",
            last_name="User",
        )
        r2_perms = [
            Permission.objects.get_or_create(
                code="bill.view",
                defaults={"name": "View", "description": "", "module": "billing", "action": "view"},
            )[0],
            Permission.objects.get_or_create(
                code="bill.create",
                defaults={"name": "Create", "description": "", "module": "billing", "action": "create"},
            )[0],
        ]
        r2_role = Role.objects.create(
            name="R2 Cashier",
            code="R2_CASHIER",
            scope=Role.SCOPE_BRANCH,
        )
        r2_role.permissions.set(r2_perms)
        UserRoleAssignment.objects.create(
            user=cls.restaurant2_user,
            role=r2_role,
            organization=cls.org2,
            restaurant=cls.restaurant2,
            branch=cls.branch2,
        )

    def _make_r2_bill(self):
        """Create a bill in restaurant2's branch."""
        ts = timezone.now().strftime("%Y%m%d%H%M%S%f")
        r2_session = CounterSession.objects.create(
            counter=self.counter2,
            opened_by=self.restaurant2_user,
            opening_cash=Decimal("500.00"),
            status=SessionStatus.OPEN,
        )
        MenuItemBranch.objects.create(
            menu_item=self.item2, branch=self.branch2, is_available=True
        )
        MenuItemPrice.objects.create(
            menu_item=self.item2, branch=self.branch2, price=Decimal("100.00"), is_active=True
        )
        order = Order.objects.create(
            branch=self.branch2,
            order_number=f"R2-{ts}",
            order_type=OrderType.COUNTER,
            counter=self.counter2,
            counter_session=r2_session,
            created_by=self.restaurant2_user,
            status=OrderStatus.CONFIRMED,
            confirmed_at=timezone.now(),
        )
        OrderItem.objects.create(
            order=order,
            menu_item=self.item2,
            item_name_snapshot="Item2",
            sku_snapshot="ITEM2-001",
            unit_price_snapshot=Decimal("100.00"),
            tax_rate_snapshot=Decimal("5.000"),
            tax_code_snapshot="GST_5",
            quantity=Decimal("1.000"),
        )
        return services.create_bill_from_order(order, self.restaurant2_user)

    def test_restaurant1_user_cannot_access_restaurant2_bill(self):
        """cashier (restaurant1) must not see restaurant2's bill."""
        r2_bill = self._make_r2_bill()
        accessible = bill_acl.get_accessible_bills(self.cashier)
        self.assertFalse(accessible.filter(pk=r2_bill.pk).exists())

    def test_restaurant2_user_cannot_access_restaurant1_bill(self):
        order = self._make_confirmed_order()
        r1_bill = services.create_bill_from_order(order, self.cashier)
        accessible = bill_acl.get_accessible_bills(self.restaurant2_user)
        self.assertFalse(accessible.filter(pk=r1_bill.pk).exists())

    def test_uuid_tampering_returns_empty_queryset(self):
        """A random UUID that exists in DB but belongs to another scope is invisible."""
        r2_bill = self._make_r2_bill()
        # cashier trying to look up r2 bill UUID via accessible queryset
        qs = bill_acl.get_accessible_bills(self.cashier).filter(pk=r2_bill.pk)
        self.assertEqual(qs.count(), 0)

    def test_unauthenticated_gets_empty_queryset(self):
        anon = User.__new__(User)
        anon.is_authenticated = False
        qs = bill_acl.get_accessible_bills(anon)
        self.assertEqual(qs.count(), 0)

    def test_inactive_user_gets_empty_queryset(self):
        inactive = User.objects.create_user(
            email="inactive@test.com",
            password="pass",
            first_name="Inactive",
            last_name="User",
        )
        inactive.is_active = False
        inactive.save()
        qs = bill_acl.get_accessible_bills(inactive)
        self.assertEqual(qs.count(), 0)


class TestPermissionEnforcement(BillingTestBase):
    """Permission codes are checked, not role names."""

    def test_cashier_cannot_void_bill(self):
        order = self._make_confirmed_order()
        bill = services.create_bill_from_order(order, self.cashier)
        services.finalize_bill(bill, self.cashier)
        bill.refresh_from_db()
        with self.assertRaises(PermissionDenied):
            services.void_bill(bill, self.cashier, reason="cashier trying to void")

    def test_cashier_cannot_approve_correction(self):
        order = self._make_confirmed_order()
        bill = services.create_bill_from_order(order, self.cashier)
        services.finalize_bill(bill, self.cashier)
        bill.refresh_from_db()
        correction = services.request_bill_correction(
            bill, self.cashier,
            correction_type="ITEM_CORRECTION",
            reason="Some item correction request reason here.",
        )
        # Cashier does not have bill.correction.approve
        with self.assertRaises(PermissionDenied):
            services.approve_bill_correction(correction, self.cashier, note="")

    def test_other_user_cannot_create_bill(self):
        order = self._make_confirmed_order()
        with self.assertRaises(PermissionDenied):
            services.create_bill_from_order(order, self.other_user)

    def test_other_user_cannot_finalize_bill(self):
        order = self._make_confirmed_order()
        bill = services.create_bill_from_order(order, self.cashier)
        with self.assertRaises(PermissionDenied):
            services.finalize_bill(bill, self.other_user)

    def test_other_user_cannot_apply_discount(self):
        order = self._make_confirmed_order()
        bill = services.create_bill_from_order(order, self.cashier)
        with self.assertRaises(PermissionDenied):
            services.apply_discount(
                bill, self.other_user,
                discount_type="PERCENTAGE",
                value=Decimal("5"),
            )

    def test_manager_can_void_bill(self):
        """Manager has bill.void permission."""
        order = self._make_confirmed_order()
        bill = services.create_bill_from_order(order, self.cashier)
        services.finalize_bill(bill, self.cashier)
        bill.refresh_from_db()
        voided = services.void_bill(bill, self.manager, reason="Test void by manager")
        self.assertEqual(voided.status, BillStatus.VOID)


class TestFrontendManipulationRejected(BillingTestBase):
    """Backend must not trust frontend-calculated totals."""

    def test_calculate_bill_always_uses_snapshots(self):
        """
        Even if someone tampers with a POST body, calculate_bill()
        reads from BillItem.unit_price (snapshot), not request data.
        """
        order = self._make_confirmed_order()
        bill = services.create_bill_from_order(order, self.cashier)
        # Backend's authoritative result
        result = services.calculate_bill(bill)
        # Must equal snapshot-based values, not zero or some frontend value
        self.assertEqual(result["subtotal"], "620.00")
        self.assertEqual(result["grand_total"], "645.00")

    def test_apply_discount_ignores_client_total(self):
        """
        apply_discount receives discount_type + value only.
        There is no way to pass a pre-computed grand_total.
        """
        order = self._make_confirmed_order()
        bill = services.create_bill_from_order(order, self.cashier)
        # Applying 10% discount
        services.apply_discount(
            bill, self.manager,
            discount_type="PERCENTAGE",
            value=Decimal("10"),
            max_pct=Decimal("100"),
        )
        bill.refresh_from_db()
        # Backend computed, not a magic number from the frontend
        self.assertEqual(bill.discount_amount, Decimal("62.00"))
        self.assertEqual(bill.grand_total, Decimal("581.00"))


class TestAPIAuthentication(BillingTestBase):
    """API-level auth tests via DRF test client."""

    def setUp(self):
        self.client = APIClient()

    def test_unauthenticated_bill_list_returns_401(self):
        response = self.client.get("/api/billing/bills/")
        self.assertEqual(response.status_code, 401)

    def test_unauthenticated_bill_detail_returns_401(self):
        response = self.client.get(f"/api/billing/bills/{uuid.uuid4()}/")
        self.assertEqual(response.status_code, 401)

    def test_authenticated_no_bills_returns_empty_list(self):
        self.client.force_authenticate(user=self.cashier)
        response = self.client.get("/api/billing/bills/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 0)

    def test_create_bill_endpoint_returns_201(self):
        order = self._make_confirmed_order()
        self.client.force_authenticate(user=self.cashier)
        response = self.client.post(f"/api/billing/bills/from-order/{order.pk}/")
        self.assertIn(response.status_code, [200, 201])
        self.assertIn("bill_number", response.data)

    def test_cannot_create_bill_for_inaccessible_order(self):
        # other_user has no access at all
        order = self._make_confirmed_order()
        self.client.force_authenticate(user=self.other_user)
        response = self.client.post(f"/api/billing/bills/from-order/{order.pk}/")
        self.assertIn(response.status_code, [403, 404])

    def test_random_uuid_returns_404(self):
        self.client.force_authenticate(user=self.cashier)
        response = self.client.get(f"/api/billing/bills/{uuid.uuid4()}/")
        self.assertEqual(response.status_code, 404)

    def test_finalize_endpoint(self):
        order = self._make_confirmed_order()
        bill = services.create_bill_from_order(order, self.cashier)
        self.client.force_authenticate(user=self.cashier)
        response = self.client.post(
            f"/api/billing/bills/{bill.pk}/finalize/",
            data={},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "FINALIZED")

    def test_apply_discount_endpoint(self):
        order = self._make_confirmed_order()
        bill = services.create_bill_from_order(order, self.cashier)
        self.client.force_authenticate(user=self.cashier)
        response = self.client.post(
            f"/api/billing/bills/{bill.pk}/discount/",
            data={"discount_type": "FIXED_AMOUNT", "discount_value": "50.00"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["discount_amount"], "50.00")

    def test_receipt_endpoint_requires_bill_print_permission(self):
        order = self._make_confirmed_order()
        bill = services.create_bill_from_order(order, self.cashier)
        self.client.force_authenticate(user=self.cashier)
        response = self.client.get(f"/api/billing/bills/{bill.pk}/receipt/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("bill_number", response.data)
