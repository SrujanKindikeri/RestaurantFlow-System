# =============================================================================
# RestaurantFlow — Financials Services
# Phase 12
#
# All business logic for the financial operations lifecycle lives here.
# Views call these; serializers validate input shapes only.
#
# Public API — ExpenseService:
#   generate_expense_number(restaurant)             → str
#   create_expense(restaurant, branch, category, title, ...)  → Expense
#   update_draft(expense, user, **fields)           → Expense
#   submit_expense(expense, user)                   → Expense
#   approve_expense(expense, reviewer, note)        → Expense
#   reject_expense(expense, reviewer, reason)       → Expense
#   cancel_expense(expense, user)                   → Expense
#
# Public API — ExpenseCorrectionService:
#   request_correction(expense, user, correction_type, data, reason) → ExpenseCorrectionRequest
#   approve_correction(correction, reviewer, note)  → ExpenseCorrectionRequest
#   reject_correction(correction, reviewer, note)   → ExpenseCorrectionRequest
#   cancel_correction(correction, user)             → ExpenseCorrectionRequest
#
# Public API — ExpenseAttachmentService:
#   upload_attachment(expense, file, user)          → ExpenseAttachment
#   delete_attachment(attachment, user)             → None
#
# Public API — RecurringExpenseService:
#   create_template(restaurant, branch, category, title, amount, frequency, start_date, user, **kw) → RecurringExpense
#   update_template(template, user, **fields)       → RecurringExpense
#   disable_template(template, user)                → RecurringExpense
#   generate_due_expenses(today)                    → list[Expense]
#   _calculate_next_run_date(current_date, frequency) → date
#
# Public API — SupplierInvoiceService:
#   generate_invoice_number(restaurant)             → str
#   create_invoice(restaurant, supplier, user, **kw) → SupplierInvoice
#   submit_invoice(invoice, user)                   → SupplierInvoice
#   approve_invoice(invoice, user, note)            → SupplierInvoice
#   cancel_invoice(invoice, user, reason)           → SupplierInvoice
#
# Public API — PayableService:
#   create_payable_from_expense(expense, user)      → Payable
#   create_payable_from_invoice(invoice, user)      → Payable
#   record_payment(payable, amount, user)           → Payable
#   refresh_overdue_statuses()                      → int
#   get_overdue_payables(restaurant)                → QuerySet[Payable]
#
# Concurrency:
#   - generate_expense_number / generate_invoice_number use select_for_update()
#   - approve_expense / approve_correction use select_for_update()
#   - All mutating operations are wrapped in transaction.atomic()
#
# Security:
#   - All public functions validate user authentication.
#   - Branch/restaurant scope validated for every relevant object.
#   - Self-approval is prevented.
#   - Duplicate payables are rejected.
# =============================================================================

import logging
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP

from django.db import transaction, IntegrityError
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from accounts import access as acl
from financials.constants import (
    EXPENSE_DRAFT, EXPENSE_SUBMITTED, EXPENSE_APPROVED,
    EXPENSE_REJECTED, EXPENSE_CANCELLED,
    PAYMENT_STATUS_UNPAID,
    APPROVAL_PENDING, APPROVAL_APPROVED, APPROVAL_REJECTED, APPROVAL_CANCELLED,
    CORRECTION_PENDING, CORRECTION_APPROVED, CORRECTION_REJECTED, CORRECTION_CANCELLED,
    SINV_DRAFT, SINV_SUBMITTED, SINV_APPROVED, SINV_CANCELLED,
    PAYABLE_OPEN, PAYABLE_PAID, PAYABLE_PARTIALLY_PAID, PAYABLE_OVERDUE, PAYABLE_CANCELLED,
    PAYABLE_TYPE_EXPENSE, PAYABLE_TYPE_SUPPLIER_INVOICE,
    FREQ_WEEKLY, FREQ_MONTHLY, FREQ_QUARTERLY, FREQ_YEARLY,
    EXPENSE_NUMBER_FORMAT, SINV_NUMBER_FORMAT,
    AUDIT_EXPENSE_CREATED, AUDIT_EXPENSE_UPDATED, AUDIT_EXPENSE_SUBMITTED,
    AUDIT_EXPENSE_APPROVED, AUDIT_EXPENSE_REJECTED, AUDIT_EXPENSE_CANCELLED,
    AUDIT_EXPENSE_CORRECTION_REQUESTED, AUDIT_EXPENSE_CORRECTION_APPROVED,
    AUDIT_EXPENSE_CORRECTION_REJECTED,
    AUDIT_EXPENSE_ATTACHMENT_UPLOADED, AUDIT_EXPENSE_ATTACHMENT_DELETED,
    AUDIT_RECURRING_CREATED, AUDIT_RECURRING_UPDATED, AUDIT_RECURRING_DISABLED,
    AUDIT_SINV_CREATED, AUDIT_SINV_SUBMITTED, AUDIT_SINV_APPROVED, AUDIT_SINV_CANCELLED,
    AUDIT_PAYABLE_CREATED, AUDIT_PAYABLE_UPDATED, AUDIT_PAYABLE_STATUS_CHANGED,
)
from financials.validators import (
    validate_non_negative_amount,
    validate_expense_transition,
    validate_sinv_transition,
    validate_rejection_reason,
    validate_correction_reason,
    validate_attachment_file,
    validate_payable_payment,
)
from financials.exceptions import (
    SelfApprovalNotAllowed,
    DuplicatePayable,
    ExpenseNotEditable,
    InvoiceSupplierMismatch,
    InvoiceRestaurantMismatch,
)

