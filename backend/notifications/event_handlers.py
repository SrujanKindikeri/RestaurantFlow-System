# =============================================================================
# RestaurantFlow — Notification Event Handlers
# Phase 16
#
# Connects to existing Django signals from all business apps.
# All handlers use transaction.on_commit() to ensure notifications are only
# dispatched AFTER the source transaction has committed.
#
# Design principles:
#   - Handlers are lightweight dispatchers — no business logic here.
#   - All errors are caught and logged; a handler failure NEVER propagates
#     to the triggering business transaction.
#   - Idempotency is enforced in NotificationService.create_notification().
#   - Company/restaurant/branch scope is resolved server-side, never trusted
#     from the event payload.
#
# Apps wired up:
#   payments   — Payment completed/failed, PaymentRefund processed
#   billing    — Bill finalized (order ready)
#   kitchen    — KitchenOrder status changes (delayed, backlog)
#   inventory  — StockBalance changes (low stock, out of stock)
#   financials — Expense lifecycle, Payable overdue, SupplierInvoice
#   accounting — Posting failures
#   central_control — Alert created/resolved, Issue assigned/resolved
# =============================================================================

import logging
from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

logger = logging.getLogger("notifications")


# ---------------------------------------------------------------------------
# Helper — safely get organization from a model that may have restaurant/branch
# ---------------------------------------------------------------------------

def _safe_get_company(instance):
    """Return the Organization for a model instance via restaurant or direct FK."""
    try:
        if hasattr(instance, "organization"):
            return instance.organization
        if hasattr(instance, "restaurant"):
            return instance.restaurant.organization
        if hasattr(instance, "branch"):
            return instance.branch.restaurant.organization
        return None
    except Exception:
        return None


# ===========================================================================
# PAYMENTS — Payment completed / failed / refund
# ===========================================================================

@receiver(post_save, sender="payments.Payment")
def on_payment_status_change(sender, instance, created, **kwargs):
    from payments.models import PaymentStatus

    if instance.status == PaymentStatus.COMPLETED:
        _dispatch_payment_completed(instance)
    elif instance.status == PaymentStatus.FAILED:
        _dispatch_payment_failed(instance)


def _dispatch_payment_completed(payment):
    payment_pk = payment.pk

    def _notify():
        try:
            from payments.models import Payment
            from notifications.services import create_and_dispatch
            from notifications.constants import (
                NOTIF_PAYMENT_COMPLETED, SEVERITY_LOW, SOURCE_PAYMENT
            )
            p = Payment.objects.select_related(
                "branch", "branch__restaurant", "branch__restaurant__organization"
            ).get(pk=payment_pk)
            company    = p.branch.restaurant.organization
            restaurant = p.branch.restaurant
            branch     = p.branch
            create_and_dispatch(
                company=company,
                notification_type=NOTIF_PAYMENT_COMPLETED,
                severity=SEVERITY_LOW,
                title="Payment Completed",
                message=f"Payment of {p.amount} has been completed.",
                source_type=SOURCE_PAYMENT,
                source_id=str(p.pk),
                restaurant=restaurant,
                branch=branch,
                metadata={
                    "payment_amount": str(p.amount),
                    "actor_id": str(p.completed_by_id) if p.completed_by_id else "",
                    "cashier_id": str(p.completed_by_id) if p.completed_by_id else "",
                },
            )
        except Exception as exc:
            logger.error("_dispatch_payment_completed failed: payment=%s error=%s", payment_pk, exc)

    transaction.on_commit(_notify)


def _dispatch_payment_failed(payment):
    payment_pk = payment.pk

    def _notify():
        try:
            from payments.models import Payment
            from notifications.services import create_and_dispatch
            from notifications.constants import (
                NOTIF_PAYMENT_FAILED, SEVERITY_HIGH, SOURCE_PAYMENT
            )
            p = Payment.objects.select_related(
                "branch", "branch__restaurant", "branch__restaurant__organization"
            ).get(pk=payment_pk)
            company    = p.branch.restaurant.organization
            restaurant = p.branch.restaurant
            branch     = p.branch
            create_and_dispatch(
                company=company,
                notification_type=NOTIF_PAYMENT_FAILED,
                severity=SEVERITY_HIGH,
                title="Payment Failed",
                message=f"Payment of {p.amount} failed.",
                source_type=SOURCE_PAYMENT,
                source_id=str(p.pk),
                restaurant=restaurant,
                branch=branch,
                metadata={
                    "payment_amount": str(p.amount),
                    "actor_id": str(p.completed_by_id) if p.completed_by_id else "",
                },
            )
        except Exception as exc:
            logger.error("_dispatch_payment_failed failed: payment=%s error=%s", payment_pk, exc)

    transaction.on_commit(_notify)


