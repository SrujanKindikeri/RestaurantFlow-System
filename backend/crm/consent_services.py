# =============================================================================
# RestaurantFlow — CRM Consent Services
# Phase 17
#
# CustomerConsentService — grant, revoke, query consent for a customer.
#
# Rules:
#   - Marketing communications REQUIRE explicit GRANTED consent.
#   - Transactional notifications do NOT require marketing consent.
#   - Consent history is IMMUTABLE — never edit CustomerConsentHistory rows.
#   - Every consent change appends a new history record.
# =============================================================================

import logging
from django.utils import timezone

from accounts import access as acl
from crm.constants import (
    CONSENT_GRANTED, CONSENT_REVOKED,
    CONSENT_SOURCE_CUSTOMER, CONSENT_SOURCE_STAFF,
    PERM_CUSTOMER_CONSENT_MANAGE,
    AUDIT_CONSENT_GRANTED, AUDIT_CONSENT_REVOKED,
)
from crm.exceptions import CRMPermissionDenied

logger = logging.getLogger("crm")


def _emit_audit(action, entity_type, entity_id, actor=None,
                company=None, restaurant=None, customer=None, metadata=None):
    from crm.models import CRMAuditLog
    try:
        CRMAuditLog.objects.create(
            actor=actor, action=action, entity_type=entity_type,
            entity_id=entity_id, company=company, restaurant=restaurant,
            customer=customer, metadata=metadata or {},
        )
    except Exception as exc:
        logger.error("_emit_audit failed: action=%s error=%s", action, exc)


class CustomerConsentService:

    @staticmethod
    def grant_consent(customer, consent_type: str, source: str = CONSENT_SOURCE_CUSTOMER,
                      actor=None) -> "CustomerConsent":
        """
        Grant a specific consent type for a customer.
        Creates or updates the CustomerConsent row and appends history.
        """
        from crm.models import CustomerConsent, CustomerConsentHistory

        if actor and not acl.has_permission(actor, PERM_CUSTOMER_CONSENT_MANAGE):
            raise CRMPermissionDenied("customer.consent.manage permission required.")

        consent, created = CustomerConsent.objects.get_or_create(
            customer=customer,
            consent_type=consent_type,
            defaults={
                "status": CONSENT_GRANTED,
                "source": source,
                "granted_at": timezone.now(),
            },
        )

        previous_status = "" if created else consent.status

        if not created:
            consent.status = CONSENT_GRANTED
            consent.source = source
            consent.granted_at = timezone.now()
            consent.revoked_at = None
            consent.save(update_fields=[
                "status", "source", "granted_at", "revoked_at", "updated_at"
            ])

        # Immutable history entry
        CustomerConsentHistory.objects.create(
            customer=customer,
            consent_type=consent_type,
            previous_status=previous_status,
            new_status=CONSENT_GRANTED,
            changed_by=actor,
            source=source,
        )

        _emit_audit(
            AUDIT_CONSENT_GRANTED, "CUSTOMER_CONSENT", consent.pk,
            actor=actor, company=customer.company,
            restaurant=customer.restaurant, customer=customer,
            metadata={"consent_type": consent_type, "source": source},
        )
        return consent

    @staticmethod
    def revoke_consent(customer, consent_type: str, source: str = CONSENT_SOURCE_CUSTOMER,
                       actor=None) -> "CustomerConsent":
        """Revoke a specific consent type for a customer."""
        from crm.models import CustomerConsent, CustomerConsentHistory

        if actor and not acl.has_permission(actor, PERM_CUSTOMER_CONSENT_MANAGE):
            raise CRMPermissionDenied("customer.consent.manage permission required.")

        consent, created = CustomerConsent.objects.get_or_create(
            customer=customer,
            consent_type=consent_type,
            defaults={
                "status": CONSENT_REVOKED,
                "source": source,
                "revoked_at": timezone.now(),
            },
        )

        previous_status = "" if created else consent.status

        if not created:
            consent.status = CONSENT_REVOKED
            consent.source = source
            consent.revoked_at = timezone.now()
            consent.save(update_fields=[
                "status", "source", "revoked_at", "updated_at"
            ])

        CustomerConsentHistory.objects.create(
            customer=customer,
            consent_type=consent_type,
            previous_status=previous_status,
            new_status=CONSENT_REVOKED,
            changed_by=actor,
            source=source,
        )

        _emit_audit(
            AUDIT_CONSENT_REVOKED, "CUSTOMER_CONSENT", consent.pk,
            actor=actor, company=customer.company,
            restaurant=customer.restaurant, customer=customer,
            metadata={"consent_type": consent_type},
        )
        return consent

    @staticmethod
    def has_consent(customer, consent_type: str) -> bool:
        """Return True if the customer has GRANTED consent for the given type."""
        from crm.models import CustomerConsent
        return CustomerConsent.objects.filter(
            customer=customer,
            consent_type=consent_type,
            status=CONSENT_GRANTED,
        ).exists()

    @staticmethod
    def get_consent_summary(customer) -> dict:
        """Return a dict mapping consent_type → status for a customer."""
        from crm.models import CustomerConsent
        return {
            c.consent_type: c.status
            for c in CustomerConsent.objects.filter(customer=customer)
        }
