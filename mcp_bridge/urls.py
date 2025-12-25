"""
URL configuration for MCP Bridge OAuth flows
"""
from django.urls import path
from . import views

urlpatterns = [
    path('oauth/start/<int:connection_id>/', views.gitlab_oauth_start, name='gitlab_oauth_start'),
    path('oauth/callback/<int:connection_id>/', views.gitlab_oauth_callback, name='gitlab_oauth_callback'),
    path('sync/<int:connection_id>/', views.gitlab_sync_repos, name='gitlab_sync_repos'),
]