@receiver(post_save, sender="payments.PaymentRefund")
def on_refund_status_change(sender, instance, created, **kwargs):
    from payments.models import RefundStatus

    if instance.status == RefundStatus.PROCESSED:
        refund_pk = instance.pk

        def _notify():
            try:
                from payments.models import PaymentRefund
                from notifications.services import create_and_dispatch
                from notifications.constants import (
                    NOTIF_REFUND_PROCESSED, SEVERITY_MEDIUM, SOURCE_REFUND
                )
                r = PaymentRefund.objects.select_related(
                    "payment__branch__restaurant__organization"
                ).get(pk=refund_pk)
                company    = r.payment.branch.restaurant.organization
                restaurant = r.payment.branch.restaurant
                branch     = r.payment.branch
                create_and_dispatch(
                    company=company,
                    notification_type=NOTIF_REFUND_PROCESSED,
                    severity=SEVERITY_MEDIUM,
                    title="Refund Processed",
                    message=f"Refund of {r.amount} has been processed.",
                    source_type=SOURCE_REFUND,
                    source_id=str(r.pk),
                    restaurant=restaurant,
                    branch=branch,
                    metadata={
                        "refund_amount": str(r.amount),
                        "actor_id": str(r.processed_by_id) if r.processed_by_id else "",
                    },
                )
            except Exception as exc:
                logger.error("on_refund_status_change._notify failed: refund=%s error=%s", refund_pk, exc)

        transaction.on_commit(_notify)


# ===========================================================================
# FINANCIALS — Expense lifecycle
# ===========================================================================

@receiver(post_save, sender="financials.Expense")
def on_expense_status_change(sender, instance, created, **kwargs):
    expense_pk = instance.pk
    status     = instance.status

    try:
        from financials.constants import (
            EXPENSE_SUBMITTED, EXPENSE_APPROVED, EXPENSE_REJECTED
        )
    except ImportError:
        # Fall back to string constants if financials.constants unavailable
        EXPENSE_SUBMITTED = "SUBMITTED"
        EXPENSE_APPROVED  = "APPROVED"
        EXPENSE_REJECTED  = "REJECTED"

    if status == EXPENSE_SUBMITTED:
        _dispatch_expense_submitted(expense_pk)
    elif status == EXPENSE_APPROVED:
        _dispatch_expense_outcome(expense_pk, approved=True)
    elif status == EXPENSE_REJECTED:
        _dispatch_expense_outcome(expense_pk, approved=False)


def _dispatch_expense_submitted(expense_pk):
    def _notify():
        try:
            from financials.models import Expense
            from notifications.services import create_and_dispatch
            from notifications.constants import (
                NOTIF_EXPENSE_SUBMITTED, NOTIF_EXPENSE_APPROVAL_REQUIRED,
                SEVERITY_MEDIUM, SOURCE_EXPENSE
            )
            e = Expense.objects.select_related(
                "restaurant__organization", "created_by"
            ).get(pk=expense_pk)
            company    = e.restaurant.organization
            restaurant = e.restaurant
            create_and_dispatch(
                company=company,
                notification_type=NOTIF_EXPENSE_APPROVAL_REQUIRED,
                severity=SEVERITY_MEDIUM,
                title="Expense Approval Required",
                message=f"Expense {getattr(e, 'expense_number', str(e.pk))} requires approval.",
                source_type=SOURCE_EXPENSE,
                source_id=str(e.pk),
                restaurant=restaurant,
                metadata={
                    "expense_number": getattr(e, "expense_number", str(e.pk)),
                    "requester_id":   str(e.created_by_id) if e.created_by_id else "",
                    "action_url":     f"/financials/expenses/{e.pk}/",
                },
            )
        except Exception as exc:
            logger.error("_dispatch_expense_submitted failed: expense=%s error=%s", expense_pk, exc)

    transaction.on_commit(_notify)


