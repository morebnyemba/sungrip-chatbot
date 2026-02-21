"""
Serializers for the orders app
"""
from rest_framework import serializers
from .models import (
    Order, OrderItem, Installation, InstallationRequest,
    ProductOrder, SupportRequest, QuoteRequest, PaymentPlan
)
from customers.serializers import CustomerSerializer


class PaymentPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentPlan
        fields = [
            'id', 'name', 'payment_term', 'description',
            'number_of_installments', 'installment_interval_days',
            'deposit_percent', 'interest_rate_percent', 'administration_fee',
            'is_active', 'display_order', 'created_at', 'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']


class OrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)

    class Meta:
        model = OrderItem
        fields = ['id', 'product', 'product_name', 'quantity', 'unit_price', 'discount_percent', 'total_price']


class OrderSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source='customer.full_name', read_only=True)
    customer_phone = serializers.CharField(source='customer.phone_number', read_only=True)
    customer_whatsapp = serializers.CharField(source='customer.whatsapp_number', read_only=True)
    items = OrderItemSerializer(many=True, read_only=True)
    balance_due = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    payment_plan_name = serializers.CharField(source='payment_plan.name', read_only=True, allow_null=True)

    class Meta:
        model = Order
        fields = [
            'id', 'order_number', 'customer', 'customer_name', 'customer_phone',
            'customer_whatsapp', 'quote', 'payment_plan', 'payment_plan_name',
            'subtotal', 'installation_cost', 'tax_amount', 'total_amount',
            'paid_amount', 'balance_due', 'currency', 'status', 'payment_status',
            'order_date', 'expected_delivery_date', 'completed_date',
            'customer_notes', 'internal_notes', 'items',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['order_number', 'order_date', 'created_at', 'updated_at']


class InstallationSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source='customer.full_name', read_only=True)
    customer_phone = serializers.CharField(source='customer.phone_number', read_only=True)
    customer_whatsapp = serializers.CharField(source='customer.whatsapp_number', read_only=True)
    lead_technician_name = serializers.CharField(source='lead_technician.username', read_only=True, allow_null=True)

    class Meta:
        model = Installation
        fields = [
            'id', 'order', 'customer', 'customer_name', 'customer_phone',
            'customer_whatsapp', 'installation_address', 'gps_latitude', 'gps_longitude',
            'system_size_kw', 'number_of_panels', 'inverter_model', 'battery_capacity_kwh',
            'scheduled_date', 'estimated_duration_days', 'actual_start_date',
            'actual_completion_date', 'lead_technician', 'lead_technician_name',
            'status', 'notes', 'completion_notes', 'created_at', 'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']


class InstallationRequestSerializer(serializers.ModelSerializer):
    customer_name_display = serializers.SerializerMethodField()
    contact_phone = serializers.SerializerMethodField()
    contact_whatsapp_id = serializers.SerializerMethodField()

    class Meta:
        model = InstallationRequest
        fields = [
            'id', 'request_id', 'customer', 'contact',
            'customer_name', 'customer_name_display', 'contact_phone', 'contact_whatsapp_id',
            'system_size', 'payment_preference', 'preferred_date', 'time_preference',
            'installation_address', 'location_pin', 'additional_notes',
            'status', 'notes', 'created_at', 'updated_at',
        ]
        read_only_fields = ['request_id', 'created_at', 'updated_at']

    def get_customer_name_display(self, obj):
        if obj.customer:
            return obj.customer.full_name
        return obj.customer_name or 'Unknown'

    def get_contact_phone(self, obj):
        if obj.contact:
            return obj.contact.phone_number
        return ''

    def get_contact_whatsapp_id(self, obj):
        if obj.contact:
            return obj.contact.whatsapp_id
        return ''


class ProductOrderSerializer(serializers.ModelSerializer):
    customer_name_display = serializers.SerializerMethodField()
    contact_whatsapp_id = serializers.SerializerMethodField()

    class Meta:
        model = ProductOrder
        fields = [
            'id', 'order_number', 'customer', 'contact',
            'customer_name', 'customer_name_display', 'customer_phone',
            'contact_whatsapp_id', 'product', 'product_name', 'product_sku',
            'quantity', 'unit_price', 'total_price', 'currency',
            'delivery_method', 'delivery_address', 'status',
            'full_order', 'customer_notes', 'internal_notes',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['order_number', 'created_at', 'updated_at']

    def get_customer_name_display(self, obj):
        if obj.customer:
            return obj.customer.full_name
        return obj.customer_name or 'Unknown'

    def get_contact_whatsapp_id(self, obj):
        if obj.contact:
            return obj.contact.whatsapp_id
        return ''


class SupportRequestSerializer(serializers.ModelSerializer):
    customer_name_display = serializers.SerializerMethodField()
    contact_whatsapp_id = serializers.SerializerMethodField()

    class Meta:
        model = SupportRequest
        fields = [
            'id', 'request_id', 'customer', 'contact',
            'customer_name', 'customer_name_display', 'contact_whatsapp_id',
            'support_category', 'issue_details', 'contact_method',
            'status', 'notes', 'created_at', 'updated_at',
        ]
        read_only_fields = ['request_id', 'created_at', 'updated_at']

    def get_customer_name_display(self, obj):
        if obj.customer:
            return obj.customer.full_name
        return obj.customer_name or 'Unknown'

    def get_contact_whatsapp_id(self, obj):
        if obj.contact:
            return obj.contact.whatsapp_id
        return ''


class QuoteRequestSerializer(serializers.ModelSerializer):
    customer_name_display = serializers.SerializerMethodField()
    contact_whatsapp_id = serializers.SerializerMethodField()

    class Meta:
        model = QuoteRequest
        fields = [
            'id', 'request_id', 'customer', 'contact',
            'customer_name', 'customer_name_display', 'contact_whatsapp_id',
            'monthly_bill', 'roof_type', 'location',
            'status', 'quote', 'notes', 'created_at', 'updated_at',
        ]
        read_only_fields = ['request_id', 'created_at', 'updated_at']

    def get_customer_name_display(self, obj):
        if obj.customer:
            return obj.customer.full_name
        return obj.customer_name or 'Unknown'

    def get_contact_whatsapp_id(self, obj):
        if obj.contact:
            return obj.contact.whatsapp_id
        return ''
