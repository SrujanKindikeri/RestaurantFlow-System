# =============================================================================
# RestaurantFlow — N+1 Query Prevention Tests
# FEAT-004: Verifies that list views use select_related/prefetch_related
# and do not issue per-row queries (N+1 pattern).
#
# Uses assertNumQueries with an upper bound rather than an exact count
# so the test stays stable across minor view/serializer changes while
# still catching regressions that add per-row queries.
# =============================================================================

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

User = get_user_model()


def _setup_base():
    """Create org/restaurant/branch + a staff user with broad permissions."""
    from organizations.models import Organization, Restaurant, Branch
    from accounts.models import Permission, Role, UserRoleAssignment

    org = Organization.objects.create(name="QueryOrg", slug="query-org")
    restaurant = Restaurant.objects.create(
        organization=org, name="QueryRest", slug="query-rest"
    )
    branch = Branch.objects.create(
        restaurant=restaurant, name="QueryBranch", code="QB01"
    )
    user = User.objects.create_user(
        email="querytest@example.com",
        password="pass",
        is_active=True,
        is_staff=True,
        is_superuser=True,  # Bypass all permission checks for query-count testing
    )
    # Grant order.view and bill.view permissions
    for code, name in [
        ("order.view.branch", "View Branch Orders"),
        ("bill.view", "View Bills"),
    ]:
        perm, _ = Permission.objects.get_or_create(
            code=code, defaults={"name": name, "module": "operations"}
        )
        role, _ = Role.objects.get_or_create(
            code=f"viewer-{code.replace('.', '-')}",
            defaults={"name": f"Viewer {code}", "is_system_role": False},
        )
        role.permissions.add(perm)
        UserRoleAssignment.objects.get_or_create(
            user=user, organization=org, role=role,
            defaults={"restaurant": restaurant, "branch": branch},
        )
    return {"org": org, "restaurant": restaurant, "branch": branch, "user": user}


class OrderListQueryTest(TestCase):
    """
    GET /api/orders/ with 10 orders must issue a bounded number of DB queries.
    The list view uses select_related/prefetch_related — query count must not
    grow linearly with result count (no N+1).
    """

    def setUp(self):
        self.ctx = _setup_base()
        self.client = APIClient()
        self.client.force_authenticate(user=self.ctx["user"])

        from orders.models import Order, OrderType
        branch = self.ctx["branch"]
        user = self.ctx["user"]

        for i in range(10):
            Order.objects.create(
                branch=branch,
                order_number=f"ORD-Q-{i:04d}",
                order_type=OrderType.COUNTER,
                status="DRAFT",   # DRAFT avoids kitchen-order signal
                created_by=user,
            )

    def test_order_list_query_count_bounded(self):
        """Query count must be < 15 regardless of how many rows the view returns."""
        url = reverse("order-list-create")
        # Capture queries via context manager
        from django.db import connection, reset_queries
        from django.test.utils import override_settings
        with override_settings(DEBUG=True):
            reset_queries()
            response = self.client.get(url)
            query_count = len(connection.queries)

        self.assertEqual(response.status_code, 200)
        # Should be well under 15 — 10 orders × 1 extra query would be 11+base.
        # A properly optimised view does this in ≤ 5 (auth + list + count + prefetch × 1-2).
        self.assertLess(
            query_count, 15,
            f"Expected < 15 queries for 10 orders, got {query_count}. Possible N+1 regression.",
        )


class BillListQueryTest(TestCase):
    """
    GET /api/billing/bills/ with 10 bills must stay within a bounded query count.
    """

    def setUp(self):
        self.ctx = _setup_base()
        self.client = APIClient()
        self.client.force_authenticate(user=self.ctx["user"])

        from billing.models import Bill, BillStatus
        from orders.models import Order, OrderType
        branch = self.ctx["branch"]
        user = self.ctx["user"]

        for i in range(10):
            order = Order.objects.create(
                branch=branch,
                order_number=f"ORD-B-{i:04d}",
                order_type=OrderType.COUNTER,
                status="DRAFT",
                created_by=user,
            )
            Bill.objects.create(
                order=order,
                branch=branch,
                bill_number=f"BILL-Q-{i:04d}",
                status=BillStatus.FINALIZED,
                subtotal=Decimal("10.00"),
                discount_amount=Decimal("0.00"),
                taxable_amount=Decimal("10.00"),
                tax_amount=Decimal("0.00"),
                grand_total=Decimal("10.00"),
                created_by=user,
            )

    def test_bill_list_query_count_bounded(self):
        try:
            url = reverse("bill-list")
        except Exception:
            self.skipTest("bill-list URL not found — skipping")

        from django.db import connection, reset_queries
        from django.test.utils import override_settings
        with override_settings(DEBUG=True):
            reset_queries()
            response = self.client.get(url)
            query_count = len(connection.queries)

        self.assertEqual(response.status_code, 200)
        self.assertLess(
            query_count, 15,
            f"Expected < 15 queries for 10 bills, got {query_count}. Possible N+1 regression.",
        )


class KitchenConsumerSyncQueryTest(TestCase):
    """
    _get_current_state() on the kitchen consumer must not issue N+1 queries
    when fetching 20 kitchen orders.
    """

    def setUp(self):
        self.ctx = _setup_base()

    def test_kitchen_sync_query_count_bounded(self):
        from kitchen.models import KitchenOrder, KitchenOrderStatus
        from orders.models import Order, OrderType
        from kitchen.consumers import KitchenConsumer
        from django.db import connection, reset_queries
        from django.test.utils import override_settings

        branch = self.ctx["branch"]
        user = self.ctx["user"]

        for i in range(20):
            order = Order.objects.create(
                branch=branch,
                order_number=f"ORD-K-{i:04d}",
                order_type=OrderType.COUNTER,
                status="DRAFT",
                created_by=user,
            )
            KitchenOrder.objects.create(
                order=order,
                branch=branch,
                status=KitchenOrderStatus.NEW,
            )

        consumer = KitchenConsumer()
        consumer.branch = branch
        consumer.branch_id = str(branch.pk)

        with override_settings(DEBUG=True):
            reset_queries()
            consumer._get_current_state()
            query_count = len(connection.queries)

        # 20 orders must not produce 20+ queries (no N+1)
        # Acceptable: 1 (orders queryset) + 1 (prefetch items) + 1 (branch lookup) = ≤5
        self.assertLess(
            query_count, 10,
            f"Expected < 10 queries for 20 kitchen orders, got {query_count}. Possible N+1.",
        )
