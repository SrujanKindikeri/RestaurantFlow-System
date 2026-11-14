# Load Test Seed Data

Seed the database before running any load test so the locust users have
real fixtures to work with. Using live-looking data produces more realistic
query plans and cache behaviour than minimal synthetic rows.

## Target fixture size

| Object          | Recommended count |
|-----------------|-------------------|
| Organizations   | 1                 |
| Restaurants     | 2                 |
| Branches        | 4 (2 per restaurant) |
| Staff users     | 20 (mix of cashier, waiter, manager) |
| Menu categories | 10                |
| Menu items      | 60 (6 per category) |
| Active orders   | 50 (open, in-flight) |
| Bills           | 30 (mix of DRAFT and FINALIZED) |
| Inventory items | 40                |
| Stock balances  | 40 (one per item) |

## Seed users required by locust scenarios

The following users must exist and their credentials set as environment
variables (see `performance/README.md`):

| Environment variable | Role                  |
|----------------------|-----------------------|
| `LOAD_TEST_STAFF_EMAIL` / `LOAD_TEST_STAFF_PASSWORD`     | Branch staff (cashier + waiter) |
| `LOAD_TEST_KITCHEN_EMAIL` / `LOAD_TEST_KITCHEN_PASSWORD` | Kitchen tablet user             |
| `LOAD_TEST_MANAGER_EMAIL` / `LOAD_TEST_MANAGER_PASSWORD` | Branch or restaurant manager    |
| `LOAD_TEST_PAYMENT_EMAIL` / `LOAD_TEST_PAYMENT_PASSWORD` | Cashier with payment.create permission |

## Management command

If a `seed_load_test_data` management command exists in any app, run it:

```bash
cd backend
python manage.py seed_load_test_data --restaurant-count 2 --branch-count 4 \
    --staff-count 20 --menu-items 60 --orders 50
```

If the command does not exist yet, load a fixture:

```bash
python manage.py loaddata performance/test_data/load_test_fixture.json
```

Create the fixture from an already-seeded database with:

```bash
python manage.py dumpdata organizations accounts menu orders billing \
    payments inventory --indent 2 \
    > performance/test_data/load_test_fixture.json
```

## Expected DB state after seeding

- `organizations_organization`: ≥ 1 row
- `organizations_branch`: ≥ 4 rows
- `accounts_user`: ≥ 20 rows, all `is_active=True`
- `menu_menuitem`: ≥ 60 rows, all with an active price
- `orders_order`: ≥ 50 rows in CONFIRMED or DRAFT status
- `billing_bill`: ≥ 30 rows; at least 10 in FINALIZED status
- `inventory_stockbalance`: ≥ 40 rows with quantity > 0

## Notes

- Never seed against a production database.
- Delete seed data after the test run or use a dedicated load-test database.
- Branch UUIDs used in `LOAD_TEST_BRANCH_ID` must exist in the seeded DB.
