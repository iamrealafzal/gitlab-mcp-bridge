"""
Django Admin configuration for MCP Bridge models
"""
from django.contrib import admin
from .models import (
    GitLabConnection,
    Repository,
    LLMProvider,
    AIModel,
    NotificationChannel,
    NotificationRule,
)


@admin.register(GitLabConnection)
class GitLabConnectionAdmin(admin.ModelAdmin):
    list_display = ['name', 'instance_url', 'is_active', 'has_token', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'instance_url']
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'instance_url', 'is_active')
        }),
        ('OAuth Configuration', {
            'fields': ('client_id', 'client_secret'),
            'description': 'After saving, use the "Connect to GitLab" button to authorize access.'
        }),
        ('Tokens (Auto-managed)', {
            'fields': ('access_token', 'refresh_token', 'token_expires_at'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ['created_at', 'updated_at']
    
    def has_token(self, obj):
        """Check if connection has an access token"""
        if not obj:
            return False
        try:
            # Access the encrypted field - it will decrypt automatically
            # If decryption fails, it returns empty string, so bool() will be False
            return bool(obj.access_token)
        except Exception:
            # If there's any error accessing the token, return False
            return False
    has_token.boolean = True
    has_token.short_description = 'Has Token'
    
    def changeform_view(self, request, object_id=None, form_url='', extra_context=None):
        extra_context = extra_context or {}
        if object_id:
            extra_context['oauth_start_url'] = f'/mcp/gitlab/oauth/start/{object_id}/'
            extra_context['sync_url'] = f'/mcp/gitlab/sync/{object_id}/'
        return super().changeform_view(request, object_id, form_url, extra_context)


@admin.register(Repository)
class RepositoryAdmin(admin.ModelAdmin):
    list_display = ['local_name', 'gitlab_project_path', 'gitlab_connection', 'force_ollama', 'is_active']
    list_filter = ['is_active', 'gitlab_connection', 'created_at']
    search_fields = ['local_name', 'gitlab_project_path']
    fieldsets = (
        ('Mapping', {
            'fields': ('gitlab_connection', 'local_name', 'gitlab_project_id', 'gitlab_project_path', 'default_branch')
        }),
        ('Privacy & Status', {
            'fields': ('force_ollama', 'is_active'),
            'description': 'Enable "Force Ollama" to ensure all AI analysis for this repository uses local models only.'
        }),
    )
    readonly_fields = ['created_at', 'updated_at']


@admin.register(LLMProvider)
class LLMProviderAdmin(admin.ModelAdmin):
    list_display = ['name', 'provider_type', 'base_url', 'is_active']
    list_filter = ['provider_type', 'is_active', 'created_at']
    search_fields = ['name', 'base_url']
    fieldsets = (
        ('Provider Information', {
            'fields': ('name', 'provider_type', 'base_url', 'is_active')
        }),
        ('Authentication', {
            'fields': ('api_key',),
            'description': 'API key is not required for Ollama (local) providers'
        }),
    )
    readonly_fields = ['created_at', 'updated_at']


@admin.register(AIModel)
class AIModelAdmin(admin.ModelAdmin):
    list_display = ['display_name', 'model_id', 'provider', 'is_default', 'is_active']
    list_filter = ['is_active', 'is_default', 'provider', 'created_at']
    search_fields = ['display_name', 'model_id']
    fieldsets = (
        ('Model Information', {
            'fields': ('provider', 'model_id', 'display_name')
        }),
        ('Configuration', {
            'fields': ('is_default', 'is_active')
        }),
    )
    readonly_fields = ['created_at']


@admin.register(NotificationChannel)
class NotificationChannelAdmin(admin.ModelAdmin):
    list_display = ['name', 'channel_type', 'is_active', 'created_at']
    list_filter = ['channel_type', 'is_active', 'created_at']
    search_fields = ['name']
    fieldsets = (
        ('Channel Information', {
            'fields': ('name', 'channel_type', 'is_active')
        }),
        ('Configuration', {
            'fields': ('webhook_url',)
        }),
    )
    readonly_fields = ['created_at', 'updated_at']


@admin.register(NotificationRule)
class NotificationRuleAdmin(admin.ModelAdmin):
    list_display = ['name', 'trigger_type', 'channel', 'is_active']
    list_filter = ['trigger_type', 'is_active', 'channel', 'created_at']
    search_fields = ['name']
    fieldsets = (
        ('Rule Information', {
            'fields': ('name', 'trigger_type', 'channel', 'is_active')
        }),
    )
    readonly_fields = ['created_at']
