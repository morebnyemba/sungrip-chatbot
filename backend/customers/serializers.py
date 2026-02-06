"""
Serializers for the customers app
"""
from rest_framework import serializers
from .models import Customer, CustomerInteraction


class CustomerSerializer(serializers.ModelSerializer):
    """Serializer for Customer model"""
    
    class Meta:
        model = Customer
        fields = [
            'id', 'phone_number', 'whatsapp_number', 'full_name', 'email',
            'address_line1', 'address_line2', 'city', 'province', 'postal_code',
            'gps_latitude', 'gps_longitude', 'customer_type', 'is_active',
            'notes', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']


class CustomerInteractionSerializer(serializers.ModelSerializer):
    """Serializer for CustomerInteraction model"""
    
    customer_name = serializers.CharField(source='customer.full_name', read_only=True)
    handled_by_name = serializers.CharField(source='handled_by.username', read_only=True)
    
    class Meta:
        model = CustomerInteraction
        fields = [
            'id', 'customer', 'customer_name', 'interaction_type', 'channel',
            'summary', 'details', 'handled_by', 'handled_by_name', 'created_at'
        ]
        read_only_fields = ['created_at']
