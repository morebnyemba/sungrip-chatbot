"""
URL configuration for meta_integration app.

Following conventions from morebnyemba/hanna and morebnyemba/whatsappcrm.
"""
from django.urls import path
from .views import MetaWebhookAPIView, WebhookStatusView

app_name = 'meta_integration'

urlpatterns = [
    path('webhook/', MetaWebhookAPIView.as_view(), name='webhook'),
    path('webhook/status/', WebhookStatusView.as_view(), name='webhook_status'),
]
