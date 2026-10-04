# =============================================================================
# RestaurantFlow — Payment Reporting Indexes
# Phase 14: Add indexes for reporting query performance
# =============================================================================

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("payments", "0001_initial"),
    ]

    operations = [
        # Index for payment analytics: completed payments by branch + date
        migrations.AddIndex(
            model_name="payment",
            index=models.Index(
                fields=["branch", "payment_method", "status"],
                name="pay_branch_method_status_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="payment",
            index=models.Index(
                fields=["branch", "status", "completed_at"],
                name="pay_branch_status_completed_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="payment",
            index=models.Index(
                fields=["completed_at"],
                name="pay_completed_at_idx",
            ),
        ),
        # Refund index for date-range queries
        migrations.AddIndex(
            model_name="paymentrefund",
            index=models.Index(
                fields=["processed_at"],
                name="refund_processed_at_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="paymentrefund",
            index=models.Index(
                fields=["status", "processed_at"],
                name="refund_status_processed_idx",
            ),
        ),
    ]
