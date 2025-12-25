# Architecture Documentation

## Overview

The GitLab MCP Bridge is a Django-based application that provides a Model Context Protocol (MCP) server for integrating GitLab repositories with AI-powered log analysis and automated fix suggestions. The system is designed to support multiple clients, various LLM providers, and notification channels.

## System Architecture

### High-Level Architecture

```mermaid
graph TB
    subgraph Client [MCP Client]
        IDE[IDE/Editor]
    end

    subgraph DjangoApp [Django Application]
        Admin[Admin UI]
        OAuth[OAuth Views]
        MCP[MCP Server]
        Services[Service Layer]
        Models[Database Models]
    end

    subgraph External [External Services]
        GitLab[GitLab API]
        OpenAI[OpenAI API]
        Anthropic[Anthropic API]
        Ollama[Ollama Local]
        Slack[Slack Webhook]
        Teams[Teams Webhook]
    end

    IDE -->|JSON-RPC| MCP
    Admin --> Models
    OAuth --> GitLab
    MCP --> Services
    Services --> Models
    Services --> GitLab
    Services --> OpenAI
    Services --> Anthropic
    Services --> Ollama
    Services --> Slack
    Services --> Teams
    Models --> DB[(SQLite/Postgres)]
```

## Component Details

### 1. Django Models

#### GitLabConnection
Stores OAuth configuration and tokens for GitLab instances.

**Fields:**
- `name`: Friendly identifier
- `instance_url`: GitLab instance URL
- `client_id`: OAuth client ID
- `client_secret`: Encrypted OAuth secret
- `access_token`: Encrypted OAuth access token
- `refresh_token`: Encrypted OAuth refresh token
- `token_expires_at`: Token expiration timestamp

#### Repository
Maps local project identifiers to GitLab repositories.

**Fields:**
- `gitlab_connection`: Foreign key to GitLabConnection
- `local_name`: Local identifier
- `gitlab_project_id`: GitLab project ID
- `gitlab_project_path`: GitLab project path
- `default_branch`: Default branch name

#### LLMProvider
Stores LLM provider configuration.

**Fields:**
- `name`: Provider name
- `provider_type`: One of 'openai', 'anthropic', 'ollama'
- `base_url`: API base URL
- `api_key`: Encrypted API key

#### AIModel
Stores AI model configurations.

**Fields:**
- `provider`: Foreign key to LLMProvider
- `model_id`: Model identifier (e.g., 'gpt-4o')
- `display_name`: Human-readable name
- `is_default`: Whether this is the default model

#### NotificationChannel
Stores notification channel configurations.

**Fields:**
- `name`: Channel name
- `channel_type`: 'slack' or 'teams'
- `webhook_url`: Encrypted webhook URL

#### NotificationRule
Defines when to send notifications.

**Fields:**
- `name`: Rule name
- `trigger_type`: 'on_error', 'on_fix_generated', 'on_critical'
- `channel`: Foreign key to NotificationChannel

### 2. Service Layer

#### GitLabService
Handles GitLab API interactions.

**Key Methods:**
- `get_file_content()`: Fetch file content from repository
- `get_file_lines()`: Fetch specific lines from a file
- `list_repositories()`: List accessible repositories

**Features:**
- Automatic token refresh (when implemented)
- Error handling and logging
- Support for different Git references (branch/tag/commit)

#### LogAnalyzer
Parses log files and extracts error information.

**Key Methods:**
- `extract_errors()`: Find errors in log file
- `get_file_references()`: Extract file paths from errors
- `get_summary()`: Get error summary statistics

**Supported Patterns:**
- Python tracebacks
- JavaScript/Node.js errors
- Java stack traces
- Generic file:line patterns

#### AIService
Unified interface for LLM providers.

**Key Methods:**
- `generate_fix_suggestion()`: Generate fix based on error and code context

**Provider Support:**
- **OpenAI**: Uses `openai` Python SDK
- **Anthropic**: Uses `anthropic` Python SDK
- **Ollama**: Uses HTTP requests to local API

**Features:**
- Unified prompt building
- Provider-specific API handling
- Error handling and fallback

#### NotificationService
Sends notifications to configured channels.

**Key Methods:**
- `send_notification()`: Send notification to a channel
- `trigger_notifications()`: Trigger notifications based on rules

**Channel Support:**
- **Slack**: Uses Slack webhook format with blocks
- **Teams**: Uses Microsoft Teams adaptive cards

### 3. MCP Server

The MCP server is implemented as a Django management command (`run_mcp`) that communicates via JSON-RPC over stdio.

**Protocol:**
- JSON-RPC 2.0
- Standard input/output communication
- Request/response pattern

**Tools Provided:**
1. `list_gitlab_connections`: List GitLab connections
2. `list_repositories`: List repositories for a connection
3. `list_ai_models`: List available AI models
4. `analyze_logs`: Analyze log file for errors
5. `fetch_gitlab_file`: Fetch file from GitLab
6. `generate_fix`: Generate AI-powered fix suggestion
7. `send_notification`: Send notification to channel

**Request Flow:**
```mermaid
sequenceDiagram
    participant Client
    participant MCP as MCP Server
    participant Services
    participant DB as Database
    participant External

    Client->>MCP: JSON-RPC Request
    MCP->>DB: Query Models
    MCP->>Services: Call Service
    Services->>External: API Call
    External-->>Services: Response
    Services-->>MCP: Result
    MCP->>DB: Update if needed
    MCP-->>Client: JSON-RPC Response
```

