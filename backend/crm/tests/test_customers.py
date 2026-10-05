# =============================================================================
# RestaurantFlow — CRM Customer Tests
# Phase 17
# =============================================================================

from django.test import TestCase
from django.core.exceptions import ValidationError

from crm.customer_services import (
    CustomerIdentityService, CustomerService, CustomerStatisticsService,
)
from crm.exceptions import (
    CustomerIdentityConflict, CustomerScopeViolation, CRMPermissionDenied,
)
from crm.validators import normalize_phone, normalize_email
from crm.tests.base import CRMTestBase


class PhoneNormalizationTests(TestCase):
    def test_strips_spaces_and_dashes(self):
        self.assertEqual(normalize_phone("+91 98765-43210"), "+919876543210")

    def test_empty_returns_empty(self):
        self.assertEqual(normalize_phone(""), "")
        self.assertEqual(normalize_phone(None), "")

    def test_preserves_plus(self):
        self.assertEqual(normalize_phone("+919876543210"), "+919876543210")


class EmailNormalizationTests(TestCase):
    def test_lowercases(self):
        self.assertEqual(normalize_email("TEST@EXAMPLE.COM"), "test@example.com")

    def test_strips_whitespace(self):
        self.assertEqual(normalize_email("  user@example.com  "), "user@example.com")

    def test_empty_returns_empty(self):
        self.assertEqual(normalize_email(""), "")


class CustomerCreationTests(CRMTestBase):

    def test_create_customer_generates_number(self):
        customer = self.make_customer(phone="+919876543210")
        self.assertTrue(customer.customer_number.startswith("CUS-"))
        self.assertTrue(customer.customer_number[4:].isdigit())

    def test_customer_numbers_are_sequential(self):
        c1 = self.make_customer(phone="+910000000001")
        c2 = self.make_customer(phone="+910000000002")
        n1 = int(c1.customer_number.split("-")[1])
        n2 = int(c2.customer_number.split("-")[1])
        self.assertGreater(n2, n1)

    def test_customer_number_unique_per_restaurant(self):
        c1 = self.make_customer(phone="+910000000003")
        c2 = self.make_customer(phone="+910000000004")
        self.assertNotEqual(c1.customer_number, c2.customer_number)

    def test_customer_scoped_to_restaurant(self):
        customer = self.make_customer()
        self.assertEqual(customer.restaurant, self.restaurant)
        self.assertEqual(customer.company, self.org)

    def test_phone_normalized_on_create(self):
        customer = self.make_customer(phone="+91 98765 43210")
        self.assertNotIn(" ", customer.phone)

    def test_email_normalized_on_create(self):
        customer = self.make_customer(email="TEST@EXAMPLE.COM")
        self.assertEqual(customer.email, "test@example.com")

    def test_create_requires_permission(self):
        # no_crm_user has no customer.create permission
        with self.assertRaises(CRMPermissionDenied):
            CustomerService.create_customer(
                restaurant=self.restaurant,
                data={"first_name": "Jane", "phone": "+919999999999"},
                actor=self.no_crm_user,
            )

    def test_masked_phone(self):
        c = self.make_customer(phone="+919876543210")
        self.assertTrue(c.masked_phone.endswith("3210"))
        self.assertIn("*", c.masked_phone)

    def test_masked_email(self):
        c = self.make_customer(email="srujan@example.com")
        self.assertIn("*", c.masked_email)
        self.assertIn("@example.com", c.masked_email)


class CustomerIdentityTests(CRMTestBase):

    def test_resolve_existing_by_phone(self):
        existing = self.make_customer(phone="+910011223344")
        resolved, created = CustomerIdentityService.resolve_or_create_customer(
            self.restaurant, {"first_name": "Repeat", "phone": "+910011223344"}
        )
        self.assertFalse(created)
        self.assertEqual(resolved.pk, existing.pk)

    def test_resolve_existing_by_email(self):
        existing = self.make_customer(email="existing@test.com")
        resolved, created = CustomerIdentityService.resolve_or_create_customer(
            self.restaurant, {"first_name": "Repeat", "email": "EXISTING@TEST.COM"}
        )
        self.assertFalse(created)
        self.assertEqual(resolved.pk, existing.pk)

    def test_create_when_no_match(self):
        _, created = CustomerIdentityService.resolve_or_create_customer(
            self.restaurant, {"first_name": "NewPerson", "phone": "+910099887766"}
        )
        self.assertTrue(created)

    def test_conflict_raises_exception(self):
        self.make_customer(phone="+910000111111", email="")
        self.make_customer(phone="", email="conflict@test.com")
        with self.assertRaises(CustomerIdentityConflict):
            CustomerIdentityService.resolve_or_create_customer(
                self.restaurant,
                {"first_name": "Both", "phone": "+910000111111", "email": "conflict@test.com"}
            )

    def test_no_cross_restaurant_match(self):
        # Customer in other_restaurant
        other = self.make_customer(restaurant=self.other_restaurant, phone="+910099999999")
        # Resolve in self.restaurant — should create a new customer
        _, created = CustomerIdentityService.resolve_or_create_customer(
            self.restaurant, {"first_name": "New", "phone": "+910099999999"}
        )
        self.assertTrue(created)


