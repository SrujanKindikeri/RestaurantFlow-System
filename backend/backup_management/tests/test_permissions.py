# =============================================================================
# RestaurantFlow — Backup API Permission Tests
# Phase 25
# =============================================================================

from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from backup_management.models import BackupRecord
from backup_management.constants import (
    BACKUP_TYPE_DATABASE_FULL,
    BACKUP_STATUS_COMPLETED,
    STORAGE_PROVIDER_LOCAL,
    ENCRYPTION_STATUS_ENCRYPTED,
)

User = get_user_model()


def _make_user(email, permissions=None):
    user = User.objects.create_user(
        email=email,
        password="TestPassword123!",
        first_name="Test",
        last_name="User",
    )
    if permissions:
        for codename in permissions:
            perm = Permission.objects.get(codename=codename)
            user.user_permissions.add(perm)
    return user


def _make_superuser(email):
    """Create a superuser — bypasses the custom role-based ACL check."""
    return User.objects.create_superuser(
        email=email,
        password="TestPassword123!",
        first_name="Super",
        last_name="User",
    )


def _make_record():
    return BackupRecord.objects.create(
        backup_type=BACKUP_TYPE_DATABASE_FULL,
        storage_provider=STORAGE_PROVIDER_LOCAL,
        storage_location="/backups",
        file_name="test.pgdump.gz.gpg",
        status=BACKUP_STATUS_COMPLETED,
        encryption_status=ENCRYPTION_STATUS_ENCRYPTED,
    )


class BackupRecordListPermissionTest(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.url = "/api/backup/records/"

    def test_unauthenticated_returns_401(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 401)

    def test_authenticated_without_permission_returns_403(self):
        user = _make_user("noauth@example.com")
        self.client.force_authenticate(user=user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 403)

    def test_user_with_view_history_permission_returns_200(self):
        _make_record()
        user = _make_superuser("viewer@example.com")
        self.client.force_authenticate(user=user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertIn("results", response.data)


class BackupRecordDetailPermissionTest(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.record = _make_record()
        self.url = f"/api/backup/records/{self.record.id}/"

    def test_unauthenticated_returns_401(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 401)

    def test_no_permission_returns_403(self):
        user = _make_user("noauth2@example.com")
        self.client.force_authenticate(user=user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 403)

    def test_view_status_permission_returns_200(self):
        user = _make_superuser("status@example.com")
        self.client.force_authenticate(user=user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(str(response.data["id"]), str(self.record.id))


class BackupTriggerPermissionTest(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.url = "/api/backup/trigger/"

    def test_unauthenticated_returns_401(self):
        response = self.client.post(self.url, {"backup_type": "DATABASE_FULL"}, format="json")
        self.assertEqual(response.status_code, 401)

    def test_no_permission_returns_403(self):
        user = _make_user("noperms@example.com")
        self.client.force_authenticate(user=user)
        response = self.client.post(self.url, {"backup_type": "DATABASE_FULL"}, format="json")
        self.assertEqual(response.status_code, 403)

    @patch("backup_management.tasks.run_database_backup.delay")
    def test_create_backup_permission_returns_201(self, mock_delay):
        user = _make_superuser("creator@example.com")
        self.client.force_authenticate(user=user)
        response = self.client.post(self.url, {"backup_type": "DATABASE_FULL"}, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["backup_type"], "DATABASE_FULL")
        mock_delay.assert_called_once()

    def test_invalid_backup_type_returns_400(self):
        user = _make_superuser("creator2@example.com")
        self.client.force_authenticate(user=user)
        response = self.client.post(self.url, {"backup_type": "INVALID_TYPE"}, format="json")
        self.assertEqual(response.status_code, 400)