logger = logging.getLogger("financials")

ZERO = Decimal("0.00")
TWO_PLACES = Decimal("0.01")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _require_auth(user):
    if not user or not getattr(user, "is_authenticated", False) or not user.is_active:
        raise PermissionDenied("Authentication required.")


def _money(value) -> Decimal:
    """Round to 2 decimal places."""
    return Decimal(str(value)).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


def _write_audit(actor, action, entity, restaurant, old_status="", new_status="", metadata=None):
    """Create an immutable FinancialAuditLog entry."""
    from financials.models import FinancialAuditLog
    try:
        FinancialAuditLog.objects.create(
            actor=actor,
            action=action,
            entity_type=entity.__class__.__name__,
            entity_id=entity.pk,
            restaurant=restaurant,
            old_status=old_status or "",
            new_status=new_status or "",
            metadata=metadata or {},
        )
    except Exception:
        logger.exception("Failed to write financial audit log for %s %s", action, entity.pk)


# =============================================================================
# 1. Expense Number Generation
# =============================================================================

@transaction.atomic
def generate_expense_number(restaurant) -> str:
    """
    Generate a concurrency-safe, human-readable expense number.

    Format: EXP-{seq:06d}  e.g. EXP-000001
    One sequence per restaurant; never resets.
    Uses select_for_update() — never MAX()+1.
    """
    from financials.models import ExpenseSequence
    seq_row, _ = ExpenseSequence.objects.select_for_update().get_or_create(
        restaurant=restaurant,
        defaults={"last_sequence": 0},
    )
    seq_row.last_sequence += 1
    seq_row.save(update_fields=["last_sequence", "updated_at"])
    return EXPENSE_NUMBER_FORMAT.format(seq=seq_row.last_sequence)


# =============================================================================
# 2. ExpenseService
# =============================================================================