class CustomerUpdateTests(CRMTestBase):

    def test_update_name(self):
        c = self.make_customer()
        updated = CustomerService.update_customer(c, {"first_name": "Updated"}, actor=self.manager_user)
        self.assertEqual(updated.first_name, "Updated")

    def test_cannot_update_customer_number(self):
        c = self.make_customer()
        original_number = c.customer_number
        CustomerService.update_customer(c, {"customer_number": "CUS-000099"}, actor=self.manager_user)
        c.refresh_from_db()
        self.assertEqual(c.customer_number, original_number)

    def test_cannot_update_computed_stats(self):
        c = self.make_customer()
        CustomerService.update_customer(
            c,
            {"total_orders": 999, "lifetime_spend": "999999.00"},
            actor=self.manager_user,
        )
        c.refresh_from_db()
        self.assertEqual(c.total_orders, 0)
        self.assertEqual(str(c.lifetime_spend), "0.00")


class CustomerBlockTests(CRMTestBase):

    def test_block_requires_reason(self):
        c = self.make_customer()
        with self.assertRaises(Exception):
            CustomerService.block_customer(c, reason="", actor=self.manager_user)

    def test_block_and_unblock(self):
        c = self.make_customer()
        CustomerService.block_customer(c, reason="Test block", actor=self.manager_user)
        c.refresh_from_db()
        self.assertTrue(c.is_blocked)

        CustomerService.unblock_customer(c, actor=self.manager_user)
        c.refresh_from_db()
        self.assertFalse(c.is_blocked)
        self.assertEqual(c.blocked_reason, "")


class CustomerScopeTests(CRMTestBase):

    def test_scope_isolation(self):
        from crm.access import get_accessible_customers
        c_mine = self.make_customer(restaurant=self.restaurant, phone="+910011111111")
        c_other = self.make_customer(restaurant=self.other_restaurant, phone="+910022222222")

        accessible = get_accessible_customers(self.manager_user)
        ids = list(accessible.values_list("id", flat=True))
        self.assertIn(c_mine.pk, ids)
        # manager_user is only assigned to self.restaurant, not other_restaurant
        self.assertNotIn(c_other.pk, ids)

    def test_superuser_sees_all(self):
        from crm.access import get_accessible_customers
        c1 = self.make_customer(restaurant=self.restaurant, phone="+910033333333")
        c2 = self.make_customer(restaurant=self.other_restaurant, phone="+910044444444")
        accessible = get_accessible_customers(self.superuser)
        ids = list(accessible.values_list("id", flat=True))
        self.assertIn(c1.pk, ids)
        self.assertIn(c2.pk, ids)


class CustomerOrderLinkTests(CRMTestBase):

    def test_link_customer_to_order_idempotent(self):
        from orders.models import Order, OrderType, OrderStatus
        c = self.make_customer(phone="+910055555555")
        order = Order.objects.create(
            branch=self.branch,
            order_number="ORD-001",
            order_type=OrderType.COUNTER,
            status=OrderStatus.CONFIRMED,
            created_by=self.cashier_user,
        )
        CustomerService.link_customer_to_order(order, c, actor=self.cashier_user)
        CustomerService.link_customer_to_order(order, c, actor=self.cashier_user)  # idempotent
        order.refresh_from_db()
        self.assertEqual(order.customer_id, c.pk)

    def test_cannot_link_cross_restaurant(self):
        from orders.models import Order, OrderType, OrderStatus
        c_other = self.make_customer(restaurant=self.other_restaurant, phone="+910066666666")
        order = Order.objects.create(
            branch=self.branch,
            order_number="ORD-002",
            order_type=OrderType.COUNTER,
            status=OrderStatus.CONFIRMED,
            created_by=self.cashier_user,
        )
        with self.assertRaises(CustomerScopeViolation):
            CustomerService.link_customer_to_order(order, c_other, actor=self.cashier_user)
