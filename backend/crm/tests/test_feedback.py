# =============================================================================
# RestaurantFlow — CRM Feedback Tests
# Phase 17
# =============================================================================

from django.test import TestCase
from rest_framework.test import APIClient

from crm.feedback_services import FeedbackService, FeedbackModerationService
from crm.exceptions import (
    FeedbackAlreadyExists, FeedbackNotAllowed, FeedbackModerationNotAllowed,
    CRMPermissionDenied,
)
from crm.tests.base import CRMTestBase


class FeedbackCreationTests(CRMTestBase):

    def test_create_feedback_basic(self):
        feedback = FeedbackService.create_feedback(
            data={
                "customer": None,
                "restaurant": self.restaurant,
                "branch": self.branch,
                "order": None,
                "rating": 4,
                "comment": "Great food!",
            },
            actor=self.cashier_user,
        )
        self.assertEqual(feedback.rating, 4)
        self.assertEqual(feedback.status, "SUBMITTED")

    def test_invalid_rating_rejected(self):
        with self.assertRaises(Exception):
            FeedbackService.create_feedback(
                data={
                    "restaurant": self.restaurant,
                    "rating": 6,  # invalid
                },
                actor=self.cashier_user,
            )

    def test_rating_zero_rejected(self):
        with self.assertRaises(Exception):
            FeedbackService.create_feedback(
                data={
                    "restaurant": self.restaurant,
                    "rating": 0,
                },
                actor=self.cashier_user,
            )

    def test_duplicate_feedback_per_order_raises(self):
        from orders.models import Order, OrderType, OrderStatus
        c = self.make_customer(phone="+910002000001")
        order = Order.objects.create(
            branch=self.branch, order_number="ORD-FB-001",
            order_type=OrderType.COUNTER,
            status=OrderStatus.CONFIRMED,
            created_by=self.cashier_user,
            customer=c,
        )
        FeedbackService.create_feedback(
            data={"customer": c, "restaurant": self.restaurant, "branch": self.branch,
                  "order": order, "rating": 4},
            actor=self.cashier_user,
        )
        with self.assertRaises(FeedbackAlreadyExists):
            FeedbackService.create_feedback(
                data={"customer": c, "restaurant": self.restaurant, "branch": self.branch,
                      "order": order, "rating": 3},
                actor=self.cashier_user,
            )

    def test_cancelled_order_feedback_blocked(self):
        from orders.models import Order, OrderType, OrderStatus
        c = self.make_customer(phone="+910002000002")
        order = Order.objects.create(
            branch=self.branch, order_number="ORD-CANC-001",
            order_type=OrderType.COUNTER,
            status=OrderStatus.CANCELLED,
            created_by=self.cashier_user,
            customer=c,
        )
        with self.assertRaises(FeedbackNotAllowed):
            FeedbackService.create_feedback(
                data={"customer": c, "restaurant": self.restaurant, "branch": self.branch,
                      "order": order, "rating": 2},
                actor=self.cashier_user,
            )

    def test_feedback_requires_permission(self):
        with self.assertRaises(CRMPermissionDenied):
            FeedbackService.create_feedback(
                data={"restaurant": self.restaurant, "rating": 3},
                actor=self.no_crm_user,
            )


class FeedbackModerationTests(CRMTestBase):

    def _make_feedback(self, rating=3):
        return FeedbackService.create_feedback(
            data={"customer": None, "restaurant": self.restaurant,
                  "branch": self.branch, "order": None, "rating": rating},
            actor=self.cashier_user,
        )

    def test_approve_feedback(self):
        feedback = self._make_feedback(rating=4)
        mod = FeedbackModerationService.moderate_feedback(
            feedback, "APPROVED", note="Looks good", actor=self.manager_user
        )
        self.assertEqual(mod.status, "APPROVED")
        feedback.refresh_from_db()
        self.assertEqual(feedback.status, "REVIEWED")

    def test_hide_feedback(self):
        feedback = self._make_feedback(rating=1)
        FeedbackModerationService.moderate_feedback(
            feedback, "HIDDEN", note="Spam", actor=self.manager_user
        )
        feedback.refresh_from_db()
        self.assertEqual(feedback.status, "HIDDEN")

    def test_moderate_requires_permission(self):
        feedback = self._make_feedback()
        with self.assertRaises(FeedbackModerationNotAllowed):
            FeedbackModerationService.moderate_feedback(
                feedback, "APPROVED", actor=self.no_crm_user
            )

    def test_resolve_feedback(self):
        feedback = self._make_feedback(rating=2)
        FeedbackModerationService.resolve_feedback(feedback, actor=self.manager_user)
        feedback.refresh_from_db()
        self.assertEqual(feedback.status, "RESOLVED")


class FeedbackAPITests(CRMTestBase):

    def setUp(self):
        self.client = APIClient()

    def test_list_feedback_requires_auth(self):
        res = self.client.get("/api/crm/feedback/")
        self.assertEqual(res.status_code, 401)

    def test_list_feedback_scoped(self):
        # Create feedback for self.restaurant
        FeedbackService.create_feedback(
            data={"restaurant": self.restaurant, "branch": self.branch,
                  "rating": 3, "customer": None, "order": None},
            actor=self.cashier_user,
        )
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {self.get_token(self.manager_user)}"
        )
        res = self.client.get("/api/crm/feedback/")
        self.assertEqual(res.status_code, 200)
        self.assertGreaterEqual(res.data["count"], 1)
