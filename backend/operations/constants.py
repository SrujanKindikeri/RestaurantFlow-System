# =============================================================================
# RestaurantFlow — Operations Constants
# Phase 19: Advanced POS & Restaurant Operations
# =============================================================================

# ---------------------------------------------------------------------------
# POS Session Status
# ---------------------------------------------------------------------------
POS_SESSION_ACTIVE = "ACTIVE"
POS_SESSION_PAUSED = "PAUSED"
POS_SESSION_ENDED  = "ENDED"

POS_SESSION_STATUS_CHOICES = [
    (POS_SESSION_ACTIVE, "Active"),
    (POS_SESSION_PAUSED, "Paused"),
    (POS_SESSION_ENDED,  "Ended"),
]

# ---------------------------------------------------------------------------
# POS Device Type
# ---------------------------------------------------------------------------
DEVICE_DESKTOP      = "DESKTOP"
DEVICE_LAPTOP       = "LAPTOP"
DEVICE_TABLET       = "TABLET"
DEVICE_POS_TERMINAL = "POS_TERMINAL"

DEVICE_TYPE_CHOICES = [
    (DEVICE_DESKTOP,      "Desktop"),
    (DEVICE_LAPTOP,       "Laptop"),
    (DEVICE_TABLET,       "Tablet"),
    (DEVICE_POS_TERMINAL, "POS Terminal"),
]

# ---------------------------------------------------------------------------
# Order Change Request — Change Type
# ---------------------------------------------------------------------------
CHANGE_ADD_ITEM          = "ADD_ITEM"
CHANGE_REMOVE_ITEM       = "REMOVE_ITEM"
CHANGE_QUANTITY          = "CHANGE_QUANTITY"
CHANGE_NOTE              = "CHANGE_NOTE"
CHANGE_TABLE             = "CHANGE_TABLE"
CHANGE_WAITER            = "CHANGE_WAITER"
CHANGE_CUSTOMER          = "CHANGE_CUSTOMER"

ORDER_CHANGE_TYPE_CHOICES = [
    (CHANGE_ADD_ITEM,    "Add Item"),
    (CHANGE_REMOVE_ITEM, "Remove Item"),
    (CHANGE_QUANTITY,    "Change Quantity"),
    (CHANGE_NOTE,        "Change Note"),
    (CHANGE_TABLE,       "Change Table"),
    (CHANGE_WAITER,      "Change Waiter"),
    (CHANGE_CUSTOMER,    "Change Customer"),
]

# ---------------------------------------------------------------------------
# Order Change Request — Status
# ---------------------------------------------------------------------------
CHANGE_STATUS_PENDING   = "PENDING"
CHANGE_STATUS_APPROVED  = "APPROVED"
CHANGE_STATUS_REJECTED  = "REJECTED"
CHANGE_STATUS_CANCELLED = "CANCELLED"

ORDER_CHANGE_STATUS_CHOICES = [
    (CHANGE_STATUS_PENDING,   "Pending"),
    (CHANGE_STATUS_APPROVED,  "Approved"),
    (CHANGE_STATUS_REJECTED,  "Rejected"),
    (CHANGE_STATUS_CANCELLED, "Cancelled"),
]

# ---------------------------------------------------------------------------
# Table Transfer Status
# ---------------------------------------------------------------------------
TRANSFER_REQUESTED  = "REQUESTED"
TRANSFER_APPROVED   = "APPROVED"
TRANSFER_COMPLETED  = "COMPLETED"
TRANSFER_REJECTED   = "REJECTED"
TRANSFER_CANCELLED  = "CANCELLED"

TABLE_TRANSFER_STATUS_CHOICES = [
    (TRANSFER_REQUESTED,  "Requested"),
    (TRANSFER_APPROVED,   "Approved"),
    (TRANSFER_COMPLETED,  "Completed"),
    (TRANSFER_REJECTED,   "Rejected"),
    (TRANSFER_CANCELLED,  "Cancelled"),
]

# ---------------------------------------------------------------------------
# Table Merge Status
# ---------------------------------------------------------------------------
MERGE_REQUESTED  = "REQUESTED"
MERGE_APPROVED   = "APPROVED"
MERGE_COMPLETED  = "COMPLETED"
MERGE_REJECTED   = "REJECTED"
MERGE_CANCELLED  = "CANCELLED"

TABLE_MERGE_STATUS_CHOICES = [
    (MERGE_REQUESTED,  "Requested"),
    (MERGE_APPROVED,   "Approved"),
    (MERGE_COMPLETED,  "Completed"),
    (MERGE_REJECTED,   "Rejected"),
    (MERGE_CANCELLED,  "Cancelled"),
]

