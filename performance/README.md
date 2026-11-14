# RestaurantFlow — Load Testing with Locust

> **WARNING: NEVER run load tests against the production environment.**
> Load tests create large volumes of synthetic transactions that corrupt
> production data, trigger alerts, and can cause real financial records to
> become inconsistent.  Always use a dedicated load-test database.

## Overview

This directory contains Locust scenarios that exercise the four main user
roles in RestaurantFlow under concurrent load.

| User class          | Scenarios                                  | Default weight |
|---------------------|--------------------------------------------|----------------|
| `RestaurantStaffUser` | Menu catalog, order creation, bill finalize | 4             |
| `KitchenUser`         | Order status updates                        | 2             |
| `ManagerUser`         | Inventory & reporting dashboards            | 1             |
| `PaymentUser`         | Concurrent payment attempts (critical)      | 2             |

## Prerequisites

### 1. Install Locust

```bash
pip install locust
```

Locust requires Python ≥ 3.9.  Install into the same virtualenv as the
backend or a dedicated one.

### 2. Seed the test database

Follow the instructions in `performance/test_data/README.md` to populate
a non-production database with realistic fixture data.

### 3. Set environment variables

```bash
# Target backend host (overridden by --host at runtime)
export LOAD_TEST_BRANCH_ID="<uuid of a seeded branch>"

# Auth credentials for each persona
export LOAD_TEST_STAFF_EMAIL="staff@loadtest.local"
export LOAD_TEST_STAFF_PASSWORD="<password>"

export LOAD_TEST_KITCHEN_EMAIL="kitchen@loadtest.local"
export LOAD_TEST_KITCHEN_PASSWORD="<password>"

export LOAD_TEST_MANAGER_EMAIL="manager@loadtest.local"
export LOAD_TEST_MANAGER_PASSWORD="<password>"

export LOAD_TEST_PAYMENT_EMAIL="cashier@loadtest.local"
export LOAD_TEST_PAYMENT_PASSWORD="<password>"

# Comma-separated list of FINALIZED bill UUIDs for concurrent payment tests
export LOAD_TEST_BILL_IDS="<uuid1>,<uuid2>,<uuid3>"

# Optional: date range for reporting queries
export LOAD_TEST_DATE_FROM="2024-01-01"
export LOAD_TEST_DATE_TO="2024-12-31"
```

## Running tests

### Interactive web UI

```bash
locust -f performance/locustfile.py --host http://localhost:8000
```

Then open http://localhost:8089 and start the swarm from the browser.

### Headless (CI / scripted)

```bash
locust -f performance/locustfile.py \
    --headless \
    --host http://localhost:8000 \
    -u 50 \
    -r 5 \
    --run-time 60s
```

Options:
- `-u 50` — total virtual users to spawn
- `-r 5` — users spawned per second (ramp-up rate)
- `--run-time 60s` — stop after 60 seconds

### Payment contention scenario

To stress the concurrent overpayment guard specifically, spawn many
`PaymentUser` instances:

```bash
locust -f performance/locustfile.py \
    --headless \
    --host http://localhost:8000 \
    --class-picker PaymentUser \
    -u 20 \
    -r 10 \
    --run-time 30s
```

### Multi-process (maximise contention)

```bash
locust -f performance/locustfile.py \
    --master \
    --host http://localhost:8000 &

locust -f performance/locustfile.py --worker &
locust -f performance/locustfile.py --worker &
```

## Output

Locust writes a CSV summary when run headless with `--csv`:

```bash
locust -f performance/locustfile.py --headless -u 50 -r 5 \
    --run-time 60s --csv results/run_$(date +%Y%m%d_%H%M%S)
```

Files written: `results/run_<ts>_stats.csv`, `_failures.csv`, `_history.csv`.

## Interpreting results

See `docs/load_testing.md` for a full guide to reading Locust output,
acceptable thresholds, and correlating slow endpoints with Django Debug
Toolbar and `pg_stat_statements`.
