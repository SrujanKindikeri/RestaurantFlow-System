# =============================================================================
# RestaurantFlow — Recipe Tests
# Phase 11
#
# Tests:
#   - Recipe creation (valid + invalid)
#   - Recipe versioning (auto-increment, no overwrite)
#   - Recipe update (DRAFT only)
#   - Recipe ingredient add / remove / update
#   - Unit compatibility validation
#   - Preparation loss validation
#   - Cross-restaurant ingredient guard
#   - Recipe activation (valid + pre-conditions)
#   - Duplicate active recipe guard
#   - Recipe archival
#   - Recipe cost calculation
#   - Permission enforcement
#   - Restaurant isolation
# =============================================================================

from decimal import Decimal

from rest_framework.exceptions import PermissionDenied, ValidationError

from inventory.constants import UNIT_KG, UNIT_GRAM, UNIT_LITRE, UNIT_MILLILITRE, UNIT_PIECE, UNIT_LITRE
from recipes import services as svc
from recipes.models import Recipe, RecipeItem
from recipes.constants import RECIPE_DRAFT, RECIPE_ACTIVE, RECIPE_ARCHIVED, RECIPE_INACTIVE
from recipes.tests.base import RecipeTestBase


class TestRecipeCreation(RecipeTestBase):
    """Tests for create_recipe()."""

    def test_creates_draft_recipe(self):
        recipe = svc.create_recipe(
            restaurant=self.restaurant,
            menu_item=self.item_biryani,
            name="Biryani v1",
            user=self.manager,
        )
        self.assertIsNotNone(recipe.id)
        self.assertEqual(recipe.status, RECIPE_DRAFT)
        self.assertEqual(recipe.version, 1)
        self.assertEqual(recipe.restaurant, self.restaurant)
        self.assertEqual(recipe.menu_item, self.item_biryani)
        self.assertEqual(recipe.created_by, self.manager)

    def test_version_starts_at_one(self):
        recipe = svc.create_recipe(
            self.restaurant, self.item_paneer, "Paneer v1", self.manager
        )
        self.assertEqual(recipe.version, 1)

    def test_version_increments_per_menu_item(self):
        r1 = svc.create_recipe(self.restaurant, self.item_biryani, "B v1", self.manager)
        r2 = svc.create_recipe(self.restaurant, self.item_biryani, "B v2", self.manager)
        r3 = svc.create_recipe(self.restaurant, self.item_biryani, "B v3", self.manager)
        self.assertEqual(r1.version, 1)
        self.assertEqual(r2.version, 2)
        self.assertEqual(r3.version, 3)

    def test_version_independent_per_menu_item(self):
        """Versions for different menu items are independent."""
        svc.create_recipe(self.restaurant, self.item_biryani, "B v1", self.manager)
        svc.create_recipe(self.restaurant, self.item_biryani, "B v2", self.manager)
        naan_r = svc.create_recipe(self.restaurant, self.item_naan, "Naan v1", self.manager)
        self.assertEqual(naan_r.version, 1)

    def test_yield_defaults_to_one_piece(self):
        recipe = svc.create_recipe(self.restaurant, self.item_biryani, "B", self.manager)
        self.assertEqual(recipe.yield_quantity, Decimal("1.000"))
        self.assertEqual(recipe.yield_unit, UNIT_PIECE)

    def test_custom_yield(self):
        recipe = svc.create_recipe(
            self.restaurant, self.item_biryani, "B",
            self.manager,
            yield_quantity=Decimal("2.000"),
            yield_unit=UNIT_KG,
        )
        self.assertEqual(recipe.yield_quantity, Decimal("2.000"))
        self.assertEqual(recipe.yield_unit, UNIT_KG)

    def test_requires_recipe_create_permission(self):
        with self.assertRaises(PermissionDenied):
            svc.create_recipe(self.restaurant, self.item_biryani, "B", self.other_user)

    def test_requires_auth(self):
        with self.assertRaises(PermissionDenied):
            svc.create_recipe(self.restaurant, self.item_biryani, "B", None)

    def test_rejects_cross_restaurant_menu_item(self):
        from menu.models import Category as Cat, MenuItem as MI
        other_cat = Cat.objects.create(
            restaurant=self.other_restaurant, name="Other Cat", slug="other-cat-r"
        )
        other_item = MI.objects.create(
            restaurant=self.other_restaurant, category=other_cat,
            name="Other Item", slug="other-item-r", sku="OI-R001",
        )
        with self.assertRaises(ValidationError) as ctx:
            svc.create_recipe(self.restaurant, other_item, "B", self.manager)
        self.assertEqual(ctx.exception.detail["code"], "CROSS_RESTAURANT_MENU_ITEM")


