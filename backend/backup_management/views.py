# =============================================================================
# RestaurantFlow — Backup Management API Views
# Phase 25
#
# Views:
#   BackupRecordListView    — GET /api/backup/records/
#   BackupRecordDetailView  — GET /api/backup/records/<uuid:pk>/
#   BackupTriggerView       — POST /api/backup/trigger/
#
# Security notes:
#   - No download URLs or raw backup file data are returned to any user.
#   - BackupTriggerView is rate-limited to prevent abuse (sensitive_op scope).
#   - All views require authentication + specific permissions.
# =============================================================================

import logging

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import HasPermission
from backup_management.models import BackupRecord
from backup_management.serializers import BackupRecordSerializer
from backup_management.constants import (
    BACKUP_TYPE_CHOICES,
    BACKUP_STATUS_PENDING,
    STORAGE_PROVIDER_LOCAL,
    ENCRYPTION_STATUS_UNKNOWN,
)
from core.pagination import SafePageNumberPagination
from core.throttles import ConfigurableScopedRateThrottle

logger = logging.getLogger("backup_management")


class BackupTriggerThrottle(ConfigurableScopedRateThrottle):
    scope = "sensitive_op"


class BackupRecordListView(APIView):
    """
    GET /api/backup/records/

    Returns a paginated list of BackupRecord instances, ordered by creation
    date descending.  Requires the view_backup_history permission.
    """

    permission_classes = [IsAuthenticated, HasPermission("backup_management.view_backup_history")]

    def get(self, request):
        queryset = BackupRecord.objects.all().order_by("-created_at")

        # Optional filters
        backup_type = request.query_params.get("backup_type")
        if backup_type:
            queryset = queryset.filter(backup_type=backup_type)

        status_filter = request.query_params.get("status")
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        paginator = SafePageNumberPagination()
        page = paginator.paginate_queryset(queryset, request, view=self)
        serializer = BackupRecordSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class BackupRecordDetailView(APIView):
    """
    GET /api/backup/records/<uuid:pk>/

    Returns a single BackupRecord.  Requires the view_backup_status permission.
    """

    permission_classes = [IsAuthenticated, HasPermission("backup_management.view_backup_status")]

    def get(self, request, pk):
        record = get_object_or_404(BackupRecord, pk=pk)
        serializer = BackupRecordSerializer(record)
        return Response(serializer.data)


class BackupTriggerView(APIView):
    """
    POST /api/backup/trigger/

    Enqueues an immediate backup task.  Creates a PENDING BackupRecord and
    returns its ID so the caller can poll for status.

    Requires the create_backup permission.
    Rate-limited via the sensitive_op throttle scope.

    Request body (JSON):
        {
            "backup_type": "DATABASE_FULL"   # required; must be a valid BACKUP_TYPE
        }
    """

    permission_classes = [IsAuthenticated, HasPermission("backup_management.create_backup")]
    throttle_classes = [BackupTriggerThrottle]

    def post(self, request):
        backup_type = request.data.get("backup_type", "").strip().upper()
        valid_types = {code for code, _ in BACKUP_TYPE_CHOICES}
        if backup_type not in valid_types:
            return Response(
                {"error": True, "message": f"Invalid backup_type. Valid values: {sorted(valid_types)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Create PENDING record first so the caller gets an ID immediately.
        record = BackupRecord.objects.create(
            backup_type=backup_type,
            storage_provider=STORAGE_PROVIDER_LOCAL,
            storage_location="",
            file_name="",
            status=BACKUP_STATUS_PENDING,
            encryption_status=ENCRYPTION_STATUS_UNKNOWN,
        )

        # Enqueue appropriate Celery task
        from backup_management.tasks import (
            run_database_backup,
            run_media_backup,
            run_configuration_backup,
        )

        try:
            if backup_type in ("DATABASE_FULL", "DATABASE_INCREMENTAL", "DATABASE_WAL"):
                run_database_backup.delay(backup_type=backup_type)
            elif backup_type == "MEDIA":
                run_media_backup.delay()
            elif backup_type == "CONFIGURATION":
                run_configuration_backup.delay()
            else:
                # APPLICATION_METADATA — treat as config backup for now
                run_configuration_backup.delay()
        except Exception as exc:
            logger.exception("BackupTriggerView: failed to enqueue task for %s", backup_type)
            # Keep the PENDING record; it will be picked up by check_backup_staleness.

        logger.info(
            "BackupTriggerView: backup triggered type=%s record=%s user=%s",
            backup_type, record.id, request.user.email if request.user else "?",
        )

        serializer = BackupRecordSerializer(record)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
