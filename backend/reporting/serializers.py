# =============================================================================
# RestaurantFlow — Reporting Serializers
# Phase 14
#
# Serializers wrap pre-computed dicts/lists from services into
# consistent JSON responses. No business logic here.
# =============================================================================

from rest_framework import serializers


# ---------------------------------------------------------------------------
# Period / Filters metadata
# ---------------------------------------------------------------------------

class PeriodSerializer(serializers.Serializer):
    date_from = serializers.DateField()
    date_to = serializers.DateField()


# ---------------------------------------------------------------------------
# Sales
# ---------------------------------------------------------------------------

class SalesSummarySerializer(serializers.Serializer):
    gross_sales = serializers.DecimalField(max_digits=16, decimal_places=2, allow_null=True)
    discount_amount = serializers.DecimalField(max_digits=16, decimal_places=2, allow_null=True)
    taxable_amount = serializers.DecimalField(max_digits=16, decimal_places=2, allow_null=True)
    tax_amount = serializers.DecimalField(max_digits=16, decimal_places=2, allow_null=True)
    rounding_amount = serializers.DecimalField(max_digits=16, decimal_places=2, allow_null=True)
    net_sales = serializers.DecimalField(max_digits=16, decimal_places=2, allow_null=True)
    number_of_bills = serializers.IntegerField(allow_null=True)
    average_bill_value = serializers.DecimalField(max_digits=16, decimal_places=2, allow_null=True)


class SalesTrendItemSerializer(serializers.Serializer):
    date = serializers.DateField(allow_null=True)
    gross_sales = serializers.DecimalField(max_digits=16, decimal_places=2)
    discounts = serializers.DecimalField(max_digits=16, decimal_places=2)
    tax = serializers.DecimalField(max_digits=16, decimal_places=2)
    net_sales = serializers.DecimalField(max_digits=16, decimal_places=2)
    bill_count = serializers.IntegerField()
    order_count = serializers.IntegerField()
    average_bill_value = serializers.DecimalField(max_digits=16, decimal_places=2, allow_null=True)


class HourlySalesItemSerializer(serializers.Serializer):
    hour = serializers.IntegerField()
    sales = serializers.DecimalField(max_digits=16, decimal_places=2)
    bill_count = serializers.IntegerField()
    order_count = serializers.IntegerField()


# ---------------------------------------------------------------------------
# Orders
# ---------------------------------------------------------------------------

class OrdersSummarySerializer(serializers.Serializer):
    total_orders = serializers.IntegerField()
    confirmed_orders = serializers.IntegerField()
    cancelled_orders = serializers.IntegerField()
    dine_in_orders = serializers.IntegerField()
    takeaway_orders = serializers.IntegerField()
    counter_orders = serializers.IntegerField()
    average_order_value = serializers.DecimalField(max_digits=16, decimal_places=2, allow_null=True)


class OrdersByTypeItemSerializer(serializers.Serializer):
    order_type = serializers.CharField()
    order_count = serializers.IntegerField()
    sales = serializers.DecimalField(max_digits=16, decimal_places=2)
    percentage_of_orders = serializers.DecimalField(max_digits=6, decimal_places=2)


# ---------------------------------------------------------------------------
# Menu
# ---------------------------------------------------------------------------

class MenuItemReportSerializer(serializers.Serializer):
    menu_item_id = serializers.CharField()
    menu_item_name = serializers.CharField()
    category = serializers.CharField(allow_null=True)
    quantity_sold = serializers.DecimalField(max_digits=14, decimal_places=3)
    gross_revenue = serializers.DecimalField(max_digits=16, decimal_places=2)
    discount_amount = serializers.DecimalField(max_digits=16, decimal_places=2)
    net_revenue = serializers.DecimalField(max_digits=16, decimal_places=2)
    average_selling_price = serializers.DecimalField(max_digits=14, decimal_places=2, allow_null=True)
    number_of_orders = serializers.IntegerField()
    percentage_of_sales = serializers.DecimalField(max_digits=8, decimal_places=2)


