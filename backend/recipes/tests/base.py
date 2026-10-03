# =============================================================================
# RestaurantFlow — Recipes Test Base
# Phase 11
#
# Shared fixture stack for all recipe and consumption integration tests.
# All test classes that need DB access inherit from RecipeTestBase.
#
# Fixture hierarchy:
#   Organization → Restaurant (with settings) → Branch (with settings)
#   Users: manager, staff, other_user
#   Permissions: all recipe + consumption permissions
#   Roles: RECIPE_MANAGER, RECIPE_STAFF
#   Menu: category, item_biryani, item_paneer, item_naan
#   Inventory: InventoryCategory, InventoryItems (rice, chicken, oil, paneer, flour)
#   StorageLocation: kitchen_store (branch), other_store (branch), external_store (other_branch)
#   BranchConsumptionConfig: kitchen_store as default location
#   Counter + CounterSession (for orders)
# =============================================================================

from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from accounts.models import User, Role, Permission, UserRoleAssignment
from organizations.models import (
    Organization, Restaurant, Branch,
    RestaurantSettings, BranchSettings,
)
from menu.models import Category, MenuItem, MenuItemPrice, MenuItemBranch, TaxRate
from orders.models import Order, OrderItem, OrderStatus, OrderType
from counters.models import Counter, CounterSession, SessionStatus, CounterStatus
from inventory.models import (
    InventoryCategory, InventoryItem, StorageLocation, StockBalance,
)
from inventory.constants import (
    UNIT_KG, UNIT_GRAM, UNIT_LITRE, UNIT_MILLILITRE, UNIT_PIECE,
    LOCATION_KITCHEN, LOCATION_MAIN_STORE,
    MOVEMENT_CONSUMPTION,
)


