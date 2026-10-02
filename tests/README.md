# RestaurantFlow — Test Structure

This directory holds cross-system and integration test organization.

Django unit and integration tests live inside each app's `tests.py`
(or a `tests/` package within the app for larger test suites).

## Running Backend Tests

```bash
cd backend
python manage.py test
```

## Structure (Current)

```
tests/
└── README.md
```

## Structure (Future — added per phase)

```
tests/
├── authentication/      ← Phase 3
├── organizations/       ← Phase 2
├── restaurants/         ← Phase 2
├── branches/            ← Phase 2
├── counters/            ← Phase 4
├── orders/              ← Phase 6
├── billing/             ← Phase 8
├── payments/            ← Phase 8
├── inventory/           ← Phase 10
└── analytics/           ← Phase 12
```

Each subdirectory will contain integration and end-to-end tests
relevant to that business domain.