def _dispatch_expense_outcome(expense_pk, approved: bool):
    def _notify():
        try:
            from financials.models import Expense
            from notifications.services import create_and_dispatch
            from notifications.constants import (
                NOTIF_EXPENSE_APPROVED, NOTIF_EXPENSE_REJECTED,
                SEVERITY_MEDIUM, SEVERITY_HIGH, SOURCE_EXPENSE
            )
            e = Expense.objects.select_related(
                "restaurant__organization", "created_by"
            ).get(pk=expense_pk)
            company    = e.restaurant.organization
            restaurant = e.restaurant
            notif_type = NOTIF_EXPENSE_APPROVED if approved else NOTIF_EXPENSE_REJECTED
            severity   = SEVERITY_MEDIUM if approved else SEVERITY_HIGH
            status_str = "approved" if approved else "rejected"
            create_and_dispatch(
                company=company,
                notification_type=notif_type,
                severity=severity,
                title=f"Expense {status_str.capitalize()}",
                message=f"Your expense {getattr(e, 'expense_number', str(e.pk))} has been {status_str}.",
                source_type=SOURCE_EXPENSE,
                source_id=str(e.pk),
                restaurant=restaurant,
                metadata={
                    "expense_number": getattr(e, "expense_number", str(e.pk)),
                    "requester_id":   str(e.created_by_id) if e.created_by_id else "",
                },
            )
        except Exception as exc:
            logger.error("_dispatch_expense_outcome failed: expense=%s error=%s", expense_pk, exc)

    transaction.on_commit(_notify)


# ===========================================================================
# FINANCIALS — Payable overdue (polled by Celery beat, also signal-driven)
# ===========================================================================

def dispatch_payable_overdue_notification(payable):
    """Called from a Celery beat task or alert detector when payable is overdue."""
    try:
        from notifications.services import create_and_dispatch
        from notifications.constants import (
            NOTIF_PAYABLE_OVERDUE, SEVERITY_HIGH, SOURCE_PAYABLE
        )
        restaurant = getattr(payable, "restaurant", None) or \
                     getattr(getattr(payable, "supplier_invoice", None), "restaurant", None)
        company    = restaurant.organization if restaurant else None
        if not company:
            return
        create_and_dispatch(
            company=company,
            notification_type=NOTIF_PAYABLE_OVERDUE,
            severity=SEVERITY_HIGH,
            title="Payable Overdue",
            message=f"Payable of {payable.amount} is overdue (due {payable.due_date}).",
            source_type=SOURCE_PAYABLE,
            source_id=str(payable.pk),
            restaurant=restaurant,
            metadata={
                "payable_amount":   str(payable.amount),
                "payable_due_date": str(payable.due_date),
            },
        )
    except Exception as exc:
        logger.error("dispatch_payable_overdue_notification failed: payable=%s error=%s",
                     getattr(payable, "pk", "?"), exc)


# ===========================================================================
# ACCOUNTING — Posting failure
# ===========================================================================

def dispatch_accounting_posting_failed_notification(
    company, restaurant, source_type: str, source_id: str, error_message: str
):
    """
    Called from accounting/signals.py error handlers when posting fails.
    Must be called OUTSIDE any active transaction (after the source transaction
    already committed or rolled back).
    """
    try:
        from notifications.services import create_and_dispatch
        from notifications.constants import (
            NOTIF_ACCOUNTING_POSTING_FAILED, SEVERITY_HIGH, SOURCE_ACCOUNTING_POSTING
        )
        create_and_dispatch(
            company=company,
            notification_type=NOTIF_ACCOUNTING_POSTING_FAILED,
            severity=SEVERITY_HIGH,
            title="Accounting Posting Failed",
            message=f"Accounting posting failed for {source_type} {source_id}: {error_message[:200]}",
            source_type=SOURCE_ACCOUNTING_POSTING,
            source_id=source_id,
            restaurant=restaurant,
            metadata={
                "failed_source_type": source_type,
                "failed_source_id":   source_id,
                "failure_reason":     error_message[:500],
            },
            bypass_cooldown=True,
        )
    except Exception as exc:
        logger.error(
            "dispatch_accounting_posting_failed_notification failed: "
            "source=%s/%s error=%s", source_type, source_id, exc,
        )