class RecipeTestBase(TestCase):
    """
    Base test class providing full fixture stack for recipe/consumption tests.
    setUpTestData runs ONCE per test class.
    """

    @classmethod
    def setUpTestData(cls):
        # -----------------------------------------------------------------
        # Organization / Restaurant / Branch
        # -----------------------------------------------------------------
        cls.org = Organization.objects.create(
            name="Recipe Test Org",
            slug="recipe-test-org",
            currency="INR",
        )
        cls.restaurant = Restaurant.objects.create(
            organization=cls.org,
            name="Recipe Test Restaurant",
            slug="recipe-test-restaurant",
            code="RTR01",
        )
        RestaurantSettings.objects.create(
            restaurant=cls.restaurant,
            currency="INR",
            tax_enabled=True,
        )
        cls.branch = Branch.objects.create(
            restaurant=cls.restaurant,
            name="Main Kitchen Branch",
            code="MKB01",
        )
        BranchSettings.objects.create(branch=cls.branch)

        cls.other_branch = Branch.objects.create(
            restaurant=cls.restaurant,
            name="Other Branch",
            code="OB01",
        )
        BranchSettings.objects.create(branch=cls.other_branch)

        # Second restaurant for isolation tests
        cls.other_restaurant = Restaurant.objects.create(
            organization=cls.org,
            name="Other Restaurant",
            slug="other-restaurant",
            code="OTR01",
        )
        RestaurantSettings.objects.create(restaurant=cls.other_restaurant)
        cls.other_rest_branch = Branch.objects.create(
            restaurant=cls.other_restaurant,
            name="Other Rest Branch",
            code="ORB01",
        )
        BranchSettings.objects.create(branch=cls.other_rest_branch)

        # -----------------------------------------------------------------
        # Users
        # -----------------------------------------------------------------
        cls.manager = User.objects.create_user(
            email="recipe_manager@test.com",
            password="pass123",
            first_name="Recipe",
            last_name="Manager",
        )
        cls.staff = User.objects.create_user(
            email="recipe_staff@test.com",
            password="pass123",
            first_name="Recipe",
            last_name="Staff",
        )
        cls.other_user = User.objects.create_user(
            email="recipe_other@test.com",
            password="pass123",
            first_name="Other",
            last_name="User",
        )

        # -----------------------------------------------------------------
        # Permissions
        # -----------------------------------------------------------------
        perm_data = [
            ("recipe.view",                   "Recipes",    "View recipes",                       "recipes",   "view"),
            ("recipe.create",                 "Recipes",    "Create recipes",                     "recipes",   "create"),
            ("recipe.update",                 "Recipes",    "Update recipes",                     "recipes",   "update"),
            ("recipe.activate",               "Recipes",    "Activate recipes",                   "recipes",   "activate"),
            ("recipe.archive",                "Recipes",    "Archive recipes",                    "recipes",   "archive"),
            ("recipe.cost.view",              "Recipes",    "View recipe cost",                   "recipes",   "cost_view"),
            ("inventory.view",                "Inventory",  "View inventory",                     "inventory", "view"),
            ("inventory.create",              "Inventory",  "Create inventory",                   "inventory", "create"),
            ("inventory.update",              "Inventory",  "Update inventory",                   "inventory", "update"),
            ("inventory.consumption.view",    "Inventory",  "View consumption",                   "inventory", "consumption_view"),
            ("inventory.consumption.manual",  "Inventory",  "Manual consumption",                 "inventory", "consumption_manual"),
            ("inventory.consumption.reverse", "Inventory",  "Reverse consumption",                "inventory", "consumption_reverse"),
            ("kitchen.accept",                "Kitchen",    "Accept kitchen orders",              "kitchen",   "accept"),
            ("kitchen.start",                 "Kitchen",    "Start kitchen preparation",          "kitchen",   "start"),
            ("kitchen.order_ready",           "Kitchen",    "Mark orders ready",                  "kitchen",   "order_ready"),
            ("kitchen.item_ready",            "Kitchen",    "Mark items ready",                   "kitchen",   "item_ready"),
            ("kitchen.cancel",                "Kitchen",    "Cancel kitchen orders",              "kitchen",   "cancel"),
            ("kitchen.item_start",            "Kitchen",    "Start item preparation",             "kitchen",   "item_start"),
        ]
        cls.perms = {}
        for code, name, desc, module, action in perm_data:
            p, _ = Permission.objects.get_or_create(
                code=code,
                defaults={
                    "name": name, "description": desc,
                    "module": module, "action": action,
                },
            )
            cls.perms[code] = p

        # -----------------------------------------------------------------
        # Roles
        # -----------------------------------------------------------------
        cls.manager_role = Role.objects.create(
            name="Recipe Manager Test",
            code="RECIPE_MANAGER_TEST",
            scope=Role.SCOPE_BRANCH,
        )
        cls.manager_role.permissions.set(list(cls.perms.values()))

        cls.staff_role = Role.objects.create(
            name="Recipe Staff Test",
            code="RECIPE_STAFF_TEST",
            scope=Role.SCOPE_BRANCH,
        )
        staff_perms = [
            "recipe.view", "recipe.create", "recipe.update",
            "inventory.view", "inventory.consumption.view",
            "kitchen.accept", "kitchen.start", "kitchen.order_ready",
            "kitchen.item_ready", "kitchen.cancel", "kitchen.item_start",
        ]
        cls.staff_role.permissions.set([cls.perms[c] for c in staff_perms])

        # -----------------------------------------------------------------
        # Role assignments
        # -----------------------------------------------------------------
        UserRoleAssignment.objects.create(
            user=cls.manager,
            role=cls.manager_role,
            organization=cls.org,
            restaurant=cls.restaurant,
            branch=cls.branch,
        )
        UserRoleAssignment.objects.create(
            user=cls.staff,
            role=cls.staff_role,
            organization=cls.org,
            restaurant=cls.restaurant,
            branch=cls.branch,
        )
        # other_user has NO assignment for cls.branch

        # -----------------------------------------------------------------
        # Tax rate
        # -----------------------------------------------------------------
        cls.tax_zero = TaxRate.objects.create(
            restaurant=cls.restaurant,
            name="Zero Tax",
            code="ZERO_TAX_RECIPE",
            rate=Decimal("0.000"),
        )

        # -----------------------------------------------------------------
        # Menu
        # -----------------------------------------------------------------
        cls.category = Category.objects.create(
            restaurant=cls.restaurant,
            name="Main Course",
            slug="main-course-recipe-test",
        )
        cls.item_biryani = MenuItem.objects.create(
            restaurant=cls.restaurant,
            category=cls.category,
            name="Chicken Biryani",
            slug="chicken-biryani-r",
            sku="BIRYA-R01",
        )
        cls.item_paneer = MenuItem.objects.create(
            restaurant=cls.restaurant,
            category=cls.category,
            name="Paneer Butter Masala",
            slug="paneer-butter-masala-r",
            sku="PANEER-R01",
        )
        cls.item_naan = MenuItem.objects.create(
            restaurant=cls.restaurant,
            category=cls.category,
            name="Naan",
            slug="naan-r",
            sku="NAAN-R01",
        )
        for item in [cls.item_biryani, cls.item_paneer, cls.item_naan]:
            MenuItemBranch.objects.create(
                menu_item=item, branch=cls.branch, is_available=True
            )
            MenuItemPrice.objects.create(
                menu_item=item, branch=cls.branch,
                price=Decimal("200.00"), is_active=True,
            )

        # -----------------------------------------------------------------
        # Inventory Categories
        # -----------------------------------------------------------------
        cls.inv_category = InventoryCategory.objects.create(
            restaurant=cls.restaurant,
            name="Dry Goods",
        )

        # -----------------------------------------------------------------
        # Inventory Items
        # -----------------------------------------------------------------
        cls.inv_rice = InventoryItem.objects.create(
            restaurant=cls.restaurant,
            category=cls.inv_category,
            name="Basmati Rice",
            sku="RICE-001",
            default_unit=UNIT_KG,
            average_cost=Decimal("60.00"),
        )
        cls.inv_chicken = InventoryItem.objects.create(
            restaurant=cls.restaurant,
            category=cls.inv_category,
            name="Chicken",
            sku="CHICKEN-001",
            default_unit=UNIT_KG,
            average_cost=Decimal("240.00"),
        )
        cls.inv_oil = InventoryItem.objects.create(
            restaurant=cls.restaurant,
            category=cls.inv_category,
            name="Cooking Oil",
            sku="OIL-001",
            default_unit=UNIT_LITRE,
            average_cost=Decimal("150.00"),
        )
        cls.inv_paneer = InventoryItem.objects.create(
            restaurant=cls.restaurant,
            category=cls.inv_category,
            name="Paneer",
            sku="PANEER-001",
            default_unit=UNIT_KG,
            average_cost=Decimal("320.00"),
        )
        cls.inv_flour = InventoryItem.objects.create(
            restaurant=cls.restaurant,
            category=cls.inv_category,
            name="Flour",
            sku="FLOUR-001",
            default_unit=UNIT_KG,
            average_cost=Decimal("40.00"),
        )

        # Inventory item from a different restaurant (for cross-restaurant tests)
        cls.other_inv_item = InventoryItem.objects.create(
            restaurant=cls.other_restaurant,
            name="Other Rice",
            sku="OTHER-RICE-001",
            default_unit=UNIT_KG,
        )

        # -----------------------------------------------------------------
        # Storage Locations
        # -----------------------------------------------------------------
        cls.kitchen_store = StorageLocation.objects.create(
            branch=cls.branch,
            name="Kitchen Store",
            code="KIT-STORE",
            location_type=LOCATION_KITCHEN,
        )
        cls.other_store = StorageLocation.objects.create(
            branch=cls.branch,
            name="Main Store",
            code="MAIN-STORE",
            location_type=LOCATION_MAIN_STORE,
        )
        cls.external_store = StorageLocation.objects.create(
            branch=cls.other_branch,
            name="External Store",
            code="EXT-STORE",
            location_type=LOCATION_MAIN_STORE,
        )

        # -----------------------------------------------------------------
        # Counter + Counter Session (for orders)
        # -----------------------------------------------------------------
        cls.counter = Counter.objects.create(
            branch=cls.branch,
            name="Counter 01",
            code="C01",
            status=CounterStatus.ACTIVE,
        )
        cls.counter_session = CounterSession.objects.create(
            counter=cls.counter,
            opened_by=cls.manager,
            opening_cash=Decimal("1000.00"),
            status=SessionStatus.OPEN,
        )

    # ------------------------------------------------------------------
    # Helper: BranchConsumptionConfig
    # ------------------------------------------------------------------
    def _setup_consumption_config(self, location=None):
        """Create/update BranchConsumptionConfig for cls.branch."""
        from recipes.models import BranchConsumptionConfig
        loc = location or self.kitchen_store
        config, _ = BranchConsumptionConfig.objects.update_or_create(
            branch=self.branch,
            defaults={
                "consumption_trigger": "KITCHEN_COMPLETED",
                "default_consumption_location": loc,
            },
        )
        return config

    # ------------------------------------------------------------------
    # Helper: Stock balance
    # ------------------------------------------------------------------
    def _set_stock(self, inventory_item, storage_location, quantity):
        """Set stock balance directly for test setup."""
        balance, _ = StockBalance.objects.get_or_create(
            inventory_item=inventory_item,
            storage_location=storage_location,
        )
        balance.quantity = Decimal(str(quantity))
        balance.average_cost = inventory_item.average_cost
        balance.save()
        return balance

    # ------------------------------------------------------------------
    # Helper: confirmed order
    # ------------------------------------------------------------------
    def _make_confirmed_order(self, items=None):
        """
        Create a CONFIRMED order.
        items: list of (menu_item, quantity) tuples. Defaults to 1 Biryani.
        """
        ts = timezone.now().strftime("%Y%m%d%H%M%S%f")
        order = Order.objects.create(
            branch=self.branch,
            order_number=f"RTEST-{ts}",
            order_type=OrderType.COUNTER,
            counter=self.counter,
            counter_session=self.counter_session,
            created_by=self.manager,
            status=OrderStatus.CONFIRMED,
            confirmed_at=timezone.now(),
        )
        if items is None:
            items = [(self.item_biryani, Decimal("1.000"))]
        for menu_item, qty in items:
            price = MenuItemPrice.objects.filter(
                menu_item=menu_item, branch=self.branch, is_active=True
            ).first()
            OrderItem.objects.create(
                order=order,
                menu_item=menu_item,
                item_name_snapshot=menu_item.name,
                sku_snapshot=menu_item.sku,
                unit_price_snapshot=price.price if price else Decimal("200.00"),
                tax_rate_snapshot=Decimal("0.000"),
                tax_code_snapshot="ZERO",
                quantity=qty,
            )
        return order

    # ------------------------------------------------------------------
    # Helper: create an ACTIVE recipe for biryani with rice + chicken
    # ------------------------------------------------------------------
    def _make_active_biryani_recipe(
        self,
        rice_qty_grams=Decimal("250"),
        chicken_qty_grams=Decimal("200"),
        oil_qty_ml=Decimal("30"),
    ):
        """
        Create and activate a recipe for Chicken Biryani.
        Default ingredients: 250g rice, 200g chicken, 30ml oil per yield.
        """
        from recipes import services as svc

        recipe = svc.create_recipe(
            restaurant=self.restaurant,
            menu_item=self.item_biryani,
            name="Chicken Biryani Recipe",
            user=self.manager,
            yield_quantity=Decimal("1.000"),
            yield_unit=UNIT_PIECE,
        )
        svc.add_recipe_item(
            recipe, self.inv_rice.id, rice_qty_grams, UNIT_GRAM, self.manager
        )
        svc.add_recipe_item(
            recipe, self.inv_chicken.id, chicken_qty_grams, UNIT_GRAM, self.manager
        )
        svc.add_recipe_item(
            recipe, self.inv_oil.id, oil_qty_ml, UNIT_MILLILITRE, self.manager
        )
        activated = svc.activate_recipe(recipe, self.manager)
        return activated
