# Generated migration for Phase 17 — CRM
# crm/migrations/0001_initial.py

import django.core.validators
import django.db.models.deletion
import django.utils.timezone
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("organizations", "0001_initial"),
        ("menu", "0001_initial"),
        ("orders", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # ---------------------------------------------------------------
        # CustomerSequence
        # ---------------------------------------------------------------
        migrations.CreateModel(
            name="CustomerSequence",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("last_sequence", models.PositiveIntegerField(default=0)),
                ("restaurant", models.OneToOneField(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="customer_sequence",
                    to="organizations.restaurant",
                )),
            ],
            options={"verbose_name": "Customer Sequence", "verbose_name_plural": "Customer Sequences"},
        ),

        # ---------------------------------------------------------------
        # Customer
        # ---------------------------------------------------------------
        migrations.CreateModel(
            name="Customer",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("customer_number", models.CharField(db_index=True, max_length=30)),
                ("first_name", models.CharField(db_index=True, max_length=150)),
                ("last_name", models.CharField(blank=True, db_index=True, max_length=150)),
                ("display_name", models.CharField(blank=True, max_length=200)),
                ("phone", models.CharField(blank=True, db_index=True, max_length=30)),
                ("email", models.EmailField(blank=True, db_index=True, max_length=254)),
                ("date_of_birth", models.DateField(blank=True, null=True)),
                ("gender", models.CharField(blank=True, choices=[("M", "Male"), ("F", "Female"), ("O", "Other")], max_length=1)),
                ("address", models.TextField(blank=True)),
                ("city", models.CharField(blank=True, max_length=100)),
                ("state", models.CharField(blank=True, max_length=100)),
                ("postal_code", models.CharField(blank=True, max_length=20)),
                ("country", models.CharField(blank=True, default="India", max_length=100)),
                ("notes", models.TextField(blank=True)),
                ("preferred_language", models.CharField(blank=True, max_length=10)),
                ("is_active", models.BooleanField(db_index=True, default=True)),
                ("is_blocked", models.BooleanField(db_index=True, default=False)),
                ("blocked_reason", models.TextField(blank=True)),
                ("total_visits", models.PositiveIntegerField(default=0)),
                ("total_orders", models.PositiveIntegerField(default=0)),
                ("lifetime_spend", models.DecimalField(decimal_places=2, default="0.00", max_digits=14)),
                ("last_visit_at", models.DateTimeField(blank=True, db_index=True, null=True)),
                ("last_order_at", models.DateTimeField(blank=True, db_index=True, null=True)),
                ("first_order_at", models.DateTimeField(blank=True, null=True)),
                ("company", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="customers", to="organizations.organization")),
                ("restaurant", models.ForeignKey(db_index=True, on_delete=django.db.models.deletion.PROTECT, related_name="customers", to="organizations.restaurant")),
                ("merged_into", models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name="merged_sources", to="crm.customer",
                )),
            ],
            options={"verbose_name": "Customer", "verbose_name_plural": "Customers", "ordering": ["-created_at"]},
        ),
        migrations.AddConstraint(
            model_name="customer",
            constraint=models.UniqueConstraint(fields=["restaurant", "customer_number"], name="unique_customer_number_per_restaurant"),
        ),
        migrations.AddIndex(model_name="customer", index=models.Index(fields=["company", "restaurant"], name="crm_cust_company_rest_idx")),
        migrations.AddIndex(model_name="customer", index=models.Index(fields=["restaurant", "is_active"], name="crm_cust_rest_active_idx")),
        migrations.AddIndex(model_name="customer", index=models.Index(fields=["phone"], name="crm_cust_phone_idx")),
        migrations.AddIndex(model_name="customer", index=models.Index(fields=["email"], name="crm_cust_email_idx")),
        migrations.AddIndex(model_name="customer", index=models.Index(fields=["last_order_at"], name="crm_cust_last_order_idx")),
        migrations.AddIndex(model_name="customer", index=models.Index(fields=["last_visit_at"], name="crm_cust_last_visit_idx")),

        # ---------------------------------------------------------------
        # CustomerPreference
        # ---------------------------------------------------------------
        migrations.CreateModel(
            name="CustomerPreference",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("preferred_order_type", models.CharField(blank=True, max_length=20)),
                ("dietary_preference", models.CharField(blank=True, choices=[("VEG","Vegetarian"),("NON_VEG","Non-Vegetarian"),("EGG","Eggetarian"),("VEGAN","Vegan"),("JAIN","Jain"),("OTHER","Other"),("UNKNOWN","Unknown")], max_length=20)),
                ("allergy_note", models.TextField(blank=True)),
                ("special_request_note", models.TextField(blank=True)),
                ("customer", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="preference", to="crm.customer")),
                ("restaurant", models.ForeignKey(db_index=True, on_delete=django.db.models.deletion.PROTECT, related_name="customer_preferences", to="organizations.restaurant")),
                ("preferred_branch", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="preferred_customers", to="organizations.branch")),
                ("favorite_category", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to="menu.menucategory")),
                ("favorite_menu_item", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to="menu.menuitem")),
            ],
            options={"verbose_name": "Customer Preference"},
        ),

        # ---------------------------------------------------------------
        # CustomerVisit
        # ---------------------------------------------------------------
        migrations.CreateModel(
            name="CustomerVisit",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("visit_number", models.PositiveIntegerField(default=1)),
                ("visit_started_at", models.DateTimeField(db_index=True)),
                ("visit_completed_at", models.DateTimeField(blank=True, null=True)),
                ("guest_count", models.PositiveIntegerField(default=1)),
                ("visit_type", models.CharField(choices=[("DINE_IN","Dine In"),("TAKEAWAY","Takeaway"),("COUNTER","Counter")], db_index=True, max_length=20)),
                ("status", models.CharField(choices=[("OPEN","Open"),("COMPLETED","Completed"),("CANCELLED","Cancelled")], db_index=True, default="OPEN", max_length=20)),
                ("customer", models.ForeignKey(db_index=True, on_delete=django.db.models.deletion.CASCADE, related_name="visits", to="crm.customer")),
                ("restaurant", models.ForeignKey(db_index=True, on_delete=django.db.models.deletion.PROTECT, related_name="customer_visits", to="organizations.restaurant")),
                ("branch", models.ForeignKey(db_index=True, on_delete=django.db.models.deletion.PROTECT, related_name="customer_visits", to="organizations.branch")),
                ("order", models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="customer_visit", to="orders.order")),
                ("table_session", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="customer_visits", to="orders.tablesession")),
            ],
            options={"verbose_name": "Customer Visit", "ordering": ["-visit_started_at"]},
        ),

        # ---------------------------------------------------------------
        # CustomerTag
        # ---------------------------------------------------------------
        migrations.CreateModel(
            name="CustomerTag",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=100)),
                ("code", models.CharField(db_index=True, max_length=50)),
                ("description", models.TextField(blank=True)),
                ("is_active", models.BooleanField(db_index=True, default=True)),
                ("restaurant", models.ForeignKey(db_index=True, on_delete=django.db.models.deletion.PROTECT, related_name="customer_tags", to="organizations.restaurant")),
            ],
            options={"verbose_name": "Customer Tag"},
        ),
        migrations.AddConstraint(
            model_name="customertag",
            constraint=models.UniqueConstraint(fields=["restaurant", "code"], name="unique_tag_code_per_restaurant"),
        ),

        # ---------------------------------------------------------------
        # CustomerTagAssignment
        # ---------------------------------------------------------------
        migrations.CreateModel(
            name="CustomerTagAssignment",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("assigned_at", models.DateTimeField(auto_now_add=True)),
                ("expires_at", models.DateTimeField(blank=True, null=True)),
                ("is_active", models.BooleanField(db_index=True, default=True)),
                ("customer", models.ForeignKey(db_index=True, on_delete=django.db.models.deletion.CASCADE, related_name="tag_assignments", to="crm.customer")),
                ("tag", models.ForeignKey(db_index=True, on_delete=django.db.models.deletion.PROTECT, related_name="assignments", to="crm.customertag")),
                ("assigned_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="tag_assignments_made", to=settings.AUTH_USER_MODEL)),
            ],
            options={"verbose_name": "Customer Tag Assignment"},
        ),
        migrations.AddConstraint(
            model_name="customertagassignment",
            constraint=models.UniqueConstraint(condition=models.Q(is_active=True), fields=["customer", "tag"], name="unique_active_tag_per_customer"),
        ),

        # ---------------------------------------------------------------
        # CustomerSegment
        # ---------------------------------------------------------------
        migrations.CreateModel(
            name="CustomerSegment",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=100)),
                ("code", models.CharField(db_index=True, max_length=50)),
                ("description", models.TextField(blank=True)),
                ("criteria", models.JSONField(default=dict)),
                ("is_active", models.BooleanField(db_index=True, default=True)),
                ("restaurant", models.ForeignKey(db_index=True, on_delete=django.db.models.deletion.PROTECT, related_name="customer_segments", to="organizations.restaurant")),
            ],
            options={"verbose_name": "Customer Segment"},
        ),
        migrations.AddConstraint(
            model_name="customersegment",
            constraint=models.UniqueConstraint(fields=["restaurant", "code"], name="unique_segment_code_per_restaurant"),
        ),

        # ---------------------------------------------------------------
        # CustomerSegmentAssignment
        # ---------------------------------------------------------------
        migrations.CreateModel(
            name="CustomerSegmentAssignment",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("assigned_at", models.DateTimeField(auto_now_add=True)),
                ("expires_at", models.DateTimeField(blank=True, null=True)),
                ("is_active", models.BooleanField(db_index=True, default=True)),
                ("evaluation_snapshot", models.JSONField(default=dict)),
                ("customer", models.ForeignKey(db_index=True, on_delete=django.db.models.deletion.CASCADE, related_name="segment_assignments", to="crm.customer")),
                ("segment", models.ForeignKey(db_index=True, on_delete=django.db.models.deletion.PROTECT, related_name="assignments", to="crm.customersegment")),
            ],
            options={"verbose_name": "Customer Segment Assignment"},
        ),
        migrations.AddConstraint(
            model_name="customersegmentassignment",
            constraint=models.UniqueConstraint(condition=models.Q(is_active=True), fields=["customer", "segment"], name="unique_active_segment_per_customer"),
        ),

        # ---------------------------------------------------------------
        # LoyaltyProgram
        # ---------------------------------------------------------------
        migrations.CreateModel(
            name="LoyaltyProgram",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=200)),
                ("description", models.TextField(blank=True)),
                ("is_active", models.BooleanField(db_index=True, default=True)),
                ("points_per_currency_unit", models.DecimalField(decimal_places=4, default="1.0000", max_digits=8, validators=[django.core.validators.MinValueValidator("0.0001")])),
                ("minimum_redemption_points", models.PositiveIntegerField(default=100)),
                ("point_expiry_days", models.PositiveIntegerField(blank=True, null=True)),
                ("restaurant", models.ForeignKey(db_index=True, on_delete=django.db.models.deletion.PROTECT, related_name="loyalty_programs", to="organizations.restaurant")),
            ],
            options={"verbose_name": "Loyalty Program"},
        ),

        # ---------------------------------------------------------------
        # LoyaltyAccount
        # ---------------------------------------------------------------
        migrations.CreateModel(
            name="LoyaltyAccount",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("points_balance", models.PositiveIntegerField(default=0)),
                ("lifetime_points_earned", models.PositiveIntegerField(default=0)),
                ("lifetime_points_redeemed", models.PositiveIntegerField(default=0)),
                ("customer", models.ForeignKey(db_index=True, on_delete=django.db.models.deletion.CASCADE, related_name="loyalty_accounts", to="crm.customer")),
                ("loyalty_program", models.ForeignKey(db_index=True, on_delete=django.db.models.deletion.PROTECT, related_name="accounts", to="crm.loyaltyprogram")),
            ],
            options={"verbose_name": "Loyalty Account"},
        ),
        migrations.AddConstraint(
            model_name="loyaltyaccount",
            constraint=models.UniqueConstraint(fields=["customer", "loyalty_program"], name="unique_loyalty_account_per_program"),
        ),

        # ---------------------------------------------------------------
        # LoyaltyTransaction
        # ---------------------------------------------------------------
        migrations.CreateModel(
            name="LoyaltyTransaction",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("transaction_type", models.CharField(choices=[("EARN","Earn"),("REDEEM","Redeem"),("BONUS","Bonus"),("ADJUSTMENT","Adjustment"),("EXPIRY","Expiry"),("REVERSAL","Reversal")], db_index=True, max_length=20)),
                ("points", models.IntegerField()),
                ("balance_before", models.PositiveIntegerField()),
                ("balance_after", models.PositiveIntegerField()),
                ("reference_type", models.CharField(blank=True, db_index=True, max_length=50)),
                ("reference_id", models.CharField(blank=True, db_index=True, max_length=100)),
                ("reason", models.TextField(blank=True)),
                ("loyalty_account", models.ForeignKey(db_index=True, on_delete=django.db.models.deletion.PROTECT, related_name="transactions", to="crm.loyaltyaccount")),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="loyalty_transactions_created", to=settings.AUTH_USER_MODEL)),
            ],
            options={"verbose_name": "Loyalty Transaction", "ordering": ["-created_at"]},
        ),
        migrations.AddConstraint(
            model_name="loyaltytransaction",
            constraint=models.UniqueConstraint(
                condition=~models.Q(reference_type=""),
                fields=["loyalty_account", "reference_type", "reference_id"],
                name="unique_loyalty_transaction_per_reference",
            ),
        ),

        # ---------------------------------------------------------------
        # LoyaltyReward
        # ---------------------------------------------------------------
        migrations.CreateModel(
            name="LoyaltyReward",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=200)),
                ("description", models.TextField(blank=True)),
                ("reward_type", models.CharField(choices=[("DISCOUNT","Discount"),("FIXED_AMOUNT","Fixed Amount"),("PERCENTAGE","Percentage"),("FREE_ITEM","Free Item"),("OTHER","Other")], db_index=True, max_length=20)),
                ("points_required", models.PositiveIntegerField(validators=[django.core.validators.MinValueValidator(1)])),
                ("reward_value", models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ("discount_type", models.CharField(blank=True, max_length=20)),
                ("discount_value", models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ("max_discount_amount", models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ("is_active", models.BooleanField(db_index=True, default=True)),
                ("valid_from", models.DateTimeField(blank=True, null=True)),
                ("valid_until", models.DateTimeField(blank=True, null=True, db_index=True)),
                ("restaurant", models.ForeignKey(db_index=True, on_delete=django.db.models.deletion.PROTECT, related_name="loyalty_rewards", to="organizations.restaurant")),
            ],
            options={"verbose_name": "Loyalty Reward", "ordering": ["points_required"]},
        ),

        # ---------------------------------------------------------------
        # RewardRedemption
        # ---------------------------------------------------------------
        migrations.CreateModel(
            name="RewardRedemption",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("points_used", models.PositiveIntegerField()),
                ("status", models.CharField(choices=[("REQUESTED","Requested"),("CONFIRMED","Confirmed"),("USED","Used"),("CANCELLED","Cancelled"),("EXPIRED","Expired")], db_index=True, default="REQUESTED", max_length=20)),
                ("reference_code", models.CharField(blank=True, db_index=True, max_length=20)),
                ("redeemed_at", models.DateTimeField(blank=True, null=True)),
                ("expires_at", models.DateTimeField(blank=True, null=True, db_index=True)),
                ("customer", models.ForeignKey(db_index=True, on_delete=django.db.models.deletion.PROTECT, related_name="reward_redemptions", to="crm.customer")),
                ("loyalty_account", models.ForeignKey(db_index=True, on_delete=django.db.models.deletion.PROTECT, related_name="redemptions", to="crm.loyaltyaccount")),
                ("reward", models.ForeignKey(db_index=True, on_delete=django.db.models.deletion.PROTECT, related_name="redemptions", to="crm.loyaltyreward")),
                ("applied_to_order", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="reward_redemptions", to="orders.order")),
            ],
            options={"verbose_name": "Reward Redemption", "ordering": ["-created_at"]},
        ),

        # ---------------------------------------------------------------
        # CustomerFeedback
        # ---------------------------------------------------------------
        migrations.CreateModel(
            name="CustomerFeedback",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("rating", models.PositiveSmallIntegerField(validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(5)])),
                ("service_rating", models.PositiveSmallIntegerField(blank=True, null=True, validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(5)])),
                ("food_rating", models.PositiveSmallIntegerField(blank=True, null=True, validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(5)])),
                ("ambience_rating", models.PositiveSmallIntegerField(blank=True, null=True, validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(5)])),
                ("comment", models.TextField(blank=True)),
                ("status", models.CharField(choices=[("SUBMITTED","Submitted"),("REVIEWED","Reviewed"),("RESOLVED","Resolved"),("HIDDEN","Hidden")], db_index=True, default="SUBMITTED", max_length=20)),
                ("customer", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="feedback", to="crm.customer")),
                ("restaurant", models.ForeignKey(db_index=True, on_delete=django.db.models.deletion.PROTECT, related_name="customer_feedback", to="organizations.restaurant")),
                ("branch", models.ForeignKey(blank=True, db_index=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="customer_feedback", to="organizations.branch")),
                ("order", models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="customer_feedback", to="orders.order")),
                ("visit", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="feedback", to="crm.customervisit")),
            ],
            options={"verbose_name": "Customer Feedback", "ordering": ["-created_at"]},
        ),

        # ---------------------------------------------------------------
        # FeedbackModeration
        # ---------------------------------------------------------------
        migrations.CreateModel(
            name="FeedbackModeration",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("status", models.CharField(choices=[("PENDING","Pending"),("APPROVED","Approved"),("HIDDEN","Hidden"),("REJECTED","Rejected")], db_index=True, default="PENDING", max_length=20)),
                ("moderation_note", models.TextField(blank=True)),
                ("reviewed_at", models.DateTimeField(blank=True, null=True)),
                ("central_issue_id", models.UUIDField(blank=True, null=True)),
                ("feedback", models.ForeignKey(db_index=True, on_delete=django.db.models.deletion.PROTECT, related_name="moderation_records", to="crm.customerfeedback")),
                ("reviewed_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="feedback_moderations", to=settings.AUTH_USER_MODEL)),
            ],
            options={"verbose_name": "Feedback Moderation", "ordering": ["-created_at"]},
        ),

        # ---------------------------------------------------------------
        # CustomerConsent
        # ---------------------------------------------------------------
        migrations.CreateModel(
            name="CustomerConsent",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("consent_type", models.CharField(choices=[("MARKETING_EMAIL","Marketing Email"),("MARKETING_SMS","Marketing SMS"),("MARKETING_WHATSAPP","Marketing WhatsApp"),("MARKETING_TELEGRAM","Marketing Telegram"),("LOYALTY","Loyalty Programme"),("FEEDBACK_COMMUNICATION","Feedback Communication")], db_index=True, max_length=40)),
                ("status", models.CharField(choices=[("GRANTED","Granted"),("REVOKED","Revoked")], db_index=True, max_length=20)),
                ("source", models.CharField(choices=[("CUSTOMER","Customer"),("STAFF","Staff"),("ADMIN","Admin"),("IMPORT","Import"),("SYSTEM","System")], default="CUSTOMER", max_length=20)),
                ("granted_at", models.DateTimeField(blank=True, null=True)),
                ("revoked_at", models.DateTimeField(blank=True, null=True)),
                ("customer", models.ForeignKey(db_index=True, on_delete=django.db.models.deletion.CASCADE, related_name="consents", to="crm.customer")),
            ],
            options={"verbose_name": "Customer Consent"},
        ),
        migrations.AddConstraint(
            model_name="customerconsent",
            constraint=models.UniqueConstraint(fields=["customer", "consent_type"], name="unique_consent_per_customer_type"),
        ),

        # ---------------------------------------------------------------
        # CustomerConsentHistory
        # ---------------------------------------------------------------
        migrations.CreateModel(
            name="CustomerConsentHistory",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("consent_type", models.CharField(choices=[("MARKETING_EMAIL","Marketing Email"),("MARKETING_SMS","Marketing SMS"),("MARKETING_WHATSAPP","Marketing WhatsApp"),("MARKETING_TELEGRAM","Marketing Telegram"),("LOYALTY","Loyalty Programme"),("FEEDBACK_COMMUNICATION","Feedback Communication")], max_length=40)),
                ("previous_status", models.CharField(blank=True, max_length=20)),
                ("new_status", models.CharField(choices=[("GRANTED","Granted"),("REVOKED","Revoked")], max_length=20)),
                ("source", models.CharField(choices=[("CUSTOMER","Customer"),("STAFF","Staff"),("ADMIN","Admin"),("IMPORT","Import"),("SYSTEM","System")], max_length=20)),
                ("changed_at", models.DateTimeField(auto_now_add=True)),
                ("customer", models.ForeignKey(db_index=True, on_delete=django.db.models.deletion.CASCADE, related_name="consent_history", to="crm.customer")),
                ("changed_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="consent_changes_made", to=settings.AUTH_USER_MODEL)),
            ],
            options={"verbose_name": "Customer Consent History", "ordering": ["-changed_at"]},
        ),

        # ---------------------------------------------------------------
        # CustomerMergeRequest
        # ---------------------------------------------------------------
        migrations.CreateModel(
            name="CustomerMergeRequest",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("status", models.CharField(choices=[("REQUESTED","Requested"),("APPROVED","Approved"),("REJECTED","Rejected"),("CANCELLED","Cancelled")], db_index=True, default="REQUESTED", max_length=20)),
                ("reason", models.TextField()),
                ("notes", models.TextField(blank=True)),
                ("approved_at", models.DateTimeField(blank=True, null=True)),
                ("rejected_at", models.DateTimeField(blank=True, null=True)),
                ("source_customer", models.ForeignKey(db_index=True, on_delete=django.db.models.deletion.PROTECT, related_name="merge_requests_as_source", to="crm.customer")),
                ("target_customer", models.ForeignKey(db_index=True, on_delete=django.db.models.deletion.PROTECT, related_name="merge_requests_as_target", to="crm.customer")),
                ("requested_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="merge_requests_made", to=settings.AUTH_USER_MODEL)),
                ("approved_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="merge_requests_approved", to=settings.AUTH_USER_MODEL)),
            ],
            options={"verbose_name": "Customer Merge Request", "ordering": ["-created_at"]},
        ),

        # ---------------------------------------------------------------
        # CRMAuditLog
        # ---------------------------------------------------------------
        migrations.CreateModel(
            name="CRMAuditLog",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("action", models.CharField(choices=[
                    ("CUSTOMER_CREATED","Customer Created"),("CUSTOMER_UPDATED","Customer Updated"),
                    ("CUSTOMER_BLOCKED","Customer Blocked"),("CUSTOMER_UNBLOCKED","Customer Unblocked"),
                    ("CUSTOMER_LINKED_TO_ORDER","Customer Linked to Order"),
                    ("CUSTOMER_TAG_ASSIGNED","Customer Tag Assigned"),("CUSTOMER_TAG_REMOVED","Customer Tag Removed"),
                    ("CUSTOMER_SEGMENT_ASSIGNED","Customer Segment Assigned"),("CUSTOMER_SEGMENT_REMOVED","Customer Segment Removed"),
                    ("LOYALTY_ACCOUNT_CREATED","Loyalty Account Created"),
                    ("LOYALTY_POINTS_EARNED","Loyalty Points Earned"),("LOYALTY_POINTS_REDEEMED","Loyalty Points Redeemed"),
                    ("LOYALTY_POINTS_ADJUSTED","Loyalty Points Adjusted"),("LOYALTY_POINTS_REVERSED","Loyalty Points Reversed"),
                    ("LOYALTY_POINTS_EXPIRED","Loyalty Points Expired"),
                    ("REWARD_CREATED","Reward Created"),("REWARD_UPDATED","Reward Updated"),
                    ("REWARD_REDEEMED","Reward Redeemed"),("REWARD_CANCELLED","Reward Cancelled"),
                    ("FEEDBACK_CREATED","Feedback Created"),("FEEDBACK_UPDATED","Feedback Updated"),
                    ("FEEDBACK_MODERATED","Feedback Moderated"),("FEEDBACK_RESOLVED","Feedback Resolved"),
                    ("CUSTOMER_CONSENT_GRANTED","Consent Granted"),("CUSTOMER_CONSENT_REVOKED","Consent Revoked"),
                    ("CUSTOMER_MERGE_REQUESTED","Merge Requested"),("CUSTOMER_MERGE_APPROVED","Merge Approved"),
                    ("CUSTOMER_MERGE_REJECTED","Merge Rejected"),
                ], db_index=True, max_length=60)),
                ("entity_type", models.CharField(db_index=True, max_length=50)),
                ("entity_id", models.UUIDField(blank=True, db_index=True, null=True)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("actor", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="crm_audit_entries", to=settings.AUTH_USER_MODEL)),
                ("company", models.ForeignKey(blank=True, db_index=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="crm_audit_logs", to="organizations.organization")),
                ("restaurant", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="crm_audit_logs", to="organizations.restaurant")),
                ("branch", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="crm_audit_logs", to="organizations.branch")),
                ("customer", models.ForeignKey(blank=True, db_index=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="audit_logs", to="crm.customer")),
            ],
            options={"verbose_name": "CRM Audit Log", "ordering": ["-created_at"]},
        ),
    ]
