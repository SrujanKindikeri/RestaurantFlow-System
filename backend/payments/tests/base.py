# =============================================================================
# RestaurantFlow — Payment Test Base
# Phase 9
#
# Extends BillingTestBase with payment-specific permissions, roles, and
# a finalized bill fixture ready for payment tests.
#
# Fixture stack (inherits from BillingTestBase):
#   All billing fixtures +
#   Payment permissions: view, create, cancel, refund.request,
#                        refund.approve, refund.process, history.view, receipt.print
#   Roles updated: cashier_role gets payment perms, manager_role gets all,
#                  refund_approver_role gets approve+process
#   finalized_bill:  grand_total = ₹620.00
#       2× Biryani ₹250 = ₹500 + 5% GST ₹25   = ₹525
#       1× Fries   ₹120 = ₹120 + 0% GST ₹0    = ₹120
#       subtotal = ₹620, tax = ₹25,  rounding=−₹0.50 → grand_total = ₹620.00
#
# Note: grand_total may vary slightly depending on rounding — use
#       cls.bill.grand_total in assertions rather than hard-coded values.
# =============================================================================

from decimal import Decimal

from django.utils import timezone

from billing.models import BillStatus
from billing import services as billing_services
from accounts.models import Permission, Role, UserRoleAssignment, User
from payments.models import PaymentStatus, PaymentMethod, RefundStatus

# Import billing base
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from billing.tests.base import BillingTestBase


class PaymentTestBase(BillingTestBase):
    """
    Base test class providing a complete payment fixture stack.

    Adds payment permissions and roles on top of BillingTestBase.
    Also provides a pre-finalized bill ready for payment.
    """

    @classmethod
    def setUpTestData(cls):
        # Run all billing fixtures first
        super().setUpTestData()

        # -----------------------------------------------------------------
        # Payment permissions
        # -----------------------------------------------------------------
        pay_perms = [
            ("payment.view",           "View Payments",         "payment", "view"),
            ("payment.create",         "Create Payment",        "payment", "create"),
            ("payment.cancel",         "Cancel Payment",        "payment", "cancel"),
            ("payment.refund.request", "Request Refund",        "payment", "refund.request"),
            ("payment.refund.approve", "Approve Refund",        "payment", "refund.approve"),
            ("payment.refund.process", "Process Refund",        "payment", "refund.process"),
            ("payment.history.view",   "View Payment History",  "payment", "history.view"),
            ("payment.receipt.print",  "Print Receipt",         "payment", "receipt.print"),
        ]
        for code, name, module, action in pay_perms:
            p, _ = Permission.objects.get_or_create(
                code=code,
                defaults={"name": name, "module": module, "action": action},
            )
            cls.perms[code] = p

        # Give cashier_role payment perms
        cls.cashier_role.permissions.add(
            cls.perms["payment.view"],
            cls.perms["payment.create"],
            cls.perms["payment.cancel"],
            cls.perms["payment.receipt.print"],
        )

        # Give manager_role all payment perms
        cls.manager_role.permissions.add(
            *[cls.perms[c] for c in [
                "payment.view", "payment.create", "payment.cancel",
                "payment.refund.request", "payment.refund.approve",
                "payment.refund.process", "payment.history.view",
                "payment.receipt.print",
            ]]
        )

        # Give owner_role all payment perms
        cls.owner_role.permissions.add(
            *[cls.perms[c] for c in [
                "payment.view", "payment.create", "payment.cancel",
                "payment.refund.request", "payment.refund.approve",
                "payment.refund.process", "payment.history.view",
                "payment.receipt.print",
            ]]
        )

        # Dedicated refund approver user (manager role)
        cls.refund_approver = User.objects.create_user(
            email="refund_approver@test.com",
            password="pass123",
            first_name="Refund",
            last_name="Approver",
        )
        UserRoleAssignment.objects.create(
            user=cls.refund_approver,
            role=cls.manager_role,
            organization=cls.org,
            restaurant=cls.restaurant,
            branch=cls.branch,
        )

    # ------------------------------------------------------------------
    # Helper: make a finalized bill (fresh each test — not class-level)
    # ------------------------------------------------------------------
    def _make_finalized_bill(self, biryani_qty=Decimal("2.000"), fries_qty=Decimal("1.000")):
        """Create a new confirmed order and finalize its bill. Returns the bill."""
        order = self._make_confirmed_order(biryani_qty=biryani_qty, fries_qty=fries_qty)
        bill = billing_services.create_bill_from_order(order, self.cashier)
        bill = billing_services.finalize_bill(bill, self.cashier)
        return bill

    def _make_draft_bill(self):
        """Create a draft bill (not finalized)."""
        order = self._make_confirmed_order()
        return billing_services.create_bill_from_order(order, self.cashier)

    def _make_cancelled_bill(self):
        """Create and cancel a bill."""
        order = self._make_confirmed_order()
        bill = billing_services.create_bill_from_order(order, self.cashier)
        return billing_services.cancel_bill(bill, self.manager, reason="Test cancellation")
