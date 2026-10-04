# =============================================================================
# RestaurantFlow — Accounting Serializers
# Phase 13
# =============================================================================

from decimal import Decimal
from rest_framework import serializers

from accounting.models import (
    FiscalYear, AccountingPeriod, Account, AccountingSettings,
    JournalEntry, JournalEntryLine, AccountingAuditLog, JournalSequence,
)
from accounting.constants import (
    ACCOUNT_TYPE_CHOICES, ACCOUNT_SUBTYPE_CHOICES,
    NORMAL_BALANCE_CHOICES, FISCAL_YEAR_STATUS_CHOICES,
    PERIOD_STATUS_CHOICES, JOURNAL_ENTRY_STATUS_CHOICES,
    SOURCE_TYPE_CHOICES,
    ACCOUNT_TYPE_NORMAL_BALANCE,
)

ZERO = Decimal("0.00")


# =============================================================================
# FiscalYear
# =============================================================================

class FiscalYearSerializer(serializers.ModelSerializer):
    restaurant_name = serializers.CharField(source="restaurant.name", read_only=True)
    closed_by_email = serializers.CharField(source="closed_by.email", read_only=True, default=None)

    class Meta:
        model = FiscalYear
        fields = [
            "id", "restaurant", "restaurant_name", "name",
            "start_date", "end_date", "status",
            "closed_at", "closed_by", "closed_by_email",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "status", "closed_at", "closed_by", "created_at", "updated_at"]

    def validate(self, data):
        start = data.get("start_date")
        end = data.get("end_date")
        if start and end and start >= end:
            raise serializers.ValidationError("start_date must be before end_date.")
        return data


class FiscalYearCreateSerializer(serializers.Serializer):
    restaurant = serializers.UUIDField()
    name = serializers.CharField(max_length=100)
    start_date = serializers.DateField()
    end_date = serializers.DateField()

    def validate(self, data):
        if data["start_date"] >= data["end_date"]:
            raise serializers.ValidationError("start_date must be before end_date.")
        return data


# =============================================================================
# AccountingPeriod
# =============================================================================

class AccountingPeriodSerializer(serializers.ModelSerializer):
    restaurant_name = serializers.CharField(source="restaurant.name", read_only=True)
    fiscal_year_name = serializers.CharField(source="fiscal_year.name", read_only=True, default=None)
    closed_by_email = serializers.CharField(source="closed_by.email", read_only=True, default=None)

    class Meta:
        model = AccountingPeriod
        fields = [
            "id", "restaurant", "restaurant_name",
            "fiscal_year", "fiscal_year_name",
            "name", "start_date", "end_date", "status",
            "closed_at", "closed_by", "closed_by_email", "closing_note",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "status", "closed_at", "closed_by",
            "created_at", "updated_at",
        ]

    def validate(self, data):
        start = data.get("start_date")
        end = data.get("end_date")
        if start and end and start >= end:
            raise serializers.ValidationError("start_date must be before end_date.")
        return data


class PeriodCloseSerializer(serializers.Serializer):
    note = serializers.CharField(required=False, allow_blank=True, default="")


# =============================================================================
# Account (Chart of Accounts)
# =============================================================================

class AccountSerializer(serializers.ModelSerializer):
    restaurant_name = serializers.CharField(source="restaurant.name", read_only=True)
    parent_code = serializers.CharField(source="parent_account.code", read_only=True, default=None)
    parent_name = serializers.CharField(source="parent_account.name", read_only=True, default=None)
    children_count = serializers.SerializerMethodField()

    class Meta:
        model = Account
        fields = [
            "id", "restaurant", "restaurant_name",
            "code", "name", "description",
            "account_type", "account_subtype",
            "parent_account", "parent_code", "parent_name",
            "is_group", "is_postable", "is_active", "is_system_account",
            "normal_balance", "children_count",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "is_system_account", "created_at", "updated_at"]

    def get_children_count(self, obj):
        return obj.children.filter(is_active=True).count()


