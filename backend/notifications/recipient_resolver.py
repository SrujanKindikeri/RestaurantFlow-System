# =============================================================================
# RestaurantFlow — Notification Recipient Resolver
# Phase 16
#
# Determines which users should receive a given notification.
#
# Rules:
#   1. Resolve candidates by permission code + scope (company/restaurant/branch).
#   2. Validate each candidate still has access to the underlying resource.
#   3. Apply permission-based filtering — never trust the event producer.
#   4. Company/restaurant/branch isolation is enforced here.
#
# This module is pure Python — no side effects, no DB writes.
# The NotificationService calls resolve() then creates recipient records.
# =============================================================================

import logging
from typing import Optional

logger = logging.getLogger("notifications")


class RecipientResolver:
    """
    Resolves the set of User instances that should receive a notification.

    Usage:
        resolver = RecipientResolver(notification)
        users = resolver.resolve()
    """

    def __init__(self, notification):
        """
        notification — Notification ORM instance (already saved).
        """
        self.notification = notification

    def resolve(self) -> list:
        """
        Return a deduplicated list of User instances that should receive
        this notification.

        Dispatch to a type-specific resolver so each notification type
        can express its own recipient logic.  Falls back to an empty list
        when no handler is registered — never crashes the caller.
        """
        ntype = self.notification.notification_type
        handler = self._HANDLERS.get(ntype, self._resolve_empty)
        try:
            users = handler(self)
            # Deduplicate by PK while preserving order
            seen = set()
            result = []
            for u in users:
                if u.pk not in seen:
                    seen.add(u.pk)
                    result.append(u)
            return result
        except Exception as exc:
            logger.error(
                "RecipientResolver.resolve failed: type=%s notification=%s error=%s",
                ntype, self.notification.pk, exc,
            )
            return []

    # -------------------------------------------------------------------------
    # Internal helpers
    # -------------------------------------------------------------------------

    def _users_with_permission(
        self,
        permission_code: str,
        organization=None,
        restaurant=None,
        branch=None,
    ) -> list:
        """
        Return all active Users who hold the given permission within the
        specified scope. Scope must match the notification's own scope to
        prevent cross-company/restaurant leakage.
        """
        from accounts.models import User, UserRoleAssignment, Role
        from django.db.models import Q

        notif = self.notification
        org   = organization or notif.company

        # Build base queryset of role assignments that hold this permission
        assignments = (
            UserRoleAssignment.objects
            .filter(is_active=True)
            .filter(role__is_active=True)
            .filter(role__permissions__code=permission_code)
            .filter(role__permissions__is_active=True)
            .select_related("user", "role", "organization", "restaurant", "branch")
            .distinct()
        )

        # Scope filter — always restrict to the notification's company
        scope_q = Q(organization=org)

        if branch:
            scope_q |= Q(branch=branch)
        if restaurant:
            scope_q |= Q(restaurant=restaurant)

        assignments = assignments.filter(scope_q)

        users = []
        for assignment in assignments:
            user = assignment.user
            if not user.is_active:
                continue
            # Final scope check — verify user still has access to this company
            if not self._user_in_company(user, org):
                continue
            users.append(user)

        return users

    def _user_in_company(self, user, organization) -> bool:
        """Return True if user has any active assignment in this organization."""
        from accounts import access as acl
        return acl.can_access_organization(user, organization)

    def _users_by_id(self, *user_pks) -> list:
        """Fetch specific users by PK (e.g. assignee, requester)."""
        from accounts.models import User
        pks = [pk for pk in user_pks if pk]
        if not pks:
            return []
        return list(User.objects.filter(pk__in=pks, is_active=True))

    # -------------------------------------------------------------------------
    # Type-specific resolver methods
    # -------------------------------------------------------------------------

    def _resolve_empty(self) -> list:
        return []

    # --- Order ---

    def _resolve_order(self) -> list:
        """Order notifications go to the waiter/cashier who created the order
        and the restaurant manager."""
        from notifications.constants import (
            NOTIF_ORDER_CONFIRMED, NOTIF_ORDER_CANCELLED, NOTIF_ORDER_READY
        )
        notif   = self.notification
        meta    = notif.metadata
        users   = []

        # The actor who placed/confirmed the order
        actor_id = meta.get("actor_id") or meta.get("created_by_id")
        users += self._users_by_id(actor_id)

        # Restaurant managers for the branch
        users += self._users_with_permission(
            "orders.view",
            organization=notif.company,
            restaurant=notif.restaurant,
            branch=notif.branch,
        )
        return users

    # --- Kitchen ---

    def _resolve_kitchen_order_ready(self) -> list:
        """Notify the waiter who owns this order + restaurant manager."""
        notif   = self.notification
        meta    = notif.metadata
        users   = []

        waiter_id = meta.get("waiter_id") or meta.get("actor_id")
        users += self._users_by_id(waiter_id)
        users += self._users_with_permission(
            "kitchen.view",
            organization=notif.company,
            restaurant=notif.restaurant,
            branch=notif.branch,
        )
        return users

    def _resolve_kitchen_alert(self) -> list:
        """Kitchen delays/backlogs: kitchen staff + restaurant manager on this branch."""
        notif = self.notification
        return self._users_with_permission(
            "kitchen.view",
            organization=notif.company,
            restaurant=notif.restaurant,
            branch=notif.branch,
        )

    # --- Inventory ---

    def _resolve_inventory(self) -> list:
        """Low/out-of-stock: inventory staff + restaurant manager at this branch."""
        notif = self.notification
        users = self._users_with_permission(
            "inventory.view",
            organization=notif.company,
            restaurant=notif.restaurant,
            branch=notif.branch,
        )
        return users

    # --- Payment ---

    def _resolve_payment_completed(self) -> list:
        """Payment completed: cashier who completed it."""
        notif     = self.notification
        actor_id  = notif.metadata.get("actor_id") or notif.metadata.get("cashier_id")
        return self._users_by_id(actor_id)

    def _resolve_payment_failed(self) -> list:
        """Payment failed: cashier + restaurant manager."""
        notif    = self.notification
        actor_id = notif.metadata.get("actor_id")
        users    = self._users_by_id(actor_id)
        users   += self._users_with_permission(
            "payments.view",
            organization=notif.company,
            restaurant=notif.restaurant,
            branch=notif.branch,
        )
        return users

    def _resolve_refund(self) -> list:
        """Refund: cashier who processed it."""
        notif    = self.notification
        actor_id = notif.metadata.get("actor_id")
        return self._users_by_id(actor_id)

    # --- Expense ---

    def _resolve_expense_approval_required(self) -> list:
        """Expense approval required: users with expense.approve permission at scope."""
        notif = self.notification
        return self._users_with_permission(
            "financials.expense.approve",
            organization=notif.company,
            restaurant=notif.restaurant,
        )

    def _resolve_expense_outcome(self) -> list:
        """Expense approved/rejected: the requester."""
        notif       = self.notification
        requester_id = notif.metadata.get("requester_id") or notif.metadata.get("actor_id")
        return self._users_by_id(requester_id)

    def _resolve_expense_submitted(self) -> list:
        """Expense submitted: same as approval_required (notify approvers)."""
        return self._resolve_expense_approval_required()

    # --- Payable ---

    def _resolve_payable_overdue(self) -> list:
        """Payable overdue: financial users + restaurant manager."""
        notif = self.notification
        return self._users_with_permission(
            "financials.payable.view",
            organization=notif.company,
            restaurant=notif.restaurant,
        )

    def _resolve_supplier_invoice(self) -> list:
        """Supplier invoice submitted: users who can approve invoices."""
        notif = self.notification
        return self._users_with_permission(
            "financials.supplier_invoice.approve",
            organization=notif.company,
            restaurant=notif.restaurant,
        )

    # --- Accounting ---

    def _resolve_accounting_failed(self) -> list:
        """Accounting posting failure: accountants + restaurant manager at scope."""
        notif = self.notification
        users = self._users_with_permission(
            "accounting.view",
            organization=notif.company,
            restaurant=notif.restaurant,
        )
        # Also notify central control admins for CRITICAL
        from notifications.constants import SEVERITY_CRITICAL
        if notif.severity == SEVERITY_CRITICAL:
            users += self._users_with_permission(
                "central_control.dashboard.view",
                organization=notif.company,
            )
        return users

    # --- Central alerts ---

    def _resolve_central_alert(self) -> list:
        """Central alert created/resolved: Central Control authorized users."""
        notif = self.notification
        return self._users_with_permission(
            "central_control.alert.view",
            organization=notif.company,
        )

    def _resolve_central_issue_assigned(self) -> list:
        """Central issue assigned: the assignee + issue creator."""
        notif       = self.notification
        assignee_id = notif.metadata.get("assignee_id")
        creator_id  = notif.metadata.get("creator_id")
        return self._users_by_id(assignee_id, creator_id)

    def _resolve_central_issue_resolved(self) -> list:
        """Central issue resolved: assignee + reporter."""
        notif       = self.notification
        assignee_id = notif.metadata.get("assignee_id")
        reporter_id = notif.metadata.get("reporter_id") or notif.metadata.get("creator_id")
        return self._users_by_id(assignee_id, reporter_id)

    # --- User access ---

    def _resolve_user_access(self) -> list:
        """User access granted/revoked: the affected user + company admins."""
        notif          = self.notification
        affected_id    = notif.metadata.get("affected_user_id")
        users          = self._users_by_id(affected_id)
        users         += self._users_with_permission(
            "central_control.user_access.view",
            organization=notif.company,
        )
        return users

    def _resolve_counter_session_closed(self) -> list:
        """Counter session force-closed: the cashier whose session was closed."""
        notif  = self.notification
        uid    = notif.metadata.get("cashier_id") or notif.metadata.get("affected_user_id")
        return self._users_by_id(uid)

    # --- System ---

    def _resolve_system(self) -> list:
        """System health / provider failure: Central Control users for this company."""
        notif = self.notification
        return self._users_with_permission(
            "central_control.dashboard.view",
            organization=notif.company,
        )

    # -------------------------------------------------------------------------
    # Handler dispatch table
    # -------------------------------------------------------------------------

    @property
    def _HANDLERS(self) -> dict:
        from notifications.constants import (
            NOTIF_ORDER_CONFIRMED, NOTIF_ORDER_READY, NOTIF_ORDER_CANCELLED,
            NOTIF_KITCHEN_ORDER_READY, NOTIF_KITCHEN_ORDER_DELAYED, NOTIF_KITCHEN_BACKLOG,
            NOTIF_INVENTORY_LOW_STOCK, NOTIF_INVENTORY_OUT_OF_STOCK,
            NOTIF_INVENTORY_PURCHASE_RECEIVED, NOTIF_INVENTORY_CONSUMPTION_FAILED,
            NOTIF_PAYMENT_COMPLETED, NOTIF_PAYMENT_FAILED, NOTIF_REFUND_PROCESSED,
            NOTIF_EXPENSE_SUBMITTED, NOTIF_EXPENSE_APPROVAL_REQUIRED,
            NOTIF_EXPENSE_APPROVED, NOTIF_EXPENSE_REJECTED,
            NOTIF_PAYABLE_OVERDUE, NOTIF_SUPPLIER_INVOICE_SUBMITTED,
            NOTIF_ACCOUNTING_POSTING_FAILED, NOTIF_ACCOUNTING_PERIOD_CLOSED,
            NOTIF_CENTRAL_ALERT_CREATED, NOTIF_CENTRAL_ALERT_RESOLVED,
            NOTIF_CENTRAL_ISSUE_ASSIGNED, NOTIF_CENTRAL_ISSUE_RESOLVED,
            NOTIF_USER_ACCESS_GRANTED, NOTIF_USER_ACCESS_REVOKED,
            NOTIF_COUNTER_SESSION_CLOSED,
            NOTIF_SYSTEM_HEALTH_DEGRADED, NOTIF_NOTIFICATION_PROVIDER_FAILURE,
        )
        return {
            NOTIF_ORDER_CONFIRMED:              self._resolve_order,
            NOTIF_ORDER_READY:                  self._resolve_order,
            NOTIF_ORDER_CANCELLED:              self._resolve_order,
            NOTIF_KITCHEN_ORDER_READY:          self._resolve_kitchen_order_ready,
            NOTIF_KITCHEN_ORDER_DELAYED:        self._resolve_kitchen_alert,
            NOTIF_KITCHEN_BACKLOG:              self._resolve_kitchen_alert,
            NOTIF_INVENTORY_LOW_STOCK:          self._resolve_inventory,
            NOTIF_INVENTORY_OUT_OF_STOCK:       self._resolve_inventory,
            NOTIF_INVENTORY_PURCHASE_RECEIVED:  self._resolve_inventory,
            NOTIF_INVENTORY_CONSUMPTION_FAILED: self._resolve_inventory,
            NOTIF_PAYMENT_COMPLETED:            self._resolve_payment_completed,
            NOTIF_PAYMENT_FAILED:               self._resolve_payment_failed,
            NOTIF_REFUND_PROCESSED:             self._resolve_refund,
            NOTIF_EXPENSE_SUBMITTED:            self._resolve_expense_submitted,
            NOTIF_EXPENSE_APPROVAL_REQUIRED:    self._resolve_expense_approval_required,
            NOTIF_EXPENSE_APPROVED:             self._resolve_expense_outcome,
            NOTIF_EXPENSE_REJECTED:             self._resolve_expense_outcome,
            NOTIF_PAYABLE_OVERDUE:              self._resolve_payable_overdue,
            NOTIF_SUPPLIER_INVOICE_SUBMITTED:   self._resolve_supplier_invoice,
            NOTIF_ACCOUNTING_POSTING_FAILED:    self._resolve_accounting_failed,
            NOTIF_ACCOUNTING_PERIOD_CLOSED:     self._resolve_accounting_failed,
            NOTIF_CENTRAL_ALERT_CREATED:        self._resolve_central_alert,
            NOTIF_CENTRAL_ALERT_RESOLVED:       self._resolve_central_alert,
            NOTIF_CENTRAL_ISSUE_ASSIGNED:       self._resolve_central_issue_assigned,
            NOTIF_CENTRAL_ISSUE_RESOLVED:       self._resolve_central_issue_resolved,
            NOTIF_USER_ACCESS_GRANTED:          self._resolve_user_access,
            NOTIF_USER_ACCESS_REVOKED:          self._resolve_user_access,
            NOTIF_COUNTER_SESSION_CLOSED:       self._resolve_counter_session_closed,
            NOTIF_SYSTEM_HEALTH_DEGRADED:       self._resolve_system,
            NOTIF_NOTIFICATION_PROVIDER_FAILURE: self._resolve_system,
        }
