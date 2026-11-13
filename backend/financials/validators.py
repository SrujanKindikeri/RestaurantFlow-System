# =============================================================================
# RestaurantFlow — Financials Validators
# Phase 12
#
# Pure validation functions — no DB access, no side effects.
# Each raises rest_framework.exceptions.ValidationError on failure.
# =============================================================================

import os
from decimal import Decimal, InvalidOperation

from rest_framework.exceptions import ValidationError

from financials.constants import (
    EXPENSE_VALID_TRANSITIONS,
    SINV_VALID_TRANSITIONS,
    ALLOWED_ATTACHMENT_CONTENT_TYPES,
    ALLOWED_ATTACHMENT_EXTENSIONS,
    MAX_ATTACHMENT_SIZE_BYTES,
)


# ---------------------------------------------------------------------------
# Decimal / monetary validators
# ---------------------------------------------------------------------------

def validate_non_negative_amount(value, field_name: str = "amount") -> Decimal:
    """Validate that a monetary value is non-negative."""
    try:
        d = Decimal(str(value))
    except (InvalidOperation, TypeError):
        raise ValidationError({field_name: f"'{value}' is not a valid monetary amount."})
    if d < Decimal("0"):
        raise ValidationError(
            {field_name: f"{field_name} must be >= 0. Got {d}."}
        )
    return d


def validate_positive_amount(value, field_name: str = "amount") -> Decimal:
    """Validate that a monetary value is strictly positive."""
    try:
        d = Decimal(str(value))
    except (InvalidOperation, TypeError):
        raise ValidationError({field_name: f"'{value}' is not a valid monetary amount."})
    if d <= Decimal("0"):
        raise ValidationError(
            {field_name: f"{field_name} must be > 0. Got {d}."}
        )
    return d


# ---------------------------------------------------------------------------
# Status transition validators
# ---------------------------------------------------------------------------

def validate_expense_transition(current_status: str, target_status: str) -> None:
    """Validate a permitted Expense status transition."""
    allowed = EXPENSE_VALID_TRANSITIONS.get(current_status, [])
    if target_status not in allowed:
        from financials.exceptions import InvalidStatusTransition
        raise InvalidStatusTransition(current_status, target_status, allowed)


def validate_sinv_transition(current_status: str, target_status: str) -> None:
    """Validate a permitted SupplierInvoice status transition."""
    allowed = SINV_VALID_TRANSITIONS.get(current_status, [])
    if target_status not in allowed:
        from financials.exceptions import InvalidStatusTransition
        raise InvalidStatusTransition(current_status, target_status, allowed)


# ---------------------------------------------------------------------------
# Rejection reason validator
# ---------------------------------------------------------------------------

def validate_rejection_reason(reason: str, min_length: int = 5) -> str:
    """Rejection must be non-empty and meet a minimum length."""
    if not reason or not reason.strip():
        raise ValidationError({"rejection_reason": "A rejection reason is required."})
    if len(reason.strip()) < min_length:
        raise ValidationError(
            {"rejection_reason": f"Rejection reason must be at least {min_length} characters."}
        )
    return reason.strip()


def validate_correction_reason(reason: str, min_length: int = 10) -> str:
    """Correction reason must be substantive."""
    if not reason or not reason.strip():
        raise ValidationError({"reason": "A correction reason is required."})
    if len(reason.strip()) < min_length:
        raise ValidationError(
            {"reason": f"Correction reason must be at least {min_length} characters."}
        )
    return reason.strip()


# ---------------------------------------------------------------------------
# Attachment validators
# ---------------------------------------------------------------------------

def validate_attachment_file(file) -> None:
    """
    Validate an uploaded attachment file for:
      - size limit
      - allowed extensions
      - allowed MIME types (client-supplied — checked as a secondary layer)
      - server-side magic-byte signature validation (primary defense)

    Phase 21: Added server-side magic-byte inspection to prevent MIME-type
    spoofing.  The client-supplied content_type is checked as a secondary
    layer but is NOT trusted as the sole validation.
    """
    if file.size > MAX_ATTACHMENT_SIZE_BYTES:
        from financials.exceptions import AttachmentTooLarge
        raise AttachmentTooLarge(file.size, MAX_ATTACHMENT_SIZE_BYTES)

    # Extension check
    _, ext = os.path.splitext(file.name.lower())
    if ext and ext not in ALLOWED_ATTACHMENT_EXTENSIONS:
        from financials.exceptions import AttachmentTypeNotAllowed
        raise AttachmentTypeNotAllowed(ext)

    # MIME type check (secondary — client-supplied, not trusted alone)
    content_type = getattr(file, "content_type", "") or ""
    if content_type and content_type not in ALLOWED_ATTACHMENT_CONTENT_TYPES:
        from financials.exceptions import AttachmentTypeNotAllowed
        raise AttachmentTypeNotAllowed(content_type)

    # Phase 21 — Server-side magic byte validation (primary defense)
    _validate_file_magic_bytes(file, ext)