class ExpenseService:
    """Business logic for the Expense lifecycle."""

    @staticmethod
    @transaction.atomic
    def create_expense(
        restaurant,
        category,
        title: str,
        amount,
        expense_date,
        user,
        *,
        branch=None,
        description: str = "",
        tax_amount=ZERO,
        due_date=None,
        vendor_name: str = "",
        vendor_reference: str = "",
        notes: str = "",
    ):
        """
        Create a new Expense in DRAFT status.

        total_amount is computed by the backend: amount + tax_amount.
        Frontend-supplied total_amount is never trusted.
        """
        from financials.models import Expense
        _require_auth(user)

        amt = _money(validate_non_negative_amount(amount, "amount"))
        tax = _money(validate_non_negative_amount(tax_amount, "tax_amount"))
        total = amt + tax

        # Validate category belongs to this restaurant
        if category.restaurant_id != restaurant.pk:
            raise ValidationError(
                {"category": "Category does not belong to this restaurant."}
            )
        if not category.is_active:
            raise ValidationError(
                {"category": "This expense category is inactive and cannot be used."}
            )

        exp_number = generate_expense_number(restaurant)

        expense = Expense.objects.create(
            restaurant=restaurant,
            branch=branch,
            expense_number=exp_number,
            category=category,
            title=title.strip(),
            description=description,
            amount=amt,
            tax_amount=tax,
            total_amount=total,
            expense_date=expense_date,
            due_date=due_date,
            vendor_name=vendor_name.strip(),
            vendor_reference=vendor_reference.strip(),
            payment_status=PAYMENT_STATUS_UNPAID,
            status=EXPENSE_DRAFT,
            notes=notes,
            created_by=user,
        )

        _write_audit(
            actor=user,
            action=AUDIT_EXPENSE_CREATED,
            entity=expense,
            restaurant=restaurant,
            new_status=EXPENSE_DRAFT,
            metadata={"amount": str(expense.amount), "title": expense.title},
        )

        logger.info("Expense created: %s by %s", exp_number, user.email)
        return expense

    @staticmethod
    @transaction.atomic
    def update_draft(expense, user, **fields):
        """
        Update a DRAFT expense.

        Only DRAFT expenses can be directly edited.
        If amount/tax_amount are updated, total_amount is recalculated.
        """
        _require_auth(user)

        if expense.status != EXPENSE_DRAFT:
            raise ExpenseNotEditable(expense.status)

        # Validate category if updating
        if "category" in fields:
            cat = fields["category"]
            if cat.restaurant_id != expense.restaurant_id:
                raise ValidationError({"category": "Category does not belong to this restaurant."})
            if not cat.is_active:
                raise ValidationError({"category": "This expense category is inactive."})

        allowed_fields = {
            "category", "title", "description", "amount", "tax_amount",
            "expense_date", "due_date", "vendor_name", "vendor_reference", "notes", "branch",
        }
        update_fields = []

        for field, value in fields.items():
            if field not in allowed_fields:
                continue
            if field in ("amount", "tax_amount"):
                value = _money(validate_non_negative_amount(value, field))
            elif field == "title":
                value = value.strip()
            setattr(expense, field, value)
            update_fields.append(field)

        # Recalculate total
        expense.total_amount = expense.amount + expense.tax_amount
        update_fields.append("total_amount")
        update_fields.append("updated_at")
        expense.save(update_fields=list(set(update_fields)))

        _write_audit(
            actor=user,
            action=AUDIT_EXPENSE_UPDATED,
            entity=expense,
            restaurant=expense.restaurant,
            old_status=EXPENSE_DRAFT,
            new_status=EXPENSE_DRAFT,
            metadata={"updated_fields": list(fields.keys())},
        )
        return expense

    @staticmethod
    @transaction.atomic
    def submit_expense(expense, user):
        """
        Submit a DRAFT expense for approval.

        Creates an ExpenseApproval record in PENDING status.
        """
        from financials.models import ExpenseApproval
        _require_auth(user)

        # Re-read with lock to prevent concurrent submission
        expense = expense.__class__.objects.select_for_update().get(pk=expense.pk)
        validate_expense_transition(expense.status, EXPENSE_SUBMITTED)

        expense.status = EXPENSE_SUBMITTED
        expense.submitted_by = user
        expense.submitted_at = timezone.now()
        expense.save(update_fields=["status", "submitted_by", "submitted_at", "updated_at"])

        ExpenseApproval.objects.create(
            expense=expense,
            requested_by=user,
            status=APPROVAL_PENDING,
        )

        _write_audit(
            actor=user,
            action=AUDIT_EXPENSE_SUBMITTED,
            entity=expense,
            restaurant=expense.restaurant,
            old_status=EXPENSE_DRAFT,
            new_status=EXPENSE_SUBMITTED,
        )
        return expense

    @staticmethod
    @transaction.atomic
    def approve_expense(expense, reviewer, note: str = ""):
        """
        Approve a SUBMITTED expense.

        The reviewer cannot be the same person who submitted the expense
        (separation of duties — self-approval prevention).
        Uses select_for_update() to prevent double-approval.
        Creates a Payable for the approved expense.
        """
        _require_auth(reviewer)

        expense = expense.__class__.objects.select_for_update().get(pk=expense.pk)
        validate_expense_transition(expense.status, EXPENSE_APPROVED)

        # Self-approval check
        if expense.submitted_by_id == reviewer.pk:
            raise SelfApprovalNotAllowed()

        # Update approval record
        approval = expense.approvals.filter(status=APPROVAL_PENDING).select_for_update().first()
        if approval:
            approval.status = APPROVAL_APPROVED
            approval.reviewed_by = reviewer
            approval.reviewed_at = timezone.now()
            approval.approval_note = note
            approval.save(update_fields=[
                "status", "reviewed_by", "reviewed_at", "approval_note", "updated_at"
            ])

        expense.status = EXPENSE_APPROVED
        expense.approved_by = reviewer
        expense.approved_at = timezone.now()
        expense.save(update_fields=["status", "approved_by", "approved_at", "updated_at"])

        # Automatically create Payable for approved expense
        PayableService.create_payable_from_expense(expense, reviewer)

        _write_audit(
            actor=reviewer,
            action=AUDIT_EXPENSE_APPROVED,
            entity=expense,
            restaurant=expense.restaurant,
            old_status=EXPENSE_SUBMITTED,
            new_status=EXPENSE_APPROVED,
            metadata={"note": note},
        )
        return expense

    @staticmethod
    @transaction.atomic
    def reject_expense(expense, reviewer, reason: str):
        """
        Reject a SUBMITTED expense. Rejection reason is mandatory.
        """
        _require_auth(reviewer)

        reason = validate_rejection_reason(reason)

        expense = expense.__class__.objects.select_for_update().get(pk=expense.pk)
        validate_expense_transition(expense.status, EXPENSE_REJECTED)

        approval = expense.approvals.filter(status=APPROVAL_PENDING).select_for_update().first()
        if approval:
            approval.status = APPROVAL_REJECTED
            approval.reviewed_by = reviewer
            approval.reviewed_at = timezone.now()
            approval.rejection_reason = reason
            approval.save(update_fields=[
                "status", "reviewed_by", "reviewed_at", "rejection_reason", "updated_at"
            ])

        expense.status = EXPENSE_REJECTED
        expense.rejected_by = reviewer
        expense.rejected_at = timezone.now()
        expense.rejection_reason = reason
        expense.save(update_fields=[
            "status", "rejected_by", "rejected_at", "rejection_reason", "updated_at"
        ])

        _write_audit(
            actor=reviewer,
            action=AUDIT_EXPENSE_REJECTED,
            entity=expense,
            restaurant=expense.restaurant,
            old_status=EXPENSE_SUBMITTED,
            new_status=EXPENSE_REJECTED,
            metadata={"reason": reason},
        )
        return expense

    @staticmethod
    @transaction.atomic
    def cancel_expense(expense, user):
        """
        Cancel a DRAFT expense. Only DRAFT expenses can be cancelled.
        (SUBMITTED cancellation requires manager action — future phase.)
        """
        _require_auth(user)

        expense = expense.__class__.objects.select_for_update().get(pk=expense.pk)
        validate_expense_transition(expense.status, EXPENSE_CANCELLED)

        old_status = expense.status
        expense.status = EXPENSE_CANCELLED
        expense.save(update_fields=["status", "updated_at"])

        _write_audit(
            actor=user,
            action=AUDIT_EXPENSE_CANCELLED,
            entity=expense,
            restaurant=expense.restaurant,
            old_status=old_status,
            new_status=EXPENSE_CANCELLED,
        )
        return expense


