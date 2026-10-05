# =============================================================================
# RestaurantFlow — CRM Segmentation Tests
# Phase 17
# =============================================================================

from decimal import Decimal
from django.test import TestCase
from django.utils import timezone

from crm.segmentation_services import CustomerSegmentationService
from crm.tests.base import CRMTestBase


class SegmentCriteriaTests(CRMTestBase):

    def _make_segment(self, code, criteria, restaurant=None):
        from crm.models import CustomerSegment
        return CustomerSegment.objects.create(
            restaurant=restaurant or self.restaurant,
            name=f"Seg {code}",
            code=code,
            criteria=criteria,
            is_active=True,
        )

    def test_min_orders_passes(self):
        seg = self._make_segment("FREQ", {"min_orders": 5})
        c = self.make_customer(phone="+910003000001")
        c.total_orders = 10
        c.save(update_fields=["total_orders"])
        self.assertTrue(CustomerSegmentationService.evaluate_customer(c, seg))

    def test_min_orders_fails(self):
        seg = self._make_segment("FREQ2", {"min_orders": 5})
        c = self.make_customer(phone="+910003000002")
        c.total_orders = 2
        c.save(update_fields=["total_orders"])
        self.assertFalse(CustomerSegmentationService.evaluate_customer(c, seg))

    def test_min_lifetime_spend_passes(self):
        seg = self._make_segment("HV", {"min_lifetime_spend": 10000})
        c = self.make_customer(phone="+910003000003")
        c.lifetime_spend = Decimal("15000.00")
        c.save(update_fields=["lifetime_spend"])
        self.assertTrue(CustomerSegmentationService.evaluate_customer(c, seg))

    def test_days_since_last_order_passes(self):
        seg = self._make_segment("ATRISKVX", {"days_since_last_order": 60})
        c = self.make_customer(phone="+910003000004")
        c.last_order_at = timezone.now() - timezone.timedelta(days=90)
        c.save(update_fields=["last_order_at"])
        self.assertTrue(CustomerSegmentationService.evaluate_customer(c, seg))

    def test_days_since_last_order_fails(self):
        seg = self._make_segment("ATRISKVXX", {"days_since_last_order": 60})
        c = self.make_customer(phone="+910003000005")
        c.last_order_at = timezone.now() - timezone.timedelta(days=10)
        c.save(update_fields=["last_order_at"])
        self.assertFalse(CustomerSegmentationService.evaluate_customer(c, seg))

    def test_assign_segments(self):
        seg = self._make_segment("HIVALUE2", {"min_lifetime_spend": 1000})
        c = self.make_customer(phone="+910003000006")
        c.lifetime_spend = Decimal("5000.00")
        c.save(update_fields=["lifetime_spend"])

        assigned = CustomerSegmentationService.assign_segments(c)
        self.assertIn(seg, assigned)

        from crm.models import CustomerSegmentAssignment
        self.assertTrue(
            CustomerSegmentAssignment.objects.filter(
                customer=c, segment=seg, is_active=True
            ).exists()
        )

    def test_no_duplicate_assignment(self):
        seg = self._make_segment("NODUP", {"min_orders": 1})
        c = self.make_customer(phone="+910003000007")
        c.total_orders = 5
        c.save(update_fields=["total_orders"])

        CustomerSegmentationService.assign_segments(c)
        CustomerSegmentationService.assign_segments(c)

        from crm.models import CustomerSegmentAssignment
        count = CustomerSegmentAssignment.objects.filter(
            customer=c, segment=seg, is_active=True
        ).count()
        self.assertEqual(count, 1)

    def test_remove_invalid_segments(self):
        seg = self._make_segment("TEMP", {"min_orders": 5})
        c = self.make_customer(phone="+910003000008")
        c.total_orders = 10
        c.save(update_fields=["total_orders"])
        CustomerSegmentationService.assign_segments(c)

        # Now customer no longer qualifies
        c.total_orders = 2
        c.save(update_fields=["total_orders"])
        removed = CustomerSegmentationService.remove_invalid_segments(c)
        self.assertEqual(removed, 1)


class SegmentScopeTests(CRMTestBase):

    def test_segments_scoped_to_restaurant(self):
        from crm.access import get_accessible_segments
        from crm.models import CustomerSegment

        seg_mine = CustomerSegment.objects.create(
            restaurant=self.restaurant, name="Mine", code="MINE", criteria={}, is_active=True
        )
        seg_other = CustomerSegment.objects.create(
            restaurant=self.other_restaurant, name="Other", code="OTHER", criteria={}, is_active=True
        )
        accessible = get_accessible_segments(self.manager_user)
        ids = list(accessible.values_list("id", flat=True))
        self.assertIn(seg_mine.pk, ids)
        self.assertNotIn(seg_other.pk, ids)
