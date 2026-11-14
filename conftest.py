"""
Root-level pytest configuration for RestaurantFlow.
pytest-django handles Django setup via DJANGO_SETTINGS_MODULE in pytest.ini.
"""
import sys
import os

# Add the project root to sys.path so the top-level tests/ package is importable
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

