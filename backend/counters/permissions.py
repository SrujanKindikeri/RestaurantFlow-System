# =============================================================================
# RestaurantFlow — Counter DRF Permission Classes
# Phase 4
#
# Mirrors the pattern in accounts/permissions.py.
# All authorization delegates to counters.access or accounts.access.
# =============================================================================

import logging
from rest_framework.permissions import BasePermission

from counters import access as counter_acl

logger = logging.getLogger("counters")


class HasCounterAccess(BasePermission):
    """
    Object-level permission: the requesting user must have access to the
    Counter instance (i.e. its branch is accessible to them).
    """

    message = "You do not have access to this counter."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        from counters.models import Counter
        if not isinstance(obj, Counter):
            return False
        result = counter_acl.can_access_counter(request.user, obj)
        if not result:
            logger.warning(
                "Counter access denied: user=%s counter=%s",
                request.user.email,
                obj.pk,
            )
        return result


class HasCounterSessionAccess(BasePermission):
    """
    Object-level permission: user must have access to the counter that
    owns this session.
    """

    message = "You do not have access to this counter session."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        from counters.models import CounterSession
        if not isinstance(obj, CounterSession):
            return False
        result = counter_acl.can_access_counter(request.user, obj.counter)
        if not result:
            logger.warning(
                "CounterSession access denied: user=%s session=%s",
                request.user.email,
                obj.pk,
            )
        return result
