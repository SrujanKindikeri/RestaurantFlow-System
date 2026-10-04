# =============================================================================
# RestaurantFlow — Central Control Center Alert Rules
# Phase 15
#
# This module defines:
#   - AlertDetectionService: detects conditions and creates/updates alerts
#   - EscalationEngine: evaluates escalation rules and creates issues
#   - _build_fingerprint(): deterministic fingerprint for deduplication
#
# IMPORTANT design invariants:
#   1. These services are IDEMPOTENT — safe to call multiple times.
#   2. They only READ from other apps; they never modify source records.
#   3. Alert storms are prevented via fingerprint-based deduplication.
#   4. Concurrent runs are safe via transaction.atomic() + select_for_update().
# =============================================================================

import hashlib
import logging

from django.db import transaction
from django.utils import timezone

from central_control.constants import (
    ALERT_OPEN, ALERT_ACKNOWLEDGED, ALERT_RESOLVED,
    ALERT_TYPE_KITCHEN_DELAY, ALERT_TYPE_KITCHEN_BACKLOG,
    ALERT_TYPE_LOW_STOCK, ALERT_TYPE_OUT_OF_STOCK,
    ALERT_TYPE_PAYMENT_FAILURE, ALERT_TYPE_PAYMENT_EXCEPTION,
    ALERT_TYPE_REFUND_EXCEPTION,
    ALERT_TYPE_EXPENSE_PENDING, ALERT_TYPE_PAYABLE_OVERDUE,
    ALERT_TYPE_ACCOUNTING_EXCEPTION,
    ALERT_TYPE_COUNTER_SESSION,
    SEVERITY_MEDIUM, SEVERITY_HIGH, SEVERITY_CRITICAL, SEVERITY_LOW,
    SOURCE_TYPE_KITCHEN_ORDER, SOURCE_TYPE_INVENTORY_ITEM,
    SOURCE_TYPE_PAYMENT, SOURCE_TYPE_EXPENSE, SOURCE_TYPE_PAYABLE,
    SOURCE_TYPE_JOURNAL_ENTRY, SOURCE_TYPE_COUNTER_SESSION,
)

logger = logging.getLogger("central_control")


# ---------------------------------------------------------------------------
# Fingerprint builder
# ---------------------------------------------------------------------------

def _build_fingerprint(
    alert_type: str,
    source_type: str,
    source_id: str,
    org_id,
    restaurant_id=None,
    branch_id=None,
) -> str:
    """
    Build a deterministic fingerprint string for alert deduplication.

    Two calls with the same arguments always produce the same fingerprint.
    The fingerprint is an SHA-256 hex digest of the canonical string.
    """
    parts = [
        str(alert_type),
        str(source_type),
        str(source_id),
        str(org_id),
        str(restaurant_id or ""),
        str(branch_id or ""),
    ]
    raw = "|".join(parts)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:64]


# ---------------------------------------------------------------------------
# Core alert upsert helper
# ---------------------------------------------------------------------------

def _upsert_alert(
    *,
    organization,
    restaurant,
    branch,
    alert_type: str,
    severity: str,
    title: str,
    message: str,
    source_type: str,
    source_id: str,
    now=None,
):
    """
    Create a new alert or increment the detection count of an existing active
    alert with the same fingerprint.

    Returns (alert, created: bool).
    Wrapped in transaction.atomic() by callers.
    """
    from central_control.models import CentralAlert

    if now is None:
        now = timezone.now()

    fingerprint = _build_fingerprint(
        alert_type=alert_type,
        source_type=source_type,
        source_id=str(source_id),
        org_id=organization.pk,
        restaurant_id=restaurant.pk if restaurant else None,
        branch_id=branch.pk if branch else None,
    )

    # Lock existing active alerts with this fingerprint to prevent race conditions
    existing = (
        CentralAlert.objects
        .select_for_update(skip_locked=False)
        .filter(
            organization=organization,
            fingerprint=fingerprint,
            status__in=[ALERT_OPEN, ALERT_ACKNOWLEDGED],
        )
        .first()
    )

    if existing:
        # Update detection count and last detected timestamp
        existing.detection_count += 1
        existing.last_detected_at = now
        # Escalate severity if the new detection is worse
        from central_control.constants import SEVERITY_ORDER
        if SEVERITY_ORDER.get(severity, 0) > SEVERITY_ORDER.get(existing.severity, 0):
            existing.severity = severity
        existing.save(update_fields=[
            "detection_count", "last_detected_at", "severity", "updated_at"
        ])
        return existing, False

    # Create a new alert
    alert = CentralAlert.objects.create(
        organization=organization,
        restaurant=restaurant,
        branch=branch,
        alert_type=alert_type,
        severity=severity,
        title=title,
        message=message,
        source_type=source_type,
        source_id=str(source_id),
        fingerprint=fingerprint,
        status=ALERT_OPEN,
        detected_at=now,
        last_detected_at=now,
        detection_count=1,
    )
    logger.info(
        "CentralAlert created: type=%s severity=%s org=%s restaurant=%s branch=%s",
        alert_type, severity,
        organization.pk,
        restaurant.pk if restaurant else None,
        branch.pk if branch else None,
    )
    return alert, True


