# =============================================================================
# RestaurantFlow — Inventory Constants
# Phase 10
#
# Centralised constants for the inventory domain.
# Import from here — never hard-code these values in models or services.
# =============================================================================

from decimal import Decimal


# ---------------------------------------------------------------------------
# Unit of Measurement choices
# ---------------------------------------------------------------------------

UNIT_KG          = "KG"
UNIT_GRAM        = "GRAM"
UNIT_LITRE       = "LITRE"
UNIT_MILLILITRE  = "MILLILITRE"
UNIT_PIECE       = "PIECE"
UNIT_PACK        = "PACK"
UNIT_BOX         = "BOX"
UNIT_BOTTLE      = "BOTTLE"
UNIT_DOZEN       = "DOZEN"

UNIT_CHOICES = [
    (UNIT_KG,         "Kilogram (KG)"),
    (UNIT_GRAM,       "Gram (g)"),
    (UNIT_LITRE,      "Litre (L)"),
    (UNIT_MILLILITRE, "Millilitre (mL)"),
    (UNIT_PIECE,      "Piece"),
    (UNIT_PACK,       "Pack"),
    (UNIT_BOX,        "Box"),
    (UNIT_BOTTLE,     "Bottle"),
    (UNIT_DOZEN,      "Dozen"),
]

# ---------------------------------------------------------------------------
# Unit conversion factors (to a canonical base unit)
#
# Conversions are defined as (from_unit, to_unit) → factor
# Such that: quantity_in_to_unit = quantity_in_from_unit × factor
#
# Base units: GRAM (for weight), MILLILITRE (for volume), PIECE (for count)
# ---------------------------------------------------------------------------

UNIT_CONVERSION_FACTORS: dict[tuple[str, str], Decimal] = {
    # Weight — base: GRAM
    (UNIT_KG,   UNIT_GRAM):  Decimal("1000"),
    (UNIT_GRAM, UNIT_KG):    Decimal("0.001"),

    # Volume — base: MILLILITRE
    (UNIT_LITRE,      UNIT_MILLILITRE): Decimal("1000"),
    (UNIT_MILLILITRE, UNIT_LITRE):      Decimal("0.001"),

    # Count — base: PIECE
    (UNIT_DOZEN, UNIT_PIECE): Decimal("12"),
    (UNIT_PIECE, UNIT_DOZEN): Decimal("0.083333333333"),
}

# Unit families — used to prevent incompatible-unit mixing
WEIGHT_UNITS   = {UNIT_KG, UNIT_GRAM}
VOLUME_UNITS   = {UNIT_LITRE, UNIT_MILLILITRE}
COUNT_UNITS    = {UNIT_PIECE, UNIT_PACK, UNIT_BOX, UNIT_BOTTLE, UNIT_DOZEN}

UNIT_FAMILIES: dict[str, str] = {}
for u in WEIGHT_UNITS:
    UNIT_FAMILIES[u] = "weight"
for u in VOLUME_UNITS:
    UNIT_FAMILIES[u] = "volume"
for u in COUNT_UNITS:
    UNIT_FAMILIES[u] = "count"


def get_conversion_factor(from_unit: str, to_unit: str) -> Decimal | None:
    """
    Return the conversion factor from `from_unit` to `to_unit`, or None
    if no conversion path is defined.

    The caller is responsible for validating that units are compatible.
    """
    if from_unit == to_unit:
        return Decimal("1")
    return UNIT_CONVERSION_FACTORS.get((from_unit, to_unit))


def are_units_compatible(unit_a: str, unit_b: str) -> bool:
    """Return True if both units belong to the same family."""
    if unit_a == unit_b:
        return True
    family_a = UNIT_FAMILIES.get(unit_a)
    family_b = UNIT_FAMILIES.get(unit_b)
    return (family_a is not None) and (family_a == family_b)


# ---------------------------------------------------------------------------
# Stock Movement types
# ---------------------------------------------------------------------------

MOVEMENT_PURCHASE         = "PURCHASE"
MOVEMENT_PURCHASE_RETURN  = "PURCHASE_RETURN"
MOVEMENT_TRANSFER_IN      = "TRANSFER_IN"
MOVEMENT_TRANSFER_OUT     = "TRANSFER_OUT"
MOVEMENT_WASTAGE          = "WASTAGE"
MOVEMENT_ADJUSTMENT_IN    = "ADJUSTMENT_IN"
MOVEMENT_ADJUSTMENT_OUT   = "ADJUSTMENT_OUT"
MOVEMENT_CONSUMPTION      = "CONSUMPTION"
MOVEMENT_OPENING_STOCK    = "OPENING_STOCK"
MOVEMENT_CORRECTION       = "CORRECTION"