class TestRecipeUpdate(RecipeTestBase):
    """Tests for update_recipe()."""

    def test_can_update_draft_recipe_name(self):
        recipe = svc.create_recipe(self.restaurant, self.item_biryani, "Old Name", self.manager)
        updated = svc.update_recipe(recipe, self.manager, name="New Name")
        self.assertEqual(updated.name, "New Name")

    def test_cannot_update_active_recipe(self):
        recipe = self._make_active_biryani_recipe()
        with self.assertRaises(ValidationError) as ctx:
            svc.update_recipe(recipe, self.manager, name="Changed")
        self.assertEqual(ctx.exception.detail["code"], "RECIPE_NOT_DRAFT")

    def test_requires_recipe_update_permission(self):
        recipe = svc.create_recipe(self.restaurant, self.item_biryani, "B", self.manager)
        with self.assertRaises(PermissionDenied):
            svc.update_recipe(recipe, self.other_user, name="X")


class TestRecipeItems(RecipeTestBase):
    """Tests for add_recipe_item / remove_recipe_item / update_recipe_item."""

    def _make_draft_recipe(self):
        return svc.create_recipe(
            self.restaurant, self.item_biryani, "Biryani Draft", self.manager
        )

    def test_add_ingredient(self):
        recipe = self._make_draft_recipe()
        item = svc.add_recipe_item(
            recipe, self.inv_rice.id, Decimal("250"), UNIT_GRAM, self.manager
        )
        self.assertEqual(item.quantity, Decimal("250.000"))
        self.assertEqual(item.unit, UNIT_GRAM)
        self.assertEqual(item.inventory_item, self.inv_rice)

    def test_add_multiple_ingredients(self):
        recipe = self._make_draft_recipe()
        svc.add_recipe_item(recipe, self.inv_rice.id, Decimal("250"), UNIT_GRAM, self.manager)
        svc.add_recipe_item(recipe, self.inv_chicken.id, Decimal("200"), UNIT_GRAM, self.manager)
        svc.add_recipe_item(recipe, self.inv_oil.id, Decimal("30"), UNIT_MILLILITRE, self.manager)
        self.assertEqual(recipe.items.count(), 3)

    def test_preparation_loss_applied(self):
        recipe = self._make_draft_recipe()
        item = svc.add_recipe_item(
            recipe, self.inv_rice.id, Decimal("250"), UNIT_GRAM,
            self.manager, preparation_loss_percentage=Decimal("5")
        )
        # effective = 250 × 1.05 = 262.5
        self.assertEqual(item.effective_quantity, Decimal("262.500"))

    def test_duplicate_ingredient_rejected(self):
        recipe = self._make_draft_recipe()
        svc.add_recipe_item(recipe, self.inv_rice.id, Decimal("250"), UNIT_GRAM, self.manager)
        with self.assertRaises(ValidationError) as ctx:
            svc.add_recipe_item(recipe, self.inv_rice.id, Decimal("100"), UNIT_GRAM, self.manager)
        self.assertEqual(ctx.exception.detail["code"], "DUPLICATE_INGREDIENT")

    def test_incompatible_unit_rejected(self):
        """GRAM (weight) vs LITRE (volume) — incompatible for rice."""
        recipe = self._make_draft_recipe()
        with self.assertRaises(ValidationError) as ctx:
            svc.add_recipe_item(recipe, self.inv_rice.id, Decimal("250"), UNIT_LITRE, self.manager)
        self.assertEqual(ctx.exception.detail["code"], "INCOMPATIBLE_UNITS")

    def test_cross_restaurant_ingredient_rejected(self):
        recipe = self._make_draft_recipe()
        with self.assertRaises(ValidationError) as ctx:
            svc.add_recipe_item(
                recipe, self.other_inv_item.id, Decimal("100"), UNIT_KG, self.manager
            )
        self.assertEqual(ctx.exception.detail["code"], "CROSS_RESTAURANT_INGREDIENT")

    def test_zero_quantity_rejected(self):
        recipe = self._make_draft_recipe()
        with self.assertRaises(ValidationError) as ctx:
            svc.add_recipe_item(recipe, self.inv_rice.id, Decimal("0"), UNIT_GRAM, self.manager)
        self.assertEqual(ctx.exception.detail["code"], "INVALID_QUANTITY")

    def test_negative_quantity_rejected(self):
        recipe = self._make_draft_recipe()
        with self.assertRaises(ValidationError) as ctx:
            svc.add_recipe_item(recipe, self.inv_rice.id, Decimal("-10"), UNIT_GRAM, self.manager)
        self.assertEqual(ctx.exception.detail["code"], "INVALID_QUANTITY")

    def test_invalid_preparation_loss_rejected(self):
        """Loss of 100% or more is invalid."""
        recipe = self._make_draft_recipe()
        with self.assertRaises(ValidationError) as ctx:
            svc.add_recipe_item(
                recipe, self.inv_rice.id, Decimal("250"), UNIT_GRAM,
                self.manager, preparation_loss_percentage=Decimal("100")
            )
        self.assertEqual(ctx.exception.detail["code"], "INVALID_PREPARATION_LOSS")

    def test_cannot_add_to_active_recipe(self):
        recipe = self._make_active_biryani_recipe()
        with self.assertRaises(ValidationError) as ctx:
            svc.add_recipe_item(recipe, self.inv_paneer.id, Decimal("100"), UNIT_GRAM, self.manager)
        self.assertEqual(ctx.exception.detail["code"], "RECIPE_NOT_DRAFT")

    def test_remove_ingredient(self):
        recipe = self._make_draft_recipe()
        item = svc.add_recipe_item(recipe, self.inv_rice.id, Decimal("250"), UNIT_GRAM, self.manager)
        svc.remove_recipe_item(item, self.manager)
        self.assertEqual(recipe.items.count(), 0)

    def test_update_ingredient_quantity(self):
        recipe = self._make_draft_recipe()
        item = svc.add_recipe_item(recipe, self.inv_rice.id, Decimal("250"), UNIT_GRAM, self.manager)
        updated = svc.update_recipe_item(item, self.manager, quantity=Decimal("300"))
        self.assertEqual(updated.quantity, Decimal("300.000"))

    def test_no_permission_add_ingredient(self):
        recipe = self._make_draft_recipe()
        with self.assertRaises(PermissionDenied):
            svc.add_recipe_item(recipe, self.inv_rice.id, Decimal("250"), UNIT_GRAM, self.other_user)


