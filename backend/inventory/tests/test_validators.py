# =============================================================================
# RestaurantFlow — Inventory Validator Tests
# Phase 10
#
# Pure unit tests for inventory/validators.py functions.
# No DB access required.
# =============================================================================

from decimal import Decimal

from django.test import SimpleTestCase
from rest_framework.exceptions import ValidationError

from inventory.validators import (
    validate_positive_quantity,
    validate_non_negative_quantity,
    validate_non_negative_cost,
    validate_unit,
    validate_compatible_units,
    validate_sufficient_stock,
    validate_purchase_order_transition,
    validate_transfer_transition,
    validate_transfer_locations,
    validate_receive_quantity,
    validate_reason,
)
from inventory.constants import (
    PO_DRAFT, PO_SUBMITTED, PO_APPROVED, PO_RECEIVED, PO_CANCELLED,
    TRANSFER_DRAFT, TRANSFER_REQUESTED, TRANSFER_APPROVED, TRANSFER_COMPLETED,
)


class TestQuantityValidators(SimpleTestCase):
    def test_positive_quantity_valid(self):
        result = validate_positive_quantity(Decimal("10.5"))
        self.assertEqual(result, Decimal("10.5"))

    def test_positive_quantity_zero_raises(self):
        with self.assertRaises(ValidationError):
            validate_positive_quantity(Decimal("0"))

    def test_positive_quantity_negative_raises(self):
        with self.assertRaises(ValidationError):
            validate_positive_quantity(Decimal("-1"))

    def test_non_negative_zero_valid(self):
        result = validate_non_negative_quantity(Decimal("0"))
        self.assertEqual(result, Decimal("0"))

    def test_non_negative_negative_raises(self):
        with self.assertRaises(ValidationError):
            validate_non_negative_quantity(Decimal("-0.001"))

    def test_non_negative_cost_zero_valid(self):
        result = validate_non_negative_cost(Decimal("0"))
        self.assertEqual(result, Decimal("0"))

    def test_non_negative_cost_negative_raises(self):
        with self.assertRaises(ValidationError):
            validate_non_negative_cost(Decimal("-1"))


class TestUnitValidators(SimpleTestCase):
    def test_valid_unit(self):
        self.assertEqual(validate_unit("KG"), "KG")
        self.assertEqual(validate_unit("LITRE"), "LITRE")
        self.assertEqual(validate_unit("PIECE"), "PIECE")

    def test_invalid_unit_raises(self):
        with self.assertRaises(ValidationError):
            validate_unit("GALLON")

    def test_compatible_units_same(self):
        # Same unit is always compatible
        validate_compatible_units("KG", "KG")  # should not raise

    def test_compatible_weight_units(self):
        validate_compatible_units("KG", "GRAM")  # both weight

    def test_compatible_volume_units(self):
        validate_compatible_units("LITRE", "MILLILITRE")

    def test_incompatible_weight_volume_raises(self):
        with self.assertRaises(ValidationError):
            validate_compatible_units("KG", "LITRE")

    def test_incompatible_weight_count_raises(self):
        with self.assertRaises(ValidationError):
            validate_compatible_units("KG", "PIECE")


class TestStockValidators(SimpleTestCase):
    def test_sufficient_stock_exact_passes(self):
        validate_sufficient_stock(Decimal("10"), Decimal("10"))  # no raise

    def test_sufficient_stock_less_than_available_passes(self):
        validate_sufficient_stock(Decimal("100"), Decimal("50"))

    def test_insufficient_stock_raises(self):
        with self.assertRaises(ValidationError) as ctx:
            validate_sufficient_stock(Decimal("5"), Decimal("10"), item_name="Rice")
        self.assertEqual(ctx.exception.detail["code"], "INSUFFICIENT_STOCK")
        self.assertIn("Rice", ctx.exception.detail["message"])


