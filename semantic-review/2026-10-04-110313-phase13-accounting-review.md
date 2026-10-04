# Phase 13 Accounting Ledger — Pre-commit Correctness Review

This review covers the double-entry bookkeeping implementation added in Phase 13: `accounting/models.py`, `accounting/services.py`, `accounting/signals.py`, `accounting/accounting_rules.py`, `accounting/selectors.py`, `accounting/migrations/0001_initial.py`, and the `Payable.refresh_status` method in `financials/models.py`. The implementation is substantial and generally well-structured — the immutability design, idempotency guards, and concurrency-safe sequence generation are all solid. The concerns below are targeted correctness issues, not architecture feedback.

**Watch for:**
- **confirmed** — `_post_from_line_specs` bypasses `JournalService.validate_entry` and instead calls only `validate_journal_entry_balanced` directly; the period-open and entry-date-in-period checks are **not run** on automatic postings.
- **confirmed** — Signals fire inside `transaction.atomic`. If `AccountingPostingService` raises (no open period, misconfigured settings), the exception is swallowed, the source transaction succeeds, and accounting is silently never posted with no way to detect or retry the gap.
- **confirmed** — `AccountingAuditLog.save()` uses a DB query to detect updates; `_state.adding` is the correct check and the current approach has a race-condition window.
- **confirmed** — `get_account_statement` opening balance uses `date_to=date_from` (inclusive), double-counting transactions on the start date.

**Verdict**: NEEDS_CHANGES

---

## High-level view

The automatic posting pipeline (`_post_from_line_specs`) is a fast path that skips `validate_entry` and calls only the balance check. This means every automatic posting (bill, payment, expense, supplier invoice, COGS) posts without verifying the period is still open or that the entry date falls within it. Manual entries via `JournalService.post_entry` run full validation; automatic ones don't. The gap is silent — no error is raised, a COGS or bill posting can land in a closed period.

The `post_save` signal design deliberately swallows exceptions so source transactions are never blocked. The trade-off is correct for availability, but the timing is wrong: Django signals fire synchronously within `transaction.atomic`, so accounting runs before the outer commit. A billing-layer constraint or post-signal middleware raising after the signal fires can roll back the bill while leaving accounting posted — there is no compensating mechanism.

The `unique_primary_posting_per_source` partial unique constraint covers `BILL`, `PAYMENT`, `PAYMENT_REFUND`, `SUPPLIER_INVOICE`, `EXPENSE`, and `INVENTORY_CONSUMPTION` — but not `CONSUMPTION_REVERSAL`. The model and migration are consistent with each other on this; it appears to be a deliberate omission. However, `CONSUMPTION_REVERSAL` postings are only protected by the application-level idempotency check (`_get_existing_posting` + `validate_no_duplicate_posting`) with no DB-level backstop. If the intent was to protect reversals too, add `CONSUMPTION_REVERSAL` to the constraint in both `models.py` and the migration.

The `build_bill_lines` accounting rule omits the discount debit line. The docstring describes `Dr Sales Discount (if any)` as an optional leg, but there is no code that adds it. When `bill.discount_amount > 0`, the debit side is only `grand_total` (Accounts Receivable), and the credit side is `taxable_amount + tax_amount`. Since `grand_total = taxable_amount + tax_amount` and discounts are already baked into `taxable_amount`, the entry balances — but the discount is never explicitly recognised in a Discount expense account. Whether this is a deliberate simplification or a missing line depends on the intended accounting policy; it is flagged because the docstring promises a discount leg that doesn't exist.

The `AccountingAuditLog` immutability check fires a SELECT on every `save()`. The correct guard is Django's `self._state.adding`, which is false only when saving an existing instance. The current approach has a window where a freshly-created object with an assigned PK could conceivably be saved a second time in the same transaction before the first commit is visible to a concurrent reader — in practice unlikely with UUIDs, but `_state.adding` is both cheaper and semantically correct.

The `get_account_statement` opening-balance query uses `date_to=date_from` (inclusive), meaning the opening balance includes transactions on the start date itself, and those same transactions also appear in the transaction list. Depending on whether "opening balance" means "balance at close of day before `date_from`" or "balance up to and including `date_from`", this double-counts the first day's movements. This is a borderline bug — worth verifying against the intended statement semantics.

