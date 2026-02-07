"""
API views for the customers app
"""
from rest_framework import viewsets, filters
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from .models import Customer, CustomerInteraction
from .serializers import CustomerSerializer, CustomerInteractionSerializer


class CustomerViewSet(viewsets.ModelViewSet):
    """API endpoint for customers"""
    
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['customer_type', 'is_active', 'province', 'city']
    search_fields = ['full_name', 'phone_number', 'email', 'address_line1']
    ordering_fields = ['created_at', 'full_name']
    ordering = ['-created_at']


class CustomerInteractionViewSet(viewsets.ModelViewSet):
    """API endpoint for customer interactions"""
    
    queryset = CustomerInteraction.objects.all()
    serializer_class = CustomerInteractionSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['customer', 'interaction_type', 'channel']
    search_fields = ['summary', 'details']
    ordering_fields = ['created_at']
    ordering = ['-created_at']

