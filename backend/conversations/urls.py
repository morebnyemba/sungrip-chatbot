"""
URL configuration for conversations app
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ContactViewSet, DashboardStatsView

router = DefaultRouter()
router.register(r'contacts', ContactViewSet, basename='contact')

urlpatterns = [
    path('dashboard-stats/', DashboardStatsView.as_view(), name='dashboard-stats'),
    path('', include(router.urls)),
]
