"""
Django models for GitLab MCP Bridge
"""
from django.db import models
from django.core.exceptions import ValidationError
from cryptography.fernet import Fernet
from django.conf import settings
import base64
import os


def get_encryption_key():
    """Get or generate encryption key for sensitive data"""
    key_file = os.path.join(settings.BASE_DIR, '.encryption_key')
    if os.path.exists(key_file):
        with open(key_file, 'rb') as f:
            return f.read()
    else:
        key = Fernet.generate_key()
        with open(key_file, 'wb') as f:
            f.write(key)
        return key


def encrypt_value(value: str) -> bytes:
    """Encrypt a string value"""
    if not value:
        return b''
    f = Fernet(get_encryption_key())
    return f.encrypt(value.encode())


def decrypt_value(encrypted: bytes) -> str:
    """Decrypt an encrypted value"""
    if not encrypted:
        return ''
    f = Fernet(get_encryption_key())
    return f.decrypt(encrypted).decode()


class EncryptedTextField(models.BinaryField):
    """Custom field that encrypts/decrypts text automatically"""
    
    def from_db_value(self, value, expression, connection):
        if value is None:
            return value
        return decrypt_value(value)
    
    def to_python(self, value):
        if isinstance(value, str):
            return value
        if value is None:
            return value
        return decrypt_value(value)
    
    def get_prep_value(self, value):
        if value is None:
            return value
        return encrypt_value(value)


class GitLabConnection(models.Model):
    """Stores GitLab OAuth connection details"""
    name = models.CharField(max_length=200, unique=True, help_text="Friendly name for this GitLab connection")
    instance_url = models.URLField(help_text="GitLab instance URL (e.g., https://gitlab.com)")
    client_id = models.CharField(max_length=200, help_text="OAuth Application Client ID")
    client_secret = EncryptedTextField(help_text="OAuth Application Client Secret")
    access_token = EncryptedTextField(null=True, blank=True, help_text="OAuth Access Token")
    refresh_token = EncryptedTextField(null=True, blank=True, help_text="OAuth Refresh Token")
    token_expires_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "GitLab Connection"
        verbose_name_plural = "GitLab Connections"
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.instance_url})"


class Repository(models.Model):
    """Maps local project identifiers to GitLab repositories"""
    gitlab_connection = models.ForeignKey(
        GitLabConnection,
        on_delete=models.CASCADE,
        related_name='repositories'
    )
    local_name = models.CharField(
        max_length=200,
        help_text="Local identifier/name for this repository"
    )
    gitlab_project_id = models.IntegerField(help_text="GitLab Project ID")
    gitlab_project_path = models.CharField(
        max_length=500,
        help_text="GitLab project path (e.g., group/project)"
    )
    default_branch = models.CharField(max_length=100, default='main')
    is_active = models.BooleanField(default=True)
    force_ollama = models.BooleanField(
        default=False,
        help_text="Force use of Ollama (local) models for this repository to ensure privacy"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Repository"
        verbose_name_plural = "Repositories"
        unique_together = [['gitlab_connection', 'local_name']]
        ordering = ['local_name']
    
    def __str__(self):
        return f"{self.local_name} -> {self.gitlab_project_path}"


class LLMProvider(models.Model):
    """Stores LLM provider configuration"""
    PROVIDER_TYPES = [
        ('openai', 'OpenAI'),
        ('anthropic', 'Anthropic'),
        ('ollama', 'Ollama (Local)'),
    ]
    
    name = models.CharField(max_length=100, unique=True, help_text="Provider name")
    provider_type = models.CharField(max_length=20, choices=PROVIDER_TYPES)
    base_url = models.URLField(
        help_text="API Base URL (e.g., https://api.openai.com/v1 or http://localhost:11434 for Ollama)"
    )
    api_key = EncryptedTextField(
        null=True,
        blank=True,
        help_text="API Key (not required for Ollama)"
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "LLM Provider"
        verbose_name_plural = "LLM Providers"
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.get_provider_type_display()})"
    
    def clean(self):
        if self.provider_type != 'ollama' and not self.api_key:
            raise ValidationError("API key is required for cloud providers")


class AIModel(models.Model):
    """Stores AI model configurations"""
    provider = models.ForeignKey(
        LLMProvider,
        on_delete=models.CASCADE,
        related_name='models'
    )
    model_id = models.CharField(
        max_length=200,
        help_text="Model identifier (e.g., gpt-4o, claude-3-5-sonnet, qwen2.5-coder:7b)"
    )
    display_name = models.CharField(max_length=200, help_text="Human-readable model name")
    is_active = models.BooleanField(default=True)
    is_default = models.BooleanField(
        default=False,
        help_text="Use this as the default model for analysis"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "AI Model"
        verbose_name_plural = "AI Models"
        unique_together = [['provider', 'model_id']]
        ordering = ['provider', 'model_id']
    
    def __str__(self):
        return f"{self.display_name} ({self.provider.name})"
    
    def save(self, *args, **kwargs):
        # Ensure only one default model exists
        if self.is_default:
            AIModel.objects.filter(is_default=True).exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)


class NotificationChannel(models.Model):
    """Stores notification channel configurations (Slack, Teams, etc.)"""
    CHANNEL_TYPES = [
        ('slack', 'Slack Webhook'),
        ('teams', 'Microsoft Teams Webhook'),
    ]
    
    name = models.CharField(max_length=200, unique=True, help_text="Channel name")
    channel_type = models.CharField(max_length=20, choices=CHANNEL_TYPES)
    webhook_url = EncryptedTextField(help_text="Webhook URL for notifications")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Notification Channel"
        verbose_name_plural = "Notification Channels"
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.get_channel_type_display()})"


class NotificationRule(models.Model):
    """Defines when and how to send notifications"""
    TRIGGER_TYPES = [
        ('on_error', 'On Error Detection'),
        ('on_fix_generated', 'On Fix Generation'),
        ('on_critical', 'On Critical Errors Only'),
    ]
    
    name = models.CharField(max_length=200, unique=True)
    trigger_type = models.CharField(max_length=20, choices=TRIGGER_TYPES)
    channel = models.ForeignKey(
        NotificationChannel,
        on_delete=models.CASCADE,
        related_name='rules'
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Notification Rule"
        verbose_name_plural = "Notification Rules"
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} -> {self.channel.name}"
