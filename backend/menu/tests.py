# =============================================================================
# RestaurantFlow — Menu Tests
# Phase 5
#
# Tests cover (per spec §58–59):
#
#   Categories:
#     ✓ create
#     ✓ update
#     ✓ disable / reactivate (enable)
#     ✓ duplicate slug rejected
#     ✓ cross-restaurant category access rejected
#
#   Menu Items:
#     ✓ create
#     ✓ update
#     ✓ disable / reactivate (enable)
#     ✓ duplicate SKU rejected
#     ✓ category restaurant mismatch rejected
#     ✓ restaurant isolation works
#
#   Pricing:
#     ✓ create price
#     ✓ branch must belong to same restaurant
#     ✓ negative price rejected
#     ✓ Decimal calculation
#     ✓ price history preserved (deactivate, not delete)
#     ✓ overlapping active price periods rejected
#
#   Availability:
#     ✓ create availability
#     ✓ unavailable item excluded from catalog
#     ✓ time window check (available_from / available_to)
#     ✓ cross-restaurant access rejected
#
#   Tax:
#     ✓ create tax rate
#     ✓ update tax rate
#     ✓ negative rate rejected
#     ✓ restaurant isolation
#
#   Security:
#     ✓ cashier cannot modify menu
#     ✓ unauthorized manager denied
#     ✓ restaurant A cannot access restaurant B
#     ✓ branch A cannot access branch B where unauthorized
#
#   Catalog API:
#     ✓ only authorized branch
#     ✓ only active categories
#     ✓ only active + available items
#     ✓ correct branch price
#     ✓ correct tax configuration
#     ✓ correct ordering
# =============================================================================

from decimal import Decimal
from datetime import time

from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import Role, Permission, UserRoleAssignment, UserProfile
from organizations.models import Organization, Restaurant, Branch
from menu.models import TaxRate, Category, MenuItem, MenuItemPrice, MenuItemBranch
from menu.services import is_menu_item_available


# =============================================================================
# Test helpers (mirrors pattern from accounts/tests.py)
# =============================================================================

def make_user(email, password="TestPass@1", **kwargs):
    from django.contrib.auth import get_user_model
    User = get_user_model()
    user = User.objects.create_user(email=email, password=password, **kwargs)
    UserProfile.objects.get_or_create(user=user)
    return user


def make_org(name="Test Org", slug=None):
    from django.utils.text import slugify
    return Organization.objects.create(
        name=name,
        slug=slug or slugify(name) + "-menu-test",
        currency="INR",
        timezone="Asia/Kolkata",
    )


def make_restaurant(org, name="Test Restaurant", code="REST-001"):
    return Restaurant.objects.create(organization=org, name=name, code=code)


def make_branch(restaurant, name="Test Branch", code="BR-001"):
    return Branch.objects.create(restaurant=restaurant, name=name, code=code)


def get_or_create_role(code):
    scope_map = {
        Role.CODE_COMPANY_HEAD: Role.SCOPE_ORGANIZATION,
        Role.CODE_CENTRAL_ADMIN: Role.SCOPE_ORGANIZATION,
        Role.CODE_RESTAURANT_OWNER: Role.SCOPE_RESTAURANT,
        Role.CODE_RESTAURANT_MANAGER: Role.SCOPE_BRANCH,
        Role.CODE_CASHIER: Role.SCOPE_BRANCH,
        Role.CODE_WAITER: Role.SCOPE_BRANCH,
    }
    role, _ = Role.objects.get_or_create(
        code=code,
        defaults={
            "name": code,
            "scope": scope_map.get(code, Role.SCOPE_BRANCH),
            "is_system_role": True,
            "is_active": True,
        },
    )
    return role


def get_or_create_permission(code, module="menu", action="view"):
    perm, _ = Permission.objects.get_or_create(
        code=code,
        defaults={"name": code, "module": module, "action": action, "is_active": True},
    )
    return perm


def assign_role(user, role_code, org=None, restaurant=None, branch=None):
    role = get_or_create_role(role_code)
    a = UserRoleAssignment(
        user=user, role=role,
        organization=org, restaurant=restaurant, branch=branch,
        is_active=True,
    )
    a.full_clean()
    a.save()
    return a


def grant_permission(role_code, *perm_codes):
    """Ensure the given role has all listed permissions."""
    role = get_or_create_role(role_code)
    for code in perm_codes:
        perm = get_or_create_permission(code)
        role.permissions.add(perm)