# ---------------------------------------------------------------------------
# Order Merge Status
# ---------------------------------------------------------------------------
ORDER_MERGE_PENDING   = "PENDING"
ORDER_MERGE_APPROVED  = "APPROVED"
ORDER_MERGE_COMPLETED = "COMPLETED"
ORDER_MERGE_REJECTED  = "REJECTED"
ORDER_MERGE_CANCELLED = "CANCELLED"

ORDER_MERGE_STATUS_CHOICES = [
    (ORDER_MERGE_PENDING,   "Pending"),
    (ORDER_MERGE_APPROVED,  "Approved"),
    (ORDER_MERGE_COMPLETED, "Completed"),
    (ORDER_MERGE_REJECTED,  "Rejected"),
    (ORDER_MERGE_CANCELLED, "Cancelled"),
]

# ---------------------------------------------------------------------------
# Bill Split Type
# ---------------------------------------------------------------------------
SPLIT_ITEM     = "ITEM"
SPLIT_QUANTITY = "QUANTITY"
SPLIT_EQUAL    = "EQUAL"
SPLIT_GUEST    = "GUEST"

BILL_SPLIT_TYPE_CHOICES = [
    (SPLIT_ITEM,     "By Item"),
    (SPLIT_QUANTITY, "By Quantity"),
    (SPLIT_EQUAL,    "Equal"),
    (SPLIT_GUEST,    "By Guest"),
]

# ---------------------------------------------------------------------------
# Bill Split Status
# ---------------------------------------------------------------------------
SPLIT_DRAFT     = "DRAFT"
SPLIT_FINALIZED = "FINALIZED"
SPLIT_CANCELLED = "CANCELLED"

BILL_SPLIT_STATUS_CHOICES = [
    (SPLIT_DRAFT,     "Draft"),
    (SPLIT_FINALIZED, "Finalized"),
    (SPLIT_CANCELLED, "Cancelled"),
]

# ---------------------------------------------------------------------------
# Receipt Print Type
# ---------------------------------------------------------------------------
PRINT_ORIGINAL  = "ORIGINAL"
PRINT_REPRINT   = "REPRINT"
PRINT_DUPLICATE = "DUPLICATE"
PRINT_KITCHEN   = "KITCHEN"

RECEIPT_PRINT_TYPE_CHOICES = [
    (PRINT_ORIGINAL,  "Original"),
    (PRINT_REPRINT,   "Reprint"),
    (PRINT_DUPLICATE, "Duplicate"),
    (PRINT_KITCHEN,   "Kitchen Ticket"),
]

# ---------------------------------------------------------------------------
# Operational Shift Type
# ---------------------------------------------------------------------------
SHIFT_MORNING   = "MORNING"
SHIFT_AFTERNOON = "AFTERNOON"
SHIFT_EVENING   = "EVENING"
SHIFT_NIGHT     = "NIGHT"
SHIFT_CUSTOM    = "CUSTOM"

OPERATIONAL_SHIFT_TYPE_CHOICES = [
    (SHIFT_MORNING,   "Morning"),
    (SHIFT_AFTERNOON, "Afternoon"),
    (SHIFT_EVENING,   "Evening"),
    (SHIFT_NIGHT,     "Night"),
    (SHIFT_CUSTOM,    "Custom"),
]

# ---------------------------------------------------------------------------
# Operational Shift Status
# ---------------------------------------------------------------------------
OP_SHIFT_OPEN   = "OPEN"
OP_SHIFT_CLOSED = "CLOSED"

OPERATIONAL_SHIFT_STATUS_CHOICES = [
    (OP_SHIFT_OPEN,   "Open"),
    (OP_SHIFT_CLOSED, "Closed"),
]

# ---------------------------------------------------------------------------
# Shift Handover Note Type
# ---------------------------------------------------------------------------
HANDOVER_GENERAL   = "GENERAL"
HANDOVER_KITCHEN   = "KITCHEN"
HANDOVER_INVENTORY = "INVENTORY"
HANDOVER_CUSTOMER  = "CUSTOMER"
HANDOVER_PAYMENT   = "PAYMENT"
HANDOVER_EQUIPMENT = "EQUIPMENT"
HANDOVER_STAFF     = "STAFF"
HANDOVER_OTHER     = "OTHER"

HANDOVER_NOTE_TYPE_CHOICES = [
    (HANDOVER_GENERAL,   "General"),
    (HANDOVER_KITCHEN,   "Kitchen"),
    (HANDOVER_INVENTORY, "Inventory"),
    (HANDOVER_CUSTOMER,  "Customer"),
    (HANDOVER_PAYMENT,   "Payment"),
    (HANDOVER_EQUIPMENT, "Equipment"),
    (HANDOVER_STAFF,     "Staff"),
    (HANDOVER_OTHER,     "Other"),
]

# ---------------------------------------------------------------------------
# Handover Note Priority
# ---------------------------------------------------------------------------
PRIORITY_LOW    = "LOW"
PRIORITY_NORMAL = "NORMAL"
PRIORITY_HIGH   = "HIGH"

