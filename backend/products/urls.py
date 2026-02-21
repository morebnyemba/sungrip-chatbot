"""
URL configuration for products app
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ProductViewSet, ProductCategoryViewSet, SolarPackageViewSet

router = DefaultRouter()
router.register(r'products', ProductViewSet)
router.register(r'product-categories', ProductCategoryViewSet)
router.register(r'solar-packages', SolarPackageViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
