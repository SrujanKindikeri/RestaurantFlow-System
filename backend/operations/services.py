# =============================================================================
# RestaurantFlow — Operations Services (top-level re-export)
# Phase 19: Advanced POS & Restaurant Operations
# =============================================================================
# This module re-exports key service functions for convenience.
# Individual service modules contain the actual implementations.
# =============================================================================

from operations.pos_services import (
    start_pos_session,
    pause_pos_session,
    resume_pos_session,
    end_pos_session,
    scan_barcode_or_sku,
    get_active_pos_session,
)

from operations.order_services import (
    hold_order,
    resume_order,
    set_order_priority,
    assign_waiter,
    create_order_change_request,
    approve_order_change_request,
    reject_order_change_request,
    merge_orders,
    add_item_modifier,
    remove_item_modifier,
    mark_order_served,
)

from operations.table_services import (
    get_table_operational_status,
    set_table_operational_status,
    request_table_transfer,
    complete_table_transfer,
    request_table_merge,
    close_table,
)

from operations.bill_services import (
    create_bill_split,
    finalize_bill_split,
    cancel_bill_split,
)

from operations.shift_services import (
    open_shift,
    close_shift,
    add_handover_note,
    get_shift_summary,
)

from operations.print_services import (
    log_receipt_print,
    build_receipt_data,
    build_kitchen_ticket_data,
)

from operations.sync_services import (
    get_pos_recovery_data,
    get_operations_dashboard_data,
)

__all__ = [
    # POS
    "start_pos_session", "pause_pos_session", "resume_pos_session",
    "end_pos_session", "scan_barcode_or_sku", "get_active_pos_session",
    # Orders
    "hold_order", "resume_order", "set_order_priority", "assign_waiter",
    "create_order_change_request", "approve_order_change_request",
    "reject_order_change_request", "merge_orders",
    "add_item_modifier", "remove_item_modifier", "mark_order_served",
    # Tables
    "get_table_operational_status", "set_table_operational_status",
    "request_table_transfer", "complete_table_transfer",
    "request_table_merge", "close_table",
    # Bills
    "create_bill_split", "finalize_bill_split", "cancel_bill_split",
    # Shifts
    "open_shift", "close_shift", "add_handover_note", "get_shift_summary",
    # Print
    "log_receipt_print", "build_receipt_data", "build_kitchen_ticket_data",
    # Sync / Dashboard
    "get_pos_recovery_data", "get_operations_dashboard_data",
]
