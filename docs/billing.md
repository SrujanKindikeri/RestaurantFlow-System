# Billing Architecture

See [phase-8.md](./phase-8.md) for the full Phase 8 implementation guide.

## Quick Reference

### Bill Number
Format: `B-{YYYY}-{seq:06d}` (e.g. `B-2026-000001`)
Sequence: annual per branch, concurrency-safe.

### Calculation Order
1. gross = qty × unit_price (from snapshot)
2. subtotal = sum(gross)
3. discount_amount (PERCENTAGE or FIXED_AMOUNT)
4. taxable_amount = subtotal − discount
5. tax per item (proportional after discount)
6. rounding (nearest integer, ROUND_HALF_UP)
7. grand_total = taxable + tax + rounding

### Key Files
| File | Purpose |
|------|---------|
| `billing/models.py` | Bill, BillItem, BillSequence, BillCorrectionRequest |
| `billing/services.py` | All business logic |
| `billing/utils.py` | Pure Decimal money helpers |
| `billing/validators.py` | Stateless validation functions |
| `billing/serializers.py` | DRF read/write serializers |
| `billing/views.py` | API views |
| `billing/urls.py` | URL patterns |
| `billing/access.py` | Scoped querysets (IDOR prevention) |
| `billing/permissions.py` | DRF permission classes |
| `billing/admin.py` | Django admin registration |
| `billing/tests/` | All test modules |
