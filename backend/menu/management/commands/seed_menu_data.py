# =============================================================================
# RestaurantFlow — Seed Menu Demo Data
# Phase 5
#
# Usage:
#   python manage.py seed_menu_data
#   python manage.py seed_menu_data --restaurant <slug>
#
# Creates:
#   - Phase 5 permission records (menu.*, category.*, tax.*, etc.)
#   - Assigns permissions to system roles
#   - Demo TaxRates (for development only — not legal/tax advice)
#   - Demo Categories: Veg, Non-Veg, Snacks, Beverages, Desserts
#   - Demo MenuItems with branch availability and pricing (if branches exist)
#
# Safe to run multiple times (get_or_create / update_or_create throughout).
# Does NOT touch Phase 1–4 data.
# =============================================================================

import logging
from decimal import Decimal

from django.core.management.base import BaseCommand

logger = logging.getLogger("menu")


# ---------------------------------------------------------------------------
# Permission definitions
# ---------------------------------------------------------------------------

MENU_PERMISSIONS = [
    # Menu items
    ("menu.view",        "View Menu Items",        "menu",     "view"),
    ("menu.create",      "Create Menu Items",       "menu",     "create"),
    ("menu.update",      "Update Menu Items",       "menu",     "update"),
    ("menu.disable",     "Disable Menu Items",      "menu",     "disable"),
    # Categories
    ("category.view",    "View Categories",         "category", "view"),
    ("category.create",  "Create Categories",       "category", "create"),
    ("category.update",  "Update Categories",       "category", "update"),
    ("category.disable", "Disable Categories",      "category", "disable"),
    # Prices
    ("menu.price.view",   "View Menu Prices",        "menu",     "price.view"),
    ("menu.price.create", "Create Menu Prices",      "menu",     "price.create"),
    ("menu.price.update", "Update Menu Prices",      "menu",     "price.update"),
    # Availability
    ("menu.availability.view",   "View Menu Availability",   "menu", "availability.view"),
    ("menu.availability.update", "Update Menu Availability", "menu", "availability.update"),
    # Tax
    ("tax.view",   "View Tax Rates",   "tax", "view"),
    ("tax.create", "Create Tax Rates", "tax", "create"),
    ("tax.update", "Update Tax Rates", "tax", "update"),
]

# Which permissions each system role gets
ROLE_PERMISSIONS = {
    "COMPANY_HEAD": [p[0] for p in MENU_PERMISSIONS],  # all
    "CENTRAL_ADMIN": [p[0] for p in MENU_PERMISSIONS],  # all
    "RESTAURANT_OWNER": [p[0] for p in MENU_PERMISSIONS],  # all
    "RESTAURANT_MANAGER": [
        "menu.view", "menu.create", "menu.update", "menu.disable",
        "category.view", "category.create", "category.update", "category.disable",
        "menu.price.view", "menu.price.create", "menu.price.update",
        "menu.availability.view", "menu.availability.update",
        "tax.view",
    ],
    "CASHIER": [
        "menu.view", "category.view",
        "menu.price.view", "menu.availability.view",
        "tax.view",
    ],
    "WAITER": [
        "menu.view", "category.view",
        "menu.price.view", "menu.availability.view",
    ],
    "KITCHEN_STAFF": [
        "menu.view", "category.view",
        "menu.availability.view",
    ],
    "INVENTORY_STAFF": [
        "menu.view", "category.view", "menu.price.view",
    ],
    "ACCOUNTANT": [
        "menu.view", "category.view",
        "menu.price.view", "tax.view",
    ],
}

# Demo categories per restaurant
DEMO_CATEGORIES = [
    {"name": "Veg",       "display_order": 1},
    {"name": "Non-Veg",   "display_order": 2},
    {"name": "Snacks",    "display_order": 3},
    {"name": "Beverages", "display_order": 4},
    {"name": "Desserts",  "display_order": 5},
]

# Demo menu items: (name, category_name, food_type, sku_suffix, prep_time)
DEMO_ITEMS = [
    ("Paneer Butter Masala", "Veg",       "VEG",     "PBM", 15),
    ("Masala Dosa",          "Veg",       "VEG",     "MD",  10),
    ("Chicken Biryani",      "Non-Veg",   "NON_VEG", "CB",  20),
    ("Egg Fried Rice",       "Non-Veg",   "EGG",     "EFR", 12),
    ("French Fries",         "Snacks",    "VEG",     "FF",  8),
    ("Samosa",               "Snacks",    "VEG",     "SAM", 5),
    ("Cold Coffee",          "Beverages", "VEG",     "COF", 5),
    ("Mango Lassi",          "Beverages", "VEG",     "ML",  3),
    ("Gulab Jamun",          "Desserts",  "VEG",     "GJ",  2),
    ("Ice Cream",            "Desserts",  "VEG",     "IC",  1),
]