class TestPurchaseOrderTransitionValidators(SimpleTestCase):
    def test_valid_transition_draft_to_submitted(self):
        validate_purchase_order_transition(PO_DRAFT, PO_SUBMITTED)  # no raise

    def test_valid_transition_submitted_to_approved(self):
        validate_purchase_order_transition(PO_SUBMITTED, PO_APPROVED)

    def test_invalid_transition_draft_to_received(self):
        with self.assertRaises(ValidationError) as ctx:
            validate_purchase_order_transition(PO_DRAFT, PO_RECEIVED)
        self.assertEqual(ctx.exception.detail["code"], "INVALID_STATUS_TRANSITION")

    def test_invalid_transition_from_received(self):
        with self.assertRaises(ValidationError):
            validate_purchase_order_transition(PO_RECEIVED, PO_APPROVED)

    def test_cancel_from_draft_valid(self):
        validate_purchase_order_transition(PO_DRAFT, PO_CANCELLED)

    def test_cancel_from_received_invalid(self):
        with self.assertRaises(ValidationError):
            validate_purchase_order_transition(PO_RECEIVED, PO_CANCELLED)


class TestTransferTransitionValidators(SimpleTestCase):
    def test_draft_to_requested_valid(self):
        validate_transfer_transition(TRANSFER_DRAFT, TRANSFER_REQUESTED)

    def test_requested_to_approved_valid(self):
        validate_transfer_transition(TRANSFER_REQUESTED, TRANSFER_APPROVED)

    def test_approved_to_completed_valid(self):
        validate_transfer_transition(TRANSFER_APPROVED, TRANSFER_COMPLETED)

    def test_draft_to_completed_invalid(self):
        with self.assertRaises(ValidationError) as ctx:
            validate_transfer_transition(TRANSFER_DRAFT, TRANSFER_COMPLETED)
        self.assertEqual(ctx.exception.detail["code"], "INVALID_STATUS_TRANSITION")


class TestTransferLocationValidators(SimpleTestCase):
    def test_same_location_raises(self):
        import uuid
        loc_id = uuid.uuid4()
        with self.assertRaises(ValidationError) as ctx:
            validate_transfer_locations(loc_id, loc_id)
        self.assertEqual(ctx.exception.detail["code"], "SAME_LOCATION")

    def test_different_locations_passes(self):
        import uuid
        validate_transfer_locations(uuid.uuid4(), uuid.uuid4())  # no raise


class TestReceiveQuantityValidator(SimpleTestCase):
    def test_valid_receive(self):
        validate_receive_quantity(
            ordered=Decimal("100"),
            already_received=Decimal("60"),
            receiving=Decimal("40"),
            item_name="Rice",
        )  # no raise

    def test_over_receive_raises(self):
        with self.assertRaises(ValidationError) as ctx:
            validate_receive_quantity(
                ordered=Decimal("100"),
                already_received=Decimal("60"),
                receiving=Decimal("41"),
                item_name="Rice",
            )
        self.assertEqual(ctx.exception.detail["code"], "OVER_RECEIVING")

    def test_zero_receive_raises(self):
        with self.assertRaises(ValidationError) as ctx:
            validate_receive_quantity(
                ordered=Decimal("100"),
                already_received=Decimal("0"),
                receiving=Decimal("0"),
                item_name="Rice",
            )
        self.assertEqual(ctx.exception.detail["code"], "INVALID_RECEIVE_QUANTITY")


class TestReasonValidator(SimpleTestCase):
    def test_valid_reason(self):
        result = validate_reason("Physical count done today")
        self.assertEqual(result, "Physical count done today")

    def test_empty_reason_raises(self):
        with self.assertRaises(ValidationError):
            validate_reason("")

    def test_whitespace_only_raises(self):
        with self.assertRaises(ValidationError):
            validate_reason("   ")

    def test_too_short_raises(self):
        with self.assertRaises(ValidationError):
            validate_reason("hi")  # less than 5 chars

    def test_strips_whitespace(self):
        result = validate_reason("  Physical count done today  ")
        self.assertEqual(result, "Physical count done today")