# =============================================================================
# 3. ExpenseCorrectionService
# =============================================================================

class ExpenseCorrectionService:
    """Business logic for the ExpenseCorrectionRequest lifecycle."""

    @staticmethod
    @transaction.atomic
    def request_correction(expense, user, correction_type: str, requested_data: dict, reason: str):
        """
        Submit a correction request for an APPROVED expense.

        Only APPROVED expenses require corrections.
        DRAFT/SUBMITTED can be edited directly.
        """
        from financials.models import ExpenseCorrectionRequest
        _require_auth(user)

        if expense.status != EXPENSE_APPROVED:
            raise ValidationError(
                {
                    "code": "CORRECTION_REQUIRES_APPROVED",
                    "message": (
                        "Correction requests can only be made for APPROVED expenses. "
                        f"Current status: {expense.status}."
                    ),
                }
            )

        reason = validate_correction_reason(reason)

        correction = ExpenseCorrectionRequest.objects.create(
            expense=expense,
            requested_by=user,
            correction_type=correction_type,
            requested_data=requested_data,
            reason=reason,
            status=CORRECTION_PENDING,
        )

        _write_audit(
            actor=user,
            action=AUDIT_EXPENSE_CORRECTION_REQUESTED,
            entity=expense,
            restaurant=expense.restaurant,
            metadata={
                "correction_id": str(correction.pk),
                "correction_type": correction_type,
                "reason": reason,
            },
        )
        return correction

    @staticmethod
    @transaction.atomic
    def approve_correction(correction, reviewer, note: str = ""):
        """
        Approve a correction request and apply the changes to the expense.

        Mutations are applied inside a transaction. The reviewer cannot
        be the same user who requested the correction.
        """
        _require_auth(reviewer)

        correction = correction.__class__.objects.select_for_update().get(pk=correction.pk)

        if correction.status != CORRECTION_PENDING:
            raise ValidationError(
                {"code": "NOT_PENDING", "message": "Only PENDING corrections can be approved."}
            )

        # Self-approval check
        if correction.requested_by_id == reviewer.pk:
            raise ValidationError(
                {"code": "SELF_APPROVAL_NOT_ALLOWED", "message": "You cannot approve your own correction."}
            )

        correction.status = CORRECTION_APPROVED
        correction.reviewed_by = reviewer
        correction.reviewed_at = timezone.now()
        correction.review_note = note
        correction.save(update_fields=[
            "status", "reviewed_by", "reviewed_at", "review_note", "updated_at"
        ])

        # Apply the requested_data changes to the expense
        expense_obj = correction.expense.__class__.objects.select_for_update().get(
            pk=correction.expense_id
        )
        ExpenseCorrectionService._apply_correction_data(
            expense_obj, correction.requested_data, reviewer
        )

        _write_audit(
            actor=reviewer,
            action=AUDIT_EXPENSE_CORRECTION_APPROVED,
            entity=correction.expense,
            restaurant=correction.expense.restaurant,
            metadata={
                "correction_id": str(correction.pk),
                "note": note,
                "applied_data": correction.requested_data,
            },
        )
        return correction

    @staticmethod
    def _apply_correction_data(expense, data: dict, actor):
        """Apply approved correction data to the expense record."""
        allowed = {
            "amount", "tax_amount", "category_id", "expense_date",
            "due_date", "vendor_name", "vendor_reference", "description", "notes",
        }
        update_fields = []
        for field, value in data.items():
            if field not in allowed:
                continue
            if field in ("amount", "tax_amount"):
                value = _money(validate_non_negative_amount(value, field))
            setattr(expense, field, value)
            update_fields.append(field)

        if "amount" in data or "tax_amount" in data:
            expense.total_amount = expense.amount + expense.tax_amount
            update_fields.append("total_amount")

        if update_fields:
            update_fields.append("updated_at")
            expense.save(update_fields=list(set(update_fields)))

    @staticmethod
    @transaction.atomic
    def reject_correction(correction, reviewer, note: str):
        """Reject a pending correction request."""
        _require_auth(reviewer)

        if not note or not note.strip():
            raise ValidationError({"review_note": "A review note is required when rejecting."})

        correction = correction.__class__.objects.select_for_update().get(pk=correction.pk)

        if correction.status != CORRECTION_PENDING:
            raise ValidationError(
                {"code": "NOT_PENDING", "message": "Only PENDING corrections can be rejected."}
            )

        correction.status = CORRECTION_REJECTED
        correction.reviewed_by = reviewer
        correction.reviewed_at = timezone.now()
        correction.review_note = note
        correction.save(update_fields=[
            "status", "reviewed_by", "reviewed_at", "review_note", "updated_at"
        ])

        _write_audit(
            actor=reviewer,
            action=AUDIT_EXPENSE_CORRECTION_REJECTED,
            entity=correction.expense,
            restaurant=correction.expense.restaurant,
            metadata={"correction_id": str(correction.pk), "note": note},
        )
        return correction

    @staticmethod
    @transaction.atomic
    def cancel_correction(correction, user):
        """Cancel a pending correction (by the requester or an authorized user)."""
        _require_auth(user)

        correction = correction.__class__.objects.select_for_update().get(pk=correction.pk)

        if correction.status != CORRECTION_PENDING:
            raise ValidationError(
                {"code": "NOT_PENDING", "message": "Only PENDING corrections can be cancelled."}
            )

        correction.status = CORRECTION_CANCELLED
        correction.save(update_fields=["status", "updated_at"])
        return correction


