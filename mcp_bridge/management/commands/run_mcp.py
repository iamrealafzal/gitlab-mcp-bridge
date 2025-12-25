"""
Django management command to run the MCP server
"""
import json
import sys
import logging
from django.core.management.base import BaseCommand
from django.core.exceptions import ObjectDoesNotExist
from mcp_bridge.models import (
    GitLabConnection,
    Repository,
    AIModel,
    NotificationChannel,
    NotificationRule,
)
from mcp_bridge.services.gitlab_service import GitLabService
from mcp_bridge.services.log_analyzer import LogAnalyzer
from mcp_bridge.services.ai_service import AIService
from mcp_bridge.services.notification_service import NotificationService

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Run the MCP server for GitLab integration'

    def handle(self, *args, **options):
        """Run the MCP server over stdio"""
        self.stdout.write("Starting GitLab MCP Bridge Server...", ending='\n')
        
        # Set up logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # Initialize MCP server
        server = MCPServer()
        server.run()


class MCPServer:
    """MCP Server implementation using JSON-RPC over stdio"""
    
    def __init__(self):
        self.tools = {
            'list_gitlab_connections': self.list_gitlab_connections,
            'list_repositories': self.list_repositories,
            'list_ai_models': self.list_ai_models,
            'analyze_logs': self.analyze_logs,
            'fetch_gitlab_file': self.fetch_gitlab_file,
            'generate_fix': self.generate_fix,
            'send_notification': self.send_notification,
        }
    
    def run(self):
        """Main server loop - reads from stdin, writes to stdout"""
        try:
            while True:
                line = sys.stdin.readline()
                if not line:
                    break
                
                line = line.strip()
                if not line:
                    continue
                
                try:
                    request = json.loads(line)
                    response = self.handle_request(request)
                    if response:
                        print(json.dumps(response), flush=True)
                except json.JSONDecodeError as e:
                    error_response = self.create_error_response(
                        None, -32700, "Parse error", str(e)
                    )
                    print(json.dumps(error_response), flush=True)
                except Exception as e:
                    logger.error(f"Error handling request: {e}", exc_info=True)
                    error_response = self.create_error_response(
                        None, -32603, "Internal error", str(e)
                    )
                    print(json.dumps(error_response), flush=True)
        except KeyboardInterrupt:
            logger.info("Server shutting down...")
        except Exception as e:
            logger.error(f"Fatal error: {e}", exc_info=True)
    
    def handle_request(self, request):
        """Handle a JSON-RPC request"""
        method = request.get('method')
        params = request.get('params', {})
        request_id = request.get('id')
        
        if method == 'initialize':
            return self.create_success_response(request_id, {
                'protocolVersion': '2024-11-05',
                'capabilities': {
                    'tools': {}
                },
                'serverInfo': {
                    'name': 'gitlab-mcp-bridge',
                    'version': '0.1.0'
                }
            })
        
        elif method == 'tools/list':
            return self.create_success_response(request_id, {
                'tools': [
                    {
                        'name': 'list_gitlab_connections',
                        'description': 'List all configured GitLab connections',
                    },
                    {
                        'name': 'list_repositories',
                        'description': 'List all mapped repositories for a GitLab connection',
                        'inputSchema': {
                            'type': 'object',
                            'properties': {
                                'connection_name': {'type': 'string'}
                            },
                            'required': ['connection_name']
                        }
                    },
                    {
                        'name': 'list_ai_models',
                        'description': 'List all available AI models',
                    },
                    {
                        'name': 'analyze_logs',
                        'description': 'Analyze a local log file and extract errors',
                        'inputSchema': {
                            'type': 'object',
                            'properties': {
                                'file_path': {'type': 'string'},
                            },
                            'required': ['file_path']
                        }
                    },
                    {
                        'name': 'fetch_gitlab_file',
                        'description': 'Fetch file content from a GitLab repository',
                        'inputSchema': {
                            'type': 'object',
                            'properties': {
                                'connection_name': {'type': 'string'},
                                'repository_name': {'type': 'string'},
                                'file_path': {'type': 'string'},
                                'ref': {'type': 'string'}
                            },
                            'required': ['connection_name', 'repository_name', 'file_path']
                        }
                    },
                    {
                        'name': 'generate_fix',
                        'description': 'Generate a fix suggestion using AI based on log errors and GitLab code',
                        'inputSchema': {
                            'type': 'object',
                            'properties': {
                                'log_file_path': {'type': 'string'},
                                'connection_name': {'type': 'string'},
                                'repository_name': {'type': 'string'},
                                'model_name': {'type': 'string'}
                            },
                            'required': ['log_file_path', 'connection_name', 'repository_name']
                        }
                    },
                    {
                        'name': 'send_notification',
                        'description': 'Send a notification to configured channels',
                        'inputSchema': {
                            'type': 'object',
                            'properties': {
                                'channel_name': {'type': 'string'},
                                'title': {'type': 'string'},
                                'message': {'type': 'string'}
                            },
                            'required': ['channel_name', 'title', 'message']
                        }
                    },
                ]
            })
        
        elif method == 'tools/call':
            tool_name = params.get('name')
            tool_args = params.get('arguments', {})
            
            if tool_name in self.tools:
                try:
                    result = self.tools[tool_name](**tool_args)
                    return self.create_success_response(request_id, {
                        'content': [
                            {
                                'type': 'text',
                                'text': json.dumps(result, indent=2)
                            }
                        ]
                    })
                except Exception as e:
                    logger.error(f"Error executing tool {tool_name}: {e}", exc_info=True)
                    return self.create_error_response(
                        request_id, -32603, "Tool execution error", str(e)
                    )
            else:
                return self.create_error_response(
                    request_id, -32601, "Method not found", f"Unknown tool: {tool_name}"
                )
        
        else:
            return self.create_error_response(
                request_id, -32601, "Method not found", f"Unknown method: {method}"
            )
    
    def create_success_response(self, request_id, result):
        """Create a successful JSON-RPC response"""
        return {
            'jsonrpc': '2.0',
            'id': request_id,
            'result': result
        }
    
    def create_error_response(self, request_id, code, message, data=None):
        """Create an error JSON-RPC response"""
        response = {
            'jsonrpc': '2.0',
            'id': request_id,
            'error': {
                'code': code,
                'message': message
            }
        }
        if data:
            response['error']['data'] = data
        return response
    
    # Tool implementations
    def list_gitlab_connections(self):
        """List all GitLab connections"""
        connections = GitLabConnection.objects.filter(is_active=True)
        return {
            'connections': [
                {
                    'name': conn.name,
                    'instance_url': conn.instance_url,
                    'has_token': bool(conn.access_token),
                }
                for conn in connections
            ]
        }
    
    def list_repositories(self, connection_name: str):
        """List repositories for a connection"""
        try:
            connection = GitLabConnection.objects.get(name=connection_name, is_active=True)
            repos = Repository.objects.filter(gitlab_connection=connection, is_active=True)
            return {
                'connection': connection_name,
                'repositories': [
                    {
                        'local_name': repo.local_name,
                        'gitlab_project_path': repo.gitlab_project_path,
                        'default_branch': repo.default_branch,
                    }
                    for repo in repos
                ]
            }
        except ObjectDoesNotExist:
            return {'error': f'Connection "{connection_name}" not found'}
    
    def list_ai_models(self):
        """List all available AI models"""
        models = AIModel.objects.filter(is_active=True).select_related('provider')
        return {
            'models': [
                {
                    'display_name': model.display_name,
                    'model_id': model.model_id,
                    'provider': model.provider.name,
                    'provider_type': model.provider.provider_type,
                    'is_default': model.is_default,
                }
                for model in models
            ]
        }
    
    def analyze_logs(self, file_path: str):
        """Analyze a log file and extract errors"""
        try:
            analyzer = LogAnalyzer(file_path)
            errors = analyzer.extract_errors()
            summary = analyzer.get_summary()
            file_refs = analyzer.get_file_references()
            
            return {
                'summary': summary,
                'errors': errors,
                'file_references': [
                    {'file_path': path, 'line_number': line}
                    for path, line in file_refs
                ]
            }
        except Exception as e:
            return {'error': str(e)}
    
    def fetch_gitlab_file(
        self,
        connection_name: str,
        repository_name: str,
        file_path: str,
        ref: str = None
    ):
        """Fetch file content from GitLab"""
        try:
            connection = GitLabConnection.objects.get(name=connection_name, is_active=True)
            repository = Repository.objects.get(
                gitlab_connection=connection,
                local_name=repository_name,
                is_active=True
            )
            
            service = GitLabService(connection)
            if ref:
                content = service.get_file_content(repository, file_path, ref)
            else:
                content = service.get_file_content(repository, file_path)
            
            return {
                'file_path': file_path,
                'content': content['content'],
                'size': content['size'],
                'ref': content['ref'],
            }
        except Exception as e:
            return {'error': str(e)}
    
    def generate_fix(
        self,
        log_file_path: str,
        connection_name: str,
        repository_name: str,
        model_name: str = None
    ):
        """Generate a fix suggestion using AI"""
        try:
            # Analyze logs
            analyzer = LogAnalyzer(log_file_path)
            errors = analyzer.extract_errors()
            file_refs = analyzer.get_file_references()
            
            if not errors:
                return {'message': 'No errors found in log file'}
            
            # Get GitLab connection and repository
            connection = GitLabConnection.objects.get(name=connection_name, is_active=True)
            repository = Repository.objects.get(
                gitlab_connection=connection,
                local_name=repository_name,
                is_active=True
            )
            
            # Get AI model (respect privacy mode)
            from django.db.models import Q
            if repository.force_ollama:
                # Privacy mode: only use Ollama models
                if model_name:
                    model = AIModel.objects.filter(
                        (Q(display_name=model_name) | Q(model_id=model_name)),
                        provider__provider_type='ollama',
                        is_active=True
                    ).first()
                else:
                    # Get default Ollama model
                    model = AIModel.objects.filter(
                        provider__provider_type='ollama',
                        is_active=True
                    ).first()
                
                if not model:
                    return {'error': 'Privacy mode enabled for this repository. Please configure an Ollama model in Django Admin.'}
            else:
                # Normal mode: use any model
                if model_name:
                    model = AIModel.objects.filter(
                        (Q(display_name=model_name) | Q(model_id=model_name)),
                        is_active=True
                    ).first()
                else:
                    model = AIService.get_default_model()
                
                if not model:
                    return {'error': 'No AI model available. Please configure one in Django Admin.'}
            
            gitlab_service = GitLabService(connection)
            ai_service = AIService(model)
            
            # Process first error with file reference
            first_error = errors[0]
            error_context = first_error.get('context', first_error.get('raw_line', ''))
            
            code_context = None
            if 'file_path' in first_error and first_error.get('line_number'):
                try:
                    file_path = first_error['file_path']
                    line_num = first_error['line_number']
                    # Fetch surrounding lines
                    code_context = gitlab_service.get_file_lines(
                        repository, file_path, max(1, line_num - 10), line_num + 10
                    )
                    code_context = f"File: {file_path}\nLines {code_context['lines'][0]}-{code_context['lines'][-1]}:\n{code_context['content']}"
                except Exception as e:
                    logger.warning(f"Could not fetch code context: {e}")
            
            # Generate fix
            fix_result = ai_service.generate_fix_suggestion(
                error_context=error_context,
                code_context=code_context,
                log_content=analyzer.content[:2000] if analyzer.content else None
            )
            
            # Trigger notifications if configured
            NotificationService.trigger_notifications(
                'on_fix_generated',
                title=f"Fix Generated for {repository_name}",
                message=f"AI-generated fix suggestion for error in {log_file_path}",
                error_details=first_error,
                fix_suggestion=fix_result.get('suggestion')
            )
            
            return {
                'error_analyzed': first_error,
                'fix_suggestion': fix_result,
                'model_used': model.display_name,
            }
            
        except Exception as e:
            logger.error(f"Error generating fix: {e}", exc_info=True)
            return {'error': str(e)}
    
    def send_notification(self, channel_name: str, title: str, message: str):
        """Send a notification to a channel"""
        try:
            channel = NotificationChannel.objects.get(name=channel_name, is_active=True)
            service = NotificationService(channel)
            success = service.send_notification(title, message)
            
            return {
                'success': success,
                'channel': channel_name,
            }
        except Exception as e:
            return {'error': str(e)}