# ===========================================================================
# CENTRAL CONTROL — Alert and Issue signals
# ===========================================================================

@receiver(post_save, sender="central_control.CentralAlert")
def on_central_alert_saved(sender, instance, created, **kwargs):
    """Create notification when a new CentralAlert is opened."""
    if not created:
        return

    alert_pk = instance.pk

    def _notify():
        try:
            from central_control.models import CentralAlert
            from notifications.services import create_and_dispatch
            from notifications.constants import (
                NOTIF_CENTRAL_ALERT_CREATED, SOURCE_CENTRAL_ALERT
            )
            from central_control.constants import (
                SEVERITY_CRITICAL as CC_CRITICAL,
                SEVERITY_HIGH as CC_HIGH,
                SEVERITY_MEDIUM as CC_MEDIUM,
                SEVERITY_LOW as CC_LOW,
            )
            from notifications.constants import (
                SEVERITY_CRITICAL, SEVERITY_HIGH, SEVERITY_MEDIUM, SEVERITY_LOW, SEVERITY_INFO
            )

            severity_map = {
                CC_CRITICAL: SEVERITY_CRITICAL,
                CC_HIGH:     SEVERITY_HIGH,
                CC_MEDIUM:   SEVERITY_MEDIUM,
                CC_LOW:      SEVERITY_LOW,
            }

            alert = CentralAlert.objects.select_related(
                "organization", "restaurant", "branch"
            ).get(pk=alert_pk)

            severity = severity_map.get(alert.severity, SEVERITY_MEDIUM)
            create_and_dispatch(
                company=alert.organization,
                notification_type=NOTIF_CENTRAL_ALERT_CREATED,
                severity=severity,
                title=alert.title,
                message=getattr(alert, "description", alert.title),
                source_type=SOURCE_CENTRAL_ALERT,
                source_id=str(alert.pk),
                restaurant=alert.restaurant,
                branch=alert.branch,
                metadata={
                    "alert_type":  alert.alert_type,
                    "alert_title": alert.title,
                    "action_url":  f"/central-control/alerts/{alert.pk}/",
                },
                bypass_cooldown=True,
            )
        except Exception as exc:
            logger.error(
                "on_central_alert_saved._notify failed: alert=%s error=%s",
                alert_pk, exc,
            )

    transaction.on_commit(_notify)


@receiver(post_save, sender="central_control.CentralIssue")
def on_central_issue_saved(sender, instance, created, **kwargs):
    """Create notification when a CentralIssue is assigned or resolved."""
    issue_pk    = instance.pk
    issue_status = instance.status

    try:
        from central_control.constants import ISSUE_ASSIGNED, ISSUE_RESOLVED
    except ImportError:
        ISSUE_ASSIGNED = "ASSIGNED"
        ISSUE_RESOLVED = "RESOLVED"

    if issue_status == ISSUE_ASSIGNED:
        _dispatch_issue_assigned(issue_pk, instance)
    elif issue_status == ISSUE_RESOLVED:
        _dispatch_issue_resolved(issue_pk, instance)


def _dispatch_issue_assigned(issue_pk, instance):
    assignee_id = getattr(instance, "assignee_id", None)

    def _notify():
        try:
            from central_control.models import CentralIssue
            from notifications.services import create_and_dispatch
            from notifications.constants import (
                NOTIF_CENTRAL_ISSUE_ASSIGNED, SEVERITY_HIGH, SOURCE_CENTRAL_ISSUE
            )
            issue = CentralIssue.objects.select_related(
                "organization", "restaurant", "assignee"
            ).get(pk=issue_pk)
            create_and_dispatch(
                company=issue.organization,
                notification_type=NOTIF_CENTRAL_ISSUE_ASSIGNED,
                severity=SEVERITY_HIGH,
                title="Central Issue Assigned to You",
                message=f"Issue '{issue.title}' has been assigned to you.",
                source_type=SOURCE_CENTRAL_ISSUE,
                source_id=str(issue.pk),
                restaurant=issue.restaurant,
                metadata={
                    "issue_title": issue.title,
                    "assignee_id": str(issue.assignee_id) if issue.assignee_id else "",
                    "creator_id":  str(issue.created_by_id) if hasattr(issue, "created_by_id") else "",
                    "action_url":  f"/central-control/issues/{issue.pk}/",
                },
                bypass_cooldown=True,
            )
        except Exception as exc:
            logger.error(
                "_dispatch_issue_assigned._notify failed: issue=%s error=%s",
                issue_pk, exc,
            )

    transaction.on_commit(_notify)


