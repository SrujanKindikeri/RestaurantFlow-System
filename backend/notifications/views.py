# =============================================================================
# RestaurantFlow — Notifications Views
# Phase 16
#
# Views are thin dispatchers — all logic lives in services/selectors.
#
# Endpoints:
#   GET    /api/notifications/                      — list user's notifications
#   GET    /api/notifications/unread-count/         — {count: N}
#   GET    /api/notifications/{id}/                 — detail
#   POST   /api/notifications/{id}/read/            — mark read
#   POST   /api/notifications/{id}/acknowledge/     — acknowledge
#   POST   /api/notifications/read-all/             — mark all read
#   GET    /api/notifications/preferences/          — user preferences
#   POST   /api/notifications/preferences/          — upsert preference
#   PATCH  /api/notifications/preferences/{id}/     — update preference
#   GET    /api/notifications/deliveries/           — admin delivery history
#   GET    /api/notifications/admin/templates/      — admin templates
#   POST   /api/notifications/admin/templates/      — create template
#   PATCH  /api/notifications/admin/templates/{id}/ — update template
#   GET    /api/notifications/admin/providers/      — admin provider configs
#   PATCH  /api/notifications/admin/providers/{id}/ — update provider config
#   GET    /api/notifications/admin/deliveries/     — admin delivery history
# =============================================================================

import logging

from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.authentication import SessionAuthentication
from rest_framework_simplejwt.authentication import JWTAuthentication

from notifications.permissions import (
    CanViewOwnNotifications,
    CanManageNotificationPreferences,
    CanViewDeliveryHistory,
    CanManageNotificationTemplates,
    CanManageProviderConfig,
    IsNotificationAdmin,
)
from notifications.selectors import (
    get_notification_recipients_for_user,
    get_unread_count_for_user,
    get_notification_recipient,
    get_user_preferences,
    get_deliveries_for_admin,
)
from notifications.services import NotificationService
from notifications.serializers import (
    NotificationRecipientSerializer,
    UnreadCountSerializer,
    NotificationPreferenceSerializer,
    NotificationPreferenceBulkSerializer,
    NotificationDeliverySerializer,
    NotificationTemplateSerializer,
    NotificationProviderConfigSerializer,
)
from notifications.exceptions import NotificationNotFoundError
from accounts import access as acl

logger = logging.getLogger("notifications")

_AUTH = [JWTAuthentication, SessionAuthentication]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_company_for_user(user):
    """Return the first accessible organization for the user."""
    orgs = acl.get_accessible_organizations(user)
    return orgs.first()


# ===========================================================================
# User-facing endpoints
# ===========================================================================

class NotificationListView(APIView):
    """
    GET /api/notifications/
    Returns the authenticated user's notification recipients.
    """
    authentication_classes = _AUTH
    permission_classes     = [CanViewOwnNotifications]

    def get(self, request):
        params        = request.query_params
        unread_only   = params.get("unread", "").lower() in ("true", "1", "yes")
        notif_type    = params.get("notification_type")
        severity      = params.get("severity")
        date_from     = params.get("date_from")
        date_to       = params.get("date_to")

        qs = get_notification_recipients_for_user(
            request.user,
            unread_only=unread_only,
            notification_type=notif_type,
            severity=severity,
            date_from=date_from,
            date_to=date_to,
        )

        # Simple pagination
        page_size = min(int(params.get("page_size", 20)), 100)
        page      = max(int(params.get("page", 1)), 1)
        start     = (page - 1) * page_size
        end       = start + page_size
        total     = qs.count()
        items     = qs[start:end]

        serializer = NotificationRecipientSerializer(items, many=True)
        return Response({
            "count":   total,
            "page":    page,
            "results": serializer.data,
        })


class NotificationUnreadCountView(APIView):
    """GET /api/notifications/unread-count/"""
    authentication_classes = _AUTH
    permission_classes     = [CanViewOwnNotifications]

    def get(self, request):
        count = get_unread_count_for_user(request.user)
        return Response({"count": count})


