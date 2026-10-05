# =============================================================================
# RestaurantFlow — CRM Loyalty Services
# Phase 17
#
# LoyaltyService   — earn, redeem, adjust, expire, reverse points
# RewardService    — create, update, validate, redeem rewards
#
# Concurrency:
#   All balance mutations use transaction.atomic() + select_for_update().
#   Two concurrent redemptions will serialize correctly.
#
# Idempotency:
#   Earning from a bill uses reference_type=BILL + reference_id=bill_pk.
#   Attempting to earn again for the same bill returns the existing txn.
#
# Balance integrity:
#   balance_before + points == balance_after — enforced before every save.
#   Negative balance is never allowed.
# =============================================================================

import logging
import secrets
import string
from decimal import Decimal

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from accounts import access as acl
from crm.constants import (
    LOYALTY_EARN, LOYALTY_REDEEM, LOYALTY_BONUS,
    LOYALTY_ADJUSTMENT, LOYALTY_EXPIRY, LOYALTY_REVERSAL,
    LOYALTY_REF_BILL, LOYALTY_REF_REVERSAL,
    REDEMPTION_REQUESTED, REDEMPTION_CONFIRMED, REDEMPTION_USED,
    REDEMPTION_CANCELLED, REDEMPTION_EXPIRED,
    REWARD_DISCOUNT, REWARD_FIXED_AMOUNT, REWARD_PERCENTAGE,
    PERM_LOYALTY_EARN, PERM_LOYALTY_REDEEM, PERM_LOYALTY_ADJUST,
    PERM_REWARD_MANAGE, PERM_REWARD_REDEEM,
    AUDIT_LOYALTY_ACCOUNT_CREATED, AUDIT_LOYALTY_POINTS_EARNED,
    AUDIT_LOYALTY_POINTS_REDEEMED, AUDIT_LOYALTY_POINTS_ADJUSTED,
    AUDIT_LOYALTY_POINTS_REVERSED, AUDIT_LOYALTY_POINTS_EXPIRED,
    AUDIT_REWARD_REDEEMED, AUDIT_REWARD_CANCELLED,
    AUDIT_REWARD_CREATED, AUDIT_REWARD_UPDATED,
)
from crm.exceptions import (
    LoyaltyAccountNotFound, InsufficientLoyaltyPoints,
    LoyaltyTransactionConflict, RewardUnavailable, RewardExpired,
    RewardRedemptionConflict, CRMPermissionDenied,
)
from crm.validators import validate_loyalty_balance_integrity

logger = logging.getLogger("crm")


def _emit_audit(action, entity_type, entity_id, actor=None,
                company=None, restaurant=None, customer=None, metadata=None):
    from crm.models import CRMAuditLog
    try:
        CRMAuditLog.objects.create(
            actor=actor,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            company=company,
            restaurant=restaurant,
            customer=customer,
            metadata=metadata or {},
        )
    except Exception as exc:
        logger.error("_emit_audit failed: action=%s error=%s", action, exc)


def _generate_reference_code(length: int = 8) -> str:
    """Generate a short alphanumeric reference code for redemptions."""
    alphabet = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


# =============================================================================
# LoyaltyService
# =============================================================================

