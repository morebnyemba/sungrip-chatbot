"""
URL configuration for agents app
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AgentViewSet, AgentClientViewSet, BetViewSet, AgentEarningViewSet

router = DefaultRouter()
router.register(r'agents', AgentViewSet)
router.register(r'agent-clients', AgentClientViewSet)
router.register(r'bets', BetViewSet)
router.register(r'agent-earnings', AgentEarningViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
