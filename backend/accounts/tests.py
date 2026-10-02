# =============================================================================
# RestaurantFlow — Accounts Tests
# =============================================================================

from django.contrib.auth import get_user_model
from django.test import TestCase

User = get_user_model()


class UserModelTest(TestCase):
    """Basic tests for the custom User model."""

    def test_create_user(self):
        user = User.objects.create_user(
            email="test@example.com",
            password="securepass123",
            first_name="Test",
            last_name="User",
        )
        self.assertEqual(user.email, "test@example.com")
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

    def test_create_superuser(self):
        admin = User.objects.create_superuser(
            email="admin@example.com",
            password="adminpass123",
        )
        self.assertTrue(admin.is_staff)
        self.assertTrue(admin.is_superuser)

    def test_email_is_unique_identifier(self):
        user = User.objects.create_user(email="unique@example.com", password="pass123")
        self.assertEqual(str(user), "unique@example.com")

    def test_full_name_property(self):
        user = User.objects.create_user(
            email="full@example.com",
            password="pass123",
            first_name="Jane",
            last_name="Doe",
        )
        self.assertEqual(user.full_name, "Jane Doe")