class TestRecipeActivation(RecipeTestBase):
    """Tests for activate_recipe()."""

    def _make_recipe_with_ingredients(self):
        recipe = svc.create_recipe(self.restaurant, self.item_biryani, "B", self.manager)
        svc.add_recipe_item(recipe, self.inv_rice.id, Decimal("250"), UNIT_GRAM, self.manager)
        svc.add_recipe_item(recipe, self.inv_chicken.id, Decimal("200"), UNIT_GRAM, self.manager)
        return recipe

    def test_activates_draft_recipe(self):
        recipe = self._make_recipe_with_ingredients()
        activated = svc.activate_recipe(recipe, self.manager)
        self.assertEqual(activated.status, RECIPE_ACTIVE)
        self.assertEqual(activated.approved_by, self.manager)
        self.assertIsNotNone(activated.approved_at)

    def test_cannot_activate_without_ingredients(self):
        recipe = svc.create_recipe(self.restaurant, self.item_biryani, "B", self.manager)
        with self.assertRaises(ValidationError) as ctx:
            svc.activate_recipe(recipe, self.manager)
        self.assertEqual(ctx.exception.detail["code"], "RECIPE_NO_INGREDIENTS")

    def test_cannot_activate_already_active_recipe(self):
        recipe = self._make_active_biryani_recipe()
        with self.assertRaises(ValidationError) as ctx:
            svc.activate_recipe(recipe, self.manager)
        self.assertEqual(ctx.exception.detail["code"], "RECIPE_NOT_ACTIVATABLE")

    def test_activating_deactivates_previous_active(self):
        """Activating a new recipe deactivates (INACTIVE) the previous ACTIVE one."""
        recipe_v1 = self._make_recipe_with_ingredients()
        active_v1 = svc.activate_recipe(recipe_v1, self.manager)
        self.assertEqual(active_v1.status, RECIPE_ACTIVE)

        # Create v2 (new recipe for same menu item)
        recipe_v2 = svc.create_recipe(self.restaurant, self.item_biryani, "B v2", self.manager)
        svc.add_recipe_item(recipe_v2, self.inv_rice.id, Decimal("300"), UNIT_GRAM, self.manager)
        active_v2 = svc.activate_recipe(recipe_v2, self.manager)
        self.assertEqual(active_v2.status, RECIPE_ACTIVE)

        # v1 should now be INACTIVE
        active_v1.refresh_from_db()
        self.assertEqual(active_v1.status, RECIPE_INACTIVE)

    def test_requires_activate_permission(self):
        recipe = self._make_recipe_with_ingredients()
        with self.assertRaises(PermissionDenied):
            svc.activate_recipe(recipe, self.other_user)


