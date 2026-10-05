# =============================================================================
# RestaurantFlow — CRM Signal Handlers
# Phase 17
#
# Connects to Django signals from orders and billing to update CRM data.
#
# All handlers use transaction.on_commit() to ensure CRM updates only fire
# AFTER the source transaction commits. A CRM failure never rolls back a
# business transaction (payment/order/bill).
#
# Connected signals:
#   orders.Order     post_save → record visit, update stats
#   billing.Bill     post_save → award loyalty points on FINALIZED
#   payments.PaymentRefund post_save → reverse loyalty on PROCESSED refund
# =============================================================================

import logging
from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

logger = logging.getLogger("crm")


# ---------------------------------------------------------------------------
# Order signals
# ---------------------------------------------------------------------------

@receiver(post_save, sender="orders.Order")
def on_order_saved(sender, instance, created, **kwargs):
    """
    When an order is CONFIRMED and has a customer:
      - Record a CustomerVisit (idempotent)
      - Refresh customer statistics asynchronously
    """
    if instance.status != "CONFIRMED":
        return
    if not instance.customer_id:
        return

    order_pk = instance.pk

    def _update():
        try:
            from orders.models import Order
            from crm.customer_services import CustomerVisitService, CustomerStatisticsService

            order = Order.objects.select_related(
                "branch__restaurant", "customer"
            ).get(pk=order_pk)

            if not order.customer_id:
                return

            # Idempotent visit creation
            CustomerVisitService.record_visit_for_order(order)

            # Queue stats refresh via Celery (non-blocking)
            from crm.tasks import refresh_customer_statistics
            refresh_customer_statistics.delay(str(order.customer_id))

        except Exception as exc:
            logger.error(
                "crm.on_order_saved failed: order=%s error=%s", order_pk, exc
            )

    transaction.on_commit(_update)


# ---------------------------------------------------------------------------
# Bill signals
# ---------------------------------------------------------------------------

@receiver(post_save, sender="billing.Bill")
def on_bill_saved(sender, instance, created, **kwargs):
    """
    When a Bill becomes FINALIZED:
      - Award loyalty points (idempotent via reference_type=BILL)
    When a Bill becomes CANCELLED/VOID:
      - Reverse loyalty points earned for this bill
    """
    from billing.models import BillStatus

    bill_pk = instance.pk
    bill_status = instance.status

    if bill_status == BillStatus.FINALIZED:
        def _earn():
            try:
                from billing.models import Bill
                from crm.loyalty_services import LoyaltyService
                bill = Bill.objects.select_related(
                    "order__customer", "branch__restaurant"
                ).get(pk=bill_pk)
                if bill.order.customer_id:
                    LoyaltyService.earn_points_for_bill(bill)
            except Exception as exc:
                logger.error(
                    "crm.on_bill_saved EARN failed: bill=%s error=%s", bill_pk, exc
                )

        transaction.on_commit(_earn)

    elif bill_status in (BillStatus.CANCELLED, BillStatus.VOID):
        def _reverse():
            try:
                from billing.models import Bill
                from crm.loyalty_services import LoyaltyService
                bill = Bill.objects.select_related("order__customer").get(pk=bill_pk)
                LoyaltyService.reverse_points_for_bill(
                    bill, reason=f"Bill {bill.bill_number} cancelled/voided"
                )
            except Exception as exc:
                logger.error(
                    "crm.on_bill_saved REVERSE failed: bill=%s error=%s", bill_pk, exc
                )

        transaction.on_commit(_reverse)


# ---------------------------------------------------------------------------
# Payment refund signals
# ---------------------------------------------------------------------------

@receiver(post_save, sender="payments.PaymentRefund")
def on_refund_processed(sender, instance, created, **kwargs):
    """
    When a PaymentRefund is PROCESSED:
      - Reverse loyalty points earned from the associated bill if applicable.
    """
    try:
        from payments.models import RefundStatus
    except ImportError:
        RefundStatus = type("RefundStatus", (), {"PROCESSED": "PROCESSED"})

    if instance.status != RefundStatus.PROCESSED:
        return

    refund_pk = instance.pk

    def _reverse():
        try:
            from payments.models import PaymentRefund
            from crm.loyalty_services import LoyaltyService
            refund = PaymentRefund.objects.select_related(
                "payment__bill__order__customer"
            ).get(pk=refund_pk)
            bill = getattr(getattr(refund, "payment", None), "bill", None)
            if bill:
                LoyaltyService.reverse_points_for_bill(
                    bill, reason=f"Refund processed for bill {bill.bill_number}"
                )
        except Exception as exc:
            logger.error(
                "crm.on_refund_processed failed: refund=%s error=%s", refund_pk, exc
            )

    transaction.on_commit(_reverse)
