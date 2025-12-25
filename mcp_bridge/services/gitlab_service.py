"""
GitLab API Service for fetching repository contents
"""
import gitlab
from typing import Optional, Dict, Any
from django.utils import timezone
from datetime import timedelta
from ..models import GitLabConnection, Repository
import logging

logger = logging.getLogger(__name__)


class GitLabService:
    """Service for interacting with GitLab API"""
    
    def __init__(self, connection: GitLabConnection):
        self.connection = connection
        self._client = None
    
    def _get_client(self) -> gitlab.Gitlab:
        """Get or create GitLab client with valid token"""
        if self._client is not None:
            return self._client
        
        # Check if token is expired and refresh if needed
        if self.connection.token_expires_at and self.connection.token_expires_at <= timezone.now():
            self._refresh_token()
        
        access_token = self.connection.access_token
        if not access_token:
            raise ValueError(f"No access token available for connection: {self.connection.name}")
        
        self._client = gitlab.Gitlab(
            self.connection.instance_url,
            oauth_token=access_token
        )
        return self._client
    
    def _refresh_token(self):
        """Refresh OAuth token if refresh_token is available"""
        if not self.connection.refresh_token:
            logger.warning(f"No refresh token available for {self.connection.name}")
            return
        
        # TODO: Implement OAuth token refresh logic
        # This would typically involve calling GitLab's token endpoint
        logger.info(f"Token refresh needed for {self.connection.name}")
    
    def get_file_content(
        self,
        repository: Repository,
        file_path: str,
        ref: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Fetch file content from GitLab repository
        
        Args:
            repository: Repository model instance
            file_path: Path to file in repository
            ref: Git reference (branch/tag/commit), defaults to repository.default_branch
        
        Returns:
            Dict with 'content', 'encoding', 'size', 'file_name'
        """
        try:
            client = self._get_client()
            project = client.projects.get(repository.gitlab_project_id)
            
            ref = ref or repository.default_branch
            file = project.files.get(file_path=file_path, ref=ref)
            
            return {
                'content': file.decode().decode('utf-8'),
                'encoding': file.encoding,
                'size': file.size,
                'file_name': file.file_name,
                'file_path': file_path,
                'ref': ref,
            }
        except gitlab.exceptions.GitlabGetError as e:
            logger.error(f"Error fetching file {file_path} from {repository.gitlab_project_path}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in get_file_content: {e}")
            raise
    
    def get_file_lines(
        self,
        repository: Repository,
        file_path: str,
        start_line: int,
        end_line: int,
        ref: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Fetch specific lines from a file
        
        Args:
            repository: Repository model instance
            file_path: Path to file in repository
            start_line: Starting line number (1-indexed)
            end_line: Ending line number (1-indexed)
            ref: Git reference
        
        Returns:
            Dict with 'content', 'lines', 'file_path', 'ref'
        """
        full_content = self.get_file_content(repository, file_path, ref)
        lines = full_content['content'].split('\n')
        
        # Extract requested lines (1-indexed to 0-indexed)
        requested_lines = lines[start_line - 1:end_line]
        
        return {
            'content': '\n'.join(requested_lines),
            'lines': list(range(start_line, end_line + 1)),
            'file_path': file_path,
            'ref': ref or repository.default_branch,
            'full_file_size': len(lines),
        }
    
    def list_repositories(self) -> list:
        """List all accessible repositories for this connection"""
        try:
            client = self._get_client()
            projects = client.projects.list(owned=True, get_all=True)
            
            return [
                {
                    'id': project.id,
                    'path': project.path_with_namespace,
                    'name': project.name,
                    'default_branch': project.default_branch,
                }
                for project in projects
            ]
        except Exception as e:
            logger.error(f"Error listing repositories: {e}")
            raise

