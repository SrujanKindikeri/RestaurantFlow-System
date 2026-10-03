from django.contrib import admin
from payments.models import Payment, PaymentRefund, PaymentSequence, PaymentAuditLog


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ["payment_number", "bill", "branch", "amount", "payment_method", "status", "created_at"]
    list_filter = ["status", "payment_method", "branch"]
    search_fields = ["payment_number", "transaction_reference", "initiated_by__email"]
    raw_id_fields = ["bill", "branch", "counter", "counter_session", "initiated_by", "completed_by"]
    readonly_fields = ["payment_number", "amount", "created_at", "updated_at"]


@admin.register(PaymentRefund)
class PaymentRefundAdmin(admin.ModelAdmin):
    list_display = ["refund_number", "payment", "amount", "status", "requested_at"]
    list_filter = ["status"]
    search_fields = ["refund_number", "payment__payment_number"]
    raw_id_fields = ["payment", "requested_by", "approved_by", "processed_by"]
    readonly_fields = ["refund_number", "amount", "created_at", "updated_at"]


@admin.register(PaymentSequence)
class PaymentSequenceAdmin(admin.ModelAdmin):
    list_display = ["sequence_key", "last_sequence", "updated_at"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(PaymentAuditLog)
class PaymentAuditLogAdmin(admin.ModelAdmin):
    list_display = ["action", "payment", "actor", "old_status", "new_status", "amount", "created_at"]
    list_filter = ["action"]
    search_fields = ["payment__payment_number", "actor__email"]
    raw_id_fields = ["payment", "refund", "actor"]

    def has_change_permission(self, request, obj=None):
        return False  # Audit logs are immutable

    def has_delete_permission(self, request, obj=None):
        return False
