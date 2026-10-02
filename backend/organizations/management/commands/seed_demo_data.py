# =============================================================================
# RestaurantFlow — Demo Data Seed Command
# Phase 2
#
# Usage:
#   python manage.py seed_demo_data
#   python manage.py seed_demo_data --reset   # clears existing demo data first
#
# ⚠️  FOR DEVELOPMENT AND TESTING ONLY.
#     Do NOT run this in a production environment.
# =============================================================================

import logging
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from organizations.models import (
    Organization,
    Restaurant,
    Branch,
    RestaurantSettings,
    BranchSettings,
)

logger = logging.getLogger("organizations")

DEMO_SLUG = "restaurantflow-foods-demo"


DEMO_DATA = {
    "organization": {
        "name": "RestaurantFlow Foods",
        "legal_name": "RestaurantFlow Foods Pvt Ltd",
        "slug": DEMO_SLUG,
        "email": "admin@restaurantflow.dev",
        "phone": "+91-9000000001",
        "address": "12 Tech Park, Sector 5",
        "city": "Bangalore",
        "state": "Karnataka",
        "country": "India",
        "postal_code": "560001",
        "tax_id": "29AABCT1332L1ZD",
        "currency": "INR",
        "timezone": "Asia/Kolkata",
    },
    "restaurants": [
        {
            "name": "Spice Garden",
            "code": "SPICE-001",
            "description": "Authentic South Indian cuisine with a modern twist.",
            "phone": "+91-9000000002",
            "email": "spicegarden@restaurantflow.dev",
            "city": "Bangalore",
            "state": "Karnataka",
            "country": "India",
            "settings": {
                "currency": "INR",
                "timezone": "Asia/Kolkata",
                "tax_enabled": True,
                "default_tax_rate": 5.00,
                "order_prefix": "SG",
            },
            "branches": [
                {
                    "name": "LPU Campus",
                    "code": "SG-LPU",
                    "address": "LPU Campus, Phagwara",
                    "city": "Phagwara",
                    "state": "Punjab",
                    "country": "India",
                    "postal_code": "144411",
                    "phone": "+91-9000000010",
                    "settings": {
                        "opening_time": "08:00:00",
                        "closing_time": "22:00:00",
                        "default_order_type": "dine_in",
                    },
                },
                {
                    "name": "Main Market",
                    "code": "SG-MKT",
                    "address": "42 Main Market Road",
                    "city": "Bangalore",
                    "state": "Karnataka",
                    "country": "India",
                    "postal_code": "560002",
                    "phone": "+91-9000000011",
                    "settings": {
                        "opening_time": "09:00:00",
                        "closing_time": "23:00:00",
                        "default_order_type": "takeaway",
                    },
                },
                {
                    "name": "City Center",
                    "code": "SG-CITY",
                    "address": "City Center Mall, 3rd Floor",
                    "city": "Bangalore",
                    "state": "Karnataka",
                    "country": "India",
                    "postal_code": "560003",
                    "phone": "+91-9000000012",
                    "settings": {
                        "opening_time": "10:00:00",
                        "closing_time": "22:00:00",
                        "default_order_type": "dine_in",
                    },
                },
            ],
        },
        {
            "name": "Urban Bites",
            "code": "URBAN-001",
            "description": "Contemporary street food and fusion snacks.",
            "phone": "+91-9000000003",
            "email": "urbanbites@restaurantflow.dev",
            "city": "Mumbai",
            "state": "Maharashtra",
            "country": "India",
            "settings": {
                "currency": "INR",
                "timezone": "Asia/Kolkata",
                "tax_enabled": True,
                "default_tax_rate": 5.00,
                "order_prefix": "UB",
            },
            "branches": [
                {
                    "name": "Downtown",
                    "code": "UB-DT",
                    "address": "88 Downtown Avenue",
                    "city": "Mumbai",
                    "state": "Maharashtra",
                    "country": "India",
                    "postal_code": "400001",
                    "phone": "+91-9000000020",
                    "settings": {
                        "opening_time": "11:00:00",
                        "closing_time": "23:00:00",
                        "default_order_type": "takeaway",
                    },
                },
                {
                    "name": "Airport Terminal 2",
                    "code": "UB-AIR",
                    "address": "CSIA Terminal 2, Airside",
                    "city": "Mumbai",
                    "state": "Maharashtra",
                    "country": "India",
                    "postal_code": "400099",
                    "phone": "+91-9000000021",
                    "settings": {
                        "opening_time": "05:00:00",
                        "closing_time": "23:59:00",
                        "default_order_type": "takeaway",
                    },
                },
            ],
        },
        {
            "name": "Royal Kitchen",
            "code": "ROYAL-001",
            "description": "Traditional Mughlai and North Indian cuisine.",
            "phone": "+91-9000000004",
            "email": "royalkitchen@restaurantflow.dev",
            "city": "Delhi",
            "state": "Delhi",
            "country": "India",
            "settings": {
                "currency": "INR",
                "timezone": "Asia/Kolkata",
                "tax_enabled": True,
                "default_tax_rate": 5.00,
                "order_prefix": "RK",
            },
            "branches": [
                {
                    "name": "Main Branch",
                    "code": "RK-MAIN",
                    "address": "1 Connaught Place",
                    "city": "New Delhi",
                    "state": "Delhi",
                    "country": "India",
                    "postal_code": "110001",
                    "phone": "+91-9000000030",
                    "settings": {
                        "opening_time": "12:00:00",
                        "closing_time": "23:00:00",
                        "default_order_type": "dine_in",
                    },
                },
                {
                    "name": "Lajpat Nagar",
                    "code": "RK-LN",
                    "address": "Central Market, Lajpat Nagar",
                    "city": "New Delhi",
                    "state": "Delhi",
                    "country": "India",
                    "postal_code": "110024",
                    "phone": "+91-9000000031",
                    "settings": {
                        "opening_time": "11:00:00",
                        "closing_time": "22:00:00",
                        "default_order_type": "dine_in",
                    },
                },
            ],
        },
    ],
}


