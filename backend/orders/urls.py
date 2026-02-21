"""
URL configuration for orders app
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    OrderViewSet, InstallationViewSet, InstallationRequestViewSet,
    ProductOrderViewSet, SupportRequestViewSet, QuoteRequestViewSet,
    PaymentPlanViewSet,
)

router = DefaultRouter()
router.register(r'orders', OrderViewSet)
router.register(r'installations', InstallationViewSet)
router.register(r'installation-requests', InstallationRequestViewSet)
router.register(r'product-orders', ProductOrderViewSet)
router.register(r'support-requests', SupportRequestViewSet)
router.register(r'quote-requests', QuoteRequestViewSet)
router.register(r'payment-plans', PaymentPlanViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
