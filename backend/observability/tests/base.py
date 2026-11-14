# =============================================================================
# RestaurantFlow — Observability Test Base
# Phase 24
#
# Minimal fixtures scoped to the observability app. We deliberately avoid the
# heavier permission-seeded user fixtures used by other apps' tests so that
# these tests are robust to cross-test cache ordering and focus only on
# monitoring behaviour.
# =============================================================================

from django.test import TestCase
from organizations.models import Organization, Restaurant, Branch


def make_org(name="Obs Corp"):
    return Organization.objects.create(
        name=name, slug=f"obs-{name.lower().replace(' ', '-')}-{Organization.objects.count()}"
    )


def make_restaurant(org, name="Obs Garden"):
    return Restaurant.objects.create(organization=org, name=name, code=f"OG{name[:3].upper()}")


def make_branch(restaurant, name="Obs Branch"):
    return Branch.objects.create(restaurant=restaurant, name=name, code=f"OB{name[:3].upper()}")


class ObservabilityTestCase(TestCase):
    """Common base that resets the in-process metrics registry per test."""

    def setUp(self):
        from observability.metrics import REGISTRY
        REGISTRY.clear()