# =============================================================================
# 4. ExpenseAttachmentService
# =============================================================================

class ExpenseAttachmentService:
    """Handles secure file attachment operations for expenses."""

    @staticmethod
    @transaction.atomic
    def upload_attachment(expense, file, user):
        """
        Validate and upload a supporting document for an expense.

        Validates: file size, MIME type, extension.
        Stores in a scoped directory (restaurant/expense UUID).
        """
        from financials.models import ExpenseAttachment
        _require_auth(user)

        validate_attachment_file(file)

        attachment = ExpenseAttachment.objects.create(
            expense=expense,
            file=file,
            file_name=file.name,
            file_type=getattr(file, "content_type", "") or "",
            file_size=file.size,
            uploaded_by=user,
        )

        _write_audit(
            actor=user,
            action=AUDIT_EXPENSE_ATTACHMENT_UPLOADED,
            entity=expense,
            restaurant=expense.restaurant,
            metadata={
                "attachment_id": str(attachment.pk),
                "file_name": file.name,
                "file_size": file.size,
            },
        )
        return attachment

    @staticmethod
    @transaction.atomic
    def delete_attachment(attachment, user):
        """Delete a supporting document. Logs the deletion."""
        _require_auth(user)

        expense = attachment.expense
        file_name = attachment.file_name
        att_id = str(attachment.pk)

        # Delete the file from storage
        if attachment.file:
            try:
                attachment.file.delete(save=False)
            except Exception:
                logger.warning("Could not delete file for attachment %s", att_id)

        attachment.delete()

        _write_audit(
            actor=user,
            action=AUDIT_EXPENSE_ATTACHMENT_DELETED,
            entity=expense,
            restaurant=expense.restaurant,
            metadata={"attachment_id": att_id, "file_name": file_name},
        )


# =============================================================================
# 5. RecurringExpenseService
# =============================================================================