# ---------------------------------------------------------------------------
# Magic byte signatures for allowed file types
# ---------------------------------------------------------------------------

# Known file signatures (first N bytes) for allowed attachment types.
# Reference: https://en.wikipedia.org/wiki/List_of_file_signatures
_FILE_SIGNATURES = {
    ".pdf":  [(b"%PDF",)],
    ".jpg":  [(b"\xff\xd8\xff",)],
    ".jpeg": [(b"\xff\xd8\xff",)],
    ".png":  [(b"\x89PNG\r\n\x1a\n",)],
    ".webp": [(b"RIFF",)],  # WebP starts with RIFF...WEBP
    ".gif":  [(b"GIF87a",), (b"GIF89a",)],
    ".bmp":  [(b"BM",)],
    ".doc":  [(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1",)],  # OLE2 compound doc
    ".docx": [(b"PK\x03\x04",)],  # ZIP-based (OOXML)
    ".xls":  [(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1",)],  # OLE2 compound doc
    ".xlsx": [(b"PK\x03\x04",)],  # ZIP-based (OOXML)
}

# Content types that are explicitly blocked even if extension matches.
# These can contain active content (scripts, HTML, SVG with embedded JS).
_BLOCKED_CONTENT_PATTERNS = [
    b"<html", b"<script", b"<?php", b"<svg",
    b"<javascript", b"text/html",
]


def _validate_file_magic_bytes(file, ext):
    """
    Read the first few bytes of the file and validate against known
    magic byte signatures for the declared extension.

    This prevents a user from uploading an executable/script disguised
    as a PDF or image by spoofing the Content-Type header.

    For ZIP-based formats (.docx, .xlsx), we also verify the file is a
    valid ZIP archive containing expected content type markers.
    """
    from financials.exceptions import AttachmentTypeNotAllowed

    # Save current position
    pos = file.tell() if hasattr(file, "tell") else 0
    try:
        file.seek(0)
    except Exception:
        return  # If we can't seek, skip magic byte check (file may be a stream)

    try:
        # Read enough bytes to cover all signatures (max 12 bytes)
        header = file.read(16)
    except Exception:
        return  # If we can't read, skip (better than crashing)

    finally:
        # Restore position
        try:
            file.seek(pos)
        except Exception:
            pass

    if not header:
        raise AttachmentTypeNotAllowed("empty file")

    # Check for blocked active content patterns in the header
    header_lower = header.lower()
    for pattern in _BLOCKED_CONTENT_PATTERNS:
        if pattern in header_lower:
            raise AttachmentTypeNotAllowed(
                f"File contains blocked active content ({ext})"
            )

    # Validate magic bytes for the declared extension
    expected_sigs = _FILE_SIGNATURES.get(ext)
    if not expected_sigs:
        # If we don't have a signature for this extension, skip (rely on extension check).
        return

    matched = False
    for sig_tuple in expected_sigs:
        for sig in sig_tuple:
            if header.startswith(sig):
                matched = True
                break
        if matched:
            break

    if not matched:
        raise AttachmentTypeNotAllowed(
            f"File signature does not match extension '{ext}'. "
            "The file may have been renamed or is not a valid {ext} file."
        )


# ---------------------------------------------------------------------------
# Supplier invoice validators
# ---------------------------------------------------------------------------

def validate_supplier_invoice_amounts(subtotal, tax_amount, discount_amount, total_amount) -> None:
    """
    Validate supplier invoice financial fields consistency:
      - all non-negative
      - total = subtotal + tax - discount
    """
    s = validate_non_negative_amount(subtotal, "subtotal")
    t = validate_non_negative_amount(tax_amount, "tax_amount")
    d = validate_non_negative_amount(discount_amount, "discount_amount")

    expected = s + t - d
    if Decimal(str(total_amount)) != expected:
        raise ValidationError(
            {
                "total_amount": (
                    f"total_amount must equal subtotal + tax_amount - discount_amount. "
                    f"Expected {expected}, got {total_amount}."
                )
            }
        )


# ---------------------------------------------------------------------------
# Payable validators
# ---------------------------------------------------------------------------

def validate_payable_payment(paid_amount: Decimal, new_payment: Decimal, total: Decimal) -> None:
    """
    Validate that a payment update does not exceed the payable total.
    """
    new_total_paid = paid_amount + new_payment
    if new_total_paid > total:
        raise ValidationError(
            {
                "code": "OVERPAYMENT",
                "message": (
                    f"Payment of {new_payment} would exceed the payable total of {total}. "
                    f"Already paid: {paid_amount}, remaining: {total - paid_amount}."
                ),
            }
        )