class NotificationDetailView(APIView):
    """GET /api/notifications/{id}/"""
    authentication_classes = _AUTH
    permission_classes     = [CanViewOwnNotifications]

    def get(self, request, pk):
        recipient = get_notification_recipient(pk, request.user)
        if not recipient:
            return Response(
                {"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND
            )
        return Response(NotificationRecipientSerializer(recipient).data)


class NotificationReadView(APIView):
    """POST /api/notifications/{id}/read/"""
    authentication_classes = _AUTH
    permission_classes     = [CanViewOwnNotifications]

    def post(self, request, pk):
        try:
            recipient = NotificationService.mark_read(str(pk), request.user)
            return Response(NotificationRecipientSerializer(recipient).data)
        except NotificationNotFoundError:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as exc:
            logger.error("NotificationReadView.post failed: %s", exc)
            return Response(
                {"detail": "Failed to mark notification as read."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class NotificationAcknowledgeView(APIView):
    """POST /api/notifications/{id}/acknowledge/"""
    authentication_classes = _AUTH
    permission_classes     = [CanViewOwnNotifications]

    def post(self, request, pk):
        try:
            recipient = NotificationService.acknowledge(str(pk), request.user)
            return Response(NotificationRecipientSerializer(recipient).data)
        except NotificationNotFoundError:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as exc:
            logger.error("NotificationAcknowledgeView.post failed: %s", exc)
            return Response(
                {"detail": "Failed to acknowledge notification."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class NotificationReadAllView(APIView):
    """POST /api/notifications/read-all/"""
    authentication_classes = _AUTH
    permission_classes     = [CanViewOwnNotifications]

    def post(self, request):
        updated = NotificationService.mark_all_read(request.user)
        return Response({"updated": updated})


# ===========================================================================
# Preferences
# ===========================================================================

class NotificationPreferenceListView(APIView):
    """GET /api/notifications/preferences/"""
    authentication_classes = _AUTH
    permission_classes     = [CanManageNotificationPreferences]

    def get(self, request):
        prefs = get_user_preferences(request.user)
        return Response(NotificationPreferenceSerializer(prefs, many=True).data)

    def post(self, request):
        """Upsert a single preference."""
        serializer = NotificationPreferenceBulkSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        from notifications.models import NotificationPreference
        d = serializer.validated_data
        pref, created = NotificationPreference.objects.update_or_create(
            user=request.user,
            notification_type=d["notification_type"],
            channel=d["channel"],
            defaults={"enabled": d["enabled"]},
        )
        return Response(
            NotificationPreferenceSerializer(pref).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class NotificationPreferenceDetailView(APIView):
    """PATCH /api/notifications/preferences/{id}/"""
    authentication_classes = _AUTH
    permission_classes     = [CanManageNotificationPreferences]

    def patch(self, request, pk):
        from notifications.models import NotificationPreference
        try:
            pref = NotificationPreference.objects.get(pk=pk, user=request.user)
        except NotificationPreference.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = NotificationPreferenceSerializer(pref, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        serializer.save()
        return Response(serializer.data)


# ===========================================================================
# Delivery history (authorized users)
# ===========================================================================

class NotificationDeliveryListView(APIView):
    """GET /api/notifications/deliveries/ — user's own delivery history"""
    authentication_classes = _AUTH
    permission_classes     = [CanViewOwnNotifications]

    def get(self, request):
        from notifications.models import NotificationDelivery
        qs = (
            NotificationDelivery.objects
            .filter(recipient__user=request.user)
            .select_related("notification", "recipient")
            .order_by("-created_at")[:50]
        )
        return Response(NotificationDeliverySerializer(qs, many=True).data)


# ===========================================================================
# Admin endpoints
# ===========================================================================

class AdminTemplateListView(APIView):
    """
    GET  /api/notifications/admin/templates/
    POST /api/notifications/admin/templates/
    """
    authentication_classes = _AUTH
    permission_classes     = [CanManageNotificationTemplates]

    def get(self, request):
        from notifications.models import NotificationTemplate
        company = _get_company_for_user(request.user)
        qs = NotificationTemplate.objects.filter(
            company=company
        ) | NotificationTemplate.objects.filter(company__isnull=True)
        return Response(NotificationTemplateSerializer(qs.distinct(), many=True).data)

    def post(self, request):
        company    = _get_company_for_user(request.user)
        serializer = NotificationTemplateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        template = serializer.save(company=company)
        return Response(NotificationTemplateSerializer(template).data, status=status.HTTP_201_CREATED)


class AdminTemplateDetailView(APIView):
    """PATCH /api/notifications/admin/templates/{id}/"""
    authentication_classes = _AUTH
    permission_classes     = [CanManageNotificationTemplates]

    def patch(self, request, pk):
        from notifications.models import NotificationTemplate
        company = _get_company_for_user(request.user)
        try:
            template = NotificationTemplate.objects.get(pk=pk, company=company)
        except NotificationTemplate.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = NotificationTemplateSerializer(template, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        serializer.save()
        return Response(serializer.data)


class AdminProviderConfigListView(APIView):
    """GET /api/notifications/admin/providers/"""
    authentication_classes = _AUTH
    permission_classes     = [CanManageProviderConfig]

    def get(self, request):
        from notifications.models import NotificationProviderConfig
        company = _get_company_for_user(request.user)
        qs = NotificationProviderConfig.objects.filter(company=company)
        return Response(NotificationProviderConfigSerializer(qs, many=True).data)


class AdminProviderConfigDetailView(APIView):
    """PATCH /api/notifications/admin/providers/{id}/"""
    authentication_classes = _AUTH
    permission_classes     = [CanManageProviderConfig]

    def patch(self, request, pk):
        from notifications.models import NotificationProviderConfig
        company = _get_company_for_user(request.user)
        try:
            config = NotificationProviderConfig.objects.get(pk=pk, company=company)
        except NotificationProviderConfig.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = NotificationProviderConfigSerializer(config, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        serializer.save()
        return Response(serializer.data)


class AdminDeliveryListView(APIView):
    """GET /api/notifications/admin/deliveries/"""
    authentication_classes = _AUTH
    permission_classes     = [CanViewDeliveryHistory]

    def get(self, request):
        company  = _get_company_for_user(request.user)
        if not company:
            return Response({"results": []})
        params   = request.query_params
        qs       = get_deliveries_for_admin(
            company=company,
            channel=params.get("channel"),
            status=params.get("status"),
            date_from=params.get("date_from"),
            date_to=params.get("date_to"),
        )
        # Pagination
        page_size = min(int(params.get("page_size", 50)), 200)
        page      = max(int(params.get("page", 1)), 1)
        start     = (page - 1) * page_size
        total     = qs.count()
        items     = qs[start:start + page_size]
        return Response({
            "count":   total,
            "page":    page,
            "results": NotificationDeliverySerializer(items, many=True).data,
        })


class ProviderStatusView(APIView):
    """GET /api/notifications/admin/providers/status/ — health check for all providers"""
    authentication_classes = _AUTH
    permission_classes     = [IsNotificationAdmin]

    def get(self, request):
        from notifications.delivery.in_app    import InAppProvider
        from notifications.delivery.websocket import WebSocketProvider
        from notifications.delivery.email     import EmailProvider
        from notifications.delivery.sms       import SMSProvider
        from notifications.delivery.whatsapp  import WhatsAppProvider
        from notifications.delivery.telegram  import TelegramProvider

        providers = [
            InAppProvider(), WebSocketProvider(), EmailProvider(),
            SMSProvider(), WhatsAppProvider(), TelegramProvider(),
        ]
        return Response([p.get_status() for p in providers])
