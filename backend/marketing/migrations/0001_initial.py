# =============================================================================
# RestaurantFlow — Marketing Initial Migration
# Phase 18
#
# Generated manually (no Python runtime available in build environment).
# Apply with: python manage.py migrate marketing
# =============================================================================

import uuid
import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("organizations", "0001_initial"),
        ("crm", "0001_initial"),
        ("orders", "0001_initial"),
        ("billing", "0001_initial"),
        ("menu", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # -----------------------------------------------------------------------
        # MarketingCampaign
        # -----------------------------------------------------------------------
        migrations.CreateModel(
            name="MarketingCampaign",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=200)),
                ("code", models.CharField(db_index=True, max_length=50)),
                ("description", models.TextField(blank=True)),
                ("campaign_type", models.CharField(
                    choices=[
                        ("PROMOTION", "Promotion"), ("LOYALTY", "Loyalty"),
                        ("REACTIVATION", "Reactivation"), ("NEW_CUSTOMER", "New Customer"),
                        ("REPEAT_CUSTOMER", "Repeat Customer"), ("BIRTHDAY", "Birthday"),
                        ("SEASONAL", "Seasonal"), ("EVENT", "Event"),
                        ("FEEDBACK", "Feedback"), ("ANNOUNCEMENT", "Announcement"),
                        ("OTHER", "Other"),
                    ],
                    db_index=True, max_length=30,
                )),
                ("status", models.CharField(
                    choices=[
                        ("DRAFT", "Draft"), ("PENDING_APPROVAL", "Pending Approval"),
                        ("APPROVED", "Approved"), ("SCHEDULED", "Scheduled"),
                        ("RUNNING", "Running"), ("PAUSED", "Paused"),
                        ("COMPLETED", "Completed"), ("CANCELLED", "Cancelled"),
                        ("FAILED", "Failed"),
                    ],
                    db_index=True, default="DRAFT", max_length=30,
                )),
                ("start_at", models.DateTimeField(blank=True, db_index=True, null=True)),
                ("end_at", models.DateTimeField(blank=True, db_index=True, null=True)),
                ("audience_type", models.CharField(blank=True, max_length=30)),
                ("approved_at", models.DateTimeField(blank=True, null=True)),
                ("cancelled_at", models.DateTimeField(blank=True, null=True)),
                ("cancellation_reason", models.TextField(blank=True)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("company", models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="marketing_campaigns",
                    to="organizations.organization",
                )),
                ("restaurant", models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="marketing_campaigns",
                    to="organizations.restaurant",
                )),
                ("branch", models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="marketing_campaigns",
                    to="organizations.branch",
                )),
                ("created_by", models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="marketing_campaigns_created",
                    to=settings.AUTH_USER_MODEL,
                )),
                ("approved_by", models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="marketing_campaigns_approved",
                    to=settings.AUTH_USER_MODEL,
                )),
                ("cancelled_by", models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="marketing_campaigns_cancelled",
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={"ordering": ["-created_at"], "verbose_name": "Marketing Campaign"},
        ),
        migrations.AddIndex(
            model_name="marketingcampaign",
            index=models.Index(fields=["company", "status"], name="mktg_campaign_company_status"),
        ),
        migrations.AddIndex(
            model_name="marketingcampaign",
            index=models.Index(fields=["restaurant", "status"], name="mktg_campaign_rest_status"),
        ),
        migrations.AddIndex(
            model_name="marketingcampaign",
            index=models.Index(fields=["status", "start_at"], name="mktg_campaign_status_start"),
        ),
        migrations.AddIndex(
            model_name="marketingcampaign",
            index=models.Index(fields=["status", "end_at"], name="mktg_campaign_status_end"),
        ),
        migrations.AddConstraint(
            model_name="marketingcampaign",
            constraint=models.UniqueConstraint(
                condition=models.Q(restaurant__isnull=False),
                fields=["company", "restaurant", "code"],
                name="unique_campaign_code_per_restaurant",
            ),
        ),
        migrations.AddConstraint(
            model_name="marketingcampaign",
            constraint=models.UniqueConstraint(
                condition=models.Q(restaurant__isnull=True),
                fields=["company", "code"],
                name="unique_campaign_code_per_company",
            ),
        ),

        # -----------------------------------------------------------------------
        # CampaignApproval
        # -----------------------------------------------------------------------
        migrations.CreateModel(
            name="CampaignApproval",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("status", models.CharField(
                    choices=[
                        ("PENDING", "Pending"), ("APPROVED", "Approved"),
                        ("REJECTED", "Rejected"), ("CANCELLED", "Cancelled"),
                    ],
                    db_index=True, default="PENDING", max_length=20,
                )),
                ("review_note", models.TextField(blank=True)),
                ("requested_at", models.DateTimeField(auto_now_add=True)),
                ("reviewed_at", models.DateTimeField(blank=True, null=True)),
                ("campaign", models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="approvals",
                    to="marketing.marketingcampaign",
                )),
                ("requested_by", models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="campaign_approvals_requested",
                    to=settings.AUTH_USER_MODEL,
                )),
                ("reviewed_by", models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="campaign_approvals_reviewed",
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={"ordering": ["-requested_at"], "verbose_name": "Campaign Approval"},
        ),
        migrations.AddIndex(
            model_name="campaignapproval",
            index=models.Index(fields=["campaign", "status"], name="mktg_approval_campaign_status"),
        ),

        # -----------------------------------------------------------------------
        # CampaignAudience
        # -----------------------------------------------------------------------
        migrations.CreateModel(
            name="CampaignAudience",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("audience_type", models.CharField(db_index=True, max_length=30)),
                ("criteria", models.JSONField(blank=True, default=dict)),
                ("estimated_count", models.PositiveIntegerField(default=0)),
                ("campaign", models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="audiences",
                    to="marketing.marketingcampaign",
                )),
            ],
            options={"ordering": ["-created_at"], "verbose_name": "Campaign Audience"},
        ),

        # -----------------------------------------------------------------------
        # CampaignAudienceMember
        # -----------------------------------------------------------------------
        migrations.CreateModel(
            name="CampaignAudienceMember",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("status", models.CharField(
                    choices=[
                        ("ELIGIBLE", "Eligible"), ("EXCLUDED", "Excluded"),
                        ("CONTACTED", "Contacted"), ("CONVERTED", "Converted"),
                        ("UNSUBSCRIBED", "Unsubscribed"),
                    ],
                    db_index=True, default="ELIGIBLE", max_length=20,
                )),
                ("added_at", models.DateTimeField(auto_now_add=True)),
                ("removed_at", models.DateTimeField(blank=True, null=True)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("campaign", models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="audience_members",
                    to="marketing.marketingcampaign",
                )),
                ("customer", models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="campaign_memberships",
                    to="crm.customer",
                )),
            ],
            options={"ordering": ["-added_at"], "verbose_name": "Campaign Audience Member"},
        ),
        migrations.AddIndex(
            model_name="campaignaudiencemember",
            index=models.Index(fields=["campaign", "status"], name="mktg_member_campaign_status"),
        ),
        migrations.AddIndex(
            model_name="campaignaudiencemember",
            index=models.Index(fields=["campaign", "customer"], name="mktg_member_campaign_cust"),
        ),
        migrations.AddConstraint(
            model_name="campaignaudiencemember",
            constraint=models.UniqueConstraint(
                fields=["campaign", "customer"],
                name="unique_campaign_audience_member",
            ),
        ),

        # -----------------------------------------------------------------------
        # Promotion
        # -----------------------------------------------------------------------
        migrations.CreateModel(
            name="Promotion",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=200)),
                ("code", models.CharField(blank=True, db_index=True, max_length=50)),
                ("description", models.TextField(blank=True)),
                ("promotion_type", models.CharField(db_index=True, max_length=30)),
                ("discount_type", models.CharField(blank=True, max_length=20, null=True)),
                ("discount_value", models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ("max_discount_amount", models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ("minimum_order_amount", models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ("minimum_quantity", models.PositiveIntegerField(blank=True, null=True)),
                ("buy_quantity", models.PositiveIntegerField(blank=True, null=True)),
                ("get_quantity", models.PositiveIntegerField(blank=True, null=True)),
                ("loyalty_bonus_multiplier", models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True)),
                ("start_at", models.DateTimeField(blank=True, db_index=True, null=True)),
                ("end_at", models.DateTimeField(blank=True, db_index=True, null=True)),
                ("usage_limit", models.PositiveIntegerField(blank=True, null=True)),
                ("usage_limit_per_customer", models.PositiveIntegerField(blank=True, null=True)),
                ("current_usage_count", models.PositiveIntegerField(default=0)),
                ("is_active", models.BooleanField(db_index=True, default=False)),
                ("company", models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="promotions",
                    to="organizations.organization",
                )),
                ("restaurant", models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="promotions",
                    to="organizations.restaurant",
                )),
                ("branch", models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="promotions",
                    to="organizations.branch",
                )),
                ("free_item", models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="free_item_promotions",
                    to="menu.menuitem",
                )),
                ("created_by", models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="promotions_created",
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={"ordering": ["-created_at"], "verbose_name": "Promotion"},
        ),
        migrations.AddIndex(
            model_name="promotion",
            index=models.Index(fields=["restaurant", "is_active"], name="mktg_promo_rest_active"),
        ),
        migrations.AddIndex(
            model_name="promotion",
            index=models.Index(fields=["restaurant", "code"], name="mktg_promo_rest_code"),
        ),
        migrations.AddIndex(
            model_name="promotion",
            index=models.Index(fields=["is_active", "start_at", "end_at"], name="mktg_promo_active_dates"),
        ),

        # -----------------------------------------------------------------------
        # PromotionRule
        # -----------------------------------------------------------------------
        migrations.CreateModel(
            name="PromotionRule",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("rule_type", models.CharField(db_index=True, max_length=30)),
                ("configuration", models.JSONField(default=dict)),
                ("priority", models.PositiveSmallIntegerField(default=10)),
                ("is_active", models.BooleanField(db_index=True, default=True)),
                ("promotion", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="rules",
                    to="marketing.promotion",
                )),
            ],
            options={"ordering": ["priority", "created_at"], "verbose_name": "Promotion Rule"},
        ),

        # -----------------------------------------------------------------------
        # PromotionUsage
        # -----------------------------------------------------------------------
        migrations.CreateModel(
            name="PromotionUsage",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("discount_amount", models.DecimalField(decimal_places=2, default="0.00", max_digits=12)),
                ("used_at", models.DateTimeField(blank=True, null=True)),
                ("status", models.CharField(
                    choices=[
                        ("RESERVED", "Reserved"), ("APPLIED", "Applied"),
                        ("REVERSED", "Reversed"), ("CANCELLED", "Cancelled"),
                    ],
                    db_index=True, default="RESERVED", max_length=20,
                )),
                ("promotion", models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="usages",
                    to="marketing.promotion",
                )),
                ("customer", models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="promotion_usages",
                    to="crm.customer",
                )),
                ("order", models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="promotion_usages",
                    to="orders.order",
                )),
                ("bill", models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="promotion_usages",
                    to="billing.bill",
                )),
            ],
            options={"ordering": ["-created_at"], "verbose_name": "Promotion Usage"},
        ),
        migrations.AddIndex(
            model_name="promotionusage",
            index=models.Index(fields=["promotion", "customer"], name="mktg_usage_promo_cust"),
        ),
        migrations.AddIndex(
            model_name="promotionusage",
            index=models.Index(fields=["promotion", "status"], name="mktg_usage_promo_status"),
        ),

        # -----------------------------------------------------------------------
        # CampaignChannel
        # -----------------------------------------------------------------------
        migrations.CreateModel(
            name="CampaignChannel",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("channel", models.CharField(db_index=True, max_length=20)),
                ("enabled", models.BooleanField(default=True)),
                ("template_id", models.CharField(blank=True, max_length=100)),
                ("scheduled_at", models.DateTimeField(blank=True, null=True)),
                ("campaign", models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="channels",
                    to="marketing.marketingcampaign",
                )),
            ],
            options={"ordering": ["channel"], "verbose_name": "Campaign Channel"},
        ),
        migrations.AddConstraint(
            model_name="campaignchannel",
            constraint=models.UniqueConstraint(
                fields=["campaign", "channel"],
                name="unique_channel_per_campaign",
            ),
        ),

        # -----------------------------------------------------------------------
        # CampaignMessage
        # -----------------------------------------------------------------------
        migrations.CreateModel(
            name="CampaignMessage",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("channel", models.CharField(db_index=True, max_length=20)),
                ("subject", models.CharField(blank=True, max_length=200)),
                ("body", models.TextField()),
                ("template_data", models.JSONField(blank=True, default=dict)),
                ("campaign", models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="messages",
                    to="marketing.marketingcampaign",
                )),
            ],
            options={"ordering": ["channel"], "verbose_name": "Campaign Message"},
        ),
        migrations.AddConstraint(
            model_name="campaignmessage",
            constraint=models.UniqueConstraint(
                fields=["campaign", "channel"],
                name="unique_message_per_campaign_channel",
            ),
        ),

        # -----------------------------------------------------------------------
        # CampaignDelivery
        # -----------------------------------------------------------------------
        migrations.CreateModel(
            name="CampaignDelivery",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("channel", models.CharField(db_index=True, max_length=20)),
                ("notification_id", models.UUIDField(blank=True, db_index=True, null=True)),
                ("status", models.CharField(db_index=True, default="PENDING", max_length=20)),
                ("sent_at", models.DateTimeField(blank=True, null=True)),
                ("delivered_at", models.DateTimeField(blank=True, null=True)),
                ("failed_at", models.DateTimeField(blank=True, null=True)),
                ("failure_reason", models.TextField(blank=True)),
                ("campaign", models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="deliveries",
                    to="marketing.marketingcampaign",
                )),
                ("customer", models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="campaign_deliveries",
                    to="crm.customer",
                )),
            ],
            options={"ordering": ["-created_at"], "verbose_name": "Campaign Delivery"},
        ),
        migrations.AddIndex(
            model_name="campaigndelivery",
            index=models.Index(fields=["campaign", "status"], name="mktg_delivery_campaign_status"),
        ),
        migrations.AddIndex(
            model_name="campaigndelivery",
            index=models.Index(fields=["campaign", "customer", "channel"], name="mktg_delivery_idempotency"),
        ),

        # -----------------------------------------------------------------------
        # CampaignConversion
        # -----------------------------------------------------------------------
        migrations.CreateModel(
            name="CampaignConversion",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("conversion_type", models.CharField(db_index=True, max_length=30)),
                ("conversion_value", models.DecimalField(decimal_places=2, default="0.00", max_digits=12)),
                ("converted_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("campaign", models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="conversions",
                    to="marketing.marketingcampaign",
                )),
                ("customer", models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="campaign_conversions",
                    to="crm.customer",
                )),
                ("order", models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="campaign_conversions",
                    to="orders.order",
                )),
                ("promotion", models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="conversions",
                    to="marketing.promotion",
                )),
            ],
            options={"ordering": ["-converted_at"], "verbose_name": "Campaign Conversion"},
        ),
        migrations.AddConstraint(
            model_name="campaignconversion",
            constraint=models.UniqueConstraint(
                condition=models.Q(order__isnull=False),
                fields=["campaign", "customer", "order", "conversion_type"],
                name="unique_campaign_conversion_with_order",
            ),
        ),
        migrations.AddIndex(
            model_name="campaignconversion",
            index=models.Index(fields=["campaign", "converted_at"], name="mktg_conversion_campaign_date"),
        ),

        # -----------------------------------------------------------------------
        # CampaignEvent
        # -----------------------------------------------------------------------
        migrations.CreateModel(
            name="CampaignEvent",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("event_type", models.CharField(db_index=True, max_length=40)),
                ("source_type", models.CharField(blank=True, max_length=50)),
                ("source_id", models.CharField(blank=True, max_length=100)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("campaign", models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="events",
                    to="marketing.marketingcampaign",
                )),
                ("customer", models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="campaign_events",
                    to="crm.customer",
                )),
            ],
            options={"ordering": ["-created_at"], "verbose_name": "Campaign Event"},
        ),
        migrations.AddIndex(
            model_name="campaignevent",
            index=models.Index(fields=["campaign", "event_type"], name="mktg_event_campaign_type"),
        ),
        migrations.AddIndex(
            model_name="campaignevent",
            index=models.Index(fields=["campaign", "created_at"], name="mktg_event_campaign_date"),
        ),

        # -----------------------------------------------------------------------
        # MarketingSettings
        # -----------------------------------------------------------------------
        migrations.CreateModel(
            name="MarketingSettings",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("default_currency", models.CharField(blank=True, default="INR", max_length=10)),
                ("max_discount_without_approval", models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ("default_campaign_timezone", models.CharField(blank=True, default="Asia/Kolkata", max_length=100)),
                ("frequency_limit_enabled", models.BooleanField(default=True)),
                ("default_daily_contact_limit", models.PositiveSmallIntegerField(default=3)),
                ("default_weekly_contact_limit", models.PositiveSmallIntegerField(default=10)),
                ("restaurant", models.OneToOneField(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="marketing_settings",
                    to="organizations.restaurant",
                )),
            ],
            options={"verbose_name": "Marketing Settings"},
        ),

        # -----------------------------------------------------------------------
        # MarketingContactPolicy
        # -----------------------------------------------------------------------
        migrations.CreateModel(
            name="MarketingContactPolicy",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("channel", models.CharField(db_index=True, max_length=20)),
                ("max_messages_per_day", models.PositiveSmallIntegerField(default=3)),
                ("max_messages_per_week", models.PositiveSmallIntegerField(default=10)),
                ("cooldown_hours", models.PositiveSmallIntegerField(default=0)),
                ("is_active", models.BooleanField(default=True)),
                ("restaurant", models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="marketing_contact_policies",
                    to="organizations.restaurant",
                )),
            ],
            options={"verbose_name": "Marketing Contact Policy"},
        ),
        migrations.AddConstraint(
            model_name="marketingcontactpolicy",
            constraint=models.UniqueConstraint(
                fields=["restaurant", "channel"],
                name="unique_contact_policy_per_channel",
            ),
        ),

        # -----------------------------------------------------------------------
        # MarketingAuditLog
        # -----------------------------------------------------------------------
        migrations.CreateModel(
            name="MarketingAuditLog",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("action", models.CharField(db_index=True, max_length=60)),
                ("entity_type", models.CharField(db_index=True, max_length=50)),
                ("entity_id", models.CharField(db_index=True, max_length=100)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("actor", models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="marketing_audit_logs",
                    to=settings.AUTH_USER_MODEL,
                )),
                ("company", models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="marketing_audit_logs",
                    to="organizations.organization",
                )),
                ("restaurant", models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="marketing_audit_logs",
                    to="organizations.restaurant",
                )),
            ],
            options={"ordering": ["-created_at"], "verbose_name": "Marketing Audit Log"},
        ),
        migrations.AddIndex(
            model_name="marketingauditlog",
            index=models.Index(fields=["action", "created_at"], name="mktg_audit_action_date"),
        ),
        migrations.AddIndex(
            model_name="marketingauditlog",
            index=models.Index(fields=["entity_type", "entity_id"], name="mktg_audit_entity"),
        ),
        migrations.AddIndex(
            model_name="marketingauditlog",
            index=models.Index(fields=["company", "created_at"], name="mktg_audit_company_date"),
        ),
    ]