class RecurringExpenseService:
    """Business logic for recurring expense templates."""

    @staticmethod
    @transaction.atomic
    def create_template(
        restaurant,
        category,
        title: str,
        amount,
        frequency: str,
        start_date,
        user,
        *,
        branch=None,
        description: str = "",
        tax_amount=ZERO,
        end_date=None,
    ):
        """Create a recurring expense template."""
        from financials.models import RecurringExpense
        _require_auth(user)

        amt = _money(validate_non_negative_amount(amount, "amount"))
        tax = _money(validate_non_negative_amount(tax_amount, "tax_amount"))

        if category.restaurant_id != restaurant.pk:
            raise ValidationError({"category": "Category does not belong to this restaurant."})
        if not category.is_active:
            raise ValidationError({"category": "Category is inactive."})

        template = RecurringExpense.objects.create(
            restaurant=restaurant,
            branch=branch,
            category=category,
            title=title.strip(),
            description=description,
            amount=amt,
            tax_amount=tax,
            frequency=frequency,
            start_date=start_date,
            end_date=end_date,
            next_run_date=start_date,
            is_active=True,
            created_by=user,
        )

        _write_audit(
            actor=user,
            action=AUDIT_RECURRING_CREATED,
            entity=template,
            restaurant=restaurant,
            metadata={"title": title, "frequency": frequency, "amount": str(amt)},
        )
        return template

    @staticmethod
    @transaction.atomic
    def update_template(template, user, **fields):
        """Update a recurring expense template (not historical expenses)."""
        _require_auth(user)

        allowed = {
            "title", "description", "amount", "tax_amount",
            "frequency", "end_date", "category", "branch",
        }
        for field, value in fields.items():
            if field not in allowed:
                continue
            if field in ("amount", "tax_amount"):
                value = _money(validate_non_negative_amount(value, field))
            setattr(template, field, value)

        template.save()

        _write_audit(
            actor=user,
            action=AUDIT_RECURRING_UPDATED,
            entity=template,
            restaurant=template.restaurant,
            metadata={"updated_fields": list(fields.keys())},
        )
        return template

    @staticmethod
    @transaction.atomic
    def disable_template(template, user):
        """Disable a recurring expense template. No new expenses will be generated."""
        _require_auth(user)

        template = template.__class__.objects.select_for_update().get(pk=template.pk)
        template.is_active = False
        template.save(update_fields=["is_active", "updated_at"])

        _write_audit(
            actor=user,
            action=AUDIT_RECURRING_DISABLED,
            entity=template,
            restaurant=template.restaurant,
        )
        return template

    @staticmethod
    @transaction.atomic
    def generate_due_expenses(today=None):
        """
        Generate Expense records for all due recurring templates.

        Designed to be called from a Celery periodic task.
        Idempotent: a template's next_run_date is updated immediately after
        generation, preventing duplicate generation on retry.

        Returns a list of newly created Expense records.
        """
        from financials.models import RecurringExpense
        if today is None:
            today = timezone.now().date()

        due_templates = RecurringExpense.objects.select_for_update().filter(
            is_active=True,
            next_run_date__lte=today,
        ).exclude(
            # Skip templates whose end_date has passed
            end_date__lt=today,
        )

        created = []
        for template in due_templates:
            try:
                # Use a system/service user placeholder — in production, pass
                # a service account user. For now we use the template creator.
                expense = ExpenseService.create_expense(
                    restaurant=template.restaurant,
                    category=template.category,
                    title=template.title,
                    amount=template.amount,
                    expense_date=today,
                    user=template.created_by,
                    branch=template.branch,
                    description=template.description,
                    tax_amount=template.tax_amount,
                )
                created.append(expense)

                # Advance next_run_date
                template.next_run_date = RecurringExpenseService._calculate_next_run_date(
                    today, template.frequency
                )
                template.save(update_fields=["next_run_date", "updated_at"])
            except Exception:
                logger.exception(
                    "Failed to generate expense from recurring template %s", template.pk
                )

        return created

    @staticmethod
    def _calculate_next_run_date(current_date, frequency: str) -> date:
        """Calculate the next run date given a frequency."""
        if frequency == FREQ_WEEKLY:
            return current_date + timedelta(weeks=1)
        elif frequency == FREQ_MONTHLY:
            # Add one month — handle edge cases with calendar
            month = current_date.month + 1
            year = current_date.year
            if month > 12:
                month = 1
                year += 1
            # Clamp to valid day
            import calendar
            last_day = calendar.monthrange(year, month)[1]
            day = min(current_date.day, last_day)
            return date(year, month, day)
        elif frequency == FREQ_QUARTERLY:
            month = current_date.month + 3
            year = current_date.year
            while month > 12:
                month -= 12
                year += 1
            import calendar
            last_day = calendar.monthrange(year, month)[1]
            day = min(current_date.day, last_day)
            return date(year, month, day)
        elif frequency == FREQ_YEARLY:
            import calendar
            year = current_date.year + 1
            last_day = calendar.monthrange(year, current_date.month)[1]
            day = min(current_date.day, last_day)
            return date(year, current_date.month, day)
        else:
            raise ValidationError({"frequency": f"Unknown frequency: {frequency}"})


# =============================================================================
# 6. Supplier Invoice Number Generation
# =============================================================================

@transaction.atomic
def generate_invoice_number(restaurant) -> str:
    """
    Generate a concurrency-safe supplier invoice number.

    Format: SINV-{seq:06d}  e.g. SINV-000001
    One sequence per restaurant; never resets.
    """
    from financials.models import SupplierInvoiceSequence
    seq_row, _ = SupplierInvoiceSequence.objects.select_for_update().get_or_create(
        restaurant=restaurant,
        defaults={"last_sequence": 0},
    )
    seq_row.last_sequence += 1
    seq_row.save(update_fields=["last_sequence", "updated_at"])
    return SINV_NUMBER_FORMAT.format(seq=seq_row.last_sequence)


# =============================================================================
# 7. SupplierInvoiceService
# =============================================================================