class TopSellingItemSerializer(serializers.Serializer):
    rank = serializers.IntegerField()
    menu_item_id = serializers.CharField()
    menu_item_name = serializers.CharField()
    category = serializers.CharField(allow_null=True)
    quantity_sold = serializers.DecimalField(max_digits=14, decimal_places=3)
    net_revenue = serializers.DecimalField(max_digits=16, decimal_places=2)
    number_of_orders = serializers.IntegerField()


class CategoryPerformanceSerializer(serializers.Serializer):
    category_id = serializers.CharField(allow_null=True)
    category = serializers.CharField()
    quantity_sold = serializers.DecimalField(max_digits=14, decimal_places=3)
    gross_revenue = serializers.DecimalField(max_digits=16, decimal_places=2)
    net_revenue = serializers.DecimalField(max_digits=16, decimal_places=2)
    sales_percentage = serializers.DecimalField(max_digits=8, decimal_places=2)
    average_item_value = serializers.DecimalField(max_digits=14, decimal_places=2, allow_null=True)


class MenuProfitabilitySerializer(serializers.Serializer):
    menu_item_id = serializers.CharField()
    menu_item_name = serializers.CharField()
    quantity_sold = serializers.DecimalField(max_digits=14, decimal_places=3)
    revenue = serializers.DecimalField(max_digits=16, decimal_places=2)
    ingredient_cost = serializers.DecimalField(max_digits=16, decimal_places=2, allow_null=True)
    gross_profit = serializers.DecimalField(max_digits=16, decimal_places=2, allow_null=True)
    gross_margin_percentage = serializers.DecimalField(max_digits=8, decimal_places=2, allow_null=True)


# ---------------------------------------------------------------------------
# Branch / Counter
# ---------------------------------------------------------------------------

class BranchPerformanceSerializer(serializers.Serializer):
    branch_id = serializers.CharField()
    branch_name = serializers.CharField()
    orders = serializers.IntegerField()
    bills = serializers.IntegerField()
    revenue = serializers.DecimalField(max_digits=16, decimal_places=2)
    payments = serializers.DecimalField(max_digits=16, decimal_places=2)
    refunds = serializers.DecimalField(max_digits=16, decimal_places=2)
    discounts = serializers.DecimalField(max_digits=16, decimal_places=2)
    taxes = serializers.DecimalField(max_digits=16, decimal_places=2)
    average_bill_value = serializers.DecimalField(max_digits=14, decimal_places=2, allow_null=True)
    average_order_value = serializers.DecimalField(max_digits=14, decimal_places=2, allow_null=True)
    ingredient_cost = serializers.DecimalField(max_digits=16, decimal_places=2, allow_null=True)
    gross_profit = serializers.DecimalField(max_digits=16, decimal_places=2, allow_null=True)
    gross_margin = serializers.DecimalField(max_digits=8, decimal_places=2, allow_null=True)


class CounterPerformanceSerializer(serializers.Serializer):
    counter_id = serializers.CharField()
    counter_name = serializers.CharField()
    orders = serializers.IntegerField()
    bills = serializers.IntegerField()
    sales = serializers.DecimalField(max_digits=16, decimal_places=2)
    payments = serializers.DecimalField(max_digits=16, decimal_places=2)
    cash_sales = serializers.DecimalField(max_digits=16, decimal_places=2)
    upi_sales = serializers.DecimalField(max_digits=16, decimal_places=2)
    card_sales = serializers.DecimalField(max_digits=16, decimal_places=2)
    refunds = serializers.DecimalField(max_digits=16, decimal_places=2)
    average_bill_value = serializers.DecimalField(max_digits=14, decimal_places=2, allow_null=True)


# ---------------------------------------------------------------------------
# Payments / Refunds / Discounts
# ---------------------------------------------------------------------------