class AccountCreateSerializer(serializers.Serializer):
    restaurant = serializers.UUIDField()
    code = serializers.CharField(max_length=20)
    name = serializers.CharField(max_length=200)
    description = serializers.CharField(required=False, allow_blank=True, default="")
    account_type = serializers.ChoiceField(choices=ACCOUNT_TYPE_CHOICES)
    account_subtype = serializers.CharField(required=False, allow_blank=True, default="")
    parent_account = serializers.UUIDField(required=False, allow_null=True, default=None)
    is_group = serializers.BooleanField(default=False)
    is_postable = serializers.BooleanField(default=True)
    normal_balance = serializers.ChoiceField(
        choices=NORMAL_BALANCE_CHOICES, required=False, allow_blank=True, default=""
    )


class AccountUpdateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=200, required=False)
    description = serializers.CharField(required=False, allow_blank=True)
    account_subtype = serializers.CharField(required=False, allow_blank=True)
    is_group = serializers.BooleanField(required=False)
    is_postable = serializers.BooleanField(required=False)


class AccountTreeSerializer(serializers.ModelSerializer):
    """Recursive serializer for account hierarchy tree."""
    children = serializers.SerializerMethodField()

    class Meta:
        model = Account
        fields = [
            "id", "code", "name", "account_type", "account_subtype",
            "normal_balance", "is_group", "is_postable", "is_active",
            "is_system_account", "children",
        ]

    def get_children(self, obj):
        active_children = obj.children.filter(is_active=True).order_by("code")
        return AccountTreeSerializer(active_children, many=True).data


# =============================================================================
# AccountingSettings
# =============================================================================

class AccountingSettingsSerializer(serializers.ModelSerializer):
    restaurant_name = serializers.CharField(source="restaurant.name", read_only=True)

    # Nested account info (read-only display)
    default_sales_account_code = serializers.CharField(
        source="default_sales_account.code", read_only=True, default=None
    )
    default_cash_account_code = serializers.CharField(
        source="default_cash_account.code", read_only=True, default=None
    )
    default_bank_account_code = serializers.CharField(
        source="default_bank_account.code", read_only=True, default=None
    )
    default_accounts_receivable_code = serializers.CharField(
        source="default_accounts_receivable.code", read_only=True, default=None
    )
    default_inventory_account_code = serializers.CharField(
        source="default_inventory_account.code", read_only=True, default=None
    )
    default_accounts_payable_code = serializers.CharField(
        source="default_accounts_payable.code", read_only=True, default=None
    )
    default_tax_payable_code = serializers.CharField(
        source="default_tax_payable.code", read_only=True, default=None
    )
    default_cogs_account_code = serializers.CharField(
        source="default_cogs_account.code", read_only=True, default=None
    )

    class Meta:
        model = AccountingSettings
        fields = [
            "id", "restaurant", "restaurant_name",
            "default_sales_account", "default_sales_account_code",
            "default_discount_account",
            "default_cash_account", "default_cash_account_code",
            "default_bank_account", "default_bank_account_code",
            "default_accounts_receivable", "default_accounts_receivable_code",
            "default_inventory_account", "default_inventory_account_code",
            "default_card_clearing_account",
            "default_upi_clearing_account",
            "default_accounts_payable", "default_accounts_payable_code",
            "default_tax_payable", "default_tax_payable_code",
            "default_cogs_account", "default_cogs_account_code",
            "default_rounding_account",
            "retained_earnings_account",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "restaurant", "created_at", "updated_at"]