---

<details>
<summary>Issues (6)</summary>

1. **Automatic posting skips period and date validation** — `_post_from_line_specs` calls only `validate_journal_entry_balanced`; it does not call `validate_period_is_open` or `validate_entry_date_in_period`. Add these two calls in `_post_from_line_specs` after the balance check, or route automatic postings through the full `JournalService.validate_entry`.

2. **Silent accounting gaps when signal handler catches an exception** — If `AccountingPostingService` raises inside a signal handler (no open period, unconfigured settings, zero COGS lines), the exception is swallowed, the source record finalises successfully, and accounting is never posted with no indication. Wrap signal dispatch with `transaction.on_commit` and add a "pending accounting" flag or outbox record to enable detection and retry.

3. **`CONSUMPTION_REVERSAL` not covered by DB-level uniqueness constraint** — The `unique_primary_posting_per_source` partial constraint covers 6 source types but excludes `CONSUMPTION_REVERSAL`. Only application-layer guards protect against duplicate reversal postings. Add `"CONSUMPTION_REVERSAL"` to the `source_type__in` condition in both `models.py` and the migration if DB-level protection is intended.

4. **`AccountingAuditLog.save()` immutability check is racy** — `if self.pk and AccountingAuditLog.objects.filter(pk=self.pk).exists()` fires a SELECT that may not see an uncommitted row from the same transaction. Replace with `if not self._state.adding:` which is Django's idiomatic, transaction-safe way to distinguish insert from update.

5. **`build_bill_lines` missing discount debit leg** — The docstring specifies `Dr Sales Discount (if any)` but no code adds this line when `bill.discount_amount > 0`. Either add the line (debit discount account, credit amount = `discount_amount`) and require `default_discount_account` to be configured, or remove the docstring claim and document that discounts are absorbed into `taxable_amount` by the billing layer.

6. **`get_account_statement` opening balance is inclusive of `date_from`** — `_account_net_balance(..., date_to=date_from)` includes transactions on the start date in the opening balance, and those transactions also appear in the period lines — double-counting the first day. If "opening balance" means balance at end-of-day before `date_from`, use `date_to=date_from - timedelta(days=1)`.

</details>

---

<details>
<summary>Details</summary>

### Automatic posting bypasses period and date guards

`_post_from_line_specs` is the shared internal helper used by every `AccountingPostingService.post_*` method. After building lines, it calls:

```python
validate_journal_entry_balanced(entry)
```

That's the only validator. `validate_period_is_open` and `validate_entry_date_in_period` — both called in `JournalService.validate_entry` — are not invoked. This means it's possible to post a bill or expense into a period that was closed between when the bill was finalised and when the signal handler ran. The entry will be created, posted, and immutable with no complaint.

The manual posting path (`JournalService.post_entry`) calls `JournalService.validate_entry` which runs all guards. The gap exists only on the automatic path. The fix is straightforward: add the two missing validator calls in `_post_from_line_specs`:

```python
validate_period_is_open(period)
validate_entry_date_in_period(entry_date, period)
validate_journal_entry_balanced(entry)
```

### Signal timing and accounting gaps

The signals swallow exceptions deliberately so source transactions are never blocked. The failure mode this creates is subtle but confirmed: if `AccountingPostingService` raises — no open period found for the entry date, `AccountingSettings` not configured, zero consumption lines — the exception is caught by the handler and logged. The bill or payment finalises successfully. There is no retry mechanism, no flag on the source record, and no way to query "bills with missing accounting postings". The gap is invisible until someone notices the trial balance doesn't tie.

The recommended fix is `transaction.on_commit`: dispatch the accounting call only after the source transaction commits. This also eliminates the timing issue where the accounting posting runs before the source record is visible to other connections:

```python
from django.db import transaction

@receiver(post_save, sender="billing.Bill")
def on_bill_finalized(sender, instance, created, **kwargs):
    from billing.models import BillStatus
    if instance.status != BillStatus.FINALIZED or not instance.finalized_by_id:
        return
    def _post():
        try:
            from accounting.services import AccountingPostingService
            AccountingPostingService.post_bill(instance, instance.finalized_by)
        except Exception as exc:
            logger.error("Accounting posting failed for bill %s: %s",
                         instance.bill_number, exc, exc_info=True)
    transaction.on_commit(_post)
```

### `unique_primary_posting_per_source` — `CONSUMPTION_REVERSAL` unprotected at DB level

Both the model and migration agree: `CONSUMPTION_REVERSAL` is not in the `source_type__in` condition. The application-level guards (`_get_existing_posting` + `validate_no_duplicate_posting`) do check for duplicate reversal postings, but a race condition between two concurrent reversal attempts can pass both application checks before either reaches the DB constraint. Adding `"CONSUMPTION_REVERSAL"` to the constraint in both places closes this window.

### `AccountingAuditLog` immutability guard

```python
def save(self, *args, **kwargs):
    if self.pk and AccountingAuditLog.objects.filter(pk=self.pk).exists():
        raise ValueError("AccountingAuditLog records are immutable.")
    super().save(*args, **kwargs)
```

`self._state.adding` is False precisely when Django is about to issue an UPDATE — which is the condition this guard is trying to catch. The current code issues a SELECT for every audit log save, and in a transaction the newly-inserted row may not be visible to the filter until committed (depending on isolation level). The correct implementation:

```python
def save(self, *args, **kwargs):
    if not self._state.adding:
        raise ValueError("AccountingAuditLog records are immutable.")
    super().save(*args, **kwargs)
```

### `build_bill_lines` discount gap

```python
def build_bill_lines(bill, settings):
    """
    ...
    Dr  Sales Discount (if any)      (discount_amount)   [optional leg]
    ...
    """
```

The code builds three lines: Dr Receivable, Cr Sales, Cr Tax Payable (plus optional rounding). The discount line described in the docstring is absent. The entry does balance because `taxable_amount = subtotal - discount_amount` is already the discounted revenue figure — the discount has been absorbed into the revenue line. So there's no accounting error, but there's also no visibility into discount cost. If the `default_discount_account` in `AccountingSettings` is populated, it goes unused. The docstring needs to either match the code or the code needs to match the docstring.

### `get_account_statement` opening balance boundary

```python
opening_balance = _account_net_balance(
    account.restaurant, account, date_to=date_from
)
```

`_account_net_balance` with `date_to=date_from` includes all lines where `entry_date <= date_from`. The transaction list below it then includes lines where `entry_date >= date_from`. Any line on exactly `date_from` appears in both: it's counted in the opening balance *and* listed as a transaction in the period, so its contribution is double-counted in the closing balance.

The standard accounting statement convention is: opening balance = all movements strictly before `date_from`, and the period covers `date_from` to `date_to` inclusive. The fix:

```python
from datetime import timedelta
opening_balance = _account_net_balance(
    account.restaurant, account, date_to=date_from - timedelta(days=1)
)
```



</details>

---

<details>
<summary>File map</summary>

| File | What was examined |
|---|---|
| `accounting/models.py` | `JournalEntry` partial unique constraint; `AccountingAuditLog.save()` immutability guard; `JournalEntryLine.clean()` XOR rule |
| `accounting/services.py` | `_post_from_line_specs` validator calls; `post_payable_payment` payable update; `generate_journal_number` savepoint nesting; `AccountingPostingService` idempotency pattern |
| `accounting/signals.py` | Signal timing relative to source transaction commit; exception swallowing behaviour |
| `accounting/accounting_rules.py` | `build_bill_lines` discount leg; `build_supplier_invoice_lines` tax debit balance; `build_payable_payment_lines` structure |
| `accounting/selectors.py` | `get_account_statement` opening balance boundary; `get_account_balance` date semantics |
| `accounting/validators.py` | `validate_journal_entry_balanced` implementation; `validate_no_duplicate_posting` logic |
| `accounting/migrations/0001_initial.py` | Index name lengths; `unique_primary_posting_per_source` condition vs. model |
| `financials/models.py` | `Payable.refresh_status()` existence and logic |

Full diff not available (local review, not PR-based).

</details>
