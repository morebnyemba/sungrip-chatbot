"""
URL configuration for meta_integration app.

Aligned with morebnyemba/hanna's meta_integration/urls.py.
Includes webhook receiver, DRF router for MetaAppConfig and WebhookEventLog,
and a status endpoint.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'meta_integration'

# DRF router — admin management API (matches hanna)
router = DefaultRouter()
router.register(r'configs', views.MetaAppConfigViewSet, basename='metaappconfig')
router.register(r'webhook-logs', views.WebhookEventLogViewSet, basename='webhookeventlog')

urlpatterns = [
    # Webhook receiver (Meta sends events here)
    path('webhook/', views.MetaWebhookAPIView.as_view(), name='meta_webhook_receiver'),

    # Status check (sungrip-chatbot convenience endpoint)
    path('webhook/status/', views.WebhookStatusView.as_view(), name='webhook_status'),

    # DRF API for MetaAppConfig CRUD and WebhookEventLog browsing
    # e.g., /meta/api/configs/, /meta/api/webhook-logs/
    path('api/', include(router.urls)),
]