MOVEMENT_TYPE_CHOICES = [
    (MOVEMENT_PURCHASE,        "Purchase"),
    (MOVEMENT_PURCHASE_RETURN, "Purchase Return"),
    (MOVEMENT_TRANSFER_IN,     "Transfer In"),
    (MOVEMENT_TRANSFER_OUT,    "Transfer Out"),
    (MOVEMENT_WASTAGE,         "Wastage"),
    (MOVEMENT_ADJUSTMENT_IN,   "Adjustment In"),
    (MOVEMENT_ADJUSTMENT_OUT,  "Adjustment Out"),
    (MOVEMENT_CONSUMPTION,     "Consumption"),
    (MOVEMENT_OPENING_STOCK,   "Opening Stock"),
    (MOVEMENT_CORRECTION,      "Correction"),
]

# Movement types that increase stock
STOCK_IN_MOVEMENTS = {
    MOVEMENT_PURCHASE,
    MOVEMENT_TRANSFER_IN,
    MOVEMENT_ADJUSTMENT_IN,
    MOVEMENT_CONSUMPTION,   # positive correction
    MOVEMENT_OPENING_STOCK,
    MOVEMENT_CORRECTION,
}

# Movement types that decrease stock
STOCK_OUT_MOVEMENTS = {
    MOVEMENT_PURCHASE_RETURN,
    MOVEMENT_TRANSFER_OUT,
    MOVEMENT_WASTAGE,
    MOVEMENT_ADJUSTMENT_OUT,
}

# ---------------------------------------------------------------------------
# Storage location types
# ---------------------------------------------------------------------------

LOCATION_MAIN_STORE   = "MAIN_STORE"
LOCATION_KITCHEN      = "KITCHEN"
LOCATION_COLD_STORAGE = "COLD_STORAGE"
LOCATION_FREEZER      = "FREEZER"
LOCATION_BAR          = "BAR"
LOCATION_DRY_STORE    = "DRY_STORE"
LOCATION_OTHER        = "OTHER"

LOCATION_TYPE_CHOICES = [
    (LOCATION_MAIN_STORE,   "Main Store"),
    (LOCATION_KITCHEN,      "Kitchen Store"),
    (LOCATION_COLD_STORAGE, "Cold Storage"),
    (LOCATION_FREEZER,      "Freezer"),
    (LOCATION_BAR,          "Bar Store"),
    (LOCATION_DRY_STORE,    "Dry Store"),
    (LOCATION_OTHER,        "Other"),
]

# ---------------------------------------------------------------------------
# Purchase Order statuses
# ---------------------------------------------------------------------------

PO_DRAFT               = "DRAFT"
PO_SUBMITTED           = "SUBMITTED"
PO_APPROVED            = "APPROVED"
PO_PARTIALLY_RECEIVED  = "PARTIALLY_RECEIVED"
PO_RECEIVED            = "RECEIVED"
PO_CANCELLED           = "CANCELLED"

PO_STATUS_CHOICES = [
    (PO_DRAFT,              "Draft"),
    (PO_SUBMITTED,          "Submitted"),
    (PO_APPROVED,           "Approved"),
    (PO_PARTIALLY_RECEIVED, "Partially Received"),
    (PO_RECEIVED,           "Received"),
    (PO_CANCELLED,          "Cancelled"),
]

# Valid state transitions for purchase orders
PO_VALID_TRANSITIONS: dict[str, list[str]] = {
    PO_DRAFT:              [PO_SUBMITTED, PO_CANCELLED],
    PO_SUBMITTED:          [PO_APPROVED, PO_CANCELLED],
    PO_APPROVED:           [PO_PARTIALLY_RECEIVED, PO_RECEIVED, PO_CANCELLED],
    PO_PARTIALLY_RECEIVED: [PO_RECEIVED, PO_CANCELLED],
    PO_RECEIVED:           [],    # terminal
    PO_CANCELLED:          [],    # terminal
}

# Statuses from which receiving is allowed
PO_RECEIVABLE_STATUSES = {PO_APPROVED, PO_PARTIALLY_RECEIVED}