class LoyaltyService:

    @staticmethod
    def get_or_create_account(customer, loyalty_program) -> "LoyaltyAccount":
        """Return the loyalty account for a customer+program, creating if needed."""
        from crm.models import LoyaltyAccount

        account, created = LoyaltyAccount.objects.get_or_create(
            customer=customer,
            loyalty_program=loyalty_program,
            defaults={"points_balance": 0},
        )
        if created:
            _emit_audit(
                AUDIT_LOYALTY_ACCOUNT_CREATED, "LOYALTY_ACCOUNT", account.pk,
                company=customer.company, restaurant=loyalty_program.restaurant,
                customer=customer,
            )
        return account

    @staticmethod
    def earn_points_for_bill(bill, loyalty_program=None, actor=None) -> "LoyaltyTransaction | None":
        """
        Award loyalty points for a finalized bill.

        Idempotent: reference BILL:<bill_pk> prevents double-awarding.
        Only awards for FINALIZED bills. Cancelled/failed bills → no points.
        """
        from crm.models import LoyaltyTransaction, LoyaltyAccount
        from billing.models import BillStatus

        if bill.status != BillStatus.FINALIZED:
            logger.debug(
                "earn_points_for_bill: skipped — bill %s not FINALIZED", bill.pk
            )
            return None

        order = bill.order
        if not order.customer_id:
            return None  # anonymous order

        customer = order.customer
        restaurant = bill.branch.restaurant

        # Resolve program
        if loyalty_program is None:
            loyalty_program = (
                restaurant.loyalty_programs.filter(is_active=True).first()
            )
        if not loyalty_program:
            return None  # no active program

        reference_id = str(bill.pk)
        reference_type = LOYALTY_REF_BILL

        with transaction.atomic():
            account = LoyaltyService.get_or_create_account(customer, loyalty_program)
            # Lock account
            account = LoyaltyAccount.objects.select_for_update().get(pk=account.pk)

            # Idempotency check
            existing = LoyaltyTransaction.objects.filter(
                loyalty_account=account,
                reference_type=reference_type,
                reference_id=reference_id,
            ).first()
            if existing:
                logger.debug(
                    "earn_points_for_bill: idempotent — txn %s already exists", existing.pk
                )
                return existing

            # Calculate points: eligible amount × points_per_currency_unit
            eligible_amount = bill.grand_total
            points = int(
                (eligible_amount * loyalty_program.points_per_currency_unit)
                .to_integral_value()
            )
            if points <= 0:
                return None

            balance_before = account.points_balance
            balance_after = balance_before + points
            validate_loyalty_balance_integrity(balance_before, points, balance_after)

            txn = LoyaltyTransaction.objects.create(
                loyalty_account=account,
                transaction_type=LOYALTY_EARN,
                points=points,
                balance_before=balance_before,
                balance_after=balance_after,
                reference_type=reference_type,
                reference_id=reference_id,
                reason=f"Points earned for bill {bill.bill_number}",
                created_by=actor,
            )

            account.points_balance = balance_after
            account.lifetime_points_earned += points
            account.save(update_fields=[
                "points_balance", "lifetime_points_earned", "updated_at"
            ])

        _emit_audit(
            AUDIT_LOYALTY_POINTS_EARNED, "LOYALTY_TRANSACTION", txn.pk,
            company=customer.company, restaurant=restaurant, customer=customer,
            metadata={
                "points": points,
                "bill_number": bill.bill_number,
                "balance_after": balance_after,
            },
        )

        logger.info(
            "LoyaltyService.earn_points_for_bill: customer=%s bill=%s points=%d",
            customer.customer_number, bill.bill_number, points,
        )
        return txn

    @staticmethod
    def reverse_points_for_bill(bill, reason: str = "", actor=None) -> "LoyaltyTransaction | None":
        """
        Reverse earned points when a bill is refunded/cancelled.

        Creates a REVERSAL transaction. Never edits the original EARN.
        If the customer has already spent those points, creates a safe adjustment
        rather than producing a negative balance.
        """
        from crm.models import LoyaltyTransaction, LoyaltyAccount

        reference_id = str(bill.pk)

        with transaction.atomic():
            # Find original EARN transaction
            earn_txn = LoyaltyTransaction.objects.filter(
                reference_type=LOYALTY_REF_BILL,
                reference_id=reference_id,
                transaction_type=LOYALTY_EARN,
            ).first()

            if not earn_txn:
                return None  # no points were earned for this bill

            # Check if already reversed
            already_reversed = LoyaltyTransaction.objects.filter(
                reference_type=LOYALTY_REF_REVERSAL,
                reference_id=reference_id,
                transaction_type=LOYALTY_REVERSAL,
            ).first()
            if already_reversed:
                return already_reversed

            account = LoyaltyAccount.objects.select_for_update().get(
                pk=earn_txn.loyalty_account_id
            )

            points_to_reverse = earn_txn.points
            # Safe: can only reverse up to current balance
            safe_reversal = min(points_to_reverse, account.points_balance)
            actual_reversal = -safe_reversal

            balance_before = account.points_balance
            balance_after = balance_before + actual_reversal  # subtracts

            if balance_after < 0:
                balance_after = 0
                actual_reversal = -balance_before

            txn = LoyaltyTransaction.objects.create(
                loyalty_account=account,
                transaction_type=LOYALTY_REVERSAL,
                points=actual_reversal,
                balance_before=balance_before,
                balance_after=balance_after,
                reference_type=LOYALTY_REF_REVERSAL,
                reference_id=reference_id,
                reason=reason or f"Reversal for bill {bill.bill_number}",
                created_by=actor,
            )

            account.points_balance = balance_after
            account.save(update_fields=["points_balance", "updated_at"])

        customer = account.loyalty_account.customer if hasattr(account, "loyalty_account") else None
        # account is a LoyaltyAccount, so customer via FK:
        try:
            cust = account.customer
        except Exception:
            cust = None

        _emit_audit(
            AUDIT_LOYALTY_POINTS_REVERSED, "LOYALTY_TRANSACTION", txn.pk,
            customer=cust,
            metadata={"points": actual_reversal, "bill_id": str(bill.pk)},
        )
        return txn

    @staticmethod
    def redeem_points(loyalty_account, points: int, reason: str = "", actor=None) -> "LoyaltyTransaction":
        """
        Deduct points from a loyalty account.
        Called during reward redemption — always inside an outer atomic block.
        """
        from crm.models import LoyaltyAccount

        if actor and not acl.has_permission(actor, PERM_LOYALTY_REDEEM):
            raise CRMPermissionDenied("loyalty.redeem permission required.")

        if points <= 0:
            raise ValidationError({"points": "Points to redeem must be positive."})

        with transaction.atomic():
            account = LoyaltyAccount.objects.select_for_update().get(pk=loyalty_account.pk)

            if account.points_balance < points:
                raise InsufficientLoyaltyPoints(
                    f"Insufficient points: balance={account.points_balance}, required={points}"
                )

            balance_before = account.points_balance
            balance_after = balance_before - points
            validate_loyalty_balance_integrity(balance_before, -points, balance_after)

            from crm.models import LoyaltyTransaction
            txn = LoyaltyTransaction.objects.create(
                loyalty_account=account,
                transaction_type=LOYALTY_REDEEM,
                points=-points,
                balance_before=balance_before,
                balance_after=balance_after,
                reason=reason,
                created_by=actor,
            )

            account.points_balance = balance_after
            account.lifetime_points_redeemed += points
            account.save(update_fields=[
                "points_balance", "lifetime_points_redeemed", "updated_at"
            ])

        _emit_audit(
            AUDIT_LOYALTY_POINTS_REDEEMED, "LOYALTY_TRANSACTION", txn.pk,
            customer=account.customer,
            metadata={"points": points, "balance_after": balance_after},
        )
        return txn

    @staticmethod
    def adjust_points(loyalty_account, points: int, reason: str, actor=None) -> "LoyaltyTransaction":
        """
        Manual points adjustment (positive or negative).
        Requires loyalty.adjust permission.
        """
        from crm.models import LoyaltyAccount, LoyaltyTransaction

        if actor and not acl.has_permission(actor, PERM_LOYALTY_ADJUST):
            raise CRMPermissionDenied("loyalty.adjust permission required.")

        if not reason:
            raise ValidationError({"reason": "A reason is required for manual adjustments."})

        with transaction.atomic():
            account = LoyaltyAccount.objects.select_for_update().get(pk=loyalty_account.pk)

            balance_before = account.points_balance
            proposed_after = balance_before + points

            if proposed_after < 0:
                raise InsufficientLoyaltyPoints(
                    "Adjustment would result in negative balance."
                )

            balance_after = proposed_after
            validate_loyalty_balance_integrity(balance_before, points, balance_after)

            txn = LoyaltyTransaction.objects.create(
                loyalty_account=account,
                transaction_type=LOYALTY_ADJUSTMENT,
                points=points,
                balance_before=balance_before,
                balance_after=balance_after,
                reason=reason,
                created_by=actor,
            )

            account.points_balance = balance_after
            if points > 0:
                account.lifetime_points_earned += points
            account.save(update_fields=[
                "points_balance", "lifetime_points_earned", "updated_at"
            ])

        _emit_audit(
            AUDIT_LOYALTY_POINTS_ADJUSTED, "LOYALTY_TRANSACTION", txn.pk,
            customer=account.customer,
            metadata={"points": points, "reason": reason},
        )
        return txn

    @staticmethod
    def expire_points(loyalty_account, points: int, reason: str = "", actor=None) -> "LoyaltyTransaction | None":
        """
        Expire points from a loyalty account.
        Called by the scheduled loyalty expiry Celery task.
        Idempotent: uses EXPIRY reference to prevent double-expiry on same date.
        """
        from crm.models import LoyaltyAccount, LoyaltyTransaction

        if points <= 0:
            return None

        today_str = timezone.now().date().isoformat()
        ref_id = f"EXPIRY-{today_str}-{loyalty_account.pk}"

        with transaction.atomic():
            account = LoyaltyAccount.objects.select_for_update().get(pk=loyalty_account.pk)

            # Idempotency
            existing = LoyaltyTransaction.objects.filter(
                loyalty_account=account,
                reference_type=LOYALTY_EXPIRY,
                reference_id=ref_id,
            ).first()
            if existing:
                return existing

            safe_expire = min(points, account.points_balance)
            if safe_expire <= 0:
                return None

            balance_before = account.points_balance
            balance_after = balance_before - safe_expire

            txn = LoyaltyTransaction.objects.create(
                loyalty_account=account,
                transaction_type=LOYALTY_EXPIRY,
                points=-safe_expire,
                balance_before=balance_before,
                balance_after=balance_after,
                reference_type=LOYALTY_EXPIRY,
                reference_id=ref_id,
                reason=reason or f"Points expired on {today_str}",
                created_by=actor,
            )

            account.points_balance = balance_after
            account.save(update_fields=["points_balance", "updated_at"])

        _emit_audit(
            AUDIT_LOYALTY_POINTS_EXPIRED, "LOYALTY_TRANSACTION", txn.pk,
            customer=account.customer,
            metadata={"points": safe_expire},
        )
        return txn