class AccountingSettingsUpdateSerializer(serializers.Serializer):
    default_sales_account = serializers.UUIDField(required=False, allow_null=True)
    default_discount_account = serializers.UUIDField(required=False, allow_null=True)
    default_cash_account = serializers.UUIDField(required=False, allow_null=True)
    default_bank_account = serializers.UUIDField(required=False, allow_null=True)
    default_accounts_receivable = serializers.UUIDField(required=False, allow_null=True)
    default_inventory_account = serializers.UUIDField(required=False, allow_null=True)
    default_card_clearing_account = serializers.UUIDField(required=False, allow_null=True)
    default_upi_clearing_account = serializers.UUIDField(required=False, allow_null=True)
    default_accounts_payable = serializers.UUIDField(required=False, allow_null=True)
    default_tax_payable = serializers.UUIDField(required=False, allow_null=True)
    default_cogs_account = serializers.UUIDField(required=False, allow_null=True)
    default_rounding_account = serializers.UUIDField(required=False, allow_null=True)
    retained_earnings_account = serializers.UUIDField(required=False, allow_null=True)


# =============================================================================
# JournalEntryLine
# =============================================================================

class JournalEntryLineSerializer(serializers.ModelSerializer):
    account_code = serializers.CharField(source="account.code", read_only=True)
    account_name = serializers.CharField(source="account.name", read_only=True)
    account_type = serializers.CharField(source="account.account_type", read_only=True)
    normal_balance = serializers.CharField(source="account.normal_balance", read_only=True)

    class Meta:
        model = JournalEntryLine
        fields = [
            "id", "journal_entry", "account",
            "account_code", "account_name", "account_type", "normal_balance",
            "description", "debit_amount", "credit_amount",
            "reference_type", "reference_id",
            "created_at",
        ]
        read_only_fields = ["id", "journal_entry", "created_at"]

    def validate(self, data):
        debit = data.get("debit_amount", ZERO)
        credit = data.get("credit_amount", ZERO)
        from accounting.validators import validate_line_debit_xor_credit
        validate_line_debit_xor_credit(debit, credit)
        return data


class JournalEntryLineCreateSerializer(serializers.Serializer):
    account = serializers.UUIDField()
    description = serializers.CharField(required=False, allow_blank=True, default="")
    debit_amount = serializers.DecimalField(max_digits=14, decimal_places=2, default=ZERO)
    credit_amount = serializers.DecimalField(max_digits=14, decimal_places=2, default=ZERO)
    reference_type = serializers.CharField(required=False, allow_blank=True, default="")
    reference_id = serializers.UUIDField(required=False, allow_null=True, default=None)

    def validate(self, data):
        from accounting.validators import validate_line_debit_xor_credit
        validate_line_debit_xor_credit(
            data.get("debit_amount", ZERO),
            data.get("credit_amount", ZERO),
        )
        return data


# =============================================================================
# JournalEntry
# =============================================================================

class JournalEntrySerializer(serializers.ModelSerializer):
    restaurant_name = serializers.CharField(source="restaurant.name", read_only=True)
    branch_name = serializers.CharField(source="branch.name", read_only=True, default=None)
    period_name = serializers.CharField(source="accounting_period.name", read_only=True)
    created_by_email = serializers.CharField(source="created_by.email", read_only=True)
    posted_by_email = serializers.CharField(source="posted_by.email", read_only=True, default=None)
    reversed_by_email = serializers.CharField(source="reversed_by.email", read_only=True, default=None)
    lines = JournalEntryLineSerializer(many=True, read_only=True)
    total_debits = serializers.SerializerMethodField()
    total_credits = serializers.SerializerMethodField()
    is_balanced = serializers.SerializerMethodField()

    class Meta:
        model = JournalEntry
        fields = [
            "id", "restaurant", "restaurant_name", "branch", "branch_name",
            "entry_number", "accounting_period", "period_name",
            "entry_date", "description",
            "source_type", "source_id", "reference_type", "reference_id",
            "status",
            "created_by", "created_by_email",
            "posted_by", "posted_by_email", "posted_at",
            "reversed_by", "reversed_by_email", "reversed_at", "reversal_reason",
            "reversal_of",
            "lines", "total_debits", "total_credits", "is_balanced",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "entry_number", "status",
            "posted_by", "posted_at", "reversed_by", "reversed_at",
            "created_at", "updated_at",
        ]

    def get_total_debits(self, obj):
        return sum((l.debit_amount for l in obj.lines.all()), ZERO)

    def get_total_credits(self, obj):
        return sum((l.credit_amount for l in obj.lines.all()), ZERO)

    def get_is_balanced(self, obj):
        return self.get_total_debits(obj) == self.get_total_credits(obj)


