"""
API views for the products app
"""
from rest_framework import viewsets, filters
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from .models import Product, ProductCategory, SolarPackage
from .serializers import ProductSerializer, ProductCategorySerializer, SolarPackageSerializer


class ProductCategoryViewSet(viewsets.ModelViewSet):
    queryset = ProductCategory.objects.all()
    serializer_class = ProductCategorySerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_active', 'parent']
    search_fields = ['name', 'description']
    ordering = ['display_order', 'name']


class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.select_related('category').all()
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_active', 'is_featured', 'product_type', 'category']
    search_fields = ['name', 'brand', 'sku', 'model_number', 'short_description']
    ordering_fields = ['name', 'selling_price', 'stock_quantity', 'created_at']
    ordering = ['name']


class SolarPackageViewSet(viewsets.ModelViewSet):
    queryset = SolarPackage.objects.all()
    serializer_class = SolarPackageSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_active', 'is_popular', 'recommended_for', 'payment_type']
    search_fields = ['name', 'description']
    ordering_fields = ['display_order', 'system_size_kw', 'total_price']
    ordering = ['display_order', 'system_size_kw']

