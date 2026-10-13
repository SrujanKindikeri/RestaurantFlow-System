# =============================================================================
# RestaurantFlow — Table Operations Tests
# Phase 19: Advanced POS & Restaurant Operations
# =============================================================================

from decimal import Decimal

from django.test import TestCase

from operations.tests.base import OperationsTestBase
from operations.table_services import (
    get_table_operational_status, set_table_operational_status,
    request_table_transfer, complete_table_transfer,
    request_table_merge, close_table,
)
from operations.exceptions import TableTransferConflict, TableNotAvailable, TableMergeConflict
from operations.constants import TABLE_OP_AVAILABLE, TABLE_OP_OCCUPIED, TABLE_OP_CLEANING
from orders.models import OrderType


class TableOperationalStatusTest(OperationsTestBase):
    """Tests for table operational status management."""

    def test_get_or_create_status(self):
        """get_table_operational_status creates a default AVAILABLE record."""
        status_obj = get_table_operational_status(self.table_a)
        self.assertEqual(status_obj.status, TABLE_OP_AVAILABLE)
        self.assertEqual(status_obj.table, self.table_a)

    def test_get_existing_status(self):
        """Calling twice returns the same record."""
        s1 = get_table_operational_status(self.table_a)
        s2 = get_table_operational_status(self.table_a)
        self.assertEqual(s1.id, s2.id)

    def test_set_table_status_occupied(self):
        status_obj = set_table_operational_status(
            table=self.table_a, new_status=TABLE_OP_OCCUPIED,
            user=self.manager, notes="Guests seated",
        )
        self.assertEqual(status_obj.status, TABLE_OP_OCCUPIED)
        self.assertEqual(status_obj.updated_by, self.manager)
        self.assertEqual(status_obj.notes, "Guests seated")

    def test_set_status_creates_audit(self):
        from operations.models import OperationsAuditLog
        from operations.constants import AUDIT_TABLE_OP_STATUS_CHANGED

        set_table_operational_status(
            table=self.table_b, new_status=TABLE_OP_CLEANING,
            user=self.manager,
        )
        self.assertTrue(
            OperationsAuditLog.objects.filter(
                event_type=AUDIT_TABLE_OP_STATUS_CHANGED,
                table_id=self.table_b.id,
            ).exists()
        )

    def test_signal_creates_operational_status_on_table_creation(self):
        """Signal auto-creates TableOperationalStatus when DiningTable is created."""
        from orders.models import DiningTable
        from operations.models import TableOperationalStatus

        new_table = DiningTable.objects.create(
            branch=self.branch, table_number="T99", capacity=2,
        )
        self.assertTrue(
            TableOperationalStatus.objects.filter(table=new_table).exists()
        )


class TableTransferTest(OperationsTestBase):
    """Tests for table transfer workflow."""

    def _setup_dine_in_order(self):
        """Create a DINE_IN order at table_a with an open TableSession."""
        from orders.models import TableSession
        session = TableSession.objects.create(
            table=self.table_a, opened_by=self.cashier, guest_count=2,
        )
        order = self._make_order(
            order_type=OrderType.DINE_IN, table=self.table_a, counter=None,
        )
        order.table_session = session
        order.save(update_fields=["table_session"])
        # Set table_a to OCCUPIED
        set_table_operational_status(
            table=self.table_a, new_status=TABLE_OP_OCCUPIED, user=self.cashier,
        )
        return order, session

    def test_request_table_transfer_success(self):
        order, _ = self._setup_dine_in_order()
        transfer = request_table_transfer(
            order=order,
            destination_table=self.table_b,
            requested_by=self.cashier,
            reason="Guest preference",
        )
        self.assertEqual(transfer.source_table, self.table_a)
        self.assertEqual(transfer.destination_table, self.table_b)
        self.assertEqual(transfer.status, "REQUESTED")

    def test_transfer_to_occupied_table_raises(self):
        """Cannot transfer to an already occupied table."""
        from orders.models import TableSession
        order, _ = self._setup_dine_in_order()
        # Make table_b occupied
        TableSession.objects.create(
            table=self.table_b, opened_by=self.cashier, guest_count=2,
        )
        with self.assertRaises(TableNotAvailable):
            request_table_transfer(
                order=order,
                destination_table=self.table_b,
                requested_by=self.cashier,
            )

    def test_transfer_non_dine_in_order_raises(self):
        """Counter orders have no table — cannot transfer."""
        order = self._make_order()  # COUNTER order, no table
        with self.assertRaises(TableTransferConflict):
            request_table_transfer(
                order=order,
                destination_table=self.table_b,
                requested_by=self.cashier,
            )

    def test_transfer_cross_branch_raises(self):
        """Cannot transfer to a table in another branch."""
        order, _ = self._setup_dine_in_order()
        with self.assertRaises(TableTransferConflict):
            request_table_transfer(
                order=order,
                destination_table=self.other_table,
                requested_by=self.cashier,
            )

    def test_complete_table_transfer(self):
        order, _ = self._setup_dine_in_order()
        transfer = request_table_transfer(
            order=order,
            destination_table=self.table_b,
            requested_by=self.cashier,
        )
        transfer = complete_table_transfer(transfer=transfer, approver=self.manager)
        self.assertEqual(transfer.status, "COMPLETED")
        order.refresh_from_db()
        self.assertEqual(order.table, self.table_b)

    def test_complete_transfer_creates_audit(self):
        from operations.models import OperationsAuditLog
        from operations.constants import AUDIT_TABLE_TRANSFER_COMPLETED

        order, _ = self._setup_dine_in_order()
        transfer = request_table_transfer(
            order=order, destination_table=self.table_b,
            requested_by=self.cashier,
        )
        complete_table_transfer(transfer=transfer, approver=self.manager)
        self.assertTrue(
            OperationsAuditLog.objects.filter(
                event_type=AUDIT_TABLE_TRANSFER_COMPLETED,
            ).exists()
        )

    def test_complete_already_completed_raises(self):
        order, _ = self._setup_dine_in_order()
        transfer = request_table_transfer(
            order=order, destination_table=self.table_b, requested_by=self.cashier,
        )
        complete_table_transfer(transfer=transfer, approver=self.manager)
        transfer.refresh_from_db()
        with self.assertRaises(TableTransferConflict):
            complete_table_transfer(transfer=transfer, approver=self.manager)


class TableMergeTest(OperationsTestBase):
    """Tests for table merge workflow."""

    def test_request_table_merge_success(self):
        merge = request_table_merge(
            source_tables=[self.table_a, self.table_b, self.table_c],
            destination_table=self.table_a,
            requested_by=self.manager,
            branch=self.branch,
            reason="Large party",
        )
        self.assertEqual(merge.status, "REQUESTED")
        self.assertEqual(merge.destination_table, self.table_a)
        self.assertEqual(merge.source_tables.count(), 3)

    def test_merge_cross_branch_tables_raises(self):
        """All tables must be in the same branch."""
        with self.assertRaises(TableMergeConflict):
            request_table_merge(
                source_tables=[self.table_a, self.other_table],
                destination_table=self.table_a,
                requested_by=self.manager,
                branch=self.branch,
            )
