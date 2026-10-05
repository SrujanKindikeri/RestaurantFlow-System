# =============================================================================
# RestaurantFlow — Promotion Services
# Phase 18
#
# PromotionService         — create/update/activate/deactivate promotions
# PromotionEligibilityService — validate eligibility for a promotion
# PromotionUsageService    — record and manage usage (concurrency-safe)
#
# Rules:
#   - Promotion codes normalized to UPPERCASE.
#   - Eligibility always validated server-side — never trust frontend.
#   - Usage limited via select_for_update() on Promotion row.
#   - Per-customer limits checked atomically.
#   - Billing remains authoritative for discount calculation.
#   - Marketing calls billing.services.apply_discount() to apply the discount.
# =============================================================================

import logging
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError, PermissionDenied

from accounts import access as acl
from marketing.constants import (
    PROMO_PERCENTAGE_DISCOUNT, PROMO_FIXED_DISCOUNT,
    PROMO_FREE_ITEM, PROMO_BUY_X_GET_Y, PROMO_LOYALTY_BONUS,
    DISCOUNT_PERCENTAGE, DISCOUNT_FIXED_AMOUNT,
    USAGE_RESERVED, USAGE_APPLIED, USAGE_REVERSED, USAGE_CANCELLED,
    PERM_PROMOTION_CREATE, PERM_PROMOTION_UPDATE,
    PERM_PROMOTION_ACTIVATE, PERM_PROMOTION_DEACTIVATE,
    PERM_PROMOTION_APPLY,
    AUDIT_PROMOTION_CREATED, AUDIT_PROMOTION_UPDATED,
    AUDIT_PROMOTION_ACTIVATED, AUDIT_PROMOTION_DEACTIVATED,
    AUDIT_PROMOTION_USED, AUDIT_PROMOTION_REVERSED,
    WS_PROMOTION_CREATED, WS_PROMOTION_UPDATED, WS_PROMOTION_USED,
    SOURCE_MARKETING_PROMOTION,
    RULE_MIN_ORDER_VALUE, RULE_MIN_QUANTITY, RULE_CUSTOMER_SEGMENT,
    RULE_CUSTOMER_TAG, RULE_FIRST_ORDER, RULE_REPEAT_ORDER,
    RULE_SPECIFIC_ITEM, RULE_MENU_CATEGORY, RULE_BRANCH,
    RULE_ORDER_TYPE, RULE_DAY_OF_WEEK, RULE_TIME_WINDOW,
    RULE_LOYALTY_POINTS,
)
from marketing.exceptions import (
    MarketingPermissionDenied, PromotionNotFound,
    PromotionIneligible, PromotionExpired,
    PromotionUsageLimitReached, PromotionAlreadyUsed,
    PromotionCodeInvalid,
)

logger = logging.getLogger("marketing")

ZERO = Decimal("0.00")


def _emit_audit(action, entity_type, entity_id, actor=None,
                company=None, restaurant=None, metadata=None):
    from marketing.models import MarketingAuditLog
    try:
        MarketingAuditLog.objects.create(
            actor=actor,
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id),
            company=company,
            restaurant=restaurant,
            metadata=metadata or {},
        )
    except Exception as exc:
        logger.error("_emit_audit failed: action=%s error=%s", action, exc)


def _emit_ws(event_name: str, promo_id, company_id):
    try:
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync
        channel_layer = get_channel_layer()
        if channel_layer:
            async_to_sync(channel_layer.group_send)(
                f"company_{company_id}",
                {"type": "marketing_event", "event": event_name, "promotion_id": str(promo_id)},
            )
    except Exception as exc:
        logger.debug("_emit_ws failed: %s", exc)


# =============================================================================
# PromotionService
# =============================================================================

