# =============================================================================
# RestaurantFlow — Operations Exceptions
# Phase 19: Advanced POS & Restaurant Operations
# =============================================================================

from rest_framework.exceptions import APIException
from rest_framework import status


class POSSessionConflict(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = "A conflicting POS session already exists."
    default_code = "pos_session_conflict"


class CounterSessionNotActive(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "No active counter session found for this counter."
    default_code = "counter_session_not_active"


class UnauthorizedCounter(APIException):
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = "You are not authorized to operate this counter."
    default_code = "unauthorized_counter"


class OrderStateConflict(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = "The order is in a state that does not allow this operation."
    default_code = "order_state_conflict"


class TableTransferConflict(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = "Table transfer cannot be completed due to a conflict."
    default_code = "table_transfer_conflict"


class TableMergeConflict(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = "Table merge cannot be completed due to a conflict."
    default_code = "table_merge_conflict"


class OrderMergeConflict(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = "Order merge cannot be completed due to a conflict."
    default_code = "order_merge_conflict"


class BillSplitConflict(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = "Bill split cannot be completed due to a conflict."
    default_code = "bill_split_conflict"


class ModifierValidationError(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Modifier validation failed."
    default_code = "modifier_validation_error"


class ShiftAlreadyClosed(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = "This shift is already closed."
    default_code = "shift_already_closed"


class ReceiptPrintNotAllowed(APIException):
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = "You do not have permission to print this receipt."
    default_code = "receipt_print_not_allowed"


class IncompatibleOrders(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "The orders are incompatible and cannot be merged."
    default_code = "incompatible_orders"


class BillNotSplittable(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "This bill cannot be split in its current state."
    default_code = "bill_not_splittable"


class SKUNotFound(APIException):
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = "No menu item found for the provided barcode or SKU."
    default_code = "sku_not_found"


class TableNotAvailable(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = "The target table is not available for this operation."
    default_code = "table_not_available"
