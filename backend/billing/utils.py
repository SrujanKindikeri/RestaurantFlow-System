# =============================================================================
# RestaurantFlow — Billing Money Utilities
# Phase 8
#
# Centralised Decimal arithmetic helpers for the billing layer.
#
# Rules:
#   - All operations use Python's Decimal — never float.
#   - Rounding mode: ROUND_HALF_UP throughout (consistent, predictable).
#   - All public functions are pure (no side effects, no DB access).
#   - The same functions are used by services.py AND tests — no duplication.
#
# Precision constants:
#   MONEY_PRECISION    = Decimal("0.01")   — 2 decimal places for currency
#   RATE_PRECISION     = Decimal("0.001")  — 3 decimal places for tax/qty rates
#   QTY_PRECISION      = Decimal("0.001")  — 3 decimal places for quantities
#
# Money calculation sequence (mirrors services.calculate_bill()):
#   1. gross = qty × unit_price                          (2dp)
#   2. item_tax = gross × rate / 100                     (2dp)
#   3. item_total = gross + item_tax                     (2dp)
#   4. subtotal = sum(gross)                             (2dp)
#   5. discount_amount = compute_discount(subtotal, ...) (2dp)
#   6. taxable = subtotal - discount                     (2dp)
#   7. total_tax = sum(item_taxes adjusted for discount) (2dp)
#   8. rounding = round_to_nearest(taxable + total_tax)  (2dp, ±0.99)
#   9. grand_total = taxable + total_tax + rounding      (2dp)
# =============================================================================

from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
import logging

logger = logging.getLogger("billing")

# ---------------------------------------------------------------------------
# Precision constants
# ---------------------------------------------------------------------------
MONEY_PRECISION = Decimal("0.01")
RATE_PRECISION  = Decimal("0.001")
ZERO            = Decimal("0.00")
ONE_HUNDRED     = Decimal("100")


def money(value) -> Decimal:
    """
    Convert a value to a rounded Decimal(2dp) monetary amount.

    Accepts: str, int, float, Decimal.
    Raises ValueError for values that cannot be parsed.

    Examples:
        money("250")     → Decimal("250.00")
        money(10.5)      → Decimal("10.50")
        money("0")       → Decimal("0.00")
        money("-1")      → Decimal("-1.00")   (negative allowed for rounding adj.)
    """
    try:
        d = Decimal(str(value))
        return d.quantize(MONEY_PRECISION, rounding=ROUND_HALF_UP)
    except InvalidOperation as e:
        raise ValueError(f"Cannot convert {value!r} to monetary Decimal: {e}") from e


def rate(value) -> Decimal:
    """
    Convert a value to a Decimal(3dp) rate (percentage or quantity).

    Examples:
        rate("5")     → Decimal("5.000")
        rate("12.5")  → Decimal("12.500")
        rate(0)       → Decimal("0.000")
    """
    try:
        d = Decimal(str(value))
        return d.quantize(RATE_PRECISION, rounding=ROUND_HALF_UP)
    except InvalidOperation as e:
        raise ValueError(f"Cannot convert {value!r} to rate Decimal: {e}") from e


def compute_gross(quantity: Decimal, unit_price: Decimal) -> Decimal:
    """
    Compute gross amount: quantity × unit_price, rounded to 2dp.

    Args:
        quantity:   Must be > 0 (Decimal(7,3))
        unit_price: Must be >= 0 (Decimal(12,2))

    Returns Decimal rounded to 2dp.
    """
    return money(quantity * unit_price)