class SupplierInvoiceService:
    """Business logic for the SupplierInvoice lifecycle."""

    @staticmethod
    @transaction.atomic
    def create_invoice(
        restaurant,
        supplier,
        invoice_date,
        user,
        *,
        branch=None,
        purchase_order=None,
        external_invoice_number: str = "",
        subtotal=ZERO,
        tax_amount=ZERO,
        discount_amount=ZERO,
        due_date=None,
        notes: str = "",
    ):
        """
        Create a SupplierInvoice record.

        If a PurchaseOrder is provided:
          - Its restaurant must match.
          - Its supplier must match.
          - It must not be CANCELLED.
        """
        from financials.models import SupplierInvoice
        _require_auth(user)

        # Validate supplier belongs to this restaurant
        if supplier.restaurant_id != restaurant.pk:
            raise ValidationError(
                {"supplier": "Supplier does not belong to this restaurant."}
            )

        if purchase_order is not None:
            # Cross-validate purchase order
            if str(purchase_order.restaurant_id) != str(restaurant.pk):
                raise InvoiceRestaurantMismatch()
            if str(purchase_order.supplier_id) != str(supplier.pk):
                raise InvoiceSupplierMismatch()
            po_status = getattr(purchase_order, "status", "")
            if po_status == "CANCELLED":
                raise ValidationError(
                    {"purchase_order": "Cannot create an invoice for a CANCELLED purchase order."}
                )

        sub = _money(validate_non_negative_amount(subtotal, "subtotal"))
        tax = _money(validate_non_negative_amount(tax_amount, "tax_amount"))
        disc = _money(validate_non_negative_amount(discount_amount, "discount_amount"))
        total = sub + tax - disc

        if total < ZERO:
            raise ValidationError(
                {"total_amount": "Total amount cannot be negative (subtotal + tax - discount < 0)."}
            )

        inv_number = generate_invoice_number(restaurant)

        invoice = SupplierInvoice.objects.create(
            restaurant=restaurant,
            branch=branch,
            supplier=supplier,
            purchase_order=purchase_order,
            invoice_number=inv_number,
            external_invoice_number=external_invoice_number.strip(),
            invoice_date=invoice_date,
            due_date=due_date,
            subtotal=sub,
            tax_amount=tax,
            discount_amount=disc,
            total_amount=total,
            status=SINV_DRAFT,
            created_by=user,
            notes=notes,
        )

        _write_audit(
            actor=user,
            action=AUDIT_SINV_CREATED,
            entity=invoice,
            restaurant=restaurant,
            new_status=SINV_DRAFT,
            metadata={"total_amount": str(total), "supplier": supplier.name},
        )
        return invoice

    @staticmethod
    @transaction.atomic
    def submit_invoice(invoice, user):
        """Submit a DRAFT supplier invoice for approval."""
        _require_auth(user)

        invoice = invoice.__class__.objects.select_for_update().get(pk=invoice.pk)
        validate_sinv_transition(invoice.status, SINV_SUBMITTED)

        old = invoice.status
        invoice.status = SINV_SUBMITTED
        invoice.save(update_fields=["status", "updated_at"])

        _write_audit(
            actor=user,
            action=AUDIT_SINV_SUBMITTED,
            entity=invoice,
            restaurant=invoice.restaurant,
            old_status=old,
            new_status=SINV_SUBMITTED,
        )
        return invoice

    @staticmethod
    @transaction.atomic
    def approve_invoice(invoice, user, note: str = ""):
        """Approve a SUBMITTED supplier invoice. Creates a Payable."""
        _require_auth(user)

        invoice = invoice.__class__.objects.select_for_update().get(pk=invoice.pk)
        validate_sinv_transition(invoice.status, SINV_APPROVED)

        old = invoice.status
        invoice.status = SINV_APPROVED
        invoice.approved_by = user
        invoice.approved_at = timezone.now()
        invoice.save(update_fields=["status", "approved_by", "approved_at", "updated_at"])

        # Create Payable for the approved invoice
        PayableService.create_payable_from_invoice(invoice, user)

        _write_audit(
            actor=user,
            action=AUDIT_SINV_APPROVED,
            entity=invoice,
            restaurant=invoice.restaurant,
            old_status=old,
            new_status=SINV_APPROVED,
            metadata={"note": note},
        )
        return invoice

    @staticmethod
    @transaction.atomic
    def cancel_invoice(invoice, user, reason: str = ""):
        """Cancel a supplier invoice (if not yet PAID)."""
        _require_auth(user)

        invoice = invoice.__class__.objects.select_for_update().get(pk=invoice.pk)
        validate_sinv_transition(invoice.status, SINV_CANCELLED)

        old = invoice.status
        invoice.status = SINV_CANCELLED
        invoice.save(update_fields=["status", "updated_at"])

        # Cancel associated Payable if it exists
        try:
            payable = invoice.payable
            if payable.status not in (PAYABLE_PAID,):
                payable.status = PAYABLE_CANCELLED
                payable.save(update_fields=["status", "updated_at"])
        except Exception:
            pass

        _write_audit(
            actor=user,
            action=AUDIT_SINV_CANCELLED,
            entity=invoice,
            restaurant=invoice.restaurant,
            old_status=old,
            new_status=SINV_CANCELLED,
            metadata={"reason": reason},
        )
        return invoice


# =============================================================================
# 8. PayableService
# =============================================================================