# Statuses from which cancellation is allowed
PO_CANCELLABLE_STATUSES = {PO_DRAFT, PO_SUBMITTED, PO_APPROVED, PO_PARTIALLY_RECEIVED}

# ---------------------------------------------------------------------------
# Stock Transfer statuses
# ---------------------------------------------------------------------------

TRANSFER_DRAFT     = "DRAFT"
TRANSFER_REQUESTED = "REQUESTED"
TRANSFER_APPROVED  = "APPROVED"
TRANSFER_COMPLETED = "COMPLETED"
TRANSFER_CANCELLED = "CANCELLED"

TRANSFER_STATUS_CHOICES = [
    (TRANSFER_DRAFT,     "Draft"),
    (TRANSFER_REQUESTED, "Requested"),
    (TRANSFER_APPROVED,  "Approved"),
    (TRANSFER_COMPLETED, "Completed"),
    (TRANSFER_CANCELLED, "Cancelled"),
]

TRANSFER_VALID_TRANSITIONS: dict[str, list[str]] = {
    TRANSFER_DRAFT:     [TRANSFER_REQUESTED, TRANSFER_CANCELLED],
    TRANSFER_REQUESTED: [TRANSFER_APPROVED, TRANSFER_CANCELLED],
    TRANSFER_APPROVED:  [TRANSFER_COMPLETED, TRANSFER_CANCELLED],
    TRANSFER_COMPLETED: [],   # terminal
    TRANSFER_CANCELLED: [],   # terminal
}

# ---------------------------------------------------------------------------
# Wastage types
# ---------------------------------------------------------------------------

WASTAGE_SPOILED          = "SPOILED"
WASTAGE_DAMAGED          = "DAMAGED"
WASTAGE_EXPIRED          = "EXPIRED"
WASTAGE_PREPARATION_LOSS = "PREPARATION_LOSS"
WASTAGE_OTHER            = "OTHER"

WASTAGE_TYPE_CHOICES = [
    (WASTAGE_SPOILED,          "Spoiled"),
    (WASTAGE_DAMAGED,          "Damaged"),
    (WASTAGE_EXPIRED,          "Expired"),
    (WASTAGE_PREPARATION_LOSS, "Preparation Loss"),
    (WASTAGE_OTHER,            "Other"),
]

# ---------------------------------------------------------------------------
# Wastage statuses
# ---------------------------------------------------------------------------

WASTAGE_PENDING  = "PENDING"
WASTAGE_APPROVED = "APPROVED"
WASTAGE_REJECTED = "REJECTED"
WASTAGE_RECORDED = "RECORDED"

WASTAGE_STATUS_CHOICES = [
    (WASTAGE_PENDING,  "Pending"),
    (WASTAGE_APPROVED, "Approved"),
    (WASTAGE_REJECTED, "Rejected"),
    (WASTAGE_RECORDED, "Recorded"),
]

# ---------------------------------------------------------------------------
# Stock status labels (derived — never stored)
# ---------------------------------------------------------------------------

STOCK_STATUS_IN_STOCK    = "IN_STOCK"
STOCK_STATUS_LOW_STOCK   = "LOW_STOCK"
STOCK_STATUS_OUT_OF_STOCK = "OUT_OF_STOCK"

# ---------------------------------------------------------------------------
# Precision constants (mirrors billing/utils.py pattern)
# ---------------------------------------------------------------------------

DECIMAL_QTY    = Decimal("0.001")    # 3dp for quantities
DECIMAL_COST   = Decimal("0.01")     # 2dp for monetary values
DECIMAL_RATE   = Decimal("0.001")    # 3dp for rates
ZERO           = Decimal("0.000")
ZERO_COST      = Decimal("0.00")

# Purchase number format: PO-{seq:06d}  e.g. PO-000001
PO_NUMBER_FORMAT = "PO-{seq:06d}"

# Transfer number format: TR-{seq:06d}  e.g. TR-000001
TRANSFER_NUMBER_FORMAT = "TR-{seq:06d}"

# Reference types for stock movements
REF_PURCHASE_ORDER    = "PURCHASE_ORDER"
REF_PURCHASE_RECEIPT  = "PURCHASE_RECEIPT"
REF_STOCK_TRANSFER    = "STOCK_TRANSFER"
REF_STOCK_WASTAGE     = "STOCK_WASTAGE"
REF_STOCK_ADJUSTMENT  = "STOCK_ADJUSTMENT"
REF_MANUAL            = "MANUAL"