HANDOVER_PRIORITY_CHOICES = [
    (PRIORITY_LOW,    "Low"),
    (PRIORITY_NORMAL, "Normal"),
    (PRIORITY_HIGH,   "High"),
]

# ---------------------------------------------------------------------------
# DiningTable Operational Status (derived; separate from TableStatus)
# ---------------------------------------------------------------------------
TABLE_OP_AVAILABLE     = "AVAILABLE"
TABLE_OP_OCCUPIED      = "OCCUPIED"
TABLE_OP_RESERVED      = "RESERVED"
TABLE_OP_BILL_PENDING  = "BILL_PENDING"
TABLE_OP_CLEANING      = "CLEANING"
TABLE_OP_OUT_OF_SERVICE = "OUT_OF_SERVICE"

TABLE_OPERATIONAL_STATUS_CHOICES = [
    (TABLE_OP_AVAILABLE,      "Available"),
    (TABLE_OP_OCCUPIED,       "Occupied"),
    (TABLE_OP_RESERVED,       "Reserved"),
    (TABLE_OP_BILL_PENDING,   "Bill Pending"),
    (TABLE_OP_CLEANING,       "Cleaning"),
    (TABLE_OP_OUT_OF_SERVICE, "Out of Service"),
]

# ---------------------------------------------------------------------------
# DiningTable Shape (floor-plan metadata)
# ---------------------------------------------------------------------------
TABLE_SHAPE_RECTANGLE = "RECTANGLE"
TABLE_SHAPE_ROUND     = "ROUND"
TABLE_SHAPE_SQUARE    = "SQUARE"

TABLE_SHAPE_CHOICES = [
    (TABLE_SHAPE_RECTANGLE, "Rectangle"),
    (TABLE_SHAPE_ROUND,     "Round"),
    (TABLE_SHAPE_SQUARE,    "Square"),
]

# ---------------------------------------------------------------------------
# Order Fulfillment Status (serving state — separate from Order.status)
# ---------------------------------------------------------------------------
FULFILLMENT_CONFIRMED = "CONFIRMED"
FULFILLMENT_PREPARING = "PREPARING"
FULFILLMENT_READY     = "READY"
FULFILLMENT_SERVED    = "SERVED"
FULFILLMENT_CANCELLED = "CANCELLED"

ORDER_FULFILLMENT_STATUS_CHOICES = [
    (FULFILLMENT_CONFIRMED, "Confirmed"),
    (FULFILLMENT_PREPARING, "Preparing"),
    (FULFILLMENT_READY,     "Ready"),
    (FULFILLMENT_SERVED,    "Served"),
    (FULFILLMENT_CANCELLED, "Cancelled"),
]

# ---------------------------------------------------------------------------
# Audit Events
# ---------------------------------------------------------------------------
AUDIT_POS_SESSION_STARTED      = "POS_SESSION_STARTED"
AUDIT_POS_SESSION_PAUSED       = "POS_SESSION_PAUSED"
AUDIT_POS_SESSION_ENDED        = "POS_SESSION_ENDED"
AUDIT_ORDER_HELD               = "ORDER_HELD"
AUDIT_ORDER_RESUMED            = "ORDER_RESUMED"
AUDIT_ORDER_PRIORITY_CHANGED   = "ORDER_PRIORITY_CHANGED"
AUDIT_ORDER_CHANGE_REQUESTED   = "ORDER_CHANGE_REQUESTED"
AUDIT_ORDER_CHANGE_APPROVED    = "ORDER_CHANGE_APPROVED"
AUDIT_ORDER_CHANGE_REJECTED    = "ORDER_CHANGE_REJECTED"
AUDIT_ORDER_MERGED             = "ORDER_MERGED"
AUDIT_TABLE_TRANSFER_REQUESTED = "TABLE_TRANSFER_REQUESTED"
AUDIT_TABLE_TRANSFER_COMPLETED = "TABLE_TRANSFER_COMPLETED"
AUDIT_TABLE_MERGED             = "TABLE_MERGED"
AUDIT_BILL_SPLIT_CREATED       = "BILL_SPLIT_CREATED"
AUDIT_BILL_SPLIT_FINALIZED     = "BILL_SPLIT_FINALIZED"
AUDIT_RECEIPT_PRINTED          = "RECEIPT_PRINTED"
AUDIT_RECEIPT_REPRINTED        = "RECEIPT_REPRINTED"
AUDIT_SHIFT_CREATED            = "SHIFT_CREATED"
AUDIT_SHIFT_CLOSED             = "SHIFT_CLOSED"
AUDIT_SHIFT_HANDOVER_CREATED   = "SHIFT_HANDOVER_CREATED"
AUDIT_MODIFIER_ADDED           = "MODIFIER_ADDED"
AUDIT_MODIFIER_REMOVED         = "MODIFIER_REMOVED"
AUDIT_WAITER_ASSIGNED          = "WAITER_ASSIGNED"
AUDIT_TABLE_OP_STATUS_CHANGED  = "TABLE_OP_STATUS_CHANGED"

