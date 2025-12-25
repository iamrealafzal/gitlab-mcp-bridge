"""
Views for GitLab OAuth flow
"""
import requests
from django.shortcuts import redirect, render
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.conf import settings
from .models import GitLabConnection, Repository
from .services.gitlab_service import GitLabService
from django.utils import timezone
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)


@require_http_methods(["GET"])
def gitlab_oauth_start(request, connection_id):
    """Initiate GitLab OAuth flow"""
    try:
        connection = GitLabConnection.objects.get(id=connection_id, is_active=True)
        
        # Build OAuth authorization URL
        redirect_uri = request.build_absolute_uri(f'/mcp/gitlab/callback/{connection_id}/')
        scope = 'api read_user'
        
        auth_url = (
            f"{connection.instance_url}/oauth/authorize"
            f"?client_id={connection.client_id}"
            f"&redirect_uri={redirect_uri}"
            f"&response_type=code"
            f"&scope={scope}"
        )
        
        # Store redirect URI in session for callback
        request.session['gitlab_redirect_uri'] = redirect_uri
        
        return redirect(auth_url)
    
    except GitLabConnection.DoesNotExist:
        messages.error(request, "GitLab connection not found")
        return redirect('admin:mcp_bridge_gitlabconnection_changelist')


@require_http_methods(["GET"])
def gitlab_oauth_callback(request, connection_id):
    """Handle GitLab OAuth callback"""
    try:
        connection = GitLabConnection.objects.get(id=connection_id, is_active=True)
        code = request.GET.get('code')
        error = request.GET.get('error')
        
        if error:
            messages.error(request, f"OAuth error: {error}")
            return redirect('admin:mcp_bridge_gitlabconnection_change', connection_id)
        
        if not code:
            messages.error(request, "No authorization code received")
            return redirect('admin:mcp_bridge_gitlabconnection_change', connection_id)
        
        # Exchange code for token
        redirect_uri = request.session.get('gitlab_redirect_uri')
        if not redirect_uri:
            redirect_uri = request.build_absolute_uri(f'/mcp/gitlab/callback/{connection_id}/')
        
        token_url = f"{connection.instance_url}/oauth/token"
        token_data = {
            'client_id': connection.client_id,
            'client_secret': connection.client_secret,
            'code': code,
            'grant_type': 'authorization_code',
            'redirect_uri': redirect_uri,
        }
        
        response = requests.post(token_url, data=token_data, timeout=10)
        response.raise_for_status()
        
        token_response = response.json()
        
        # Save tokens
        connection.access_token = token_response.get('access_token')
        connection.refresh_token = token_response.get('refresh_token')
        
        # Calculate expiration (GitLab tokens typically expire in 2 hours)
        expires_in = token_response.get('expires_in', 7200)
        connection.token_expires_at = timezone.now() + timedelta(seconds=expires_in)
        
        connection.save()
        
        # Sync repositories
        try:
            gitlab_service = GitLabService(connection)
            repos = gitlab_service.list_repositories()
            
            # Create or update repository mappings
            for repo_info in repos:
                Repository.objects.update_or_create(
                    gitlab_connection=connection,
                    gitlab_project_id=repo_info['id'],
                    defaults={
                        'local_name': repo_info['path'].replace('/', '_'),
                        'gitlab_project_path': repo_info['path'],
                        'default_branch': repo_info.get('default_branch', 'main'),
                        'is_active': True,
                    }
                )
            
            messages.success(
                request,
                f"Successfully connected! Synced {len(repos)} repositories."
            )
        except Exception as e:
            logger.error(f"Error syncing repositories: {e}")
            messages.warning(
                request,
                "Connected but failed to sync repositories. You can add them manually."
            )
        
        return redirect('admin:mcp_bridge_gitlabconnection_change', connection_id)
    
    except GitLabConnection.DoesNotExist:
        messages.error(request, "GitLab connection not found")
        return redirect('admin:mcp_bridge_gitlabconnection_changelist')
    except Exception as e:
        logger.error(f"OAuth callback error: {e}", exc_info=True)
        messages.error(request, f"OAuth error: {str(e)}")
        return redirect('admin:mcp_bridge_gitlabconnection_changelist')


@require_http_methods(["GET"])
def gitlab_sync_repos(request, connection_id):
    """Manually sync repositories for a connection"""
    try:
        connection = GitLabConnection.objects.get(id=connection_id, is_active=True)
        
        if not connection.access_token:
            messages.error(request, "No access token. Please connect via OAuth first.")
            return redirect('admin:mcp_bridge_gitlabconnection_change', connection_id)
        
        gitlab_service = GitLabService(connection)
        repos = gitlab_service.list_repositories()
        
        # Create or update repository mappings
        created_count = 0
        updated_count = 0
        
        for repo_info in repos:
            repo, created = Repository.objects.update_or_create(
                gitlab_connection=connection,
                gitlab_project_id=repo_info['id'],
                defaults={
                    'local_name': repo_info['path'].replace('/', '_'),
                    'gitlab_project_path': repo_info['path'],
                    'default_branch': repo_info.get('default_branch', 'main'),
                    'is_active': True,
                }
            )
            
            if created:
                created_count += 1
            else:
                updated_count += 1
        
        messages.success(
            request,
            f"Synced {len(repos)} repositories ({created_count} new, {updated_count} updated)."
        )
        
        return redirect('admin:mcp_bridge_repository_changelist')
    
    except Exception as e:
        logger.error(f"Error syncing repositories: {e}", exc_info=True)
        messages.error(request, f"Error syncing repositories: {str(e)}")
        return redirect('admin:mcp_bridge_gitlabconnection_change', connection_id)
