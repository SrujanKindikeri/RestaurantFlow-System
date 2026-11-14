"""
Pytest configuration for RestaurantFlow backend tests.
Adds the project root to sys.path so the top-level tests/ package is importable.
"""
import sys
import os

# Add the project root to sys.path so that tests.e2e.* is importable
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Configure Django settings
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.test_settings")

import django
django.setup()
