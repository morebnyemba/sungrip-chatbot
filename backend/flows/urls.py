"""
URL configuration for flows app.

Following conventions from morebnyemba/hanna and morebnyemba/whatsappcrm.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'flows'

# Create router for viewsets
router = DefaultRouter()
router.register(r'flows', views.FlowViewSet, basename='flow')
router.register(r'steps', views.FlowStepViewSet, basename='step')
router.register(r'transitions', views.FlowTransitionViewSet, basename='transition')
router.register(r'sessions', views.ContactFlowStateViewSet, basename='session')
router.register(r'whatsapp-flows', views.WhatsAppFlowViewSet, basename='whatsapp-flow')
router.register(r'whatsapp-responses', views.WhatsAppFlowResponseViewSet, basename='whatsapp-response')

urlpatterns = [
    path('', include(router.urls)),
]