def _resolve_condition_alert(*, organization, alert_type: str, source_type: str, source_id: str):
    """
    Resolve any active alert matching the given fingerprint where the
    underlying condition no longer exists (e.g. stock replenished).
    This does NOT create an audit entry — it's an automated resolution.
    """
    from central_control.models import CentralAlert

    now = timezone.now()
    fingerprint_prefix = _build_fingerprint(
        alert_type=alert_type,
        source_type=source_type,
        source_id=str(source_id),
        org_id=organization.pk,
    )
    # Resolve any matching active alerts
    updated = CentralAlert.objects.filter(
        organization=organization,
        alert_type=alert_type,
        source_type=source_type,
        source_id=str(source_id),
        status__in=[ALERT_OPEN, ALERT_ACKNOWLEDGED],
    ).update(
        status=ALERT_RESOLVED,
        resolved_at=now,
        resolution_note="Automatically resolved — condition no longer detected.",
    )
    if updated:
        logger.info(
            "Auto-resolved %d alert(s): type=%s source_id=%s",
            updated, alert_type, source_id,
        )


# ---------------------------------------------------------------------------
# AlertDetectionService
# ---------------------------------------------------------------------------

class AlertDetectionService:
    """
    Detects operational conditions and creates/updates CentralAlerts.

    All detection methods are idempotent and safe to call repeatedly.
    They read existing data from other apps — they NEVER modify source records.
    """

    def __init__(self, organization):
        self.organization = organization
        self.now = timezone.now()

    # ------------------------------------------------------------------
    # Kitchen
    # ------------------------------------------------------------------

    @transaction.atomic
    def detect_kitchen_alerts(self):
        """
        Detect KITCHEN_DELAY and KITCHEN_BACKLOG conditions.

        KITCHEN_DELAY: a KitchenOrder has been PREPARING for longer than
            the configured threshold.
        KITCHEN_BACKLOG: the total number of active (NEW/ACCEPTED/PREPARING)
            kitchen orders for a branch exceeds the configured threshold.
        """
        from organizations.models import Branch
        from kitchen.models import KitchenOrder, KitchenOrderStatus
        from central_control.models import CentralControlSettings

        # Load settings with defaults
        try:
            settings_obj = self.organization.central_control_settings
            delay_threshold_minutes = settings_obj.kitchen_delay_minutes
            backlog_threshold = settings_obj.kitchen_backlog_threshold
        except CentralControlSettings.DoesNotExist:
            from central_control.constants import (
                DEFAULT_KITCHEN_DELAY_MINUTES, DEFAULT_KITCHEN_BACKLOG_THRESHOLD
            )
            delay_threshold_minutes = DEFAULT_KITCHEN_DELAY_MINUTES
            backlog_threshold = DEFAULT_KITCHEN_BACKLOG_THRESHOLD

        from datetime import timedelta
        delay_cutoff = self.now - timedelta(minutes=delay_threshold_minutes)

        # Detect delayed individual orders
        delayed_orders = KitchenOrder.objects.filter(
            branch__restaurant__organization=self.organization,
            status=KitchenOrderStatus.PREPARING,
            started_at__lt=delay_cutoff,
        ).select_related("branch", "branch__restaurant", "order")

        delay_source_ids_seen = set()

        for ko in delayed_orders:
            source_id = str(ko.pk)
            delay_source_ids_seen.add(source_id)
            branch = ko.branch
            restaurant = branch.restaurant

            elapsed_min = int((self.now - ko.started_at).total_seconds() / 60)

            _upsert_alert(
                organization=self.organization,
                restaurant=restaurant,
                branch=branch,
                alert_type=ALERT_TYPE_KITCHEN_DELAY,
                severity=SEVERITY_HIGH if elapsed_min > delay_threshold_minutes * 2 else SEVERITY_MEDIUM,
                title=f"Kitchen delay: order {ko.order.order_number}",
                message=(
                    f"Kitchen order {ko.order.order_number} at {branch.name} has been "
                    f"in PREPARING status for {elapsed_min} minutes "
                    f"(threshold: {delay_threshold_minutes} min)."
                ),
                source_type=SOURCE_TYPE_KITCHEN_ORDER,
                source_id=source_id,
                now=self.now,
            )

        # Detect kitchen backlog per branch
        active_statuses = [
            KitchenOrderStatus.NEW,
            KitchenOrderStatus.ACCEPTED,
            KitchenOrderStatus.PREPARING,
        ]

        from django.db.models import Count
        branch_counts = (
            KitchenOrder.objects
            .filter(
                branch__restaurant__organization=self.organization,
                status__in=active_statuses,
            )
            .values("branch", "branch__restaurant")
            .annotate(active_count=Count("id"))
            .filter(active_count__gte=backlog_threshold)
        )

        for row in branch_counts:
            try:
                branch = Branch.objects.select_related("restaurant").get(pk=row["branch"])
            except Branch.DoesNotExist:
                continue

            _upsert_alert(
                organization=self.organization,
                restaurant=branch.restaurant,
                branch=branch,
                alert_type=ALERT_TYPE_KITCHEN_BACKLOG,
                severity=SEVERITY_HIGH,
                title=f"Kitchen backlog at {branch.name}",
                message=(
                    f"{branch.name} has {row['active_count']} active kitchen orders "
                    f"(threshold: {backlog_threshold})."
                ),
                source_type=SOURCE_TYPE_KITCHEN_ORDER,
                source_id=f"backlog_{branch.pk}",
                now=self.now,
            )

    # ------------------------------------------------------------------
    # Inventory
    # ------------------------------------------------------------------

    @transaction.atomic
    def detect_inventory_alerts(self):
        """
        Detect LOW_STOCK and OUT_OF_STOCK conditions.

        Reads StockBalance.available_quantity vs InventoryItem.reorder_level.
        Automatically resolves alerts when stock condition clears.
        """
        from decimal import Decimal
        from inventory.models import StockBalance, InventoryItem

        try:
            settings_obj = self.organization.central_control_settings
            low_enabled = settings_obj.low_stock_alert_enabled
            out_enabled = settings_obj.out_of_stock_alert_enabled
        except Exception:
            low_enabled = True
            out_enabled = True

        # Get all stock balances for this org (via restaurant)
        balances = (
            StockBalance.objects
            .filter(
                inventory_item__restaurant__organization=self.organization,
                inventory_item__is_active=True,
            )
            .select_related(
                "inventory_item",
                "inventory_item__restaurant",
                "storage_location",
                "storage_location__branch",
                "storage_location__branch__restaurant",
            )
        )

        # Track which items we've processed (aggregate across locations)
        # We alert per-item, not per-location, to avoid noise
        item_totals: dict = {}  # item_id → {available, reorder_level, item, restaurant}
        for sb in balances:
            item = sb.inventory_item
            iid = str(item.pk)
            if iid not in item_totals:
                item_totals[iid] = {
                    "item": item,
                    "restaurant": item.restaurant,
                    "available": Decimal("0.000"),
                    "reorder_level": item.reorder_level,
                }
            item_totals[iid]["available"] += sb.available_quantity

        for iid, data in item_totals.items():
            item = data["item"]
            restaurant = data["restaurant"]
            available = data["available"]
            reorder = data["reorder_level"]

            if available <= Decimal("0.000"):
                # Out of stock
                if out_enabled:
                    _upsert_alert(
                        organization=self.organization,
                        restaurant=restaurant,
                        branch=None,
                        alert_type=ALERT_TYPE_OUT_OF_STOCK,
                        severity=SEVERITY_CRITICAL,
                        title=f"Out of stock: {item.name}",
                        message=(
                            f"{item.name} [{item.sku}] at {restaurant.name} "
                            f"has zero available stock."
                        ),
                        source_type=SOURCE_TYPE_INVENTORY_ITEM,
                        source_id=iid,
                        now=self.now,
                    )
                # Also resolve LOW_STOCK alert if it exists (now out-of-stock supersedes it)
                _resolve_condition_alert(
                    organization=self.organization,
                    alert_type=ALERT_TYPE_LOW_STOCK,
                    source_type=SOURCE_TYPE_INVENTORY_ITEM,
                    source_id=iid,
                )
            elif available <= reorder:
                # Low stock
                if low_enabled:
                    _upsert_alert(
                        organization=self.organization,
                        restaurant=restaurant,
                        branch=None,
                        alert_type=ALERT_TYPE_LOW_STOCK,
                        severity=SEVERITY_MEDIUM,
                        title=f"Low stock: {item.name}",
                        message=(
                            f"{item.name} [{item.sku}] at {restaurant.name} has "
                            f"{available:.3f} {item.default_unit} available "
                            f"(reorder level: {reorder:.3f} {item.default_unit})."
                        ),
                        source_type=SOURCE_TYPE_INVENTORY_ITEM,
                        source_id=iid,
                        now=self.now,
                    )
                # Resolve OUT_OF_STOCK if it existed and stock came back above zero
                _resolve_condition_alert(
                    organization=self.organization,
                    alert_type=ALERT_TYPE_OUT_OF_STOCK,
                    source_type=SOURCE_TYPE_INVENTORY_ITEM,
                    source_id=iid,
                )
            else:
                # Stock is fine — resolve any existing alerts for this item
                _resolve_condition_alert(
                    organization=self.organization,
                    alert_type=ALERT_TYPE_LOW_STOCK,
                    source_type=SOURCE_TYPE_INVENTORY_ITEM,
                    source_id=iid,
                )
                _resolve_condition_alert(
                    organization=self.organization,
                    alert_type=ALERT_TYPE_OUT_OF_STOCK,
                    source_type=SOURCE_TYPE_INVENTORY_ITEM,
                    source_id=iid,
                )

    # ------------------------------------------------------------------
    # Payments
    # ------------------------------------------------------------------

    @transaction.atomic
    def detect_payment_alerts(self):
        """
        Detect PAYMENT_FAILURE conditions.

        Detects unusual failure patterns — not individual failed customer payments.
        Specifically: if the number of FAILED payments within today exceeds the
        configured threshold for a branch, create an alert.
        """
        from datetime import date
        from django.db.models import Count
        from payments.models import Payment, PaymentStatus
        from organizations.models import Branch

        try:
            settings_obj = self.organization.central_control_settings
            threshold = settings_obj.payment_failure_threshold
        except Exception:
            from central_control.constants import DEFAULT_PAYMENT_FAILURE_THRESHOLD
            threshold = DEFAULT_PAYMENT_FAILURE_THRESHOLD

        today = date.today()

        branch_failure_counts = (
            Payment.objects
            .filter(
                branch__restaurant__organization=self.organization,
                status=PaymentStatus.FAILED,
                created_at__date=today,
            )
            .values("branch")
            .annotate(failure_count=Count("id"))
            .filter(failure_count__gte=threshold)
        )

        for row in branch_failure_counts:
            try:
                branch = Branch.objects.select_related("restaurant").get(pk=row["branch"])
            except Branch.DoesNotExist:
                continue

            _upsert_alert(
                organization=self.organization,
                restaurant=branch.restaurant,
                branch=branch,
                alert_type=ALERT_TYPE_PAYMENT_FAILURE,
                severity=SEVERITY_HIGH,
                title=f"High payment failure rate at {branch.name}",
                message=(
                    f"{branch.name} has {row['failure_count']} failed payments today "
                    f"(threshold: {threshold})."
                ),
                source_type=SOURCE_TYPE_PAYMENT,
                source_id=f"failure_{branch.pk}_{today.isoformat()}",
                now=self.now,
            )

    # ------------------------------------------------------------------
    # Financial
    # ------------------------------------------------------------------

    @transaction.atomic
    def detect_financial_alerts(self):
        """
        Detect EXPENSE_PENDING and PAYABLE_OVERDUE conditions.
        """
        from decimal import Decimal
        from django.db.models import Count
        from financials.models import Expense, Payable
        from financials.constants import EXPENSE_SUBMITTED, PAYABLE_OVERDUE
        from organizations.models import Restaurant

        try:
            settings_obj = self.organization.central_control_settings
            payable_alert_enabled = settings_obj.payable_overdue_alert_enabled
        except Exception:
            payable_alert_enabled = True

        # Detect overdue payables
        if payable_alert_enabled:
            overdue_payables = (
                Payable.objects
                .filter(
                    restaurant__organization=self.organization,
                    status=PAYABLE_OVERDUE,
                )
                .select_related("restaurant", "branch")
            )
            for payable in overdue_payables:
                _upsert_alert(
                    organization=self.organization,
                    restaurant=payable.restaurant,
                    branch=payable.branch,
                    alert_type=ALERT_TYPE_PAYABLE_OVERDUE,
                    severity=SEVERITY_HIGH,
                    title=f"Overdue payable: {payable.reference_number}",
                    message=(
                        f"Payable {payable.reference_number} at {payable.restaurant.name} "
                        f"is overdue. Remaining: {payable.remaining_amount}."
                    ),
                    source_type=SOURCE_TYPE_PAYABLE,
                    source_id=str(payable.pk),
                    now=self.now,
                )

        # Detect stale SUBMITTED expenses (older than 3 days without approval)
        from datetime import timedelta
        stale_cutoff = self.now - timedelta(days=3)
        stale_expenses = (
            Expense.objects
            .filter(
                restaurant__organization=self.organization,
                status=EXPENSE_SUBMITTED,
                submitted_at__lt=stale_cutoff,
            )
            .select_related("restaurant", "branch")
        )
        for expense in stale_expenses:
            _upsert_alert(
                organization=self.organization,
                restaurant=expense.restaurant,
                branch=expense.branch,
                alert_type=ALERT_TYPE_EXPENSE_PENDING,
                severity=SEVERITY_MEDIUM,
                title=f"Stale expense pending approval: {expense.expense_number}",
                message=(
                    f"Expense {expense.expense_number} at {expense.restaurant.name} "
                    f"has been awaiting approval since "
                    f"{expense.submitted_at.strftime('%Y-%m-%d')}."
                ),
                source_type=SOURCE_TYPE_EXPENSE,
                source_id=str(expense.pk),
                now=self.now,
            )

    # ------------------------------------------------------------------
    # Counter Sessions
    # ------------------------------------------------------------------

    @transaction.atomic
    def detect_counter_alerts(self):
        """
        Detect unusually long-open counter sessions and force-closed sessions
        with unresolved cash differences.
        """
        from datetime import timedelta
        from counters.models import CounterSession, SessionStatus

        try:
            settings_obj = self.organization.central_control_settings
            max_hours = settings_obj.counter_session_max_hours
        except Exception:
            from central_control.constants import DEFAULT_COUNTER_SESSION_MAX_HOURS
            max_hours = DEFAULT_COUNTER_SESSION_MAX_HOURS

        long_open_cutoff = self.now - timedelta(hours=max_hours)

        # Long-open sessions
        long_sessions = (
            CounterSession.objects
            .filter(
                counter__branch__restaurant__organization=self.organization,
                status=SessionStatus.OPEN,
                opened_at__lt=long_open_cutoff,
            )
            .select_related(
                "counter", "counter__branch", "counter__branch__restaurant"
            )
        )
        for session in long_sessions:
            branch = session.counter.branch
            restaurant = branch.restaurant
            elapsed_h = int((self.now - session.opened_at).total_seconds() / 3600)
            _upsert_alert(
                organization=self.organization,
                restaurant=restaurant,
                branch=branch,
                alert_type=ALERT_TYPE_COUNTER_SESSION,
                severity=SEVERITY_MEDIUM,
                title=f"Long-open counter session at {branch.name}",
                message=(
                    f"Counter '{session.counter.name}' at {branch.name} "
                    f"has an OPEN session for {elapsed_h} hours "
                    f"(threshold: {max_hours} hours)."
                ),
                source_type=SOURCE_TYPE_COUNTER_SESSION,
                source_id=str(session.pk),
                now=self.now,
            )

        # Force-closed sessions with cash difference
        from decimal import Decimal
        force_closed = (
            CounterSession.objects
            .filter(
                counter__branch__restaurant__organization=self.organization,
                status=SessionStatus.FORCE_CLOSED,
                cash_difference__isnull=False,
            )
            .exclude(cash_difference=Decimal("0.00"))
            .select_related(
                "counter", "counter__branch", "counter__branch__restaurant"
            )
        )
        for session in force_closed:
            branch = session.counter.branch
            restaurant = branch.restaurant
            _upsert_alert(
                organization=self.organization,
                restaurant=restaurant,
                branch=branch,
                alert_type=ALERT_TYPE_COUNTER_SESSION,
                severity=SEVERITY_HIGH,
                title=f"Force-closed session with cash difference at {branch.name}",
                message=(
                    f"Counter '{session.counter.name}' at {branch.name} "
                    f"was force-closed with a cash difference of "
                    f"{session.cash_difference}."
                ),
                source_type=SOURCE_TYPE_COUNTER_SESSION,
                source_id=f"forceclosed_{session.pk}",
                now=self.now,
            )

    # ------------------------------------------------------------------
    # System alerts (lightweight — no heavy DB queries)
    # ------------------------------------------------------------------

    def detect_system_alerts(self):
        """
        Stub for system-level alerts (health degradation).
        These are driven by the SystemHealthService, not detected here.
        This method is intentionally minimal.
        """
        pass

    def detect_access_alerts(self):
        """
        Stub for user access alerts.
        These are event-driven (from audit logs), not polled.
        """
        pass

    # ------------------------------------------------------------------
    # Run all detections for this organization
    # ------------------------------------------------------------------

    def run_all(self):
        """Run all alert detection methods for this organization."""
        results = {}
        for method_name in [
            "detect_kitchen_alerts",
            "detect_inventory_alerts",
            "detect_payment_alerts",
            "detect_financial_alerts",
            "detect_counter_alerts",
        ]:
            try:
                getattr(self, method_name)()
                results[method_name] = "ok"
            except Exception as exc:
                logger.error(
                    "AlertDetectionService.%s failed for org=%s: %s",
                    method_name, self.organization.pk, exc,
                    exc_info=True,
                )
                results[method_name] = f"error: {exc}"
        return results