def compute_tax(taxable_amount: Decimal, tax_rate_pct: Decimal) -> Decimal:
    """
    Compute tax amount: taxable_amount × tax_rate_pct / 100, rounded to 2dp.

    Args:
        taxable_amount: Must be >= 0
        tax_rate_pct:   Percentage (e.g. Decimal("5.000") for 5%)

    Returns Decimal rounded to 2dp.

    Examples:
        compute_tax(Decimal("1000.00"), Decimal("5.000"))  → Decimal("50.00")
        compute_tax(Decimal("100.00"),  Decimal("0.000"))  → Decimal("0.00")
        compute_tax(Decimal("333.33"),  Decimal("9.000"))  → Decimal("30.00")
    """
    if tax_rate_pct <= ZERO:
        return ZERO
    tax = taxable_amount * tax_rate_pct / ONE_HUNDRED
    return money(tax)


def compute_percentage_discount(subtotal: Decimal, pct: Decimal) -> Decimal:
    """
    Compute a percentage discount on subtotal.

    Args:
        subtotal: >= 0
        pct:      0 ≤ pct ≤ 100

    Returns Decimal(2dp), capped at subtotal so discount cannot exceed it.
    """
    if pct <= ZERO:
        return ZERO
    discount = subtotal * pct / ONE_HUNDRED
    discount = money(discount)
    # Cap at subtotal (safety — validators should reject > 100% before this)
    return min(discount, subtotal)


def compute_fixed_discount(subtotal: Decimal, fixed: Decimal) -> Decimal:
    """
    Return the effective fixed discount, capped at subtotal.

    Args:
        subtotal: >= 0
        fixed:    >= 0

    Returns Decimal(2dp).
    """
    if fixed <= ZERO:
        return ZERO
    fixed = money(fixed)
    # Cap at subtotal — discount can't exceed what you owe
    return min(fixed, subtotal)


def compute_rounding(pre_rounding_total: Decimal) -> Decimal:
    """
    Compute a rounding adjustment to reach the nearest whole number.

    Strategy: round to nearest integer (ROUND_HALF_UP).

    Examples:
        pre_rounding_total = 1050.30  → rounded = 1050  → adjustment = -0.30
        pre_rounding_total = 1050.60  → rounded = 1051  → adjustment = +0.40
        pre_rounding_total = 1050.00  → rounded = 1050  → adjustment =  0.00

    Rounding range: -0.49 to +0.50 (nearest-integer strategy).
    This is the standard restaurant POS rounding convention.

    Returns Decimal(2dp).  Range guaranteed: (-0.50, +0.50].
    """
    rounded = pre_rounding_total.quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    adjustment = money(Decimal(str(rounded)) - pre_rounding_total)
    return adjustment


def build_tax_breakdown(items: list[dict]) -> dict[str, str]:
    """
    Aggregate tax amounts per tax_code across all bill items.

    Args:
        items: list of dicts, each with:
            {
                "tax_code": str,       — e.g. "GST_STANDARD" or "" for zero-tax
                "tax_amount": Decimal, — computed tax for this item
            }

    Returns:
        {
            "GST_STANDARD": "50.00",
            "ZERO_TAX": "0.00",
            ...
        }
        Keys are tax codes; values are string-formatted Decimal amounts (2dp).

    Empty tax_code items are grouped under "NO_TAX".
    """
    breakdown: dict[str, Decimal] = {}
    for item in items:
        code = (item.get("tax_code") or "").strip() or "NO_TAX"
        amount = item.get("tax_amount", ZERO)
        if not isinstance(amount, Decimal):
            amount = money(amount)
        breakdown[code] = breakdown.get(code, ZERO) + amount

    # Convert to rounded strings
    return {code: str(money(amt)) for code, amt in sorted(breakdown.items())}


def format_money(value: Decimal, currency_symbol: str = "₹") -> str:
    """
    Format a Decimal monetary value as a human-readable string.

    Examples:
        format_money(Decimal("1050.00"))      → "₹1,050.00"
        format_money(Decimal("0.00"), "USD ") → "USD 0.00"
    """
    rounded = money(value)
    # Format with comma-separated thousands
    abs_val = abs(rounded)
    formatted = f"{abs_val:,.2f}"
    sign = "-" if rounded < 0 else ""
    return f"{sign}{currency_symbol}{formatted}"