def _dispatch_issue_resolved(issue_pk, instance):
    def _notify():
        try:
            from central_control.models import CentralIssue
            from notifications.services import create_and_dispatch
            from notifications.constants import (
                NOTIF_CENTRAL_ISSUE_RESOLVED, SEVERITY_MEDIUM, SOURCE_CENTRAL_ISSUE
            )
            issue = CentralIssue.objects.select_related(
                "organization", "restaurant", "assignee"
            ).get(pk=issue_pk)
            create_and_dispatch(
                company=issue.organization,
                notification_type=NOTIF_CENTRAL_ISSUE_RESOLVED,
                severity=SEVERITY_MEDIUM,
                title="Central Issue Resolved",
                message=f"Issue '{issue.title}' has been resolved.",
                source_type=SOURCE_CENTRAL_ISSUE,
                source_id=str(issue.pk),
                restaurant=issue.restaurant,
                metadata={
                    "issue_title":  issue.title,
                    "assignee_id":  str(issue.assignee_id) if issue.assignee_id else "",
                    "reporter_id":  str(issue.created_by_id) if hasattr(issue, "created_by_id") else "",
                },
            )
        except Exception as exc:
            logger.error(
                "_dispatch_issue_resolved._notify failed: issue=%s error=%s",
                issue_pk, exc,
            )

    transaction.on_commit(_notify)


# ===========================================================================
# INVENTORY — Low stock / out of stock (StockBalance post_save)
# ===========================================================================

@receiver(post_save, sender="inventory.StockBalance")
def on_stock_balance_saved(sender, instance, created, **kwargs):
    """
    Detect low-stock and out-of-stock events from StockBalance changes.

    StockBalance.get_stock_status() returns:
        "IN_STOCK" | "LOW_STOCK" | "OUT_OF_STOCK"
    """
    stock_balance_pk = instance.pk

    def _notify():
        try:
            from inventory.models import StockBalance
            from notifications.services import create_and_dispatch
            from notifications.constants import (
                NOTIF_INVENTORY_LOW_STOCK, NOTIF_INVENTORY_OUT_OF_STOCK,
                SEVERITY_MEDIUM, SEVERITY_HIGH, SEVERITY_CRITICAL,
                SOURCE_STOCK_BALANCE
            )
            sb = StockBalance.objects.select_related(
                "item", "branch", "branch__restaurant", "branch__restaurant__organization"
            ).get(pk=stock_balance_pk)

            status_method = getattr(sb, "get_stock_status", None)
            if not status_method:
                return

            stock_status = status_method()
            if stock_status == "OUT_OF_STOCK":
                create_and_dispatch(
                    company=sb.branch.restaurant.organization,
                    notification_type=NOTIF_INVENTORY_OUT_OF_STOCK,
                    severity=SEVERITY_CRITICAL,
                    title=f"{sb.item.name} Out of Stock",
                    message=f"{sb.item.name} is out of stock at {sb.branch.name}.",
                    source_type=SOURCE_STOCK_BALANCE,
                    source_id=str(sb.pk),
                    restaurant=sb.branch.restaurant,
                    branch=sb.branch,
                    metadata={
                        "item_name":   sb.item.name,
                        "branch_name": sb.branch.name,
                        "quantity":    str(sb.available_quantity),
                    },
                    bypass_cooldown=True,
                )
            elif stock_status == "LOW_STOCK":
                create_and_dispatch(
                    company=sb.branch.restaurant.organization,
                    notification_type=NOTIF_INVENTORY_LOW_STOCK,
                    severity=SEVERITY_MEDIUM,
                    title=f"{sb.item.name} Low Stock",
                    message=(
                        f"{sb.item.name} is below reorder level at {sb.branch.name}. "
                        f"Available: {sb.available_quantity}."
                    ),
                    source_type=SOURCE_STOCK_BALANCE,
                    source_id=str(sb.pk),
                    restaurant=sb.branch.restaurant,
                    branch=sb.branch,
                    metadata={
                        "item_name":   sb.item.name,
                        "branch_name": sb.branch.name,
                        "quantity":    str(sb.available_quantity),
                    },
                )
        except Exception as exc:
            logger.error(
                "on_stock_balance_saved._notify failed: stock_balance=%s error=%s",
                stock_balance_pk, exc,
            )

    transaction.on_commit(_notify)


