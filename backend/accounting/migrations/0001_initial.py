# =============================================================================
# RestaurantFlow — Accounting Initial Migration
# Phase 13: Accounting Ledger, Double-Entry Bookkeeping
# Generated manually — run: python manage.py migrate
# =============================================================================

import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("organizations", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [

        # =====================================================================
        # FiscalYear
        # =====================================================================
        migrations.CreateModel(
            name="FiscalYear",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=100)),
                ("start_date", models.DateField()),
                ("end_date", models.DateField()),
                ("status", models.CharField(
                    choices=[("OPEN", "Open"), ("CLOSED", "Closed")],
                    db_index=True, default="OPEN", max_length=10,
                )),
                ("closed_at", models.DateTimeField(blank=True, null=True)),
                ("restaurant", models.ForeignKey(
                    db_index=True,
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="fiscal_years",
                    to="organizations.restaurant",
                )),
                ("closed_by", models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="closed_fiscal_years",
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={"verbose_name": "Fiscal Year", "verbose_name_plural": "Fiscal Years", "ordering": ["-start_date"]},
        ),
        migrations.AddIndex(
            model_name="fiscalyear",
            index=models.Index(fields=["restaurant", "status"], name="accounting_fy_restaurant_status_idx"),
        ),
        migrations.AddIndex(
            model_name="fiscalyear",
            index=models.Index(fields=["restaurant", "start_date"], name="accounting_fy_restaurant_start_idx"),
        ),

        # =====================================================================
        # AccountingPeriod
        # =====================================================================
        migrations.CreateModel(
            name="AccountingPeriod",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=100)),
                ("start_date", models.DateField(db_index=True)),
                ("end_date", models.DateField(db_index=True)),
                ("status", models.CharField(
                    choices=[("OPEN", "Open"), ("CLOSE_REQUESTED", "Close Requested"), ("CLOSED", "Closed")],
                    db_index=True, default="OPEN", max_length=20,
                )),
                ("closed_at", models.DateTimeField(blank=True, null=True)),
                ("closing_note", models.TextField(blank=True)),
                ("restaurant", models.ForeignKey(
                    db_index=True,
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="accounting_periods",
                    to="organizations.restaurant",
                )),
                ("fiscal_year", models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="periods",
                    to="accounting.fiscalyear",
                )),
                ("closed_by", models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="closed_accounting_periods",
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={"verbose_name": "Accounting Period", "verbose_name_plural": "Accounting Periods", "ordering": ["-start_date"]},
        ),
        migrations.AddIndex(
            model_name="accountingperiod",
            index=models.Index(fields=["restaurant", "status"], name="accounting_period_rest_status_idx"),
        ),
        migrations.AddIndex(
            model_name="accountingperiod",
            index=models.Index(fields=["restaurant", "start_date"], name="accounting_period_rest_start_idx"),
        ),
        migrations.AddIndex(
            model_name="accountingperiod",
            index=models.Index(fields=["restaurant", "end_date"], name="accounting_period_rest_end_idx"),
        ),
        migrations.AddIndex(
            model_name="accountingperiod",
            index=models.Index(fields=["fiscal_year", "status"], name="accounting_period_fy_status_idx"),
        ),

        # =====================================================================
        # Account (Chart of Accounts)
        # =====================================================================
        migrations.CreateModel(
            name="Account",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("code", models.CharField(db_index=True, max_length=20)),
                ("name", models.CharField(max_length=200)),
                ("description", models.TextField(blank=True)),
                ("account_type", models.CharField(
                    choices=[
                        ("ASSET", "Asset"), ("LIABILITY", "Liability"),
                        ("EQUITY", "Equity"), ("REVENUE", "Revenue"), ("EXPENSE", "Expense"),
                    ],
                    db_index=True, max_length=15,
                )),
                ("account_subtype", models.CharField(blank=True, db_index=True, max_length=30)),
                ("is_group", models.BooleanField(db_index=True, default=False)),
                ("is_postable", models.BooleanField(db_index=True, default=True)),
                ("is_active", models.BooleanField(db_index=True, default=True)),
                ("is_system_account", models.BooleanField(db_index=True, default=False)),
                ("normal_balance", models.CharField(
                    choices=[("DEBIT", "Debit"), ("CREDIT", "Credit")],
                    max_length=6,
                )),
                ("restaurant", models.ForeignKey(
                    db_index=True,
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="accounts",
                    to="organizations.restaurant",
                )),
                ("parent_account", models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="children",
                    to="accounting.account",
                )),
            ],
            options={"verbose_name": "Account", "verbose_name_plural": "Accounts", "ordering": ["code"]},
        ),
        migrations.AddConstraint(
            model_name="account",
            constraint=models.UniqueConstraint(
                fields=["restaurant", "code"],
                name="unique_account_code_per_restaurant",
            ),
        ),
        migrations.AddIndex(
            model_name="account",
            index=models.Index(fields=["restaurant", "account_type"], name="accounting_acct_rest_type_idx"),
        ),
        migrations.AddIndex(
            model_name="account",
            index=models.Index(fields=["restaurant", "is_active"], name="accounting_acct_rest_active_idx"),
        ),
        migrations.AddIndex(
            model_name="account",
            index=models.Index(fields=["restaurant", "is_system_account"], name="accounting_acct_rest_sys_idx"),
        ),
        migrations.AddIndex(
            model_name="account",
            index=models.Index(fields=["restaurant", "code"], name="accounting_acct_rest_code_idx"),
        ),
        migrations.AddIndex(
            model_name="account",
            index=models.Index(fields=["parent_account"], name="accounting_acct_parent_idx"),
        ),
        migrations.AddIndex(
            model_name="account",
            index=models.Index(fields=["account_type", "account_subtype"], name="accounting_acct_type_sub_idx"),
        ),

        # =====================================================================
        # AccountingSettings
        # =====================================================================
        migrations.CreateModel(
            name="AccountingSettings",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("restaurant", models.OneToOneField(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="accounting_settings",
                    to="organizations.restaurant",
                )),
                ("default_sales_account", models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="+",
                    to="accounting.account",
                )),
                ("default_discount_account", models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="+",
                    to="accounting.account",
                )),
                ("default_cash_account", models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="+",
                    to="accounting.account",
                )),
                ("default_bank_account", models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="+",
                    to="accounting.account",
                )),
                ("default_accounts_receivable", models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="+",
                    to="accounting.account",
                )),
                ("default_inventory_account", models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="+",
                    to="accounting.account",
                )),
                ("default_card_clearing_account", models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="+",
                    to="accounting.account",
                )),
                ("default_upi_clearing_account", models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="+",
                    to="accounting.account",
                )),
                ("default_accounts_payable", models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="+",
                    to="accounting.account",
                )),
                ("default_tax_payable", models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="+",
                    to="accounting.account",
                )),
                ("default_cogs_account", models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="+",
                    to="accounting.account",
                )),
                ("default_rounding_account", models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="+",
                    to="accounting.account",
                )),
                ("retained_earnings_account", models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="+",
                    to="accounting.account",
                )),
            ],
            options={"verbose_name": "Accounting Settings", "verbose_name_plural": "Accounting Settings"},
        ),

        # =====================================================================
        # JournalSequence
        # =====================================================================
        migrations.CreateModel(
            name="JournalSequence",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("last_sequence", models.PositiveIntegerField(default=0)),
                ("restaurant", models.OneToOneField(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="journal_sequence",
                    to="organizations.restaurant",
                )),
            ],
            options={"verbose_name": "Journal Sequence", "verbose_name_plural": "Journal Sequences"},
        ),

        # =====================================================================
        # JournalEntry
        # =====================================================================
        migrations.CreateModel(
            name="JournalEntry",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("entry_number", models.CharField(db_index=True, max_length=20)),
                ("entry_date", models.DateField(db_index=True)),
                ("description", models.TextField()),
                ("source_type", models.CharField(
                    choices=[
                        ("BILL", "Bill"), ("PAYMENT", "Payment"),
                        ("PAYMENT_REFUND", "Payment Refund"),
                        ("SUPPLIER_INVOICE", "Supplier Invoice"),
                        ("EXPENSE", "Expense"),
                        ("INVENTORY_CONSUMPTION", "Inventory Consumption"),
                        ("CONSUMPTION_REVERSAL", "Consumption Reversal"),
                        ("PAYABLE_PAYMENT", "Payable Payment"),
                        ("MANUAL", "Manual"),
                        ("PERIOD_CLOSE", "Period Close"),
                    ],
                    db_index=True, default="MANUAL", max_length=30,
                )),
                ("source_id", models.UUIDField(blank=True, db_index=True, null=True)),
                ("reference_type", models.CharField(blank=True, db_index=True, max_length=30)),
                ("reference_id", models.UUIDField(blank=True, db_index=True, null=True)),
                ("status", models.CharField(
                    choices=[
                        ("DRAFT", "Draft"), ("POSTED", "Posted"),
                        ("REVERSED", "Reversed"), ("VOID", "Void"),
                    ],
                    db_index=True, default="DRAFT", max_length=10,
                )),
                ("posted_at", models.DateTimeField(blank=True, null=True)),
                ("reversed_at", models.DateTimeField(blank=True, null=True)),
                ("reversal_reason", models.TextField(blank=True)),
                ("restaurant", models.ForeignKey(
                    db_index=True,
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="journal_entries",
                    to="organizations.restaurant",
                )),
                ("branch", models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="journal_entries",
                    to="organizations.branch",
                )),
                ("accounting_period", models.ForeignKey(
                    db_index=True,
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="journal_entries",
                    to="accounting.accountingperiod",
                )),
                ("created_by", models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="created_journal_entries",
                    to=settings.AUTH_USER_MODEL,
                )),
                ("posted_by", models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="posted_journal_entries",
                    to=settings.AUTH_USER_MODEL,
                )),
                ("reversed_by", models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="reversed_journal_entries",
                    to=settings.AUTH_USER_MODEL,
                )),
                ("reversal_of", models.OneToOneField(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="reversal_entry",
                    to="accounting.journalentry",
                )),
            ],
            options={"verbose_name": "Journal Entry", "verbose_name_plural": "Journal Entries", "ordering": ["-entry_date", "-created_at"]},
        ),
        migrations.AddConstraint(
            model_name="journalentry",
            constraint=models.UniqueConstraint(
                fields=["restaurant", "entry_number"],
                name="unique_journal_entry_number_per_restaurant",
            ),
        ),
        migrations.AddConstraint(
            model_name="journalentry",
            constraint=models.UniqueConstraint(
                fields=["source_type", "source_id"],
                condition=models.Q(
                    status__in=["POSTED"],
                    source_type__in=[
                        "BILL", "PAYMENT", "PAYMENT_REFUND",
                        "SUPPLIER_INVOICE", "EXPENSE",
                        "INVENTORY_CONSUMPTION", "CONSUMPTION_REVERSAL",
                    ],
                ),
                name="unique_primary_posting_per_source",
            ),
        ),
        migrations.AddIndex(
            model_name="journalentry",
            index=models.Index(fields=["restaurant", "entry_date"], name="accounting_je_rest_date_idx"),
        ),
        migrations.AddIndex(
            model_name="journalentry",
            index=models.Index(fields=["restaurant", "status"], name="accounting_je_rest_status_idx"),
        ),
        migrations.AddIndex(
            model_name="journalentry",
            index=models.Index(fields=["restaurant", "accounting_period"], name="accounting_je_rest_period_idx"),
        ),
        migrations.AddIndex(
            model_name="journalentry",
            index=models.Index(fields=["source_type", "source_id"], name="accounting_je_source_idx"),
        ),
        migrations.AddIndex(
            model_name="journalentry",
            index=models.Index(fields=["entry_date", "status"], name="accounting_je_date_status_idx"),
        ),
        migrations.AddIndex(
            model_name="journalentry",
            index=models.Index(fields=["branch", "entry_date"], name="accounting_je_branch_date_idx"),
        ),

        # =====================================================================
        # JournalEntryLine
        # =====================================================================
        migrations.CreateModel(
            name="JournalEntryLine",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("description", models.CharField(blank=True, max_length=300)),
                ("debit_amount", models.DecimalField(decimal_places=2, default="0.00", max_digits=14)),
                ("credit_amount", models.DecimalField(decimal_places=2, default="0.00", max_digits=14)),
                ("reference_type", models.CharField(blank=True, db_index=True, max_length=30)),
                ("reference_id", models.UUIDField(blank=True, db_index=True, null=True)),
                ("journal_entry", models.ForeignKey(
                    db_index=True,
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="lines",
                    to="accounting.journalentry",
                )),
                ("account", models.ForeignKey(
                    db_index=True,
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="journal_lines",
                    to="accounting.account",
                )),
            ],
            options={"verbose_name": "Journal Entry Line", "verbose_name_plural": "Journal Entry Lines", "ordering": ["created_at"]},
        ),
        migrations.AddConstraint(
            model_name="journalentryline",
            constraint=models.CheckConstraint(
                check=models.Q(debit_amount__gte=0),
                name="je_line_debit_non_negative",
            ),
        ),
        migrations.AddConstraint(
            model_name="journalentryline",
            constraint=models.CheckConstraint(
                check=models.Q(credit_amount__gte=0),
                name="je_line_credit_non_negative",
            ),
        ),
        migrations.AddIndex(
            model_name="journalentryline",
            index=models.Index(fields=["journal_entry", "account"], name="accounting_jel_je_acct_idx"),
        ),
        migrations.AddIndex(
            model_name="journalentryline",
            index=models.Index(fields=["account", "created_at"], name="accounting_jel_acct_date_idx"),
        ),
        migrations.AddIndex(
            model_name="journalentryline",
            index=models.Index(fields=["reference_type", "reference_id"], name="accounting_jel_ref_idx"),
        ),

        # =====================================================================
        # AccountingAuditLog
        # =====================================================================
        migrations.CreateModel(
            name="AccountingAuditLog",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("action", models.CharField(db_index=True, max_length=60)),
                ("entity_type", models.CharField(db_index=True, max_length=50)),
                ("entity_id", models.UUIDField(blank=True, db_index=True, null=True)),
                ("old_status", models.CharField(blank=True, max_length=30)),
                ("new_status", models.CharField(blank=True, max_length=30)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("actor", models.ForeignKey(
                    db_index=True,
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="accounting_audit_logs",
                    to=settings.AUTH_USER_MODEL,
                )),
                ("restaurant", models.ForeignKey(
                    db_index=True,
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="accounting_audit_logs",
                    to="organizations.restaurant",
                )),
                ("branch", models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="accounting_audit_logs",
                    to="organizations.branch",
                )),
            ],
            options={"verbose_name": "Accounting Audit Log", "verbose_name_plural": "Accounting Audit Logs", "ordering": ["-created_at"]},
        ),
        migrations.AddIndex(
            model_name="accountingauditlog",
            index=models.Index(fields=["restaurant", "action"], name="accounting_aal_rest_action_idx"),
        ),
        migrations.AddIndex(
            model_name="accountingauditlog",
            index=models.Index(fields=["restaurant", "created_at"], name="accounting_aal_rest_date_idx"),
        ),
        migrations.AddIndex(
            model_name="accountingauditlog",
            index=models.Index(fields=["entity_type", "entity_id"], name="accounting_aal_entity_idx"),
        ),
        migrations.AddIndex(
            model_name="accountingauditlog",
            index=models.Index(fields=["actor", "created_at"], name="accounting_aal_actor_date_idx"),
        ),
    ]