class TestRecipeVersioning(RecipeTestBase):
    """Tests for recipe version history."""

    def test_historical_version_not_overwritten(self):
        """Creating a new version does not modify the old one."""
        r1 = svc.create_recipe(self.restaurant, self.item_biryani, "B v1", self.manager)
        svc.add_recipe_item(r1, self.inv_rice.id, Decimal("250"), UNIT_GRAM, self.manager)
        svc.activate_recipe(r1, self.manager)
        r1_id = r1.id
        r1_ingredient_count = r1.items.count()

        # Create v2 and activate
        r2 = svc.create_recipe(self.restaurant, self.item_biryani, "B v2", self.manager)
        svc.add_recipe_item(r2, self.inv_rice.id, Decimal("300"), UNIT_GRAM, self.manager)
        svc.add_recipe_item(r2, self.inv_chicken.id, Decimal("200"), UNIT_GRAM, self.manager)
        svc.activate_recipe(r2, self.manager)

        # v1 still exists and is unchanged
        r1_reload = Recipe.objects.get(pk=r1_id)
        self.assertEqual(r1_reload.items.count(), r1_ingredient_count)
        self.assertEqual(r1_reload.version, 1)

    def test_all_versions_queryable(self):
        r1 = svc.create_recipe(self.restaurant, self.item_biryani, "B v1", self.manager)
        svc.add_recipe_item(r1, self.inv_rice.id, Decimal("250"), UNIT_GRAM, self.manager)
        svc.activate_recipe(r1, self.manager)

        r2 = svc.create_recipe(self.restaurant, self.item_biryani, "B v2", self.manager)
        svc.add_recipe_item(r2, self.inv_rice.id, Decimal("300"), UNIT_GRAM, self.manager)
        svc.activate_recipe(r2, self.manager)

        all_versions = Recipe.objects.filter(menu_item=self.item_biryani).order_by("version")
        self.assertEqual(all_versions.count(), 2)
        self.assertEqual(all_versions[0].version, 1)
        self.assertEqual(all_versions[1].version, 2)


class TestRecipeArchival(RecipeTestBase):
    """Tests for archive_recipe()."""

    def test_archive_active_recipe(self):
        recipe = self._make_active_biryani_recipe()
        archived = svc.archive_recipe(recipe, self.manager)
        self.assertEqual(archived.status, RECIPE_ARCHIVED)

    def test_archive_draft_recipe(self):
        recipe = svc.create_recipe(self.restaurant, self.item_biryani, "B", self.manager)
        archived = svc.archive_recipe(recipe, self.manager)
        self.assertEqual(archived.status, RECIPE_ARCHIVED)

    def test_cannot_archive_already_archived(self):
        recipe = self._make_active_biryani_recipe()
        svc.archive_recipe(recipe, self.manager)
        recipe.refresh_from_db()
        with self.assertRaises(ValidationError) as ctx:
            svc.archive_recipe(recipe, self.manager)
        self.assertEqual(ctx.exception.detail["code"], "RECIPE_NOT_ARCHIVABLE")

    def test_requires_archive_permission(self):
        recipe = self._make_active_biryani_recipe()
        with self.assertRaises(PermissionDenied):
            svc.archive_recipe(recipe, self.other_user)


