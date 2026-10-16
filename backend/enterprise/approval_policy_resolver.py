# =============================================================================
# RestaurantFlow — Approval Policy Resolver
# Phase 20
#
# Resolves whether a given operation requires approval by looking up
# ApprovalPolicy records using the same hierarchy as ConfigurationResolver:
#
#   Branch → Restaurant → Company → System default (no approval)
#
# Existing modules (billing, inventory, financials) can consume this
# resolver WITHOUT rewriting their existing approval workflows.
#
# Usage example:
#
#   resolver = ApprovalPolicyResolver(
#       policy_type=POLICY_TYPE_EXPENSE,
#       amount=Decimal("12000.00"),
#       branch=branch,
#   )
#   if resolver.requires_approval():
#       required_perm = resolver.get_required_permission()
# =============================================================================

import logging
from decimal import Decimal
from typing import Optional

from enterprise.constants import (
    POLICY_TYPE_EXPENSE,
    POLICY_TYPE_DISCOUNT,
    POLICY_TYPE_REFUND,
    POLICY_TYPE_WASTAGE,
    POLICY_TYPE_STOCK_TRANSFER,
    POLICY_TYPE_CONFIGURATION,
    POLICY_TYPE_PRICE_ROLLOUT,
)

logger = logging.getLogger("enterprise")


