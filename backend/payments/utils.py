# =============================================================================
# RestaurantFlow — Payment Utilities
# Phase 9
#
# Pure utility functions for the payment module.
# All monetary helpers follow the same Decimal-only discipline as billing/utils.py.
#
# Public API:
#   money(value)                     → Decimal rounded to 2dp ROUND_HALF_UP
#   compute_remaining_amount(bill)   → Decimal
#   compute_bill_payment_status(bill, total_paid) → str (BillPaymentStatus)
#   derive_payment_status_for_bill(bill) → str (BillPaymentStatus)
# =============================================================================

from decimal import Decimal, ROUND_HALF_UP


ZERO = Decimal("0.00")
TWO_PLACES = Decimal("0.01")


def money(value) -> Decimal:
    """
    Round a Decimal value to 2 decimal places using ROUND_HALF_UP.
    This is the only rounding method used for money in this module.
    Never pass float — always Decimal or str.
    """
    if not isinstance(value, Decimal):
        value = Decimal(str(value))
    return value.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


def compute_successful_payments_total(bill) -> Decimal:
    """
    Return the sum of all COMPLETED payment amounts for a bill.

    Uses a database aggregation — not Python sum — for correctness
    under concurrent load.
    """
    from django.db.models import Sum
    from payments.models import Payment, PaymentStatus

    result = Payment.objects.filter(
        bill=bill,
        status=PaymentStatus.COMPLETED,
    ).aggregate(total=Sum("amount"))

    return money(result["total"] or ZERO)


def compute_remaining_amount(bill) -> Decimal:
    """
    Return the remaining payable amount for a bill.

    remaining = bill.grand_total - sum(COMPLETED payments)
    Never negative — clamped to 0.
    """
    total_paid = compute_successful_payments_total(bill)
    remaining = money(bill.grand_total) - total_paid
    return max(remaining, ZERO)


def compute_bill_payment_status(grand_total: Decimal, total_paid: Decimal) -> str:
    """
    Derive the bill payment status from the grand total and total paid.

    Returns a BillPaymentStatus string.

    Rules:
        total_paid == 0            → UNPAID
        0 < total_paid < total     → PARTIALLY_PAID
        total_paid == total        → PAID
        total_paid > total         → OVERPAID  (should not occur — guarded)
    """
    from payments.models import BillPaymentStatus

    if total_paid <= ZERO:
        return BillPaymentStatus.UNPAID

    diff = money(total_paid - grand_total)

    if diff < ZERO:
        return BillPaymentStatus.PARTIALLY_PAID
    elif diff == ZERO:
        return BillPaymentStatus.PAID
    else:
        return BillPaymentStatus.OVERPAID


def derive_payment_status_for_bill(bill) -> str:
    """
    Compute the live bill payment status from DB aggregation.
    Use this when you need the authoritative payment status for a bill.
    """
    total_paid = compute_successful_payments_total(bill)
    return compute_bill_payment_status(money(bill.grand_total), total_paid)


def compute_refund_summary_for_payment(payment) -> dict:
    """
    Return a summary of refunds for a given payment.

    Returns:
    {
        "total_refunded":    Decimal,
        "refundable_amount": Decimal,
        "refund_count":      int,
    }
    """
    from django.db.models import Sum, Count
    from payments.models import RefundStatus

    agg = payment.refunds.filter(status=RefundStatus.PROCESSED).aggregate(
        total=Sum("amount"),
        count=Count("id"),
    )
    total_refunded = money(agg["total"] or ZERO)
    refundable = money(payment.amount - total_refunded)
    return {
        "total_refunded":    total_refunded,
        "refundable_amount": max(refundable, ZERO),
        "refund_count":      agg["count"] or 0,
    }
