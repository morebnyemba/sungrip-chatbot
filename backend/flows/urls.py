"""
URL configuration for flows app.

Following conventions from morebnyemba/hanna and morebnyemba/whatsappcrm.
"""
from django.urls import path
from .views import FlowListView, FlowSessionView

app_name = 'flows'

urlpatterns = [
    # Add flow-related endpoints here as needed
    # path('list/', FlowListView.as_view(), name='flow_list'),
    # path('session/<int:session_id>/', FlowSessionView.as_view(), name='flow_session'),
]