# ===========================================================================
# KITCHEN — Order ready / delayed (driven by KitchenOrder post_save)
# ===========================================================================

@receiver(post_save, sender="kitchen.KitchenOrder")
def on_kitchen_order_status_change(sender, instance, created, **kwargs):
    """Trigger notifications for kitchen order status transitions."""
    ko_pk   = instance.pk
    status  = instance.status

    try:
        from kitchen.models import KitchenOrderStatus
        READY   = KitchenOrderStatus.READY
        DELAYED = getattr(KitchenOrderStatus, "DELAYED", "DELAYED")
    except (ImportError, AttributeError):
        READY   = "READY"
        DELAYED = "DELAYED"

    if status == READY:
        _dispatch_kitchen_order_ready(ko_pk)
    elif status == DELAYED:
        _dispatch_kitchen_order_delayed(ko_pk)


def _dispatch_kitchen_order_ready(ko_pk):
    def _notify():
        try:
            from kitchen.models import KitchenOrder
            from notifications.services import create_and_dispatch
            from notifications.constants import (
                NOTIF_KITCHEN_ORDER_READY, SEVERITY_MEDIUM, SOURCE_KITCHEN_ORDER
            )
            ko = KitchenOrder.objects.select_related(
                "order", "order__branch", "order__branch__restaurant",
                "order__branch__restaurant__organization",
            ).get(pk=ko_pk)
            branch     = ko.order.branch
            restaurant = branch.restaurant
            company    = restaurant.organization
            order_num  = getattr(ko.order, "order_number", str(ko.order_id))
            create_and_dispatch(
                company=company,
                notification_type=NOTIF_KITCHEN_ORDER_READY,
                severity=SEVERITY_MEDIUM,
                title=f"Order {order_num} is Ready",
                message=f"Kitchen order for {order_num} is ready for service.",
                source_type=SOURCE_KITCHEN_ORDER,
                source_id=str(ko.pk),
                restaurant=restaurant,
                branch=branch,
                metadata={
                    "order_number":        order_num,
                    "kitchen_order_number": str(ko.pk),
                    "waiter_id":           str(ko.order.created_by_id) if hasattr(ko.order, "created_by_id") else "",
                },
            )
        except Exception as exc:
            logger.error("_dispatch_kitchen_order_ready failed: ko=%s error=%s", ko_pk, exc)

    transaction.on_commit(_notify)


def _dispatch_kitchen_order_delayed(ko_pk):
    def _notify():
        try:
            from kitchen.models import KitchenOrder
            from notifications.services import create_and_dispatch
            from notifications.constants import (
                NOTIF_KITCHEN_ORDER_DELAYED, SEVERITY_HIGH, SOURCE_KITCHEN_ORDER
            )
            ko = KitchenOrder.objects.select_related(
                "order__branch__restaurant__organization"
            ).get(pk=ko_pk)
            branch     = ko.order.branch
            restaurant = branch.restaurant
            company    = restaurant.organization
            order_num  = getattr(ko.order, "order_number", str(ko.order_id))
            delay_mins = int(ko.age_seconds() / 60) if hasattr(ko, "age_seconds") else 0
            create_and_dispatch(
                company=company,
                notification_type=NOTIF_KITCHEN_ORDER_DELAYED,
                severity=SEVERITY_HIGH,
                title=f"Kitchen Delay: Order {order_num}",
                message=f"Order {order_num} has been in the kitchen for {delay_mins} minutes.",
                source_type=SOURCE_KITCHEN_ORDER,
                source_id=str(ko.pk),
                restaurant=restaurant,
                branch=branch,
                metadata={
                    "order_number":  order_num,
                    "delay_minutes": str(delay_mins),
                    "branch_name":   branch.name,
                },
            )
        except Exception as exc:
            logger.error("_dispatch_kitchen_order_delayed failed: ko=%s error=%s", ko_pk, exc)

    transaction.on_commit(_notify)