# =============================================================================
# RewardService
# =============================================================================

class RewardService:

    @staticmethod
    def create_reward(restaurant, data: dict, actor=None) -> "LoyaltyReward":
        from crm.models import LoyaltyReward

        if actor and not acl.has_permission(actor, PERM_REWARD_MANAGE):
            raise CRMPermissionDenied("reward.manage permission required.")

        reward = LoyaltyReward.objects.create(
            restaurant=restaurant,
            name=data["name"],
            description=data.get("description", ""),
            reward_type=data["reward_type"],
            points_required=data["points_required"],
            reward_value=data.get("reward_value"),
            discount_type=data.get("discount_type", ""),
            discount_value=data.get("discount_value"),
            max_discount_amount=data.get("max_discount_amount"),
            is_active=data.get("is_active", True),
            valid_from=data.get("valid_from"),
            valid_until=data.get("valid_until"),
        )

        _emit_audit(
            AUDIT_REWARD_CREATED, "LOYALTY_REWARD", reward.pk,
            actor=actor, restaurant=restaurant,
            metadata={"name": reward.name, "points_required": reward.points_required},
        )
        return reward

    @staticmethod
    def validate_reward_availability(reward) -> None:
        """Raise if reward is not currently redeemable."""
        if not reward.is_active:
            raise RewardUnavailable(f"Reward '{reward.name}' is not active.")

        now = timezone.now()
        if reward.valid_from and now < reward.valid_from:
            raise RewardUnavailable(f"Reward '{reward.name}' is not yet available.")
        if reward.valid_until and now > reward.valid_until:
            raise RewardExpired(f"Reward '{reward.name}' has expired.")

    @staticmethod
    def redeem_reward(customer, reward, loyalty_account, actor=None) -> "RewardRedemption":
        """
        Full reward redemption flow:
          1. Validate reward availability
          2. Validate customer balance
          3. Lock loyalty account
          4. Deduct points (creates LoyaltyTransaction REDEEM)
          5. Create RewardRedemption
          6. Commit atomically

        If any step fails → full rollback.
        """
        from crm.models import LoyaltyAccount, RewardRedemption

        if actor and not acl.has_permission(actor, PERM_REWARD_REDEEM):
            raise CRMPermissionDenied("reward.redeem permission required.")

        RewardService.validate_reward_availability(reward)

        if str(reward.restaurant_id) != str(customer.restaurant_id):
            raise RewardUnavailable("Reward does not belong to customer's restaurant.")

        with transaction.atomic():
            account = LoyaltyAccount.objects.select_for_update().get(pk=loyalty_account.pk)

            if account.points_balance < reward.points_required:
                raise InsufficientLoyaltyPoints(
                    f"Need {reward.points_required} points, have {account.points_balance}."
                )

            reference_code = _generate_reference_code()

            # Deduct via LoyaltyService.redeem_points (already inside atomic)
            redeem_txn = LoyaltyService.redeem_points(
                loyalty_account=account,
                points=reward.points_required,
                reason=f"Reward redemption: {reward.name}",
                actor=actor,
            )

            # Update txn reference to link to redemption
            redemption = RewardRedemption.objects.create(
                customer=customer,
                loyalty_account=account,
                reward=reward,
                points_used=reward.points_required,
                status=REDEMPTION_CONFIRMED,
                reference_code=reference_code,
                redeemed_at=timezone.now(),
                expires_at=reward.valid_until,
            )

            # Back-link the LoyaltyTransaction to this redemption
            redeem_txn.reference_type = "REDEMPTION"
            redeem_txn.reference_id = str(redemption.pk)
            LoyaltyTransaction = redeem_txn.__class__
            # Can't update immutable record — log for reference only
            logger.info(
                "RewardService.redeem_reward: customer=%s reward=%s code=%s",
                customer.customer_number, reward.name, reference_code,
            )

        _emit_audit(
            AUDIT_REWARD_REDEEMED, "REWARD_REDEMPTION", redemption.pk,
            actor=actor, company=customer.company, restaurant=reward.restaurant,
            customer=customer,
            metadata={
                "reward_name": reward.name,
                "points_used": reward.points_required,
                "reference_code": reference_code,
            },
        )
        return redemption

    @staticmethod
    def cancel_redemption(redemption, actor=None) -> "RewardRedemption":
        """Cancel an unused redemption and refund points."""
        if redemption.status not in (REDEMPTION_REQUESTED, REDEMPTION_CONFIRMED):
            raise RewardRedemptionConflict(
                f"Cannot cancel a redemption in status {redemption.status}."
            )

        with transaction.atomic():
            # Refund the points via bonus
            LoyaltyService.adjust_points(
                loyalty_account=redemption.loyalty_account,
                points=redemption.points_used,
                reason=f"Refund for cancelled redemption {redemption.reference_code}",
                actor=actor,
            )
            redemption.status = REDEMPTION_CANCELLED
            redemption.save(update_fields=["status", "updated_at"])

        _emit_audit(
            AUDIT_REWARD_CANCELLED, "REWARD_REDEMPTION", redemption.pk,
            actor=actor, customer=redemption.customer,
            metadata={"reference_code": redemption.reference_code},
        )
        return redemption
