# =============================================================================
# RestaurantFlow — Export Tests
# Phase 14
# =============================================================================

from decimal import Decimal
from datetime import date

from django.urls import reverse
from rest_framework.test import APIClient

from reporting.tests.base import ReportingTestBase
from reporting.export_services import generate_csv


class CSVGenerationTests(ReportingTestBase):

    def test_generate_csv_from_list(self):
        """generate_csv should produce valid UTF-8 CSV bytes."""
        data = [
            {
                "menu_item_name": "Chicken Biryani",
                "category": "Main Course",
                "quantity_sold": Decimal("10.000"),
                "gross_revenue": Decimal("2500.00"),
                "discount_amount": Decimal("0.00"),
                "net_revenue": Decimal("2625.00"),
                "average_selling_price": Decimal("250.00"),
                "number_of_orders": 10,
                "percentage_of_sales": Decimal("100.00"),
            }
        ]
        csv_bytes, row_count = generate_csv("menu_items", data)
        self.assertIsInstance(csv_bytes, bytes)
        self.assertEqual(row_count, 1)
        content = csv_bytes.decode("utf-8-sig")
        self.assertIn("Chicken Biryani", content)
        self.assertIn("Item Name", content)  # header

    def test_generate_csv_dict_summary(self):
        data = {
            "gross_sales": Decimal("5000.00"),
            "discount_amount": Decimal("0.00"),
            "taxable_amount": Decimal("5000.00"),
            "tax_amount": Decimal("250.00"),
            "rounding_amount": Decimal("0.00"),
            "net_sales": Decimal("5250.00"),
            "number_of_bills": 10,
            "average_bill_value": Decimal("525.00"),
        }
        csv_bytes, row_count = generate_csv("sales_summary", data)
        self.assertIsInstance(csv_bytes, bytes)
        content = csv_bytes.decode("utf-8-sig")
        self.assertIn("Gross Sales", content)

    def test_generate_csv_empty_list(self):
        csv_bytes, row_count = generate_csv("menu_items", [])
        self.assertEqual(row_count, 0)
        content = csv_bytes.decode("utf-8-sig")
        # Should still have header
        self.assertIn("Item Name", content)

    def test_generate_csv_unknown_report_type_raises(self):
        from reporting.exceptions import ExportGenerationError
        with self.assertRaises(ExportGenerationError):
            generate_csv("unknown_type", [])


class ExportEndpointTests(ReportingTestBase):

    def setUp(self):
        self.client = APIClient()

    def test_export_csv_requires_auth(self):
        url = reverse("reporting:export-csv", kwargs={"report_type": "sales_summary"})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 401)

    def test_export_csv_requires_permission(self):
        from accounts.models import User
        noperm_user = User.objects.create_user(email="noexp@test.com", password="pass")
        self.client.force_authenticate(user=noperm_user)
        url = reverse("reporting:export-csv", kwargs={"report_type": "menu_top_selling"})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

    def test_export_csv_authorized_returns_csv(self):
        self._make_finalized_bill()
        self.client.force_authenticate(user=self.manager_a)
        url = reverse("reporting:export-csv", kwargs={"report_type": "menu_top_selling"})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/csv", response["Content-Type"])

    def test_export_csv_content_disposition_set(self):
        self.client.force_authenticate(user=self.manager_a)
        url = reverse("reporting:export-csv", kwargs={"report_type": "menu_top_selling"})
        response = self.client.get(url)
        self.assertIn("attachment", response["Content-Disposition"])

    def test_export_invalid_report_type_returns_400(self):
        self.client.force_authenticate(user=self.manager_a)
        url = reverse("reporting:export-csv", kwargs={"report_type": "nonexistent_report"})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 400)

    def test_export_audit_record_created_on_success(self):
        from reporting.models import ReportExportAudit
        self._make_finalized_bill()
        self.client.force_authenticate(user=self.manager_a)
        initial_count = ReportExportAudit.objects.count()
        url = reverse("reporting:export-csv", kwargs={"report_type": "menu_top_selling"})
        self.client.get(url)
        self.assertEqual(ReportExportAudit.objects.count(), initial_count + 1)

    def test_export_scoped_to_user_org(self):
        """Org B manager exporting menu_top_selling gets no Org A data."""
        self._make_finalized_bill()  # Org A data
        self.client.force_authenticate(user=self.manager_b)
        url = reverse("reporting:export-csv", kwargs={"report_type": "menu_top_selling"})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        content = response.content.decode("utf-8-sig")
        # Should only contain header, no data rows for Org A items
        lines = [l.strip() for l in content.strip().split("\n") if l.strip()]
        # Either 0 or 1 (header-only) lines
        self.assertLessEqual(len(lines), 1)
