# Generated migration — Phase 17: Add nullable customer FK to Order

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0002_reporting_indexes"),
        ("crm", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="order",
            name="customer",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="orders",
                to="crm.customer",
                help_text=(
                    "Optional CRM customer link. Null for anonymous/guest orders. "
                    "Never required — POS can create orders without a customer."
                ),
            ),
        ),
        migrations.AddIndex(
            model_name="order",
            index=models.Index(fields=["customer", "status"], name="orders_order_customer_status_idx"),
        ),
        migrations.AddIndex(
            model_name="order",
            index=models.Index(fields=["customer", "created_at"], name="orders_order_customer_created_idx"),
        ),
    ]
