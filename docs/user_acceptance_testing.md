# RestaurantFlow — User Acceptance Testing (UAT) Checklist
## Phase 26 — Pre-Release UAT

---

## Overview

This document provides step-by-step UAT scenarios for each system role. Each scenario follows a realistic operational flow a real user would take. Testers record pass/fail and severity of any finding.

---

## Role-Based UAT Scenarios

---

### 1. Company Head

**Scenario: Onboard a new restaurant and owner**

| # | Step | Expected Result | Pass/Fail |
|---|---|---|---|
| 1 | Log in with Company Head credentials | Dashboard loads; restaurant list visible | |
| 2 | Navigate to Restaurants → Create New | Form allows name, code, timezone | |
| 3 | Fill restaurant details and submit | Restaurant created; appears in list | |
| 4 | Navigate to Users → Create User for new owner | Owner account created | |
| 5 | Assign Restaurant Owner role scoped to new restaurant | Assignment visible in user profile | |
| 6 | Log out and log in as the new owner | Owner dashboard shows the assigned restaurant only | |
| 7 | Try to access another company's data as Company Head | 403 or empty result returned | |

---

### 2. Restaurant Owner

**Scenario: Set up branches, managers, and counters**

| # | Step | Expected Result | Pass/Fail |
|---|---|---|---|
| 1 | Log in as Restaurant Owner | Dashboard shows owned restaurants | |
| 2 | Navigate to Branches → Create Branch | Branch form loads | |
| 3 | Fill branch name, code, address; submit | Branch created; appears in list | |
| 4 | Navigate to Users → Create Manager | Manager account created | |
| 5 | Assign Restaurant Manager role scoped to the branch | Assignment visible | |
| 6 | Navigate to Menu → Create Category and Items | Menu items created with tax rates | |
| 7 | Assign menu items to the branch | Items visible in branch menu | |

---

### 3. Restaurant Manager

**Scenario: Configure counter, open shift, and monitor operations**

| # | Step | Expected Result | Pass/Fail |
|---|---|---|---|
| 1 | Log in as Restaurant Manager | Dashboard shows managed branch | |
| 2 | Navigate to Counters → Create Counter | Counter created | |
| 3 | Assign Cashier to the counter | Assignment saved | |
| 4 | Navigate to Reports → Today's summary | Branch sales summary visible | |
| 5 | View active orders on branch | Kitchen and POS orders listed | |
| 6 | Apply discount override to a bill (if permitted) | Discount applied; bill total updated | |
| 7 | Try to access another branch's data | 403 or empty result returned | |

---

### 4. Cashier

**Scenario: Complete a full POS order cycle**

| # | Step | Expected Result | Pass/Fail |
|---|---|---|---|
| 1 | Log in as Cashier | POS dashboard loads | |
| 2 | Open counter session with opening cash amount | Session opens; counter shows OPEN | |
| 3 | Create new TAKEAWAY order | Order created in DRAFT | |
| 4 | Add 2 menu items to the order | Items added; subtotal calculated | |
| 5 | Confirm the order | Status changes to CONFIRMED; kitchen receives order | |
| 6 | Generate bill for the confirmed order | Bill created with correct tax and total | |
| 7 | Accept cash payment for the full bill amount | Payment recorded as COMPLETED | |
| 8 | Print receipt | Receipt shows bill number, items, tax, payment | |
| 9 | Close counter session with closing cash | Session closed; cash reconciliation summary shown | |

---

### 5. Waiter

**Scenario: Manage dine-in table orders**

| # | Step | Expected Result | Pass/Fail |
|---|---|---|---|
| 1 | Log in as Waiter | Table management view loads | |
| 2 | Open a table session for Table 5 | Table session opens | |
| 3 | Create new DINE_IN order for Table 5 | Order linked to table session | |
| 4 | Add items to the order and confirm | Kitchen receives the order | |
| 5 | View kitchen status updates in real time | WebSocket updates show order status | |
| 6 | Notify cashier when food is ready to bill | Bill ready indicator set | |
| 7 | Try to access cashier billing functions | 403 returned (Waiter cannot finalize bills) | |

---

### 6. Kitchen Staff

**Scenario: Accept and complete kitchen orders**

| # | Step | Expected Result | Pass/Fail |
|---|---|---|---|
| 1 | Log in as Kitchen Staff | Kitchen display/list loads | |
| 2 | View incoming kitchen orders | New orders visible with item details | |
| 3 | Accept Order #001 | Status changes to ACCEPTED | |
| 4 | Mark order as PREPARING | Status updates; timestamp recorded | |
| 5 | Mark order as READY | Status updates; waiter/cashier notified | |
| 6 | Try to access financial reports | 403 returned | |

---

### 7. Inventory Staff

**Scenario: Receive goods and check stock levels**

| # | Step | Expected Result | Pass/Fail |
|---|---|---|---|
| 1 | Log in as Inventory Staff | Inventory dashboard loads | |
| 2 | Navigate to Purchase Orders — view approved PO | PO details visible | |
| 3 | Record goods receipt for the PO | Stock balance increases; weighted average cost updates | |
| 4 | Check stock balance for Tomato at Main Store | Available quantity shown correctly | |
| 5 | Record a stock wastage (spoiled vegetables) | Wastage request created; pending approval | |
| 6 | Try to access payroll or financial entries | 403 returned | |

---

### 8. Accountant

**Scenario: Record expense and view financial reports**

| # | Step | Expected Result | Pass/Fail |
|---|---|---|---|
| 1 | Log in as Accountant | Financial dashboard loads | |
| 2 | Navigate to Expenses → Create Expense | Expense form with categories loads | |
| 3 | Fill in electricity bill: amount, category, date | Expense saved in DRAFT | |
| 4 | Submit expense for approval | Status changes to SUBMITTED | |
| 5 | View journal entries for the month | Posted journal entries listed | |
| 6 | Verify debit == credit on a posted entry | Sum of debits == sum of credits | |
| 7 | Generate P&L statement for current month | Statement loads with revenue and expenses | |

---

## Feedback Classification

After completing UAT scenarios, record findings using this classification:

| Severity | Definition | Examples |
|---|---|---|
| **Critical** | System unusable or data loss risk | Cannot log in, payment creates duplicate, data from another tenant visible |
| **Major** | Key workflow blocked but workaround exists | Bill total incorrect, stock not deducted on order completion |
| **Minor** | Feature works but has edge case failures | Decimal rounding off by 1 paisa, pagination breaks on page 10 |
| **Usability** | Confusing UX, no functional impact | Button label unclear, success message missing, loading state absent |
| **Enhancement** | Desired feature not in scope | Shortcut keys, bulk import, dark mode |

---

## UAT Feedback Template

```
Finding #: [AUTO]
Scenario: [e.g., Cashier / Step 7]
Severity: [Critical / Major / Minor / Usability / Enhancement]
Description: [What happened]
Expected: [What should have happened]
Steps to reproduce: [Numbered steps]
Screenshot/log: [Attach if available]
Reported by: [Tester name]
Date: [Date]
```

---

## UAT Sign-Off Criteria

Before production release, the following must be satisfied:
- All **Critical** findings resolved
- All **Major** findings resolved or accepted with documented workaround
- At least 2 testers per role complete all UAT scenarios
- UAT sign-off obtained from each department head (Operations, Finance, IT)