class JournalEntryCreateSerializer(serializers.Serializer):
    restaurant = serializers.UUIDField()
    branch = serializers.UUIDField(required=False, allow_null=True, default=None)
    accounting_period = serializers.UUIDField()
    entry_date = serializers.DateField()
    description = serializers.CharField()
    source_type = serializers.CharField(required=False, default="MANUAL")
    source_id = serializers.UUIDField(required=False, allow_null=True, default=None)
    lines = JournalEntryLineCreateSerializer(many=True, min_length=2)

    def validate_lines(self, value):
        if len(value) < 2:
            raise serializers.ValidationError(
                "A journal entry requires at least 2 lines."
            )
        total_debit = sum(l.get("debit_amount", ZERO) for l in value)
        total_credit = sum(l.get("credit_amount", ZERO) for l in value)
        if total_debit != total_credit:
            raise serializers.ValidationError(
                f"Lines are not balanced: debits={total_debit}, credits={total_credit}."
            )
        return value


class JournalReverseSerializer(serializers.Serializer):
    reason = serializers.CharField(min_length=1)
    reversal_date = serializers.DateField(required=False, allow_null=True, default=None)


class JournalVoidSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True, default="")


# =============================================================================
# AccountingAuditLog
# =============================================================================

class AccountingAuditLogSerializer(serializers.ModelSerializer):
    actor_email = serializers.CharField(source="actor.email", read_only=True)
    restaurant_name = serializers.CharField(source="restaurant.name", read_only=True)

    class Meta:
        model = AccountingAuditLog
        fields = [
            "id", "actor", "actor_email", "action",
            "entity_type", "entity_id",
            "restaurant", "restaurant_name", "branch",
            "old_status", "new_status", "metadata",
            "created_at",
        ]
        read_only_fields = ["__all__"]


# =============================================================================
# Report serializers (output shapes)
# =============================================================================

class GeneralLedgerRowSerializer(serializers.Serializer):
    date = serializers.DateField()
    journal_number = serializers.CharField()
    description = serializers.CharField()
    debit = serializers.DecimalField(max_digits=14, decimal_places=2)
    credit = serializers.DecimalField(max_digits=14, decimal_places=2)
    balance = serializers.DecimalField(max_digits=14, decimal_places=2)
    account_code = serializers.CharField()
    account_name = serializers.CharField()
    source_type = serializers.CharField()
    branch = serializers.CharField(allow_null=True)
    journal_entry_id = serializers.CharField()


class TrialBalanceRowSerializer(serializers.Serializer):
    account_code = serializers.CharField()
    account_name = serializers.CharField()
    account_type = serializers.CharField()
    normal_balance = serializers.CharField()
    debit_total = serializers.DecimalField(max_digits=14, decimal_places=2)
    credit_total = serializers.DecimalField(max_digits=14, decimal_places=2)


class AccountStatementTransactionSerializer(serializers.Serializer):
    date = serializers.DateField()
    journal_number = serializers.CharField()
    description = serializers.CharField()
    debit = serializers.DecimalField(max_digits=14, decimal_places=2)
    credit = serializers.DecimalField(max_digits=14, decimal_places=2)
    balance = serializers.DecimalField(max_digits=14, decimal_places=2)


class PayablePaymentSerializer(serializers.Serializer):
    payable = serializers.UUIDField()
    amount = serializers.DecimalField(max_digits=14, decimal_places=2, min_value=Decimal("0.01"))
    payment_method = serializers.CharField(default="CASH")