# ---------------------------------------------------------------------------
# EscalationEngine
# ---------------------------------------------------------------------------

class EscalationEngine:
    """
    Evaluates EscalationRules and creates CentralIssues for unresolved alerts.

    Run this after AlertDetectionService to close the alert→issue loop.
    """

    def __init__(self, organization):
        self.organization = organization
        self.now = timezone.now()

    @transaction.atomic
    def run(self):
        """
        Evaluate all active escalation rules for this organization.
        For each matching unresolved alert, create a CentralIssue if:
            1. The rule is active.
            2. The alert has been open longer than threshold_minutes.
            3. No existing active issue is already linked to this alert.
        """
        from central_control.models import EscalationRule, CentralAlert, CentralIssue
        from central_control.constants import (
            ISSUE_OPEN, ISSUE_SEVERITY_MEDIUM, ISSUE_SEVERITY_HIGH, ISSUE_SEVERITY_CRITICAL,
            ISSUE_CATEGORY_KITCHEN, ISSUE_CATEGORY_INVENTORY,
            ISSUE_CATEGORY_PAYMENTS, ISSUE_CATEGORY_FINANCE,
            ISSUE_CATEGORY_OPERATIONS, ALERT_ACTIVE_STATUSES,
        )
        from datetime import timedelta
        from accounts.models import Role

        try:
            settings_obj = self.organization.central_control_settings
            if not settings_obj.alert_escalation_enabled:
                return
            if not settings_obj.issue_auto_creation_enabled:
                return
        except Exception:
            pass  # Use defaults (enabled)

        rules = EscalationRule.objects.filter(
            organization=self.organization,
            is_active=True,
        ).select_related("restaurant")

        for rule in rules:
            cutoff = self.now - timedelta(minutes=rule.threshold_minutes)

            # Find qualifying alerts
            alert_qs = CentralAlert.objects.filter(
                organization=self.organization,
                alert_type=rule.alert_type,
                severity=rule.severity,
                status__in=list(ALERT_ACTIVE_STATUSES),
                detected_at__lt=cutoff,
            )
            if rule.restaurant:
                alert_qs = alert_qs.filter(restaurant=rule.restaurant)

            for alert in alert_qs:
                # Check if an issue already exists for this alert
                if alert.created_issues.filter(
                    status__in=["OPEN", "ASSIGNED", "IN_PROGRESS"]
                ).exists():
                    continue

                # Determine issue category from alert type
                category_map = {
                    ALERT_TYPE_KITCHEN_DELAY:   ISSUE_CATEGORY_KITCHEN,
                    ALERT_TYPE_KITCHEN_BACKLOG:  ISSUE_CATEGORY_KITCHEN,
                    ALERT_TYPE_LOW_STOCK:        ISSUE_CATEGORY_INVENTORY,
                    ALERT_TYPE_OUT_OF_STOCK:     ISSUE_CATEGORY_INVENTORY,
                    ALERT_TYPE_PAYMENT_FAILURE:  ISSUE_CATEGORY_PAYMENTS,
                    ALERT_TYPE_PAYMENT_EXCEPTION: ISSUE_CATEGORY_PAYMENTS,
                    ALERT_TYPE_EXPENSE_PENDING:  ISSUE_CATEGORY_FINANCE,
                    ALERT_TYPE_PAYABLE_OVERDUE:  ISSUE_CATEGORY_FINANCE,
                    ALERT_TYPE_ACCOUNTING_EXCEPTION: "ACCOUNTING",
                    ALERT_TYPE_COUNTER_SESSION:  ISSUE_CATEGORY_OPERATIONS,
                }
                category = category_map.get(alert.alert_type, ISSUE_CATEGORY_OPERATIONS)

                severity_map = {
                    "INFO":     ISSUE_SEVERITY_MEDIUM,
                    "LOW":      ISSUE_SEVERITY_MEDIUM,
                    "MEDIUM":   ISSUE_SEVERITY_MEDIUM,
                    "HIGH":     ISSUE_SEVERITY_HIGH,
                    "CRITICAL": ISSUE_SEVERITY_CRITICAL,
                }
                issue_severity = severity_map.get(alert.severity, ISSUE_SEVERITY_MEDIUM)

                # Find a system/service user to be the creator
                # Use the first superuser or fall back to the actor field being null
                from django.contrib.auth import get_user_model
                User = get_user_model()
                system_user = User.objects.filter(is_superuser=True).first()
                if system_user is None:
                    system_user = User.objects.filter(is_staff=True).first()

                if system_user is None:
                    logger.warning(
                        "EscalationEngine: no superuser found for org=%s, "
                        "skipping auto issue creation for alert=%s",
                        self.organization.pk, alert.pk,
                    )
                    continue

                issue = CentralIssue.objects.create(
                    organization=self.organization,
                    restaurant=alert.restaurant,
                    branch=alert.branch,
                    category=category,
                    title=f"[Auto-Escalated] {alert.title}",
                    description=(
                        f"This issue was automatically created by the escalation engine.\n\n"
                        f"Alert: {alert.title}\n"
                        f"Alert type: {alert.alert_type}\n"
                        f"Severity: {alert.severity}\n"
                        f"Detected at: {alert.detected_at}\n"
                        f"Message: {alert.message}"
                    ),
                    severity=issue_severity,
                    status=ISSUE_OPEN,
                    detected_from_alert=alert,
                    created_by=system_user,
                )
                logger.info(
                    "EscalationEngine: created issue=%s for alert=%s rule=%s",
                    issue.pk, alert.pk, rule.pk,
                )
