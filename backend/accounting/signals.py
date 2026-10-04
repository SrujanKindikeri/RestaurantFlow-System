# =============================================================================
# RestaurantFlow — Accounting Signals
# Phase 13
#
# These signals trigger automatic accounting posting when source transactions
# reach the correct terminal state.
#
# Design:
#   - Signals use transaction.on_commit to ensure accounting only runs AFTER
#     the source transaction commits. This prevents:
#       a) Accounting posting against an uncommitted source record.
#       b) Source-transaction rollback leaving orphaned accounting entries.
#   - Errors inside on_commit callbacks are caught and logged — a posting
#     failure must NOT block the source transaction.
#   - The idempotency check in AccountingPostingService handles retries:
#     if the signal fires multiple times for the same source, the existing
#     posting is returned rather than duplicated.
#
# Gap handling:
#   - If accounting fails (no open period, unconfigured settings, zero cost),
#     the error is logged. Future phases can add a "pending accounting" outbox
#     table for automated detection and retry.
# =============================================================================

import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db import transaction

logger = logging.getLogger("accounting")


@receiver(post_save, sender="billing.Bill")
def on_bill_finalized(sender, instance, created, **kwargs):
    """Post accounting when a Bill is finalized."""
    from billing.models import BillStatus
    if instance.status != BillStatus.FINALIZED:
        return
    if not instance.finalized_by_id:
        return

    # Capture values before on_commit closure to avoid stale state
    bill_pk = instance.pk
    user_pk = instance.finalized_by_id

    def _post():
        try:
            from billing.models import Bill
            from accounts.models import User
            from accounting.services import AccountingPostingService
            bill = Bill.objects.get(pk=bill_pk)
            user = User.objects.get(pk=user_pk)
            AccountingPostingService.post_bill(bill, user)
        except Exception as exc:
            logger.error(
                "Accounting posting failed for bill pk=%s: %s",
                bill_pk, exc, exc_info=True,
            )

    transaction.on_commit(_post)


@receiver(post_save, sender="payments.Payment")
def on_payment_completed(sender, instance, created, **kwargs):
    """Post accounting when a Payment is completed."""
    from payments.models import PaymentStatus
    if instance.status != PaymentStatus.COMPLETED:
        return
    if not instance.completed_by_id:
        return

    payment_pk = instance.pk
    user_pk = instance.completed_by_id

    def _post():
        try:
            from payments.models import Payment
            from accounts.models import User
            from accounting.services import AccountingPostingService
            payment = Payment.objects.select_related("branch").get(pk=payment_pk)
            user = User.objects.get(pk=user_pk)
            AccountingPostingService.post_payment(payment, user)
        except Exception as exc:
            logger.error(
                "Accounting posting failed for payment pk=%s: %s",
                payment_pk, exc, exc_info=True,
            )

    transaction.on_commit(_post)


@receiver(post_save, sender="payments.PaymentRefund")
def on_refund_processed(sender, instance, created, **kwargs):
    """Post accounting when a PaymentRefund is processed."""
    from payments.models import RefundStatus
    if instance.status != RefundStatus.PROCESSED:
        return
    if not instance.processed_by_id:
        return

    refund_pk = instance.pk
    user_pk = instance.processed_by_id

    def _post():
        try:
            from payments.models import PaymentRefund
            from accounts.models import User
            from accounting.services import AccountingPostingService
            refund = PaymentRefund.objects.select_related("payment__branch").get(pk=refund_pk)
            user = User.objects.get(pk=user_pk)
            AccountingPostingService.post_refund(refund, user)
        except Exception as exc:
            logger.error(
                "Accounting posting failed for refund pk=%s: %s",
                refund_pk, exc, exc_info=True,
            )

    transaction.on_commit(_post)


@receiver(post_save, sender="financials.SupplierInvoice")
def on_supplier_invoice_approved(sender, instance, created, **kwargs):
    """Post accounting when a SupplierInvoice is approved."""
    from financials.constants import SINV_APPROVED
    if instance.status != SINV_APPROVED:
        return
    if not instance.approved_by_id:
        return

    invoice_pk = instance.pk
    user_pk = instance.approved_by_id

    def _post():
        try:
            from financials.models import SupplierInvoice
            from accounts.models import User
            from accounting.services import AccountingPostingService
            invoice = SupplierInvoice.objects.get(pk=invoice_pk)
            user = User.objects.get(pk=user_pk)
            AccountingPostingService.post_supplier_invoice(invoice, user)
        except Exception as exc:
            logger.error(
                "Accounting posting failed for supplier invoice pk=%s: %s",
                invoice_pk, exc, exc_info=True,
            )

    transaction.on_commit(_post)


@receiver(post_save, sender="financials.Expense")
def on_expense_approved(sender, instance, created, **kwargs):
    """Post accounting when an Expense is approved."""
    from financials.constants import EXPENSE_APPROVED
    if instance.status != EXPENSE_APPROVED:
        return
    if not instance.approved_by_id:
        return

    expense_pk = instance.pk
    user_pk = instance.approved_by_id

    def _post():
        try:
            from financials.models import Expense
            from accounts.models import User
            from accounting.services import AccountingPostingService
            expense = Expense.objects.select_related("category").get(pk=expense_pk)
            user = User.objects.get(pk=user_pk)
            AccountingPostingService.post_expense(expense, user)
        except Exception as exc:
            logger.error(
                "Accounting posting failed for expense pk=%s: %s",
                expense_pk, exc, exc_info=True,
            )

    transaction.on_commit(_post)


@receiver(post_save, sender="recipes.ConsumptionBatch")
def on_consumption_batch_completed(sender, instance, created, **kwargs):
    """Post COGS accounting when a ConsumptionBatch is completed or reversed."""
    status = instance.status
    if status not in ("COMPLETED", "REVERSED"):
        return
    actor = instance.triggered_by
    if not actor:
        return

    batch_pk = instance.pk
    user_pk = actor.pk
    is_reversal = (status == "REVERSED")

    def _post():
        try:
            from recipes.models import ConsumptionBatch
            from accounts.models import User
            from accounting.services import AccountingPostingService
            batch = ConsumptionBatch.objects.select_related("branch").get(pk=batch_pk)
            user = User.objects.get(pk=user_pk)
            if is_reversal:
                AccountingPostingService.post_consumption_reversal(batch, user)
            else:
                AccountingPostingService.post_inventory_consumption(batch, user)
        except Exception as exc:
            logger.error(
                "Accounting COGS posting failed for batch pk=%s (reversal=%s): %s",
                batch_pk, is_reversal, exc, exc_info=True,
            )

    transaction.on_commit(_post)