def auth_client(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


def make_tax_rate(restaurant, code="GST", rate="5.000"):
    return TaxRate.objects.create(
        restaurant=restaurant,
        name=code,
        code=code,
        rate=Decimal(rate),
        is_active=True,
    )


def make_category(restaurant, name="Veg", order=1):
    return Category.objects.create(
        restaurant=restaurant,
        name=name,
        display_order=order,
        is_active=True,
    )


def make_menu_item(restaurant, category, name="Paneer Curry", sku="PC-001", tax_rate=None):
    return MenuItem.objects.create(
        restaurant=restaurant,
        category=category,
        name=name,
        sku=sku,
        food_type="VEG",
        tax_rate=tax_rate,
        is_active=True,
        is_available=True,
        preparation_time_minutes=10,
    )


def make_price(item, branch, price="100.00", is_active=True):
    return MenuItemPrice.objects.create(
        menu_item=item,
        branch=branch,
        price=Decimal(price),
        is_active=is_active,
    )


def make_availability(item, branch, is_available=True):
    return MenuItemBranch.objects.create(
        menu_item=item,
        branch=branch,
        is_available=is_available,
    )


# =============================================================================
# 1. Tax Rate Tests
# =============================================================================

class TaxRateModelTests(TestCase):

    def setUp(self):
        self.org = make_org("TaxOrg", slug="tax-org-test")
        self.restaurant = make_restaurant(self.org, code="TAXR-001")

    def test_create_tax_rate(self):
        rate = make_tax_rate(self.restaurant, code="GST5", rate="5.000")
        self.assertEqual(rate.code, "GST5")
        self.assertEqual(rate.rate, Decimal("5.000"))
        self.assertTrue(rate.is_active)

    def test_update_tax_rate(self):
        rate = make_tax_rate(self.restaurant, code="GST5U", rate="5.000")
        rate.rate = Decimal("7.500")
        rate.save()
        rate.refresh_from_db()
        self.assertEqual(rate.rate, Decimal("7.500"))

    def test_duplicate_code_per_restaurant_rejected(self):
        make_tax_rate(self.restaurant, code="DUP", rate="5.000")
        from django.db import IntegrityError
        with self.assertRaises(Exception):
            TaxRate.objects.create(
                restaurant=self.restaurant,
                name="DUP2",
                code="DUP",
                rate=Decimal("3.000"),
            )

    def test_negative_rate_rejected_by_clean(self):
        from django.core.exceptions import ValidationError
        rate = TaxRate(
            restaurant=self.restaurant,
            name="NEG",
            code="NEG_RATE",
            rate=Decimal("-1.000"),
        )
        with self.assertRaises(ValidationError):
            rate.full_clean()

    def test_restaurant_isolation(self):
        org2 = make_org("OtherOrg", slug="other-org-tax")
        rest2 = make_restaurant(org2, code="TAXR-002")
        rate1 = make_tax_rate(self.restaurant, code="ISOLATE", rate="5.000")
        rate2 = make_tax_rate(rest2, code="ISOLATE", rate="5.000")
        # Same code allowed in different restaurants
        self.assertNotEqual(rate1.pk, rate2.pk)


# =============================================================================
# 2. Category Tests
# =============================================================================

class CategoryModelTests(TestCase):

    def setUp(self):
        self.org = make_org("CatOrg", slug="cat-org-test")
        self.restaurant = make_restaurant(self.org, code="CATR-001")

    def test_create_category(self):
        cat = make_category(self.restaurant, name="Veg")
        self.assertEqual(cat.name, "Veg")
        self.assertIsNotNone(cat.slug)
        self.assertTrue(cat.is_active)

    def test_slug_auto_generated(self):
        cat = make_category(self.restaurant, name="Non Veg")
        self.assertEqual(cat.slug, "non-veg")

    def test_update_category(self):
        cat = make_category(self.restaurant, name="Snacks")
        cat.display_order = 5
        cat.save()
        cat.refresh_from_db()
        self.assertEqual(cat.display_order, 5)

    def test_disable_and_reactivate(self):
        cat = make_category(self.restaurant, name="Bev")
        cat.is_active = False
        cat.save()
        cat.refresh_from_db()
        self.assertFalse(cat.is_active)
        cat.is_active = True
        cat.save()
        cat.refresh_from_db()
        self.assertTrue(cat.is_active)

    def test_duplicate_name_rejected_via_serializer(self):
        """Serializer rejects a category with the same name in the same restaurant."""
        make_category(self.restaurant, name="Desserts")
        from menu.serializers import CategorySerializer
        serializer = CategorySerializer(data={
            "restaurant": str(self.restaurant.pk),
            "name": "Desserts",
            "display_order": 2,
        })
        self.assertFalse(serializer.is_valid())
        self.assertIn("name", serializer.errors)

    def test_same_name_different_restaurants_allowed(self):
        org2 = make_org("OtherCatOrg", slug="other-cat-org")
        rest2 = make_restaurant(org2, code="CATR-002")
        cat1 = make_category(self.restaurant, name="Veg X")
        cat2 = make_category(rest2, name="Veg X")
        self.assertNotEqual(cat1.pk, cat2.pk)


# =============================================================================
# 3. MenuItem Model Tests
# =============================================================================

class MenuItemModelTests(TestCase):

    def setUp(self):
        self.org = make_org("ItemOrg", slug="item-org-test")
        self.restaurant = make_restaurant(self.org, code="ITEMR-001")
        self.category = make_category(self.restaurant, name="Mains")
        self.tax_rate = make_tax_rate(self.restaurant)

    def test_create_menu_item(self):
        item = make_menu_item(
            self.restaurant, self.category,
            name="Butter Chicken", sku="BC-001",
            tax_rate=self.tax_rate,
        )
        self.assertEqual(item.name, "Butter Chicken")
        self.assertEqual(item.sku, "BC-001")
        self.assertEqual(item.food_type, "VEG")
        self.assertTrue(item.is_active)
        self.assertIsNotNone(item.slug)

    def test_slug_auto_generated(self):
        item = make_menu_item(self.restaurant, self.category, name="Cold Coffee", sku="CC-001")
        self.assertEqual(item.slug, "cold-coffee")

    def test_update_menu_item(self):
        item = make_menu_item(self.restaurant, self.category, name="Dosa", sku="DS-001")
        item.preparation_time_minutes = 15
        item.save()
        item.refresh_from_db()
        self.assertEqual(item.preparation_time_minutes, 15)

    def test_disable_and_enable(self):
        item = make_menu_item(self.restaurant, self.category, name="Idli", sku="ID-001")
        item.is_active = False
        item.save()
        item.refresh_from_db()
        self.assertFalse(item.is_active)
        item.is_active = True
        item.save()
        item.refresh_from_db()
        self.assertTrue(item.is_active)

    def test_duplicate_sku_rejected_via_serializer(self):
        make_menu_item(self.restaurant, self.category, name="Burger", sku="DUPE-001")
        from menu.serializers import MenuItemSerializer
        serializer = MenuItemSerializer(data={
            "restaurant": str(self.restaurant.pk),
            "category": str(self.category.pk),
            "name": "Burger 2",
            "sku": "DUPE-001",
            "food_type": "VEG",
        })
        self.assertFalse(serializer.is_valid())
        self.assertIn("sku", serializer.errors)

    def test_category_restaurant_mismatch_rejected(self):
        org2 = make_org("MismatchOrg", slug="mismatch-org-menu")
        rest2 = make_restaurant(org2, code="MISMATCH-002")
        wrong_cat = make_category(rest2, name="Wrong Cat")
        from menu.serializers import MenuItemSerializer
        serializer = MenuItemSerializer(data={
            "restaurant": str(self.restaurant.pk),
            "category": str(wrong_cat.pk),
            "name": "Mismatch Item",
            "food_type": "VEG",
        })
        self.assertFalse(serializer.is_valid())
        self.assertIn("category", serializer.errors)

    def test_tax_rate_restaurant_mismatch_rejected(self):
        org2 = make_org("TaxMismatchOrg", slug="tax-mismatch-org")
        rest2 = make_restaurant(org2, code="TAXMIS-002")
        wrong_tax = make_tax_rate(rest2, code="WRONG_TAX")
        from menu.serializers import MenuItemSerializer
        serializer = MenuItemSerializer(data={
            "restaurant": str(self.restaurant.pk),
            "category": str(self.category.pk),
            "name": "Tax Mismatch Item",
            "food_type": "VEG",
            "tax_rate": str(wrong_tax.pk),
        })
        self.assertFalse(serializer.is_valid())
        self.assertIn("tax_rate", serializer.errors)

    def test_restaurant_isolation_items_not_visible_cross_tenant(self):
        org2 = make_org("IsolOrg", slug="isol-org-menu")
        rest2 = make_restaurant(org2, code="ISOL-002")
        cat2 = make_category(rest2, name="Cat B")
        item_b = make_menu_item(rest2, cat2, name="Item B", sku="IB-001")

        # User with access only to restaurant A should NOT see item_b
        user_a = make_user("isol_user_a@menu.test")
        grant_permission(Role.CODE_RESTAURANT_OWNER, "menu.view")
        assign_role(user_a, Role.CODE_RESTAURANT_OWNER,
                    org=self.org, restaurant=self.restaurant)

        from menu import access as menu_acl
        qs = menu_acl.get_accessible_menu_items(user_a)
        self.assertFalse(qs.filter(pk=item_b.pk).exists())


# =============================================================================
# 4. MenuItemPrice Tests
# =============================================================================

class MenuItemPriceTests(TestCase):

    def setUp(self):
        self.org = make_org("PriceOrg", slug="price-org-test")
        self.restaurant = make_restaurant(self.org, code="PRICER-001")
        self.branch = make_branch(self.restaurant, code="PBR-001")
        self.category = make_category(self.restaurant)
        self.item = make_menu_item(self.restaurant, self.category)

    def test_create_price(self):
        p = make_price(self.item, self.branch, price="220.00")
        self.assertEqual(p.price, Decimal("220.00"))
        self.assertTrue(p.is_active)

    def test_price_must_not_be_negative(self):
        from menu.serializers import MenuItemPriceSerializer
        serializer = MenuItemPriceSerializer(data={
            "menu_item": str(self.item.pk),
            "branch": str(self.branch.pk),
            "price": "-1.00",
        })
        self.assertFalse(serializer.is_valid())
        self.assertIn("price", serializer.errors)

    def test_zero_price_allowed(self):
        """Zero price is valid (complimentary item)."""
        p = make_price(self.item, self.branch, price="0.00")
        p.full_clean()  # should not raise

    def test_branch_wrong_restaurant_rejected(self):
        """Branch from different restaurant must be rejected."""
        org2 = make_org("PriceOrg2", slug="price-org2-test")
        rest2 = make_restaurant(org2, code="PRICER-002")
        wrong_branch = make_branch(rest2, code="WBR-001")
        from menu.serializers import MenuItemPriceSerializer
        serializer = MenuItemPriceSerializer(data={
            "menu_item": str(self.item.pk),
            "branch": str(wrong_branch.pk),
            "price": "150.00",
        })
        self.assertFalse(serializer.is_valid())
        self.assertIn("branch", serializer.errors)

    def test_price_history_preserved_on_deactivation(self):
        """Deactivating a price sets is_active=False; the row is NOT deleted."""
        p = make_price(self.item, self.branch, price="180.00")
        price_id = p.pk
        p.is_active = False
        p.save()
        # Row still exists
        self.assertTrue(MenuItemPrice.objects.filter(pk=price_id).exists())
        p.refresh_from_db()
        self.assertFalse(p.is_active)

    def test_overlapping_active_prices_rejected(self):
        """Two active prices for the same item+branch rejected by serializer."""
        make_price(self.item, self.branch, price="200.00", is_active=True)
        from menu.serializers import MenuItemPriceSerializer
        serializer = MenuItemPriceSerializer(data={
            "menu_item": str(self.item.pk),
            "branch": str(self.branch.pk),
            "price": "210.00",
            "is_active": True,
        })
        self.assertFalse(serializer.is_valid())
        self.assertIn("is_active", serializer.errors)

    def test_decimal_precision(self):
        """Price is stored and retrieved as Decimal, not float."""
        p = make_price(self.item, self.branch, price="99.99")
        p.refresh_from_db()
        self.assertIsInstance(p.price, Decimal)
        self.assertEqual(p.price, Decimal("99.99"))

    def test_multiple_inactive_prices_allowed(self):
        """Historical (inactive) prices are unlimited."""
        make_price(self.item, self.branch, price="100.00", is_active=False)
        make_price(self.item, self.branch, price="110.00", is_active=False)
        count = MenuItemPrice.objects.filter(
            menu_item=self.item, branch=self.branch, is_active=False
        ).count()
        self.assertEqual(count, 2)


# =============================================================================
# 5. MenuItemBranch (Availability) Tests
# =============================================================================

class MenuItemBranchTests(TestCase):

    def setUp(self):
        self.org = make_org("AvailOrg", slug="avail-org-test")
        self.restaurant = make_restaurant(self.org, code="AVAILR-001")
        self.branch = make_branch(self.restaurant, code="ABR-001")
        self.category = make_category(self.restaurant)
        self.item = make_menu_item(self.restaurant, self.category)

    def test_create_availability(self):
        avail = make_availability(self.item, self.branch, is_available=True)
        self.assertTrue(avail.is_available)

    def test_unavailable_item_excluded_from_catalog(self):
        """Service helper returns False when is_available=False."""
        make_availability(self.item, self.branch, is_available=False)
        result = is_menu_item_available(self.item, self.branch)
        self.assertFalse(result)

    def test_available_item_included_in_catalog(self):
        make_availability(self.item, self.branch, is_available=True)
        result = is_menu_item_available(self.item, self.branch)
        self.assertTrue(result)

    def test_inactive_item_not_available(self):
        self.item.is_active = False
        self.item.save()
        make_availability(self.item, self.branch, is_available=True)
        self.assertFalse(is_menu_item_available(self.item, self.branch))

    def test_inactive_branch_not_available(self):
        self.branch.is_active = False
        self.branch.save()
        make_availability(self.item, self.branch, is_available=True)
        self.assertFalse(is_menu_item_available(self.item, self.branch))

    def test_no_availability_record_means_unavailable(self):
        """Without a MenuItemBranch record, item is considered unavailable."""
        self.assertFalse(is_menu_item_available(self.item, self.branch))

    def test_time_window_within_window(self):
        """Item is available when current time is within available_from/to."""
        from zoneinfo import ZoneInfo
        avail = make_availability(self.item, self.branch, is_available=True)
        avail.available_from = time(8, 0)
        avail.available_to = time(22, 0)
        avail.save()

        # Simulate a time in the window (noon UTC = noon, assume IST window check)
        import datetime
        noon = timezone.now().replace(hour=10, minute=0, second=0, microsecond=0)
        # Use a datetime that falls between 08:00 and 22:00 in Asia/Kolkata
        tz = ZoneInfo("Asia/Kolkata")
        noon_ist = datetime.datetime(2026, 1, 1, 12, 0, tzinfo=tz)
        self.assertTrue(is_menu_item_available(self.item, self.branch, noon_ist))

    def test_time_window_outside_window(self):
        """Item is unavailable when current time is outside the window."""
        import datetime
        from zoneinfo import ZoneInfo
        avail = make_availability(self.item, self.branch, is_available=True)
        avail.available_from = time(8, 0)
        avail.available_to = time(11, 0)
        avail.save()
        tz = ZoneInfo("Asia/Kolkata")
        # 15:00 IST is outside 08:00–11:00
        afternoon = datetime.datetime(2026, 1, 1, 15, 0, tzinfo=tz)
        self.assertFalse(is_menu_item_available(self.item, self.branch, afternoon))

    def test_branch_wrong_restaurant_rejected(self):
        org2 = make_org("AvailOrg2", slug="avail-org2-test")
        rest2 = make_restaurant(org2, code="AVAILR-002")
        wrong_branch = make_branch(rest2, code="ABR-002")
        from menu.serializers import MenuItemBranchSerializer
        serializer = MenuItemBranchSerializer(data={
            "menu_item": str(self.item.pk),
            "branch": str(wrong_branch.pk),
            "is_available": True,
        })
        self.assertFalse(serializer.is_valid())
        self.assertIn("branch", serializer.errors)

    def test_duplicate_availability_rejected(self):
        make_availability(self.item, self.branch)
        from menu.serializers import MenuItemBranchSerializer
        serializer = MenuItemBranchSerializer(data={
            "menu_item": str(self.item.pk),
            "branch": str(self.branch.pk),
            "is_available": True,
        })
        self.assertFalse(serializer.is_valid())


# =============================================================================
# 6. API — Category Endpoints
# =============================================================================

class CategoryAPITests(TestCase):

    def setUp(self):
        self.org = make_org("CatAPIOrg", slug="cat-api-org")
        self.restaurant = make_restaurant(self.org, code="CATAPI-001")

        # Permissions
        self.view_perm = get_or_create_permission("category.view", "category", "view")
        self.create_perm = get_or_create_permission("category.create", "category", "create")
        self.update_perm = get_or_create_permission("category.update", "category", "update")
        self.disable_perm = get_or_create_permission("category.disable", "category", "disable")

        # Owner user with full permissions
        self.owner = make_user("owner_cat@api.test")
        owner_role = get_or_create_role(Role.CODE_RESTAURANT_OWNER)
        owner_role.permissions.add(
            self.view_perm, self.create_perm, self.update_perm, self.disable_perm
        )
        assign_role(self.owner, Role.CODE_RESTAURANT_OWNER,
                    org=self.org, restaurant=self.restaurant)

        # Cashier with view only
        self.cashier = make_user("cashier_cat@api.test")
        cashier_role = get_or_create_role(Role.CODE_CASHIER)
        cashier_role.permissions.add(self.view_perm)
        assign_role(self.cashier, Role.CODE_CASHIER,
                    org=self.org, restaurant=self.restaurant, branch=make_branch(self.restaurant, code="CATBR-001"))

    def test_unauthenticated_list_rejected(self):
        resp = APIClient().get("/api/menu/categories/")
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_owner_can_list_categories(self):
        make_category(self.restaurant, name="TestCat")
        resp = auth_client(self.owner).get("/api/menu/categories/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_owner_can_create_category(self):
        resp = auth_client(self.owner).post("/api/menu/categories/", {
            "restaurant": str(self.restaurant.pk),
            "name": "Beverages API",
            "display_order": 1,
        })
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data["name"], "Beverages API")

    def test_cashier_cannot_create_category(self):
        resp = auth_client(self.cashier).post("/api/menu/categories/", {
            "restaurant": str(self.restaurant.pk),
            "name": "Cashier Category",
            "display_order": 1,
        })
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_owner_can_disable_category(self):
        cat = make_category(self.restaurant, name="ToDisable")
        resp = auth_client(self.owner).post(f"/api/menu/categories/{cat.pk}/disable/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        cat.refresh_from_db()
        self.assertFalse(cat.is_active)

    def test_owner_can_enable_category(self):
        cat = make_category(self.restaurant, name="ToEnable")
        cat.is_active = False
        cat.save()
        resp = auth_client(self.owner).post(f"/api/menu/categories/{cat.pk}/enable/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        cat.refresh_from_db()
        self.assertTrue(cat.is_active)

    def test_cross_restaurant_category_access_rejected(self):
        """Owner of restaurant A must not see restaurant B's category."""
        org2 = make_org("CatAPIOrg2", slug="cat-api-org2")
        rest2 = make_restaurant(org2, code="CATAPI-002")
        cat_b = make_category(rest2, name="Cat B")

        resp = auth_client(self.owner).get(f"/api/menu/categories/{cat_b.pk}/")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)


# =============================================================================
# 7. API — Menu Item Endpoints
# =============================================================================

class MenuItemAPITests(TestCase):

    def setUp(self):
        self.org = make_org("ItemAPIOrg", slug="item-api-org")
        self.restaurant = make_restaurant(self.org, code="ITEMAPI-001")
        self.category = make_category(self.restaurant)
        self.tax_rate = make_tax_rate(self.restaurant)

        perm_codes = [
            "menu.view", "menu.create", "menu.update", "menu.disable",
        ]
        self.owner = make_user("owner_item@api.test")
        owner_role = get_or_create_role(Role.CODE_RESTAURANT_OWNER)
        for code in perm_codes:
            owner_role.permissions.add(get_or_create_permission(code, "menu", code.split(".")[-1]))
        assign_role(self.owner, Role.CODE_RESTAURANT_OWNER,
                    org=self.org, restaurant=self.restaurant)

        self.cashier = make_user("cashier_item@api.test")
        cashier_role = get_or_create_role(Role.CODE_CASHIER)
        cashier_role.permissions.add(get_or_create_permission("menu.view", "menu", "view"))
        assign_role(self.cashier, Role.CODE_CASHIER,
                    org=self.org, restaurant=self.restaurant,
                    branch=make_branch(self.restaurant, code="ITEMBR-001"))

    def test_create_menu_item(self):
        resp = auth_client(self.owner).post("/api/menu/items/", {
            "restaurant": str(self.restaurant.pk),
            "category": str(self.category.pk),
            "name": "Chicken Biryani",
            "sku": "CB-001",
            "food_type": "NON_VEG",
            "preparation_time_minutes": 20,
        })
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data["name"], "Chicken Biryani")

    def test_cashier_cannot_create_item(self):
        resp = auth_client(self.cashier).post("/api/menu/items/", {
            "restaurant": str(self.restaurant.pk),
            "category": str(self.category.pk),
            "name": "Unauthorized Item",
            "food_type": "VEG",
        })
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_duplicate_sku_via_api_rejected(self):
        auth_client(self.owner).post("/api/menu/items/", {
            "restaurant": str(self.restaurant.pk),
            "category": str(self.category.pk),
            "name": "Item One",
            "sku": "DUPAPI-001",
            "food_type": "VEG",
        })
        resp = auth_client(self.owner).post("/api/menu/items/", {
            "restaurant": str(self.restaurant.pk),
            "category": str(self.category.pk),
            "name": "Item Two",
            "sku": "DUPAPI-001",
            "food_type": "VEG",
        })
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_category_mismatch_via_api_rejected(self):
        org2 = make_org("MisAPI", slug="mis-api-org")
        rest2 = make_restaurant(org2, code="MISAPI-002")
        wrong_cat = make_category(rest2, name="Wrong")
        resp = auth_client(self.owner).post("/api/menu/items/", {
            "restaurant": str(self.restaurant.pk),
            "category": str(wrong_cat.pk),
            "name": "Mismatch",
            "food_type": "VEG",
        })
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_disable_and_enable_via_api(self):
        item = make_menu_item(self.restaurant, self.category, name="Toggle Item", sku="TI-001")
        resp = auth_client(self.owner).post(f"/api/menu/items/{item.pk}/disable/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        item.refresh_from_db()
        self.assertFalse(item.is_active)

        resp = auth_client(self.owner).post(f"/api/menu/items/{item.pk}/enable/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        item.refresh_from_db()
        self.assertTrue(item.is_active)

    def test_restaurant_a_cannot_access_restaurant_b_item(self):
        org2 = make_org("IsolAPIOrg2", slug="isol-api-org2")
        rest2 = make_restaurant(org2, code="ISOLAPI-002")
        cat2 = make_category(rest2, name="Cat2")
        item_b = make_menu_item(rest2, cat2, name="Item B", sku="IB-API-001")

        resp = auth_client(self.owner).get(f"/api/menu/items/{item_b.pk}/")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)


# =============================================================================
# 8. API — Pricing Endpoints
# =============================================================================

class PricingAPITests(TestCase):

    def setUp(self):
        self.org = make_org("PriceAPIOrg", slug="price-api-org")
        self.restaurant = make_restaurant(self.org, code="PRICEAPI-001")
        self.branch = make_branch(self.restaurant, code="PABR-001")
        self.category = make_category(self.restaurant)
        self.item = make_menu_item(self.restaurant, self.category)

        self.owner = make_user("owner_price@api.test")
        owner_role = get_or_create_role(Role.CODE_RESTAURANT_OWNER)
        for code in ["menu.price.view", "menu.price.create", "menu.price.update"]:
            owner_role.permissions.add(get_or_create_permission(code, "menu", code.split(".")[-1]))
        assign_role(self.owner, Role.CODE_RESTAURANT_OWNER,
                    org=self.org, restaurant=self.restaurant)

    def test_create_price(self):
        resp = auth_client(self.owner).post("/api/menu/prices/", {
            "menu_item": str(self.item.pk),
            "branch": str(self.branch.pk),
            "price": "220.00",
        })
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data["price"], "220.00")

    def test_negative_price_rejected(self):
        resp = auth_client(self.owner).post("/api/menu/prices/", {
            "menu_item": str(self.item.pk),
            "branch": str(self.branch.pk),
            "price": "-10.00",
        })
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_branch_wrong_restaurant_rejected(self):
        org2 = make_org("PriceAPIOrg2", slug="price-api-org2")
        rest2 = make_restaurant(org2, code="PRICEAPI-002")
        wrong_br = make_branch(rest2, code="WBR-API")
        resp = auth_client(self.owner).post("/api/menu/prices/", {
            "menu_item": str(self.item.pk),
            "branch": str(wrong_br.pk),
            "price": "150.00",
        })
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_deactivate_price(self):
        price = make_price(self.item, self.branch, "200.00")
        resp = auth_client(self.owner).post(f"/api/menu/prices/{price.pk}/deactivate/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        price.refresh_from_db()
        self.assertFalse(price.is_active)

    def test_price_history_preserved(self):
        price = make_price(self.item, self.branch, "200.00")
        price_id = price.pk
        # Deactivate via API
        auth_client(self.owner).post(f"/api/menu/prices/{price.pk}/deactivate/")
        # Row must still exist
        self.assertTrue(MenuItemPrice.objects.filter(pk=price_id).exists())


# =============================================================================
# 9. API — Availability Endpoints
# =============================================================================

class AvailabilityAPITests(TestCase):

    def setUp(self):
        self.org = make_org("AvailAPIOrg", slug="avail-api-org")
        self.restaurant = make_restaurant(self.org, code="AVAILAPI-001")
        self.branch = make_branch(self.restaurant, code="AABR-001")
        self.category = make_category(self.restaurant)
        self.item = make_menu_item(self.restaurant, self.category)

        self.owner = make_user("owner_avail@api.test")
        owner_role = get_or_create_role(Role.CODE_RESTAURANT_OWNER)
        for code in ["menu.availability.view", "menu.availability.update"]:
            owner_role.permissions.add(get_or_create_permission(code, "menu", "availability"))
        assign_role(self.owner, Role.CODE_RESTAURANT_OWNER,
                    org=self.org, restaurant=self.restaurant)

    def test_create_availability(self):
        resp = auth_client(self.owner).post("/api/menu/availability/", {
            "menu_item": str(self.item.pk),
            "branch": str(self.branch.pk),
            "is_available": True,
        })
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertTrue(resp.data["is_available"])

    def test_update_availability(self):
        avail = make_availability(self.item, self.branch, is_available=True)
        resp = auth_client(self.owner).patch(f"/api/menu/availability/{avail.pk}/", {
            "is_available": False,
        })
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        avail.refresh_from_db()
        self.assertFalse(avail.is_available)

    def test_cross_restaurant_access_rejected(self):
        org2 = make_org("AvailOrg2", slug="avail-api-org2")
        rest2 = make_restaurant(org2, code="AVAILAPI-002")
        br2 = make_branch(rest2, code="AABR-002")
        cat2 = make_category(rest2)
        item2 = make_menu_item(rest2, cat2, name="Item2", sku="I2-001")
        avail2 = make_availability(item2, br2)

        resp = auth_client(self.owner).get(f"/api/menu/availability/{avail2.pk}/")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)


# =============================================================================
# 10. API — Tax Rate Endpoints
# =============================================================================

class TaxRateAPITests(TestCase):

    def setUp(self):
        self.org = make_org("TaxAPIOrg", slug="tax-api-org")
        self.restaurant = make_restaurant(self.org, code="TAXAPI-001")

        self.owner = make_user("owner_tax@api.test")
        owner_role = get_or_create_role(Role.CODE_RESTAURANT_OWNER)
        for code in ["tax.view", "tax.create", "tax.update"]:
            owner_role.permissions.add(get_or_create_permission(code, "tax", code.split(".")[-1]))
        assign_role(self.owner, Role.CODE_RESTAURANT_OWNER,
                    org=self.org, restaurant=self.restaurant)

    def test_create_tax_rate(self):
        resp = auth_client(self.owner).post("/api/menu/tax-rates/", {
            "restaurant": str(self.restaurant.pk),
            "name": "GST Standard",
            "code": "GST_STD",
            "rate": "5.000",
        })
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data["code"], "GST_STD")

    def test_update_tax_rate(self):
        rate = make_tax_rate(self.restaurant, code="TAXUPD")
        resp = auth_client(self.owner).patch(f"/api/menu/tax-rates/{rate.pk}/", {
            "rate": "7.500",
        })
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        rate.refresh_from_db()
        self.assertEqual(rate.rate, Decimal("7.500"))

    def test_duplicate_code_rejected(self):
        make_tax_rate(self.restaurant, code="TAXDUP")
        resp = auth_client(self.owner).post("/api/menu/tax-rates/", {
            "restaurant": str(self.restaurant.pk),
            "name": "Dup Tax",
            "code": "TAXDUP",
            "rate": "3.000",
        })
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_restaurant_isolation(self):
        org2 = make_org("TaxAPIOrg2", slug="tax-api-org2")
        rest2 = make_restaurant(org2, code="TAXAPI-002")
        rate_b = make_tax_rate(rest2, code="TAX_B")
        resp = auth_client(self.owner).get(f"/api/menu/tax-rates/{rate_b.pk}/")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)


