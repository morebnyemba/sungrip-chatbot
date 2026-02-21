"""
WebSocket URL routing for conversations app
"""
from django.urls import path
from .consumers import ConversationConsumer

websocket_urlpatterns = [
    path('ws/conversations/<int:contact_id>/', ConversationConsumer.as_asgi()),
]