### 4. OAuth Flow

```mermaid
sequenceDiagram
    participant User
    participant Admin as Django Admin
    participant Django
    participant GitLab

    User->>Admin: Click "Connect to GitLab"
    Admin->>Django: Redirect to OAuth Start
    Django->>GitLab: Redirect to Authorization
    GitLab->>User: Show Authorization Page
    User->>GitLab: Grant Access
    GitLab->>Django: Callback with Code
    Django->>GitLab: Exchange Code for Token
    GitLab-->>Django: Access Token + Refresh Token
    Django->>Django: Save Tokens (Encrypted)
    Django->>GitLab: Fetch Repositories
    GitLab-->>Django: Repository List
    Django->>Django: Sync Repositories to DB
    Django-->>Admin: Show Success Message
```

## Data Flow

### Fix Generation Flow

```mermaid
graph LR
    A[Log File] --> B[Log Analyzer]
    B --> C[Extract Errors]
    C --> D[Get File References]
    D --> E[GitLab Service]
    E --> F[Fetch Code Context]
    F --> G[AI Service]
    G --> H[Generate Fix]
    H --> I[Notification Service]
    I --> J[Send Notifications]
    J --> K[Return Result]
```

### Security Flow

```mermaid
graph TD
    A[User Input] --> B[Validation]
    B --> C{Valid?}
    C -->|No| D[Error Response]
    C -->|Yes| E[Encrypt Sensitive Data]
    E --> F[Store in DB]
    F --> G[Retrieve When Needed]
    G --> H[Decrypt]
    H --> I[Use in API Call]
```

## Database Schema

### Entity Relationships

```mermaid
erDiagram
    GitLabConnection ||--o{ Repository : "has"
    LLMProvider ||--o{ AIModel : "has"
    NotificationChannel ||--o{ NotificationRule : "has"
    
    GitLabConnection {
        int id PK
        string name
        string instance_url
        string client_id
        binary client_secret
        binary access_token
        binary refresh_token
        datetime token_expires_at
    }
    
    Repository {
        int id PK
        int gitlab_connection_id FK
        string local_name
        int gitlab_project_id
        string gitlab_project_path
    }
    
    LLMProvider {
        int id PK
        string name
        string provider_type
        string base_url
        binary api_key
    }
    
    AIModel {
        int id PK
        int provider_id FK
        string model_id
        string display_name
        bool is_default
    }
    
    NotificationChannel {
        int id PK
        string name
        string channel_type
        binary webhook_url
    }
    
    NotificationRule {
        int id PK
        int channel_id FK
        string trigger_type
    }
```

## Encryption

All sensitive data is encrypted using Fernet (symmetric encryption from the `cryptography` library).

**Encryption Key:**
- Stored in `.encryption_key` file in project root
- Generated automatically on first use
- **Important**: Keep this file secure and backed up

**Encrypted Fields:**
- `GitLabConnection.client_secret`
- `GitLabConnection.access_token`
- `GitLabConnection.refresh_token`
- `LLMProvider.api_key`
- `NotificationChannel.webhook_url`

## Error Handling

### Service-Level Errors
- All services use try/except blocks
- Errors are logged with context
- User-friendly error messages returned

### MCP-Level Errors
- JSON-RPC error codes:
  - `-32700`: Parse error
  - `-32601`: Method not found
  - `-32603`: Internal error
- Error details included in response

## Scalability Considerations

### Multi-Client Support
- Each client can have multiple GitLab connections
- Repository mappings are isolated per connection
- LLM providers can be shared or per-client

### Performance
- Database queries optimized with `select_related()`
- Token caching in service instances
- Log file reading is streamed for large files

### Future Enhancements
- Celery for async task processing
- Redis for caching
- Database connection pooling
- Rate limiting for API calls

## Deployment

### Production Checklist
- [ ] Use PostgreSQL instead of SQLite
- [ ] Set `DEBUG = False`
- [ ] Configure `ALLOWED_HOSTS`
- [ ] Set up proper secret key management
- [ ] Use environment variables for sensitive config
- [ ] Set up SSL/TLS
- [ ] Configure proper logging
- [ ] Set up monitoring and alerts
- [ ] Backup encryption key securely
- [ ] Configure token refresh automation

### Environment Variables
```bash
SECRET_KEY=your-secret-key
DEBUG=False
ALLOWED_HOSTS=your-domain.com
DATABASE_URL=postgresql://user:pass@host/db
```

## Testing Strategy

### Unit Tests
- Service layer methods
- Model validation
- Encryption/decryption

### Integration Tests
- OAuth flow
- MCP tool execution
- End-to-end fix generation

### Manual Testing
- Django Admin workflows
- MCP server communication
- Notification delivery

## Monitoring and Logging

### Logging Levels
- **INFO**: Normal operations
- **WARNING**: Non-critical issues
- **ERROR**: Errors requiring attention
- **DEBUG**: Detailed debugging information

### Key Metrics to Monitor
- MCP request count and latency
- GitLab API call success rate
- AI model response times
- Notification delivery success rate
- Token expiration and refresh events

## Future Architecture Enhancements

1. **WebSocket Support**: Real-time MCP communication
2. **GraphQL API**: Alternative to MCP for web clients
3. **Plugin System**: Extensible tool registration
4. **Multi-Tenancy**: Complete isolation per client
5. **Event Sourcing**: Audit trail for all operations
6. **Microservices**: Split into separate services if needed

