# =============================================================================
# RestaurantFlow — E2E Test Helpers
# Phase 26 — Shared fixture factories for E2E test suite
# =============================================================================

from django.contrib.auth import get_user_model
from django.utils.text import slugify

from accounts.models import Role, Permission, UserRoleAssignment, UserProfile
from organizations.models import Organization, Restaurant, Branch, RestaurantSettings, BranchSettings
from counters.models import Counter, CounterSession
from menu.models import TaxRate, Category, MenuItem, MenuItemPrice, MenuItemBranch
from rest_framework.test import APIClient

User = get_user_model()


# ---------------------------------------------------------------------------
# User & auth helpers
# ---------------------------------------------------------------------------

_user_counter = 0


def make_user(email=None, password="TestPass@1", first_name="Test", last_name="User", **kwargs):
    global _user_counter
    if email is None:
        _user_counter += 1
        email = f"user{_user_counter}@testflow.dev"
    user = User.objects.create_user(
        email=email, password=password,
        first_name=first_name, last_name=last_name,
        **kwargs
    )
    UserProfile.objects.get_or_create(user=user)
    return user


def auth_client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


# ---------------------------------------------------------------------------
# Role helpers
# ---------------------------------------------------------------------------

def _role_scope(code):
    ORG_ROLES = {Role.CODE_COMPANY_HEAD, Role.CODE_CENTRAL_ADMIN}
    REST_ROLES = {Role.CODE_RESTAURANT_OWNER}
    if code in ORG_ROLES:
        return Role.SCOPE_ORGANIZATION
    if code in REST_ROLES:
        return Role.SCOPE_RESTAURANT
    return Role.SCOPE_BRANCH


def get_or_create_role(code):
    role, _ = Role.objects.get_or_create(
        code=code,
        defaults={
            "name": code,
            "scope": _role_scope(code),
            "is_system_role": True,
            "is_active": True,
        },
    )
    return role


def assign_role(user, role_code, org=None, restaurant=None, branch=None):
    role = get_or_create_role(role_code)
    assignment = UserRoleAssignment(
        user=user, role=role,
        organization=org, restaurant=restaurant, branch=branch,
        is_active=True,
    )
    assignment.full_clean()
    assignment.save()
    return assignment


# ---------------------------------------------------------------------------
# Organization hierarchy factories
# ---------------------------------------------------------------------------

_org_counter = 0
_rest_counter = 0
_branch_counter = 0


def make_org(name=None, **kwargs):
    global _org_counter
    _org_counter += 1
    name = name or f"Test Org {_org_counter}"
    slug = slugify(name) + f"-{_org_counter}"
    return Organization.objects.create(name=name, slug=slug, currency="INR", timezone="Asia/Kolkata", **kwargs)


def make_restaurant(org, name=None, code=None, **kwargs):
    global _rest_counter
    _rest_counter += 1
    name = name or f"Restaurant {_rest_counter}"
    code = code or f"REST-{_rest_counter:03d}"
    rest = Restaurant.objects.create(organization=org, name=name, code=code, **kwargs)
    RestaurantSettings.objects.get_or_create(restaurant=rest)
    return rest


def make_branch(restaurant, name=None, code=None, **kwargs):
    global _branch_counter
    _branch_counter += 1
    name = name or f"Branch {_branch_counter}"
    code = code or f"BR-{_branch_counter:03d}"
    branch = Branch.objects.create(restaurant=restaurant, name=name, code=code, **kwargs)
    BranchSettings.objects.get_or_create(branch=branch)
    return branch


def make_counter(branch, name="Counter 1", code=None, **kwargs):
    global _branch_counter
    code = code or f"C{_branch_counter:02d}"
    return Counter.objects.create(branch=branch, name=name, code=code, **kwargs)


def make_counter_session(counter, opened_by, opening_cash="100.00"):
    return CounterSession.objects.create(
        counter=counter,
        opened_by=opened_by,
        opening_cash=opening_cash,
    )


# ---------------------------------------------------------------------------
# Menu helpers
# ---------------------------------------------------------------------------

_menu_counter = 0


def make_tax_rate(restaurant, code=None, rate="5.000"):
    global _menu_counter
    _menu_counter += 1
    code = code or f"GST_{_menu_counter}"
    return TaxRate.objects.create(
        restaurant=restaurant,
        name=code,
        code=code,
        rate=rate,
        is_active=True,
    )


def make_category(restaurant, name=None):
    global _menu_counter
    _menu_counter += 1
    name = name or f"Category {_menu_counter}"
    return Category.objects.create(
        restaurant=restaurant,
        name=name,
        is_active=True,
    )


def make_menu_item(restaurant, category, tax_rate, name=None, price="100.00", branch=None):
    global _menu_counter
    _menu_counter += 1
    name = name or f"Menu Item {_menu_counter}"
    item = MenuItem.objects.create(
        restaurant=restaurant,
        category=category,
        name=name,
        tax_rate=tax_rate,
        is_available=True,
        is_active=True,
        food_type="VEG",
    )
    if branch is not None:
        MenuItemPrice.objects.create(
            menu_item=item,
            branch=branch,
            price=price,
            is_active=True,
        )
    return item


def make_menu_item_branch(menu_item, branch, price=None):
    """Make a MenuItem available at a specific branch with an optional branch price."""
    mib, _ = MenuItemBranch.objects.get_or_create(
        menu_item=menu_item,
        branch=branch,
        defaults={"is_available": True},
    )
    return mib
