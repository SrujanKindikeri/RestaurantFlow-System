# =============================================================================
# RestaurantFlow — Financials Exceptions
# Phase 12
# =============================================================================

from rest_framework.exceptions import ValidationError


class InvalidStatusTransition(ValidationError):
    def __init__(self, current, target, allowed=None):
        allowed_str = f" Allowed: {allowed}." if allowed else ""
        detail = {
            "code": "INVALID_STATUS_TRANSITION",
            "message": (
                f"Cannot transition from '{current}' to '{target}'.{allowed_str}"
            ),
        }
        super().__init__(detail=detail)


class DuplicatePayable(ValidationError):
    def __init__(self, source_type):
        detail = {
            "code": "DUPLICATE_PAYABLE",
            "message": (
                f"A Payable already exists for this {source_type}. "
                "Duplicate payables are not allowed."
            ),
        }
        super().__init__(detail=detail)


class SelfApprovalNotAllowed(ValidationError):
    def __init__(self):
        detail = {
            "code": "SELF_APPROVAL_NOT_ALLOWED",
            "message": "You cannot approve your own expense submission.",
        }
        super().__init__(detail=detail)


class ExpenseNotEditable(ValidationError):
    def __init__(self, status):
        detail = {
            "code": "EXPENSE_NOT_EDITABLE",
            "message": (
                f"Expense with status '{status}' cannot be edited. "
                "Only DRAFT expenses can be directly modified."
            ),
        }
        super().__init__(detail=detail)


class AttachmentTooLarge(ValidationError):
    def __init__(self, size_bytes, max_bytes):
        detail = {
            "code": "ATTACHMENT_TOO_LARGE",
            "message": (
                f"File size {size_bytes} bytes exceeds the maximum "
                f"allowed size of {max_bytes} bytes."
            ),
        }
        super().__init__(detail=detail)


class AttachmentTypeNotAllowed(ValidationError):
    def __init__(self, file_type):
        detail = {
            "code": "ATTACHMENT_TYPE_NOT_ALLOWED",
            "message": f"File type '{file_type}' is not allowed.",
        }
        super().__init__(detail=detail)


class InvoiceSupplierMismatch(ValidationError):
    def __init__(self):
        detail = {
            "code": "INVOICE_SUPPLIER_MISMATCH",
            "message": (
                "The supplier on the purchase order does not match "
                "the supplier on this invoice."
            ),
        }
        super().__init__(detail=detail)


class InvoiceRestaurantMismatch(ValidationError):
    def __init__(self):
        detail = {
            "code": "INVOICE_RESTAURANT_MISMATCH",
            "message": (
                "The purchase order belongs to a different restaurant."
            ),
        }
        super().__init__(detail=detail)