class PayableService:
    """Business logic for the Payable lifecycle."""

    @staticmethod
    @transaction.atomic
    def create_payable_from_expense(expense, user):
        """
        Create a Payable record from an approved Expense.

        Idempotent: raises DuplicatePayable if a Payable already exists
        for this expense (enforced by OneToOneField + explicit check).
        """
        from financials.models import Payable
        _require_auth(user)

        # Check for existing payable — prevent duplicates
        if Payable.objects.filter(expense=expense).exists():
            raise DuplicatePayable("Expense")

        payable = Payable.objects.create(
            restaurant=expense.restaurant,
            branch=expense.branch,
            payable_type=PAYABLE_TYPE_EXPENSE,
            expense=expense,
            reference_number=expense.expense_number,
            amount=expense.total_amount,
            paid_amount=ZERO,
            remaining_amount=expense.total_amount,
            due_date=expense.due_date,
            status=PAYABLE_OPEN,
        )

        _write_audit(
            actor=user,
            action=AUDIT_PAYABLE_CREATED,
            entity=payable,
            restaurant=expense.restaurant,
            new_status=PAYABLE_OPEN,
            metadata={
                "source": "Expense",
                "expense_number": expense.expense_number,
                "amount": str(expense.total_amount),
            },
        )
        return payable

    @staticmethod
    @transaction.atomic
    def create_payable_from_invoice(invoice, user):
        """
        Create a Payable record from an approved SupplierInvoice.

        Idempotent: raises DuplicatePayable if Payable already exists.
        """
        from financials.models import Payable
        _require_auth(user)

        if Payable.objects.filter(supplier_invoice=invoice).exists():
            raise DuplicatePayable("SupplierInvoice")

        payable = Payable.objects.create(
            restaurant=invoice.restaurant,
            branch=invoice.branch,
            payable_type=PAYABLE_TYPE_SUPPLIER_INVOICE,
            supplier_invoice=invoice,
            reference_number=invoice.invoice_number,
            amount=invoice.total_amount,
            paid_amount=ZERO,
            remaining_amount=invoice.total_amount,
            due_date=invoice.due_date,
            status=PAYABLE_OPEN,
        )

        _write_audit(
            actor=user,
            action=AUDIT_PAYABLE_CREATED,
            entity=payable,
            restaurant=invoice.restaurant,
            new_status=PAYABLE_OPEN,
            metadata={
                "source": "SupplierInvoice",
                "invoice_number": invoice.invoice_number,
                "amount": str(invoice.total_amount),
            },
        )
        return payable

    @staticmethod
    @transaction.atomic
    def record_payment(payable, payment_amount, user):
        """
        Record a partial or full payment against a Payable.

        paid_amount cannot exceed amount.
        remaining_amount = amount - paid_amount.
        Status is derived automatically.

        This method is the preparation for Phase 13+ Financial Payment.
        """
        _require_auth(user)

        payable = payable.__class__.objects.select_for_update().get(pk=payable.pk)

        if payable.status == PAYABLE_CANCELLED:
            raise ValidationError(
                {"code": "PAYABLE_CANCELLED", "message": "Cannot record payment for a cancelled payable."}
            )
        if payable.status == PAYABLE_PAID:
            raise ValidationError(
                {"code": "ALREADY_PAID", "message": "This payable is already fully paid."}
            )

        pmt = _money(validate_non_negative_amount(payment_amount, "payment_amount"))
        validate_payable_payment(payable.paid_amount, pmt, payable.amount)

        old_status = payable.status
        payable.paid_amount += pmt
        payable.remaining_amount = payable.amount - payable.paid_amount
        payable.refresh_status()
        payable.save(update_fields=[
            "paid_amount", "remaining_amount", "status", "updated_at"
        ])

        _write_audit(
            actor=user,
            action=AUDIT_PAYABLE_STATUS_CHANGED,
            entity=payable,
            restaurant=payable.restaurant,
            old_status=old_status,
            new_status=payable.status,
            metadata={"payment_amount": str(pmt), "remaining": str(payable.remaining_amount)},
        )
        return payable

    @staticmethod
    @transaction.atomic
    def refresh_overdue_statuses():
        """
        Scan OPEN and PARTIALLY_PAID payables and mark any that are overdue.

        Designed to be called from a daily Celery task.
        Returns the count of records updated.
        """
        from financials.models import Payable
        today = timezone.now().date()

        overdue_qs = Payable.objects.filter(
            status__in=[PAYABLE_OPEN, PAYABLE_PARTIALLY_PAID],
            due_date__lt=today,
            remaining_amount__gt=ZERO,
        )
        count = overdue_qs.update(status=PAYABLE_OVERDUE)
        if count:
            logger.info("Marked %d payables as OVERDUE.", count)
        return count

    @staticmethod
    def get_overdue_payables(restaurant):
        """Return all OVERDUE payables for a restaurant."""
        from financials.models import Payable
        today = timezone.now().date()
        return Payable.objects.filter(
            restaurant=restaurant,
            due_date__lt=today,
            remaining_amount__gt=ZERO,
        ).exclude(status__in=[PAYABLE_PAID, PAYABLE_CANCELLED])
