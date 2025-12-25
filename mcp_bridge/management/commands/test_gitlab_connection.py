"""
Management command to test GitLab connection and diagnose issues
"""
from django.core.management.base import BaseCommand
from mcp_bridge.models import GitLabConnection, Repository
from mcp_bridge.services.gitlab_service import GitLabService
import gitlab


class Command(BaseCommand):
    help = 'Test GitLab connection and diagnose issues'

    def add_arguments(self, parser):
        parser.add_argument(
            'connection_id',
            type=int,
            help='GitLab Connection ID to test'
        )

    def handle(self, *args, **options):
        connection_id = options['connection_id']
        
        try:
            connection = GitLabConnection.objects.get(id=connection_id)
            
            self.stdout.write("=" * 60)
            self.stdout.write(f"Testing GitLab Connection: {connection.name}")
            self.stdout.write("=" * 60)
            
            # Check basic info
            self.stdout.write(f"\n✓ Connection found:")
            self.stdout.write(f"  - Name: {connection.name}")
            self.stdout.write(f"  - Instance URL: {connection.instance_url}")
            self.stdout.write(f"  - Client ID: {connection.client_id}")
            self.stdout.write(f"  - Is Active: {connection.is_active}")
            
            # Check tokens
            self.stdout.write(f"\n📋 Token Status:")
            has_access_token = bool(connection.access_token)
            has_refresh_token = bool(connection.refresh_token)
            self.stdout.write(f"  - Access Token: {'✓ Present' if has_access_token else '✗ Missing'}")
            self.stdout.write(f"  - Refresh Token: {'✓ Present' if has_refresh_token else '✗ Missing'}")
            
            if connection.token_expires_at:
                from django.utils import timezone
                is_expired = connection.token_expires_at <= timezone.now()
                self.stdout.write(f"  - Expires At: {connection.token_expires_at}")
                self.stdout.write(f"  - Status: {'✗ EXPIRED' if is_expired else '✓ Valid'}")
            else:
                self.stdout.write(f"  - Expires At: Not set")
            
            if not has_access_token:
                self.stdout.write(self.style.ERROR(
                    "\n❌ No access token found. Please complete OAuth flow first."
                ))
                return
            
            # Test GitLab API connection
            self.stdout.write(f"\n🔌 Testing GitLab API Connection...")
            try:
                service = GitLabService(connection)
                client = service._get_client()
                
                # Test with a simple API call
                user = client.user
                self.stdout.write(self.style.SUCCESS(f"✓ Connected successfully!"))
                self.stdout.write(f"  - Authenticated as: {user.username if hasattr(user, 'username') else 'User'}")
                
                # Try to list repositories
                self.stdout.write(f"\n📦 Testing Repository Access...")
                repos = service.list_repositories()
                self.stdout.write(self.style.SUCCESS(f"✓ Found {len(repos)} repositories"))
                
                if repos:
                    self.stdout.write(f"\n  Repositories:")
                    for repo in repos[:5]:  # Show first 5
                        self.stdout.write(f"    - {repo['path']} (ID: {repo['id']})")
                    if len(repos) > 5:
                        self.stdout.write(f"    ... and {len(repos) - 5} more")
                
                # Check synced repositories
                synced_repos = Repository.objects.filter(gitlab_connection=connection, is_active=True)
                self.stdout.write(f"\n💾 Synced Repositories in Database: {synced_repos.count()}")
                if synced_repos.exists():
                    for repo in synced_repos[:5]:
                        self.stdout.write(f"    - {repo.local_name} -> {repo.gitlab_project_path}")
                
            except gitlab.exceptions.GitlabAuthenticationError as e:
                self.stdout.write(self.style.ERROR(f"\n❌ Authentication failed: {e}"))
                self.stdout.write("   The access token may be invalid or expired.")
                self.stdout.write("   Please re-authenticate via OAuth.")
            except gitlab.exceptions.GitlabError as e:
                self.stdout.write(self.style.ERROR(f"\n❌ GitLab API error: {e}"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"\n❌ Unexpected error: {e}"))
                import traceback
                self.stdout.write(traceback.format_exc())
            
        except GitLabConnection.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"Connection with ID {connection_id} not found"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error: {e}"))
            import traceback
            self.stdout.write(traceback.format_exc())