class Command(BaseCommand):
    help = (
        "Seed the database with demo Organization / Restaurant / Branch data. "
        "FOR DEVELOPMENT AND TESTING ONLY."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete the existing demo organization before re-seeding.",
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.WARNING(
                "\n⚠️  seed_demo_data — DEVELOPMENT ONLY\n"
                "   Do NOT run in production.\n"
            )
        )

        if options["reset"]:
            self._reset_demo_data()

        try:
            with transaction.atomic():
                org = self._create_organization()
                for restaurant_data in DEMO_DATA["restaurants"]:
                    self._create_restaurant(org, restaurant_data)

            self.stdout.write(
                self.style.SUCCESS(
                    "\n✓ Demo data seeded successfully.\n"
                    f"  Organization : {DEMO_DATA['organization']['name']}\n"
                    f"  Restaurants  : {len(DEMO_DATA['restaurants'])}\n"
                    f"  Branches     : {sum(len(r['branches']) for r in DEMO_DATA['restaurants'])}\n"
                )
            )
        except Exception as exc:
            raise CommandError(f"Seeding failed: {exc}") from exc

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def _reset_demo_data(self):
        deleted, _ = Organization.objects.filter(slug=DEMO_SLUG).delete()
        if deleted:
            self.stdout.write(
                self.style.WARNING(f"  Deleted existing demo organization ({DEMO_SLUG}).")
            )

    def _create_organization(self):
        org, created = Organization.objects.get_or_create(
            slug=DEMO_SLUG,
            defaults=DEMO_DATA["organization"],
        )
        if created:
            self.stdout.write(f"  Created organization: {org.name}")
        else:
            self.stdout.write(
                self.style.NOTICE(
                    f"  Organization already exists: {org.name} — skipping (use --reset to recreate)."
                )
            )
        return org

    def _create_restaurant(self, org, restaurant_data):
        settings_data = restaurant_data.pop("settings", {})
        branches_data = restaurant_data.pop("branches", [])

        restaurant, created = Restaurant.objects.get_or_create(
            organization=org,
            code=restaurant_data["code"],
            defaults={**restaurant_data, "organization": org},
        )

        if created:
            self.stdout.write(f"    Created restaurant: {restaurant.name}")
            # Create / update settings
            rs, _ = RestaurantSettings.objects.get_or_create(restaurant=restaurant)
            for key, val in settings_data.items():
                setattr(rs, key, val)
            rs.save()
        else:
            self.stdout.write(
                self.style.NOTICE(
                    f"    Restaurant already exists: {restaurant.name} — skipping."
                )
            )

        for branch_data in branches_data:
            self._create_branch(restaurant, branch_data)

        # Restore popped keys so the data dict stays reusable if called again
        restaurant_data["settings"] = settings_data
        restaurant_data["branches"] = branches_data

    def _create_branch(self, restaurant, branch_data):
        settings_data = branch_data.pop("settings", {})

        branch, created = Branch.objects.get_or_create(
            restaurant=restaurant,
            code=branch_data["code"],
            defaults={**branch_data, "restaurant": restaurant},
        )

        if created:
            self.stdout.write(f"      Created branch: {branch.name}")
            bs, _ = BranchSettings.objects.get_or_create(branch=branch)
            for key, val in settings_data.items():
                setattr(bs, key, val)
            bs.save()
        else:
            self.stdout.write(
                self.style.NOTICE(
                    f"      Branch already exists: {branch.name} — skipping."
                )
            )

        branch_data["settings"] = settings_data