class PaymentSummarySerializer(serializers.Serializer):
    total_paid = serializers.DecimalField(max_digits=16, decimal_places=2)
    cash = serializers.DecimalField(max_digits=16, decimal_places=2)
    upi = serializers.DecimalField(max_digits=16, decimal_places=2)
    card = serializers.DecimalField(max_digits=16, decimal_places=2)
    other = serializers.DecimalField(max_digits=16, decimal_places=2)
    payment_count = serializers.IntegerField()
    refund_amount = serializers.DecimalField(max_digits=16, decimal_places=2)
    refund_count = serializers.IntegerField()


class PaymentMethodSerializer(serializers.Serializer):
    payment_method = serializers.CharField()
    total = serializers.DecimalField(max_digits=16, decimal_places=2)
    count = serializers.IntegerField()
    percentage = serializers.DecimalField(max_digits=8, decimal_places=2)


# ---------------------------------------------------------------------------
# Kitchen
# ---------------------------------------------------------------------------

class KitchenPerformanceSerializer(serializers.Serializer):
    orders_received = serializers.IntegerField()
    orders_ready = serializers.IntegerField()
    orders_cancelled = serializers.IntegerField()
    orders_pending = serializers.IntegerField()
    average_preparation_time_seconds = serializers.FloatField(allow_null=True)
    median_preparation_time_seconds = serializers.FloatField(allow_null=True)
    maximum_preparation_time_seconds = serializers.FloatField(allow_null=True)


class KitchenItemSerializer(serializers.Serializer):
    menu_item_id = serializers.CharField()
    menu_item_name = serializers.CharField()
    quantity_prepared = serializers.DecimalField(max_digits=14, decimal_places=3)
    average_preparation_time_seconds = serializers.FloatField(allow_null=True)
    max_preparation_time_seconds = serializers.FloatField(allow_null=True)
    ready_count = serializers.IntegerField()
    cancelled_count = serializers.IntegerField()


# ---------------------------------------------------------------------------
# Staff
# ---------------------------------------------------------------------------

class WaiterPerformanceSerializer(serializers.Serializer):
    waiter_id = serializers.CharField()
    waiter_name = serializers.CharField()
    order_count = serializers.IntegerField()
    sales = serializers.DecimalField(max_digits=16, decimal_places=2)
    average_order_value = serializers.DecimalField(max_digits=14, decimal_places=2, allow_null=True)
    cancellation_count = serializers.IntegerField()


class CashierPerformanceSerializer(serializers.Serializer):
    cashier_id = serializers.CharField()
    cashier_name = serializers.CharField()
    payment_count = serializers.IntegerField()
    collected_amount = serializers.DecimalField(max_digits=16, decimal_places=2)
    cash_collected = serializers.DecimalField(max_digits=16, decimal_places=2)
    upi_collected = serializers.DecimalField(max_digits=16, decimal_places=2)
    card_collected = serializers.DecimalField(max_digits=16, decimal_places=2)
    refund_count = serializers.IntegerField()


# ---------------------------------------------------------------------------
# Inventory
# ---------------------------------------------------------------------------

class InventorySummarySerializer(serializers.Serializer):
    total_inventory_items = serializers.IntegerField()
    low_stock_items = serializers.IntegerField()
    out_of_stock_items = serializers.IntegerField()
    stock_value_estimate = serializers.DecimalField(max_digits=18, decimal_places=2)


class InventoryConsumptionSerializer(serializers.Serializer):
    inventory_item_id = serializers.CharField()
    inventory_item = serializers.CharField()
    unit = serializers.CharField()
    quantity_consumed = serializers.DecimalField(max_digits=14, decimal_places=3)
    consumption_cost = serializers.DecimalField(max_digits=16, decimal_places=2)


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

class DashboardKPISerializer(serializers.Serializer):
    period = serializers.DictField()
    sales = serializers.DictField()
    orders = serializers.DictField()
    products = serializers.DictField()
    payments = serializers.DictField()
    kitchen = serializers.DictField()
    inventory = serializers.DictField()
    financials = serializers.DictField()
