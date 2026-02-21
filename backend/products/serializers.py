"""
Serializers for the products app
"""
from rest_framework import serializers
from .models import Product, ProductCategory, SolarPackage, PackageItem


class ProductCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductCategory
        fields = ['id', 'name', 'description', 'icon', 'parent', 'is_active', 'display_order']


class ProductSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True, allow_null=True)
    is_low_stock = serializers.BooleanField(read_only=True)

    class Meta:
        model = Product
        fields = [
            'id', 'category', 'category_name', 'product_type', 'name', 'brand',
            'model_number', 'sku', 'short_description', 'specifications',
            'cost_price', 'selling_price', 'currency', 'stock_quantity',
            'low_stock_threshold', 'unit_of_measure', 'image_url',
            'warranty_period_months', 'is_active', 'is_featured', 'is_low_stock',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']


class PackageItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)

    class Meta:
        model = PackageItem
        fields = ['id', 'product', 'product_name', 'quantity', 'notes']


class SolarPackageSerializer(serializers.ModelSerializer):
    items = PackageItemSerializer(many=True, read_only=True, source='packageitem_set')
    monthly_payment = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True, allow_null=True)
    payment_label = serializers.CharField(read_only=True)

    class Meta:
        model = SolarPackage
        fields = [
            'id', 'name', 'description', 'image_url', 'system_size_kw',
            'recommended_for', 'total_price', 'deposit_amount', 'payment_type',
            'installment_months', 'installation_included', 'equipment_summary',
            'powers', 'features', 'is_active', 'is_popular', 'display_order',
            'monthly_payment', 'payment_label', 'items',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']