class TestRecipeCost(RecipeTestBase):
    """Tests for calculate_recipe_cost()."""

    def test_cost_calculation(self):
        """
        Rice 250g @ ₹60/kg = ₹15
        Chicken 200g @ ₹240/kg = ₹48
        Oil 30ml @ ₹150/L = ₹4.50
        Total = ₹67.50
        """
        recipe = self._make_active_biryani_recipe()
        cost_data = svc.calculate_recipe_cost(recipe)

        self.assertEqual(cost_data["version"], recipe.version)
        self.assertIn("total_cost", cost_data)
        self.assertEqual(len(cost_data["ingredients"]), 3)

        total = Decimal(cost_data["total_cost"])
        # Rice: 250g × (60/1000) = 0.250 kg × 60 = 15.00
        # Chicken: 200g × (240/1000) = 0.200 kg × 240 = 48.00
        # Oil: 30ml × (150/1000) = 0.030 L × 150 = 4.50
        self.assertEqual(total, Decimal("67.50"))

    def test_cost_uses_current_average_cost(self):
        """Cost must use InventoryItem.average_cost, not a hardcoded value."""
        recipe = self._make_active_biryani_recipe(rice_qty_grams=Decimal("1000"))
        # 1kg rice @ 60/kg = 60
        cost_data = svc.calculate_recipe_cost(recipe)
        rice_ingredient = next(
            i for i in cost_data["ingredients"]
            if i["inventory_item_name"] == "Basmati Rice"
        )
        self.assertEqual(Decimal(rice_ingredient["unit_cost"]), Decimal("60.00"))

    def test_cost_includes_preparation_loss(self):
        """Loss increases effective quantity, which increases cost."""
        recipe = svc.create_recipe(
            self.restaurant, self.item_naan, "Naan", self.manager,
            yield_quantity=Decimal("1"), yield_unit=UNIT_PIECE,
        )
        svc.add_recipe_item(
            recipe, self.inv_flour.id, Decimal("200"), UNIT_GRAM,
            self.manager, preparation_loss_percentage=Decimal("10")
        )
        svc.activate_recipe(recipe, self.manager)

        cost_data = svc.calculate_recipe_cost(recipe)
        flour_item = cost_data["ingredients"][0]
        # effective = 200 × 1.10 = 220g = 0.22 kg @ 40/kg = 8.80
        self.assertEqual(Decimal(flour_item["effective_quantity"]), Decimal("220.000"))
        self.assertEqual(Decimal(flour_item["line_cost"]), Decimal("8.80"))


class TestRecipePermissions(RecipeTestBase):
    """Tests that every operation enforces the correct permission code."""

    def test_view_recipe_requires_recipe_view(self):
        """Staff without recipe.view cannot see recipes via access layer."""
        from recipes.access import get_accessible_recipes
        # other_user has no role assignment — sees nothing
        qs = get_accessible_recipes(self.other_user)
        self.assertEqual(qs.count(), 0)

    def test_manager_can_see_own_restaurant_recipes(self):
        from recipes.access import get_accessible_recipes
        svc.create_recipe(self.restaurant, self.item_biryani, "B", self.manager)
        qs = get_accessible_recipes(self.manager)
        self.assertGreater(qs.count(), 0)

    def test_other_restaurant_recipes_not_visible(self):
        """Manager from restaurant A cannot see recipes from restaurant B."""
        from recipes.access import get_accessible_recipes
        from menu.models import Category as Cat, MenuItem as MI

        other_cat = Cat.objects.create(
            restaurant=self.other_restaurant, name="OC", slug="oc-test-perm"
        )
        other_item = MI.objects.create(
            restaurant=self.other_restaurant, category=other_cat,
            name="Other Dish", slug="other-dish-perm", sku="OD-PERM01",
        )
        # Create recipe for other_restaurant using staff from other_restaurant
        other_manager = User.objects.create_user(
            email="other_manager_perm@test.com", password="pass123",
            first_name="Mgr", last_name="Other",
        )
        other_role = Role.objects.create(
            name="Other Mgr Role", code="OTHER_MGR_PERM_TEST", scope=Role.SCOPE_BRANCH
        )
        other_role.permissions.set(list(self.perms.values()))
        UserRoleAssignment.objects.create(
            user=other_manager, role=other_role,
            organization=self.org, restaurant=self.other_restaurant,
            branch=self.other_rest_branch,
        )
        svc.create_recipe(self.other_restaurant, other_item, "Other", other_manager)

        # cls.manager can only see recipes for cls.restaurant
        manager_recipes = get_accessible_recipes(self.manager)
        for r in manager_recipes:
            self.assertEqual(r.restaurant_id, self.restaurant.id)