class Command(BaseCommand):
    help = "Seed Phase 5 menu permissions and demo data"

    def add_arguments(self, parser):
        parser.add_argument(
            "--restaurant",
            type=str,
            default=None,
            help="Restaurant slug to seed menu data for (default: all restaurants)",
        )
        parser.add_argument(
            "--permissions-only",
            action="store_true",
            default=False,
            help="Only seed permissions; skip demo categories/items",
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING("=== Phase 5 Menu Seed ==="))

        self._seed_permissions()

        if not options["permissions_only"]:
            restaurant_slug = options.get("restaurant")
            self._seed_menu_data(restaurant_slug)

        self.stdout.write(self.style.SUCCESS("Phase 5 seed complete."))

    # -------------------------------------------------------------------------
    # Permissions
    # -------------------------------------------------------------------------

    def _seed_permissions(self):
        from accounts.models import Permission, Role

        self.stdout.write("Seeding Phase 5 permissions…")
        perms = {}

        for code, name, module, action in MENU_PERMISSIONS:
            perm, created = Permission.objects.get_or_create(
                code=code,
                defaults={
                    "name": name,
                    "module": module,
                    "action": action,
                    "is_active": True,
                },
            )
            perms[code] = perm
            if created:
                self.stdout.write(f"  + Permission: {code}")

        self.stdout.write("Assigning permissions to roles…")

        for role_code, perm_codes in ROLE_PERMISSIONS.items():
            try:
                role = Role.objects.get(code=role_code, is_active=True)
            except Role.DoesNotExist:
                self.stdout.write(
                    self.style.WARNING(f"  Role {role_code} not found — skipping")
                )
                continue

            for code in perm_codes:
                if code in perms:
                    role.permissions.add(perms[code])

            self.stdout.write(f"  ✓ {role_code}: {len(perm_codes)} permissions")

    # -------------------------------------------------------------------------
    # Menu data
    # -------------------------------------------------------------------------

    def _seed_menu_data(self, restaurant_slug):
        from organizations.models import Restaurant
        from menu.models import TaxRate, Category, MenuItem, MenuItemPrice, MenuItemBranch

        restaurants = Restaurant.objects.filter(is_active=True)
        if restaurant_slug:
            restaurants = restaurants.filter(slug=restaurant_slug)

        if not restaurants.exists():
            self.stdout.write(self.style.WARNING("No active restaurants found. Skipping menu data."))
            return

        for restaurant in restaurants:
            self.stdout.write(f"\nRestaurant: {restaurant.name}")
            self._seed_tax_rates(restaurant)
            self._seed_categories(restaurant)
            self._seed_items(restaurant)

    def _seed_tax_rates(self, restaurant):
        from menu.models import TaxRate

        # NOTE: These are DEMO values only — not legal/tax advice.
        demo_rates = [
            {"code": "GST_STANDARD", "name": "GST Standard",  "rate": Decimal("5.000"),  "description": "Standard GST rate (demo only)"},
            {"code": "GST_REDUCED",  "name": "GST Reduced",   "rate": Decimal("2.500"),  "description": "Reduced GST rate (demo only)"},
            {"code": "ZERO_TAX",     "name": "Zero Tax",      "rate": Decimal("0.000"),  "description": "Zero rated (demo only)"},
        ]

        self.stdout.write("  Tax rates…")
        for rate_data in demo_rates:
            obj, created = TaxRate.objects.get_or_create(
                restaurant=restaurant,
                code=rate_data["code"],
                defaults={
                    "name": rate_data["name"],
                    "rate": rate_data["rate"],
                    "description": rate_data["description"],
                    "is_active": True,
                },
            )
            if created:
                self.stdout.write(f"    + TaxRate: {rate_data['code']}")

    def _seed_categories(self, restaurant):
        from menu.models import Category

        self.stdout.write("  Categories…")
        for cat_data in DEMO_CATEGORIES:
            obj, created = Category.objects.get_or_create(
                restaurant=restaurant,
                name=cat_data["name"],
                defaults={
                    "display_order": cat_data["display_order"],
                    "is_active": True,
                },
            )
            if not created and obj.display_order != cat_data["display_order"]:
                obj.display_order = cat_data["display_order"]
                obj.save(update_fields=["display_order", "updated_at"])
            if created:
                self.stdout.write(f"    + Category: {cat_data['name']}")

    def _seed_items(self, restaurant):
        from menu.models import TaxRate, Category, MenuItem, MenuItemPrice, MenuItemBranch
        from django.utils.text import slugify

        self.stdout.write("  Menu items…")

        try:
            std_tax = TaxRate.objects.get(restaurant=restaurant, code="GST_STANDARD")
        except TaxRate.DoesNotExist:
            std_tax = None

        branches = list(restaurant.branches.filter(is_active=True))
        # Use restaurant code prefix for SKU generation
        prefix = restaurant.code[:3].upper() if restaurant.code else "RST"

        for item_name, cat_name, food_type, sku_suffix, prep_time in DEMO_ITEMS:
            try:
                category = Category.objects.get(restaurant=restaurant, name=cat_name)
            except Category.DoesNotExist:
                self.stdout.write(
                    self.style.WARNING(f"    Category '{cat_name}' not found — skipping {item_name}")
                )
                continue

            sku = f"{prefix}-{sku_suffix}-001"

            item, created = MenuItem.objects.get_or_create(
                restaurant=restaurant,
                sku=sku,
                defaults={
                    "category": category,
                    "name": item_name,
                    "food_type": food_type,
                    "tax_rate": std_tax,
                    "preparation_time_minutes": prep_time,
                    "is_active": True,
                    "is_available": True,
                    "short_description": f"Demo {item_name}",
                },
            )

            if created:
                self.stdout.write(f"    + MenuItem: {item_name} ({sku})")

            # Create branch-specific pricing and availability
            for i, branch in enumerate(branches):
                # Slightly different price per branch for realism
                base_price = Decimal("150.00") + Decimal(str(i * 30))

                # Branch availability
                MenuItemBranch.objects.get_or_create(
                    menu_item=item,
                    branch=branch,
                    defaults={"is_available": True},
                )

                # Active price (only if no active price exists)
                if not MenuItemPrice.objects.filter(
                    menu_item=item, branch=branch, is_active=True
                ).exists():
                    MenuItemPrice.objects.create(
                        menu_item=item,
                        branch=branch,
                        price=base_price,
                        is_active=True,
                    )

        self.stdout.write(f"  ✓ Menu items seeded for {restaurant.name}")