class PromotionService:

    @staticmethod
    def create_promotion(*, company, restaurant=None, branch=None,
                         data: dict, actor) -> "Promotion":
        """Create a new (inactive) promotion."""
        from marketing.models import Promotion

        if not acl.has_permission(actor, PERM_PROMOTION_CREATE):
            raise MarketingPermissionDenied(PERM_PROMOTION_CREATE + " permission required.")

        if restaurant and not acl.can_access_restaurant(actor, restaurant):
            raise PermissionDenied("You do not have access to this restaurant.")

        # Normalize promo code
        code = (data.get("code") or "").strip().upper()

        # Validate code uniqueness within restaurant scope
        if code:
            from marketing.models import Promotion as P
            qs = P.objects.filter(company=company, code=code, is_active=True)
            if restaurant:
                qs = qs.filter(restaurant=restaurant)
            if qs.exists():
                raise ValidationError(
                    {"code": f"An active promotion with code '{code}' already exists."}
                )

        # Validate dates
        start_at = data.get("start_at")
        end_at = data.get("end_at")
        if start_at and end_at and start_at >= end_at:
            raise ValidationError({"end_at": "end_at must be after start_at."})

        with transaction.atomic():
            promotion = Promotion.objects.create(
                company=company,
                restaurant=restaurant,
                branch=branch,
                name=data["name"],
                code=code,
                description=data.get("description", ""),
                promotion_type=data["promotion_type"],
                discount_type=data.get("discount_type"),
                discount_value=data.get("discount_value"),
                max_discount_amount=data.get("max_discount_amount"),
                minimum_order_amount=data.get("minimum_order_amount"),
                minimum_quantity=data.get("minimum_quantity"),
                free_item_id=data.get("free_item_id"),
                buy_quantity=data.get("buy_quantity"),
                get_quantity=data.get("get_quantity"),
                loyalty_bonus_multiplier=data.get("loyalty_bonus_multiplier"),
                start_at=start_at,
                end_at=end_at,
                usage_limit=data.get("usage_limit"),
                usage_limit_per_customer=data.get("usage_limit_per_customer"),
                is_active=False,  # always starts inactive
                created_by=actor,
            )
            promo_id = promotion.pk
            co_id = company.pk

            transaction.on_commit(lambda: _emit_ws(WS_PROMOTION_CREATED, promo_id, co_id))

        _emit_audit(
            AUDIT_PROMOTION_CREATED, "PROMOTION", promotion.pk,
            actor=actor, company=company, restaurant=restaurant,
            metadata={"name": promotion.name, "code": code, "type": promotion.promotion_type},
        )
        logger.info("PromotionService.create_promotion: %s by %s", promotion.name, actor.email)
        return promotion

    @staticmethod
    def update_promotion(promotion, *, data: dict, actor) -> "Promotion":
        """Update a promotion. Only inactive promotions can be freely edited."""
        if not acl.has_permission(actor, PERM_PROMOTION_UPDATE):
            raise MarketingPermissionDenied(PERM_PROMOTION_UPDATE + " permission required.")

        if promotion.is_active:
            raise ValidationError(
                {"is_active": "Deactivate the promotion before editing it."}
            )

        updatable = [
            "name", "description", "discount_type", "discount_value",
            "max_discount_amount", "minimum_order_amount", "minimum_quantity",
            "start_at", "end_at", "usage_limit", "usage_limit_per_customer",
            "loyalty_bonus_multiplier", "buy_quantity", "get_quantity",
        ]
        with transaction.atomic():
            for field in updatable:
                if field in data:
                    setattr(promotion, field, data[field])
            if "code" in data:
                promotion.code = (data["code"] or "").strip().upper()
            promotion.save()

        _emit_audit(
            AUDIT_PROMOTION_UPDATED, "PROMOTION", promotion.pk,
            actor=actor, company=promotion.company, restaurant=promotion.restaurant,
            metadata={"updated_fields": list(data.keys())},
        )
        promo_id = promotion.pk
        co_id = promotion.company_id
        transaction.on_commit(lambda: _emit_ws(WS_PROMOTION_UPDATED, promo_id, co_id))
        return promotion

    @staticmethod
    def activate(promotion, actor) -> "Promotion":
        """Activate a promotion so it can be applied."""
        if not acl.has_permission(actor, PERM_PROMOTION_ACTIVATE):
            raise MarketingPermissionDenied(PERM_PROMOTION_ACTIVATE + " permission required.")

        if promotion.is_active:
            raise ValidationError({"is_active": "Promotion is already active."})

        # Validate promotion is structurally complete
        PromotionService._validate_completeness(promotion)

        with transaction.atomic():
            from marketing.models import Promotion
            Promotion.objects.filter(pk=promotion.pk).update(
                is_active=True, updated_at=timezone.now()
            )

        _emit_audit(
            AUDIT_PROMOTION_ACTIVATED, "PROMOTION", promotion.pk,
            actor=actor, company=promotion.company, restaurant=promotion.restaurant,
        )
        promotion.is_active = True
        return promotion

    @staticmethod
    def deactivate(promotion, actor) -> "Promotion":
        """Deactivate a promotion."""
        if not acl.has_permission(actor, PERM_PROMOTION_DEACTIVATE):
            raise MarketingPermissionDenied(PERM_PROMOTION_DEACTIVATE + " permission required.")

        if not promotion.is_active:
            raise ValidationError({"is_active": "Promotion is already inactive."})

        with transaction.atomic():
            from marketing.models import Promotion
            Promotion.objects.filter(pk=promotion.pk).update(
                is_active=False, updated_at=timezone.now()
            )

        _emit_audit(
            AUDIT_PROMOTION_DEACTIVATED, "PROMOTION", promotion.pk,
            actor=actor, company=promotion.company, restaurant=promotion.restaurant,
        )
        promotion.is_active = False
        return promotion

    @staticmethod
    def _validate_completeness(promotion):
        """Ensure the promotion has all required fields for its type."""
        promo_type = promotion.promotion_type
        if promo_type in (PROMO_PERCENTAGE_DISCOUNT, PROMO_FIXED_DISCOUNT):
            if not promotion.discount_value:
                raise ValidationError(
                    {"discount_value": "Discount value is required for this promotion type."}
                )
            if not promotion.discount_type:
                raise ValidationError(
                    {"discount_type": "Discount type is required for this promotion type."}
                )
        elif promo_type == PROMO_FREE_ITEM:
            if not promotion.free_item_id:
                raise ValidationError(
                    {"free_item": "A free item must be specified for FREE_ITEM promotions."}
                )
        elif promo_type == PROMO_BUY_X_GET_Y:
            if not promotion.buy_quantity or not promotion.get_quantity:
                raise ValidationError(
                    {"buy_quantity": "buy_quantity and get_quantity are required for BUY_X_GET_Y."}
                )
        elif promo_type == PROMO_LOYALTY_BONUS:
            if not promotion.loyalty_bonus_multiplier:
                raise ValidationError(
                    {"loyalty_bonus_multiplier": "Multiplier required for LOYALTY_BONUS promotions."}
                )