AUDIT_EVENT_CHOICES = [
    (AUDIT_POS_SESSION_STARTED,      "POS Session Started"),
    (AUDIT_POS_SESSION_PAUSED,       "POS Session Paused"),
    (AUDIT_POS_SESSION_ENDED,        "POS Session Ended"),
    (AUDIT_ORDER_HELD,               "Order Held"),
    (AUDIT_ORDER_RESUMED,            "Order Resumed"),
    (AUDIT_ORDER_PRIORITY_CHANGED,   "Order Priority Changed"),
    (AUDIT_ORDER_CHANGE_REQUESTED,   "Order Change Requested"),
    (AUDIT_ORDER_CHANGE_APPROVED,    "Order Change Approved"),
    (AUDIT_ORDER_CHANGE_REJECTED,    "Order Change Rejected"),
    (AUDIT_ORDER_MERGED,             "Order Merged"),
    (AUDIT_TABLE_TRANSFER_REQUESTED, "Table Transfer Requested"),
    (AUDIT_TABLE_TRANSFER_COMPLETED, "Table Transfer Completed"),
    (AUDIT_TABLE_MERGED,             "Table Merged"),
    (AUDIT_BILL_SPLIT_CREATED,       "Bill Split Created"),
    (AUDIT_BILL_SPLIT_FINALIZED,     "Bill Split Finalized"),
    (AUDIT_RECEIPT_PRINTED,          "Receipt Printed"),
    (AUDIT_RECEIPT_REPRINTED,        "Receipt Reprinted"),
    (AUDIT_SHIFT_CREATED,            "Shift Created"),
    (AUDIT_SHIFT_CLOSED,             "Shift Closed"),
    (AUDIT_SHIFT_HANDOVER_CREATED,   "Shift Handover Created"),
    (AUDIT_MODIFIER_ADDED,           "Modifier Added"),
    (AUDIT_MODIFIER_REMOVED,         "Modifier Removed"),
    (AUDIT_WAITER_ASSIGNED,          "Waiter Assigned"),
    (AUDIT_TABLE_OP_STATUS_CHANGED,  "Table Operational Status Changed"),
]

# ---------------------------------------------------------------------------
# Permissions
# ---------------------------------------------------------------------------
PERM_POS_ACCESS                 = "pos.access"
PERM_POS_SESSION_START          = "pos.session.start"
PERM_POS_SESSION_PAUSE          = "pos.session.pause"
PERM_POS_SESSION_END            = "pos.session.end"
PERM_POS_ORDER_CREATE           = "pos.order.create"
PERM_POS_ORDER_EDIT             = "pos.order.edit"
PERM_POS_ORDER_HOLD             = "pos.order.hold"
PERM_POS_ORDER_RESUME           = "pos.order.resume"
PERM_POS_ORDER_CANCEL           = "pos.order.cancel"
PERM_POS_ORDER_PRIORITY         = "pos.order.priority"
PERM_POS_ORDER_PRIORITY_URGENT  = "pos.order.priority.urgent"

PERM_ORDER_MODIFIER_MANAGE      = "order.modifier.manage"
PERM_ORDER_TABLE_ASSIGN         = "order.table.assign"
PERM_ORDER_TABLE_TRANSFER       = "order.table.transfer"
PERM_ORDER_MERGE                = "order.merge"
PERM_ORDER_CHANGE_REQUEST       = "order.change.request"
PERM_ORDER_CHANGE_APPROVE       = "order.change.approve"
PERM_ORDER_WAITER_ASSIGN        = "order.waiter.assign"
PERM_ORDER_WAITER_REASSIGN      = "order.waiter.reassign"

PERM_TABLE_VIEW                 = "table.view"
PERM_TABLE_MANAGE               = "table.manage"
PERM_TABLE_TRANSFER             = "table.transfer"
PERM_TABLE_MERGE                = "table.merge"

PERM_BILL_SPLIT                 = "bill.split"
PERM_BILL_MERGE                 = "bill.merge"

PERM_RECEIPT_PRINT              = "receipt.print"
PERM_RECEIPT_REPRINT            = "receipt.reprint"

PERM_SHIFT_VIEW                 = "shift.view"
PERM_SHIFT_CREATE               = "shift.create"
PERM_SHIFT_CLOSE                = "shift.close"
PERM_SHIFT_HANDOVER_VIEW        = "shift.handover.view"

PERM_OPERATIONS_DASHBOARD       = "operations.dashboard.view"
PERM_OPERATIONS_EXPORT          = "operations.export"