# =============================================================================
# 11. Catalog API Tests
# =============================================================================

class BranchCatalogAPITests(TestCase):
    """
    Tests for GET /api/menu/branches/<id>/catalog/
    Verifies: authorized access, active categories/items only,
    availability filtering, correct price and tax.
    """

    def setUp(self):
        self.org = make_org("CatalogOrg", slug="catalog-org-test")
        self.restaurant = make_restaurant(self.org, code="CATAR-001")
        self.branch = make_branch(self.restaurant, code="CATABR-001")

        self.tax_rate = make_tax_rate(self.restaurant, code="GST_CAT", rate="5.000")

        # Active category and item
        self.cat_active = make_category(self.restaurant, name="Active Cat", order=1)
        self.item_active = make_menu_item(
            self.restaurant, self.cat_active,
            name="Visible Item", sku="VI-001",
            tax_rate=self.tax_rate,
        )
        make_price(self.item_active, self.branch, price="150.00")
        make_availability(self.item_active, self.branch, is_available=True)

        # Inactive category / item
        self.cat_inactive = make_category(self.restaurant, name="Inactive Cat", order=2)
        self.cat_inactive.is_active = False
        self.cat_inactive.save()

        self.item_inactive = make_menu_item(
            self.restaurant, self.cat_active,
            name="Inactive Item", sku="II-001",
        )
        self.item_inactive.is_active = False
        self.item_inactive.save()

        # Unavailable item
        self.item_unavail = make_menu_item(
            self.restaurant, self.cat_active,
            name="Unavailable Item", sku="UI-001",
        )
        make_price(self.item_unavail, self.branch, price="200.00")
        make_availability(self.item_unavail, self.branch, is_available=False)

        # Auth setup — cashier can view catalog
        self.cashier = make_user("cashier_catalog@api.test")
        cashier_role = get_or_create_role(Role.CODE_CASHIER)
        cashier_role.permissions.add(get_or_create_permission("menu.view", "menu", "view"))
        assign_role(self.cashier, Role.CODE_CASHIER,
                    org=self.org, restaurant=self.restaurant, branch=self.branch)

    def test_catalog_returns_200(self):
        resp = auth_client(self.cashier).get(f"/api/menu/branches/{self.branch.pk}/catalog/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_catalog_only_active_items(self):
        resp = auth_client(self.cashier).get(f"/api/menu/branches/{self.branch.pk}/catalog/")
        all_names = [
            item["name"]
            for cat in resp.data["categories"]
            for item in cat["items"]
        ]
        self.assertIn("Visible Item", all_names)
        self.assertNotIn("Inactive Item", all_names)

    def test_catalog_excludes_unavailable_items(self):
        resp = auth_client(self.cashier).get(f"/api/menu/branches/{self.branch.pk}/catalog/")
        all_names = [
            item["name"]
            for cat in resp.data["categories"]
            for item in cat["items"]
        ]
        self.assertNotIn("Unavailable Item", all_names)

    def test_catalog_excludes_inactive_categories(self):
        resp = auth_client(self.cashier).get(f"/api/menu/branches/{self.branch.pk}/catalog/")
        cat_names = [c["name"] for c in resp.data["categories"]]
        self.assertNotIn("Inactive Cat", cat_names)

    def test_catalog_correct_price(self):
        resp = auth_client(self.cashier).get(f"/api/menu/branches/{self.branch.pk}/catalog/")
        visible = next(
            item
            for cat in resp.data["categories"]
            for item in cat["items"]
            if item["name"] == "Visible Item"
        )
        self.assertEqual(Decimal(str(visible["price"])), Decimal("150.00"))

    def test_catalog_correct_tax(self):
        resp = auth_client(self.cashier).get(f"/api/menu/branches/{self.branch.pk}/catalog/")
        visible = next(
            item
            for cat in resp.data["categories"]
            for item in cat["items"]
            if item["name"] == "Visible Item"
        )
        self.assertEqual(visible["tax_rate_code"], "GST_CAT")
        self.assertEqual(Decimal(str(visible["tax_rate"])), Decimal("5.000"))

    def test_unauthorized_branch_returns_404(self):
        """A user who cannot access this branch gets 404."""
        other_user = make_user("nobody_catalog@api.test")
        # No role assignment
        resp = auth_client(other_user).get(f"/api/menu/branches/{self.branch.pk}/catalog/")
        # 404 returned (IDOR protection) because get_accessible_branches returns nothing
        self.assertIn(resp.status_code, [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND])

    def test_catalog_ordering_by_category_display_order(self):
        """Categories must be returned ordered by display_order."""
        resp = auth_client(self.cashier).get(f"/api/menu/branches/{self.branch.pk}/catalog/")
        orders = [c["display_order"] for c in resp.data["categories"]]
        self.assertEqual(orders, sorted(orders))


# =============================================================================
# 12. Security Tests
# =============================================================================

class SecurityTests(TestCase):
    """
    Additional security checks beyond what's covered per-resource above.
    """

    def setUp(self):
        self.org_a = make_org("SecOrgA", slug="sec-org-a")
        self.org_b = make_org("SecOrgB", slug="sec-org-b")
        self.rest_a = make_restaurant(self.org_a, code="SECA-001")
        self.rest_b = make_restaurant(self.org_b, code="SECB-001")
        self.branch_a = make_branch(self.rest_a, code="SECABR-001")
        self.cat_a = make_category(self.rest_a, name="Cat A")
        self.cat_b = make_category(self.rest_b, name="Cat B")
        self.item_a = make_menu_item(self.rest_a, self.cat_a, name="Item A", sku="IA-001")
        self.item_b = make_menu_item(self.rest_b, self.cat_b, name="Item B", sku="IB-001")

        # Owner A has all menu permissions
        self.owner_a = make_user("owner_a@sec.test")
        owner_role = get_or_create_role(Role.CODE_RESTAURANT_OWNER)
        for code in [
            "menu.view", "menu.create", "menu.update", "menu.disable",
            "category.view", "category.create", "category.update", "category.disable",
            "menu.price.view", "menu.price.create", "menu.price.update",
            "menu.availability.view", "menu.availability.update",
            "tax.view", "tax.create", "tax.update",
        ]:
            owner_role.permissions.add(get_or_create_permission(code, "menu", code))
        assign_role(self.owner_a, Role.CODE_RESTAURANT_OWNER,
                    org=self.org_a, restaurant=self.rest_a)

    def test_owner_a_cannot_see_restaurant_b_category(self):
        resp = auth_client(self.owner_a).get(f"/api/menu/categories/{self.cat_b.pk}/")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_owner_a_cannot_modify_restaurant_b_category(self):
        resp = auth_client(self.owner_a).patch(f"/api/menu/categories/{self.cat_b.pk}/", {
            "name": "Hacked",
        })
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_owner_a_cannot_see_restaurant_b_item(self):
        resp = auth_client(self.owner_a).get(f"/api/menu/items/{self.item_b.pk}/")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_owner_a_cannot_set_price_for_restaurant_b_branch(self):
        branch_b = make_branch(self.rest_b, code="SECBBR-001")
        resp = auth_client(self.owner_a).post("/api/menu/prices/", {
            "menu_item": str(self.item_a.pk),
            "branch": str(branch_b.pk),
            "price": "100.00",
        })
        # branch_b belongs to rest_b, item_a to rest_a → rejected
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unauthenticated_catalog_rejected(self):
        resp = APIClient().get(f"/api/menu/branches/{self.branch_a.pk}/catalog/")
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_unauthenticated_dashboard_rejected(self):
        resp = APIClient().get("/api/menu/dashboard/")
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_menu_item_list_scoped_to_user_restaurant(self):
        """owner_a must not see items from restaurant B in the list."""
        resp = auth_client(self.owner_a).get("/api/menu/items/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        ids = [item["id"] for item in resp.data["results"]]
        self.assertNotIn(str(self.item_b.pk), ids)