# =============================================================================
# PromotionEligibilityService
# =============================================================================

class PromotionEligibilityService:

    @staticmethod
    def validate(*, promotion_code: str = None, promotion=None,
                 customer=None, order=None, branch=None,
                 order_subtotal: Decimal = ZERO,
                 order_items: list = None) -> dict:
        """
        Validate promotion eligibility.

        Returns a dict:
            {
                "eligible": bool,
                "promotion_id": str | None,
                "promotion_name": str,
                "promotion_type": str,
                "estimated_discount": Decimal,
                "discount_type": str | None,
                "discount_value": Decimal | None,
                "reason": str,
            }

        Never trusts frontend input. All checks server-side.
        """
        if promotion is None and promotion_code:
            promotion = PromotionEligibilityService._lookup_by_code(
                promotion_code, branch=branch
            )

        if promotion is None:
            return _ineligible("Promotion not found.")

        result = PromotionEligibilityService._check_all(
            promotion=promotion,
            customer=customer,
            order=order,
            branch=branch,
            order_subtotal=order_subtotal,
            order_items=order_items or [],
        )
        return result

    @staticmethod
    def _lookup_by_code(code: str, branch=None) -> "Promotion | None":
        """Find an active promotion by code (case-insensitive, scope-aware)."""
        from marketing.models import Promotion

        normalized = code.strip().upper()
        if not normalized:
            return None

        now = timezone.now()
        qs = Promotion.objects.filter(
            code=normalized,
            is_active=True,
        ).filter(
            # Valid time window
            models_Q_start_end_filter(now)
        )

        if branch:
            # Scope: branch-specific OR restaurant-specific OR company-wide
            restaurant = branch.restaurant
            qs = qs.filter(
                models_scope_filter(branch, restaurant)
            )

        return qs.select_related("restaurant", "branch", "free_item").first()

    @staticmethod
    def _check_all(*, promotion, customer, order, branch,
                   order_subtotal: Decimal, order_items: list) -> dict:
        """Run all eligibility checks. Return first failure or success."""
        now = timezone.now()

        # 1. Active check
        if not promotion.is_active:
            return _ineligible("Promotion is not active.")

        # 2. Date/time validity
        if promotion.start_at and now < promotion.start_at:
            return _ineligible("Promotion has not started yet.")
        if promotion.end_at and now > promotion.end_at:
            return _ineligible("Promotion has expired.")

        # 3. Branch scope
        if branch:
            if promotion.branch_id and promotion.branch_id != branch.pk:
                return _ineligible("This promotion is not valid at this branch.")
            if promotion.restaurant_id and branch.restaurant_id != promotion.restaurant_id:
                return _ineligible("This promotion is not valid at this restaurant.")

        # 4. Global usage limit
        if promotion.usage_limit is not None:
            if promotion.current_usage_count >= promotion.usage_limit:
                return _ineligible("Promotion usage limit has been reached.")

        # 5. Minimum order amount
        if promotion.minimum_order_amount is not None:
            if order_subtotal < promotion.minimum_order_amount:
                return _ineligible(
                    f"Minimum order amount of {promotion.minimum_order_amount} required."
                )

        # 6. Per-customer limit
        if customer and promotion.usage_limit_per_customer is not None:
            from marketing.models import PromotionUsage
            customer_usage = PromotionUsage.objects.filter(
                promotion=promotion,
                customer=customer,
                status=USAGE_APPLIED,
            ).count()
            if customer_usage >= promotion.usage_limit_per_customer:
                return _ineligible("You have already used this promotion the maximum number of times.")

        # 7. Rule-based checks
        active_rules = list(
            promotion.rules.filter(is_active=True).order_by("priority")
        )
        for rule in active_rules:
            fail_reason = PromotionEligibilityService._evaluate_rule(
                rule, customer=customer, order=order, branch=branch,
                order_subtotal=order_subtotal, order_items=order_items,
            )
            if fail_reason:
                return _ineligible(fail_reason)

        # All checks passed — calculate estimated discount
        estimated_discount = PromotionEligibilityService._estimate_discount(
            promotion, order_subtotal
        )

        return {
            "eligible": True,
            "promotion_id": str(promotion.pk),
            "promotion_name": promotion.name,
            "promotion_type": promotion.promotion_type,
            "estimated_discount": estimated_discount,
            "discount_type": promotion.discount_type,
            "discount_value": promotion.discount_value,
            "reason": "eligible",
        }

    @staticmethod
    def _evaluate_rule(rule, *, customer, order, branch,
                       order_subtotal, order_items) -> str:
        """Evaluate a single rule. Return failure reason string or empty string."""
        rule_type = rule.rule_type
        config = rule.configuration or {}

        if rule_type == RULE_MIN_ORDER_VALUE:
            amount = Decimal(str(config.get("amount", "0")))
            if order_subtotal < amount:
                return f"Minimum order value of {amount} required."

        elif rule_type == RULE_MIN_QUANTITY:
            min_qty = int(config.get("quantity", 1))
            total_qty = sum(
                int(getattr(item, "quantity", 1)) for item in order_items
            )
            if total_qty < min_qty:
                return f"Minimum quantity of {min_qty} required."

        elif rule_type == RULE_CUSTOMER_SEGMENT:
            if not customer:
                return "Customer required for this promotion."
            seg_code = config.get("segment_code") or config.get("segment")
            if seg_code:
                has_seg = customer.segment_assignments.filter(
                    segment__code=seg_code, is_active=True
                ).exists()
                if not has_seg:
                    return "Customer is not in the required segment."

        elif rule_type == RULE_CUSTOMER_TAG:
            if not customer:
                return "Customer required for this promotion."
            tag_code = config.get("tag_code") or config.get("tag")
            if tag_code:
                has_tag = customer.tag_assignments.filter(
                    tag__code=tag_code, is_active=True
                ).exists()
                if not has_tag:
                    return "Customer does not have the required tag."

        elif rule_type == RULE_FIRST_ORDER:
            if not customer:
                return "Customer required for first-order promotion."
            if customer.total_orders > 0:
                return "This promotion is only valid for first-time customers."

        elif rule_type == RULE_REPEAT_ORDER:
            if not customer:
                return "Customer required for repeat-order promotion."
            min_orders = int(config.get("min_orders", 2))
            if customer.total_orders < min_orders:
                return f"This promotion requires at least {min_orders} previous orders."

        elif rule_type == RULE_BRANCH:
            required_branch_id = config.get("branch_id")
            if required_branch_id and branch and str(branch.pk) != required_branch_id:
                return "This promotion is not valid at this branch."

        elif rule_type == RULE_ORDER_TYPE:
            allowed_types = config.get("order_types", [])
            if allowed_types and order:
                if order.order_type not in allowed_types:
                    return f"This promotion is only valid for {', '.join(allowed_types)} orders."

        elif rule_type == RULE_DAY_OF_WEEK:
            allowed_days = config.get("days", [])  # 0=Mon, 6=Sun
            if allowed_days:
                today = timezone.now().weekday()  # 0=Mon
                if today not in allowed_days:
                    return "This promotion is not valid today."

        elif rule_type == RULE_TIME_WINDOW:
            start_time_str = config.get("start")
            end_time_str = config.get("end")
            if start_time_str and end_time_str:
                now = timezone.now().time()
                import datetime
                start_t = datetime.time.fromisoformat(start_time_str)
                end_t = datetime.time.fromisoformat(end_time_str)
                if not (start_t <= now <= end_t):
                    return f"This promotion is only valid between {start_time_str} and {end_time_str}."

        elif rule_type == RULE_LOYALTY_POINTS:
            if not customer:
                return "Customer required for loyalty-point-gated promotion."
            min_points = int(config.get("min_points", 0))
            if min_points > 0:
                total_balance = sum(
                    acct.points_balance
                    for acct in customer.loyalty_accounts.all()
                )
                if total_balance < min_points:
                    return f"Minimum {min_points} loyalty points required."

        return ""  # passed

    @staticmethod
    def _estimate_discount(promotion, order_subtotal: Decimal) -> Decimal:
        """Estimate the discount amount. Final calculation is done by Billing."""
        promo_type = promotion.promotion_type
        if promo_type == PROMO_PERCENTAGE_DISCOUNT:
            if promotion.discount_value:
                raw = (order_subtotal * promotion.discount_value / 100).quantize(Decimal("0.01"))
                if promotion.max_discount_amount:
                    return min(raw, promotion.max_discount_amount)
                return raw
        elif promo_type == PROMO_FIXED_DISCOUNT:
            if promotion.discount_value:
                return min(promotion.discount_value, order_subtotal)
        return ZERO


