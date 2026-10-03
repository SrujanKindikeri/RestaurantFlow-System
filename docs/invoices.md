# Invoices / Receipts — RestaurantFlow

## Receipt Data

The `/api/billing/bills/{id}/receipt/` endpoint returns structured JSON for receipt rendering.

## Receipt Fields

```json
{
  "bill_number": "B-2026-000001",
  "order_number": "C01-20261003-0001",
  "order_type": "COUNTER",
  "date": "2026-10-03T12:30:00Z",
  "finalized_at": "2026-10-03T12:31:00Z",
  "currency": "INR",
  "restaurant": {
    "name": "Spice Garden",
    "address": "...", "city": "...", "state": "...",
    "postal_code": "...", "phone": "...", "email": "...",
    "tax_id": "GSTIN123456"
  },
  "branch": {
    "name": "LPU Campus",
    "address": "...", ...
  },
  "cashier": "Counter Cashier",
  "table_number": null,
  "counter_code": "C01",
  "receipt_header": "Welcome to Spice Garden",
  "receipt_footer": "Thank you for visiting!",
  "items": [
    {
      "name": "Chicken Biryani",
      "sku": "BIRYA-001",
      "quantity": "2.000",
      "unit_price": "250.00",
      "gross_amount": "500.00",
      "discount_amount": "0.00",
      "taxable_amount": "500.00",
      "tax_rate": "5.000",
      "tax_code": "GST_5",
      "tax_amount": "25.00",
      "total_amount": "525.00"
    }
  ],
  "subtotal": "620.00",
  "discount_amount": "0.00",
  "discount_type": null,
  "discount_value": "0.00",
  "taxable_amount": "620.00",
  "tax_breakdown": {"GST_5": "25.00", "ZERO_TAX": "0.00"},
  "tax_amount": "25.00",
  "rounding_amount": "0.00",
  "grand_total": "645.00",
  "status": "FINALIZED",
  "correction_count": 0
}
```

## Sample Receipt Layout

```
=====================================
       SPICE GARDEN
       LPU Campus
       123 University Ave, Phagwara
       Ph: 9876543210
       GSTIN: 12ABCDE1234F1Z5
=====================================
Bill No.   B-2026-000001
Order No.  C01-20261003-0001
Type       COUNTER (C01)
Date       03/10/2026 12:31 PM
Cashier    Counter Cashier
-------------------------------------
Chicken Biryani         2 × ₹250.00
                               ₹500.00
  GST_5 5%                   ₹25.00

French Fries            1 × ₹120.00
                               ₹120.00
  ZERO_TAX 0%                  ₹0.00

-------------------------------------
Subtotal                      ₹620.00
Tax (GST_5)                    ₹25.00
Tax (ZERO_TAX)                  ₹0.00
-------------------------------------
TOTAL                         ₹645.00
-------------------------------------
[ Payment — Phase 9 ]
-------------------------------------
       Thank you for visiting!
    Powered by RestaurantFlow
=====================================
```

## Print Support

The `BillReceiptPage` React component:
- Renders a print-styled layout (A4 + receipt-width friendly)
- Uses `window.print()` for browser printing
- Hides navigation chrome in print media query
- Does **not** use any vendor-specific printer SDK

## Payment Section

The payment section of the receipt is intentionally blank in Phase 8.
Phase 9 will add:
- Payment method (Cash / Card / UPI)
- Paid amount
- Change given
- Transaction reference
