"""
URL configuration for customers app
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CustomerViewSet, CustomerInteractionViewSet

router = DefaultRouter()
router.register(r'customers', CustomerViewSet)
router.register(r'interactions', CustomerInteractionViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
