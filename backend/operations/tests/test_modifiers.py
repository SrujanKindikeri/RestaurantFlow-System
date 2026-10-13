# =============================================================================
# RestaurantFlow — Modifier Group / Option Tests
# Phase 19: Advanced POS & Restaurant Operations
# =============================================================================

from decimal import Decimal

from django.test import TestCase

from operations.tests.base import OperationsTestBase
from operations.models import MenuModifierGroup, MenuModifierOption
from operations.validators import validate_modifier_selections
from operations.exceptions import ModifierValidationError


class ModifierGroupTest(OperationsTestBase):
    """Tests for MenuModifierGroup and MenuModifierOption models."""

    def test_create_modifier_group(self):
        group = MenuModifierGroup.objects.create(
            restaurant=self.restaurant,
            name="Spice Level",
            is_required=True,
            min_selections=1,
            max_selections=1,
        )
        self.assertEqual(group.name, "Spice Level")
        self.assertTrue(group.is_required)

    def test_create_modifier_option_with_price(self):
        group = MenuModifierGroup.objects.create(
            restaurant=self.restaurant, name="Cheese",
        )
        option = MenuModifierOption.objects.create(
            modifier_group=group,
            name="Extra Cheese",
            price_adjustment=Decimal("30.00"),
        )
        self.assertEqual(option.price_adjustment, Decimal("30.00"))
        self.assertTrue(option.is_active)

    def test_modifier_option_zero_price(self):
        group = MenuModifierGroup.objects.create(
            restaurant=self.restaurant, name="Temperature",
        )
        option = MenuModifierOption.objects.create(
            modifier_group=group, name="Hot", price_adjustment=Decimal("0.00"),
        )
        self.assertEqual(option.price_adjustment, Decimal("0.00"))

    def test_attach_modifier_group_to_menu_item(self):
        group = MenuModifierGroup.objects.create(
            restaurant=self.restaurant, name="Toppings",
            max_selections=3,
        )
        group.menu_items.add(self.item_pizza)
        self.assertIn(self.item_pizza, group.menu_items.all())

    def test_modifier_group_options_cascade_delete(self):
        """Deleting a group cascades to its options."""
        group = MenuModifierGroup.objects.create(
            restaurant=self.restaurant, name="TempGroup",
        )
        opt = MenuModifierOption.objects.create(
            modifier_group=group, name="TempOpt",
        )
        opt_id = opt.id
        group.delete()
        self.assertFalse(
            MenuModifierOption.objects.filter(pk=opt_id).exists()
        )


class ModifierValidationTest(OperationsTestBase):
    """Tests for modifier selection validation."""

    def setUp(self):
        self.group = MenuModifierGroup.objects.create(
            restaurant=self.restaurant,
            name="Sauce",
            is_required=True,
            min_selections=1,
            max_selections=2,
        )
        self.opt1 = MenuModifierOption.objects.create(
            modifier_group=self.group, name="Ketchup",
        )
        self.opt2 = MenuModifierOption.objects.create(
            modifier_group=self.group, name="Mayo",
        )
        self.opt3 = MenuModifierOption.objects.create(
            modifier_group=self.group, name="Hot Sauce",
        )

    def test_valid_single_selection(self):
        """Selecting one option passes for a min=1,max=2 group."""
        validate_modifier_selections(
            self.group, [str(self.opt1.id)]
        )  # Should not raise

    def test_valid_two_selections(self):
        validate_modifier_selections(
            self.group, [str(self.opt1.id), str(self.opt2.id)]
        )  # Should not raise

    def test_too_few_selections_raises(self):
        """Required group with 0 selections raises ModifierValidationError."""
        with self.assertRaises(ModifierValidationError):
            validate_modifier_selections(self.group, [])

    def test_too_many_selections_raises(self):
        """More than max_selections raises ModifierValidationError."""
        with self.assertRaises(ModifierValidationError):
            validate_modifier_selections(
                self.group,
                [str(self.opt1.id), str(self.opt2.id), str(self.opt3.id)],
            )

    def test_invalid_option_id_raises(self):
        """Unknown option IDs raise ModifierValidationError."""
        with self.assertRaises(ModifierValidationError):
            validate_modifier_selections(
                self.group,
                ["00000000-0000-0000-0000-000000000000"],
            )

    def test_inactive_option_raises(self):
        inactive = MenuModifierOption.objects.create(
            modifier_group=self.group, name="Inactive",
            price_adjustment=Decimal("0.00"), is_active=False,
        )
        with self.assertRaises(ModifierValidationError):
            validate_modifier_selections(
                self.group, [str(inactive.id)]
            )

    def test_optional_group_zero_selections_ok(self):
        """Optional group with 0 selections should pass."""
        optional_group = MenuModifierGroup.objects.create(
            restaurant=self.restaurant,
            name="Extras",
            is_required=False,
            min_selections=0,
            max_selections=3,
        )
        validate_modifier_selections(optional_group, [])  # Should not raise

    def test_unlimited_selections_allowed(self):
        """max_selections=0 means unlimited — any count passes."""
        unlimited_group = MenuModifierGroup.objects.create(
            restaurant=self.restaurant,
            name="Toppings",
            is_required=False,
            min_selections=0,
            max_selections=0,  # 0 = unlimited
        )
        opts = [
            MenuModifierOption.objects.create(modifier_group=unlimited_group, name=f"Topping {i}")
            for i in range(5)
        ]
        validate_modifier_selections(
            unlimited_group, [str(o.id) for o in opts]
        )  # Should not raise


class MenuItemModifierAPITest(OperationsTestBase):
    """API test for retrieving modifier groups for a menu item."""

    def setUp(self):
        self.client.force_login(self.cashier)
        self.group = MenuModifierGroup.objects.create(
            restaurant=self.restaurant, name="Pizza Size",
            is_required=True, min_selections=1, max_selections=1,
        )
        MenuModifierOption.objects.create(
            modifier_group=self.group, name='Small', price_adjustment=Decimal('-50.00'),
        )
        MenuModifierOption.objects.create(
            modifier_group=self.group, name='Large', price_adjustment=Decimal('50.00'),
        )
        self.group.menu_items.add(self.item_pizza)

    def test_get_modifiers_for_menu_item(self):
        r = self.client.get(
            f"/api/operations/menu-items/{self.item_pizza.id}/modifiers/"
        )
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertIsInstance(data, list)

    def test_get_modifiers_nonexistent_item_404(self):
        r = self.client.get(
            "/api/operations/menu-items/00000000-0000-0000-0000-000000000000/modifiers/"
        )
        self.assertEqual(r.status_code, 404)