def _ineligible(reason: str) -> dict:
    return {
        "eligible": False,
        "promotion_id": None,
        "promotion_name": "",
        "promotion_type": "",
        "estimated_discount": ZERO,
        "discount_type": None,
        "discount_value": None,
        "reason": reason,
    }


def models_Q_start_end_filter(now):
    """Return a Q filter for promotions valid at `now`."""
    from django.db.models import Q
    return (
        Q(start_at__isnull=True) | Q(start_at__lte=now)
    ) & (
        Q(end_at__isnull=True) | Q(end_at__gte=now)
    )


def models_scope_filter(branch, restaurant):
    """Return a Q filter for promotions scoped to branch/restaurant/company."""
    from django.db.models import Q
    return (
        Q(branch=branch) |
        Q(branch__isnull=True, restaurant=restaurant) |
        Q(branch__isnull=True, restaurant__isnull=True, company=restaurant.company)
    )


# =============================================================================
# PromotionUsageService
# =============================================================================

class PromotionUsageService:

    @staticmethod
    def reserve_usage(promotion, *, customer=None, order=None,
                      actor=None) -> "PromotionUsage":
        """
        Reserve a promotion usage slot for an order in progress.

        Transactional: locks the Promotion row to prevent race conditions.
        Returns a PromotionUsage in RESERVED status.
        """
        from marketing.models import PromotionUsage, Promotion

        with transaction.atomic():
            # Lock the promotion to prevent concurrent over-redemption
            locked_promo = Promotion.objects.select_for_update().get(pk=promotion.pk)

            # Global usage limit check (inside lock)
            if locked_promo.usage_limit is not None:
                applied_count = PromotionUsage.objects.filter(
                    promotion=locked_promo,
                    status=USAGE_APPLIED,
                ).count()
                reserved_count = PromotionUsage.objects.filter(
                    promotion=locked_promo,
                    status=USAGE_RESERVED,
                ).count()
                if (applied_count + reserved_count) >= locked_promo.usage_limit:
                    raise PromotionUsageLimitReached(
                        f"Promotion '{locked_promo.name}' has reached its usage limit."
                    )

            # Per-customer limit check (inside lock)
            if customer and locked_promo.usage_limit_per_customer is not None:
                cust_count = PromotionUsage.objects.filter(
                    promotion=locked_promo,
                    customer=customer,
                    status__in=(USAGE_APPLIED, USAGE_RESERVED),
                ).count()
                if cust_count >= locked_promo.usage_limit_per_customer:
                    raise PromotionAlreadyUsed(
                        "You have already used this promotion the maximum number of times."
                    )

            usage = PromotionUsage.objects.create(
                promotion=locked_promo,
                customer=customer,
                order=order,
                status=USAGE_RESERVED,
                discount_amount=ZERO,
            )

        logger.info(
            "PromotionUsageService.reserve_usage: promo=%s customer=%s",
            locked_promo.name,
            customer.customer_number if customer else "anonymous",
        )
        return usage

    @staticmethod
    def apply_usage(usage, *, bill, discount_amount: Decimal,
                    actor=None) -> "PromotionUsage":
        """
        Commit a reserved usage as APPLIED after the bill is finalized.

        Also increments Promotion.current_usage_count atomically.
        """
        from marketing.models import PromotionUsage, Promotion

        if usage.status != USAGE_RESERVED:
            raise ValidationError(
                {"status": f"Cannot apply usage in status '{usage.status}'."}
            )

        with transaction.atomic():
            locked_usage = PromotionUsage.objects.select_for_update().get(pk=usage.pk)
            locked_usage.status = USAGE_APPLIED
            locked_usage.bill = bill
            locked_usage.discount_amount = discount_amount
            locked_usage.used_at = timezone.now()
            locked_usage.save(update_fields=[
                "status", "bill", "discount_amount", "used_at", "updated_at"
            ])

            # Increment global usage counter atomically
            Promotion.objects.filter(pk=usage.promotion_id).update(
                current_usage_count=models_F("current_usage_count") + 1,
                updated_at=timezone.now(),
            )

        _emit_audit(
            AUDIT_PROMOTION_USED, "PROMOTION_USAGE", usage.pk,
            actor=actor,
            company=usage.promotion.company,
            restaurant=usage.promotion.restaurant,
            metadata={
                "promotion_name": usage.promotion.name,
                "discount_amount": str(discount_amount),
                "bill_id": str(bill.pk) if bill else None,
            },
        )

        promo_id = usage.promotion_id
        co_id = usage.promotion.company_id
        transaction.on_commit(lambda: _emit_ws(WS_PROMOTION_USED, promo_id, co_id))

        usage.status = USAGE_APPLIED
        return usage

    @staticmethod
    def cancel_usage(usage, actor=None) -> "PromotionUsage":
        """Cancel a RESERVED usage (e.g., order cancelled before finalization)."""
        from marketing.models import PromotionUsage

        if usage.status != USAGE_RESERVED:
            raise ValidationError(
                {"status": f"Cannot cancel usage in status '{usage.status}'."}
            )

        with transaction.atomic():
            PromotionUsage.objects.filter(pk=usage.pk).update(
                status=USAGE_CANCELLED, updated_at=timezone.now()
            )

        usage.status = USAGE_CANCELLED
        return usage

    @staticmethod
    def reverse_usage(usage, reason: str = "", actor=None) -> "PromotionUsage":
        """
        Reverse an APPLIED usage (e.g., bill voided / refunded).

        Creates a new PromotionUsage in REVERSED status.
        Never edits the original APPLIED record.
        Decrements Promotion.current_usage_count atomically.
        """
        from marketing.models import PromotionUsage, Promotion

        if usage.status != USAGE_APPLIED:
            raise ValidationError(
                {"status": "Only APPLIED usages can be reversed."}
            )

        with transaction.atomic():
            # Create reversal record
            reversal = PromotionUsage.objects.create(
                promotion=usage.promotion,
                customer=usage.customer,
                order=usage.order,
                bill=usage.bill,
                discount_amount=-abs(usage.discount_amount),
                status=USAGE_REVERSED,
                used_at=timezone.now(),
            )

            # Decrement usage counter safely
            Promotion.objects.filter(
                pk=usage.promotion_id,
                current_usage_count__gt=0,
            ).update(
                current_usage_count=models_F("current_usage_count") - 1,
                updated_at=timezone.now(),
            )

        _emit_audit(
            AUDIT_PROMOTION_REVERSED, "PROMOTION_USAGE", reversal.pk,
            actor=actor,
            company=usage.promotion.company,
            restaurant=usage.promotion.restaurant,
            metadata={"original_usage_id": str(usage.pk), "reason": reason},
        )
        return reversal

    @staticmethod
    def apply_promotion_to_bill(usage, bill, *, actor=None):
        """
        Apply a marketing promotion to a Bill via the existing billing service.

        Marketing defines the promotion.
        Billing remains authoritative for the actual discount calculation.

        Source attribution is stored on PromotionUsage (bill FK + discount_amount)
        rather than on the Bill itself — the existing Bill model does not carry
        source_type / source_id fields.
        """
        if not acl.has_permission(actor, PERM_PROMOTION_APPLY):
            raise MarketingPermissionDenied(PERM_PROMOTION_APPLY + " permission required.")

        promotion = usage.promotion
        if promotion.promotion_type not in (PROMO_PERCENTAGE_DISCOUNT, PROMO_FIXED_DISCOUNT):
            # FREE_ITEM / LOYALTY_BONUS handled separately
            return

        from billing.services import apply_discount

        # Map marketing discount type to billing discount type string
        billing_dtype = promotion.discount_type  # "PERCENTAGE" or "FIXED_AMOUNT"
        if not billing_dtype:
            return

        # Billing service applies the discount and recalculates the bill.
        # max_pct=100 allows any percentage (permission already checked via
        # marketing.promotion.apply above; billing will re-check bill.discount.apply).
        apply_discount(
            bill=bill,
            user=actor,
            discount_type=billing_dtype,
            value=promotion.discount_value,
            max_pct=Decimal("100"),
        )


def models_F(field):
    """Lazy import of Django F() to avoid top-level import."""
    from django.db.models import F
    return F(field)