class ApprovalPolicyResolver:
    """
    Stateful resolver for a single approval check.

    Instantiate with the context of the operation being checked, then call
    the query methods.

    Hierarchy resolution:
        Branch  → most-specific
        Restaurant → restaurant-level default
        Company → broadest configured scope
        System  → no approval required by default (safe fail-open)

    The resolver returns the MOST RESTRICTIVE policy found at the most
    specific scope — it does NOT merge policies across levels.
    """

    def __init__(
        self,
        policy_type: str,
        branch=None,
        restaurant=None,
        company=None,
        amount: Optional[Decimal] = None,
        percentage: Optional[Decimal] = None,
    ):
        """
        Args:
            policy_type:  One of the POLICY_TYPE_* constants.
            branch:       Branch instance (most-specific scope).
            restaurant:   Restaurant instance (derived from branch if omitted).
            company:      Organization instance (derived if omitted).
            amount:       Monetary amount for threshold checks.
            percentage:   Percentage value for threshold checks.
        """
        self.policy_type = policy_type
        self.branch = branch
        self.restaurant = restaurant or (branch.restaurant if branch else None)
        self.company = company or (self.restaurant.organization if self.restaurant else None)
        self.amount = Decimal(str(amount)) if amount is not None else None
        self.percentage = Decimal(str(percentage)) if percentage is not None else None

        # Resolved on first access via _resolve()
        self._resolved_policy = None
        self._resolved = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def requires_approval(self) -> bool:
        """
        Return True if the operation requires approval given the current context.

        An operation requires approval if:
        1. A matching ApprovalPolicy exists at the most-specific scope, AND
        2. The provided amount/percentage meets or exceeds the policy threshold.

        Returns False if no policy is found (system default = no approval required).
        """
        policy = self._resolve()
        if policy is None:
            return False

        # Check monetary threshold
        if policy.threshold_amount is not None and self.amount is not None:
            if self.amount >= policy.threshold_amount:
                return True

        # Check percentage threshold
        if policy.threshold_percentage is not None and self.percentage is not None:
            if self.percentage >= policy.threshold_percentage:
                return True

        # If a policy exists but thresholds are null, the policy always triggers
        if policy.threshold_amount is None and policy.threshold_percentage is None:
            return True

        return False

    def get_required_permission(self) -> Optional[str]:
        """
        Return the permission code required to approve this operation.
        Returns None if no approval is required.
        """
        if not self.requires_approval():
            return None
        policy = self._resolve()
        return policy.required_permission if policy else None

    def get_required_role(self):
        """
        Return the Role instance required to approve (or None).
        """
        if not self.requires_approval():
            return None
        policy = self._resolve()
        return policy.required_role if policy else None

    def get_policy(self):
        """
        Return the resolved ApprovalPolicy instance, or None if no policy found.
        """
        return self._resolve()

    def get_policy_summary(self) -> dict:
        """
        Return a structured summary of the resolved policy for API/UI display.

        {
            "requires_approval": bool,
            "policy_found": bool,
            "policy_scope": "BRANCH" | "RESTAURANT" | "COMPANY" | None,
            "required_permission": str | None,
            "required_role": str | None,
            "threshold_amount": Decimal | None,
            "threshold_percentage": Decimal | None,
        }
        """
        policy = self._resolve()
        approval_required = self.requires_approval()
        return {
            "requires_approval": approval_required,
            "policy_found": policy is not None,
            "policy_scope": self._get_policy_scope(policy),
            "required_permission": policy.required_permission if policy else None,
            "required_role": policy.required_role.code if (policy and policy.required_role) else None,
            "threshold_amount": policy.threshold_amount if policy else None,
            "threshold_percentage": policy.threshold_percentage if policy else None,
        }

    # ------------------------------------------------------------------
    # Class-level helpers (stateless convenience)
    # ------------------------------------------------------------------

    @classmethod
    def check(
        cls,
        policy_type: str,
        branch=None,
        restaurant=None,
        company=None,
        amount: Optional[Decimal] = None,
        percentage: Optional[Decimal] = None,
    ) -> bool:
        """
        One-shot convenience method — return True if approval is required.

        Equivalent to:
            ApprovalPolicyResolver(policy_type, branch=branch, amount=amount).requires_approval()
        """
        return cls(
            policy_type=policy_type,
            branch=branch,
            restaurant=restaurant,
            company=company,
            amount=amount,
            percentage=percentage,
        ).requires_approval()

    @classmethod
    def get_permission_for(
        cls,
        policy_type: str,
        branch=None,
        restaurant=None,
        company=None,
        amount: Optional[Decimal] = None,
        percentage: Optional[Decimal] = None,
    ) -> Optional[str]:
        """
        One-shot convenience method — return the required permission code.
        """
        return cls(
            policy_type=policy_type,
            branch=branch,
            restaurant=restaurant,
            company=company,
            amount=amount,
            percentage=percentage,
        ).get_required_permission()

    @classmethod
    def list_policies_for_scope(
        cls,
        company,
        restaurant=None,
        branch=None,
        active_only: bool = True,
    ):
        """
        Return all ApprovalPolicy records for a given scope (most-specific
        available at that scope — does NOT resolve hierarchy).

        Useful for the approval policy management UI.
        """
        from enterprise.models import ApprovalPolicy

        qs = ApprovalPolicy.objects.filter(company=company)
        if active_only:
            qs = qs.filter(is_active=True)

        if branch:
            qs = qs.filter(restaurant=restaurant, branch=branch)
        elif restaurant:
            qs = qs.filter(restaurant=restaurant, branch__isnull=True)
        else:
            qs = qs.filter(restaurant__isnull=True, branch__isnull=True)

        return qs.select_related("required_role", "company", "restaurant", "branch")

    # ------------------------------------------------------------------
    # Resolution logic
    # ------------------------------------------------------------------

    def _resolve(self):
        """
        Resolve and cache the most-specific ApprovalPolicy for this context.
        Resolution is lazy — computed once per resolver instance.
        """
        if self._resolved:
            return self._resolved_policy

        self._resolved = True
        self._resolved_policy = None

        if self.company is None:
            logger.debug(
                "approval_resolver: no company scope — cannot resolve policy for type=%s",
                self.policy_type,
            )
            return None

        # 1. Branch scope
        if self.branch is not None and self.restaurant is not None:
            policy = self._fetch_policy(
                company=self.company,
                restaurant=self.restaurant,
                branch=self.branch,
            )
            if policy is not None:
                self._resolved_policy = policy
                logger.debug(
                    "approval_resolver: resolved policy at BRANCH scope type=%s branch=%s",
                    self.policy_type,
                    self.branch.pk,
                )
                return self._resolved_policy

        # 2. Restaurant scope
        if self.restaurant is not None:
            policy = self._fetch_policy(
                company=self.company,
                restaurant=self.restaurant,
                branch=None,
            )
            if policy is not None:
                self._resolved_policy = policy
                logger.debug(
                    "approval_resolver: resolved policy at RESTAURANT scope type=%s rest=%s",
                    self.policy_type,
                    self.restaurant.pk,
                )
                return self._resolved_policy

        # 3. Company scope
        policy = self._fetch_policy(
            company=self.company,
            restaurant=None,
            branch=None,
        )
        if policy is not None:
            self._resolved_policy = policy
            logger.debug(
                "approval_resolver: resolved policy at COMPANY scope type=%s company=%s",
                self.policy_type,
                self.company.pk,
            )

        return self._resolved_policy

    def _fetch_policy(self, company, restaurant, branch):
        """Fetch a single active ApprovalPolicy for the exact scope."""
        from enterprise.models import ApprovalPolicy

        qs = ApprovalPolicy.objects.filter(
            company=company,
            restaurant=restaurant,
            branch=branch,
            policy_type=self.policy_type,
            is_active=True,
        ).select_related("required_role")

        # Return the most restrictive (lowest threshold) if multiples exist
        # Normally there should be at most one per scope due to policy management
        policy = qs.order_by("threshold_amount", "threshold_percentage").first()
        return policy

    def _get_policy_scope(self, policy) -> Optional[str]:
        """Return the scope level string for a resolved policy."""
        if policy is None:
            return None
        if policy.branch_id:
            return "BRANCH"
        if policy.restaurant_id:
            return "RESTAURANT"
        return "COMPANY"
