"""
API views for the orders app
"""
from rest_framework import viewsets, filters
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend

from .models import (
    Order, Installation, InstallationRequest,
    ProductOrder, SupportRequest, QuoteRequest, PaymentPlan,
)
from .serializers import (
    OrderSerializer, InstallationSerializer, InstallationRequestSerializer,
    ProductOrderSerializer, SupportRequestSerializer, QuoteRequestSerializer,
    PaymentPlanSerializer,
)


class PaymentPlanViewSet(viewsets.ModelViewSet):
    queryset = PaymentPlan.objects.all()
    serializer_class = PaymentPlanSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_active', 'payment_term']
    search_fields = ['name', 'description']
    ordering_fields = ['display_order', 'name', 'created_at']
    ordering = ['display_order']


class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.select_related('customer', 'payment_plan').all()
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'payment_status', 'customer']
    search_fields = ['order_number', 'customer__full_name', 'customer__phone_number']
    ordering_fields = ['created_at', 'order_date', 'total_amount']
    ordering = ['-created_at']


class InstallationViewSet(viewsets.ModelViewSet):
    queryset = Installation.objects.select_related('customer', 'lead_technician').all()
    serializer_class = InstallationSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'customer']
    search_fields = ['installation_address', 'customer__full_name', 'inverter_model']
    ordering_fields = ['created_at', 'scheduled_date']
    ordering = ['-created_at']


class InstallationRequestViewSet(viewsets.ModelViewSet):
    queryset = InstallationRequest.objects.select_related('customer', 'contact').all()
    serializer_class = InstallationRequestSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status']
    search_fields = ['request_id', 'customer_name', 'installation_address', 'customer__full_name']
    ordering_fields = ['created_at']
    ordering = ['-created_at']


class ProductOrderViewSet(viewsets.ModelViewSet):
    queryset = ProductOrder.objects.select_related('customer', 'contact', 'product').all()
    serializer_class = ProductOrderSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'delivery_method']
    search_fields = ['order_number', 'customer_name', 'product_name', 'customer__full_name']
    ordering_fields = ['created_at', 'total_price']
    ordering = ['-created_at']


class SupportRequestViewSet(viewsets.ModelViewSet):
    queryset = SupportRequest.objects.select_related('customer', 'contact').all()
    serializer_class = SupportRequestSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'support_category']
    search_fields = ['request_id', 'customer_name', 'issue_details']
    ordering_fields = ['created_at']
    ordering = ['-created_at']


class QuoteRequestViewSet(viewsets.ModelViewSet):
    queryset = QuoteRequest.objects.select_related('customer', 'contact').all()
    serializer_class = QuoteRequestSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status']
    search_fields = ['request_id', 'customer_name', 'location']
    ordering_fields = ['created_at']
    ordering = ['-created_at']

