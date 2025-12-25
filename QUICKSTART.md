# Quick Start Guide

Get up and running with GitLab MCP Bridge in 5 minutes!

## Prerequisites

- Python 3.10+
- GitLab account
- (Optional) OpenAI/Anthropic API key or Ollama installed

## Installation

1. **Run the setup script**:
   ```bash
   ./setup.sh
   ```

   Or manually:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   python manage.py migrate
   python manage.py createsuperuser
   ```

2. **Start the Django server**:
   ```bash
   python manage.py runserver
   ```

3. **Access Django Admin**:
   Open http://localhost:8000/admin/ and log in.

## Basic Configuration

### Step 1: Add GitLab Connection (Create First)

1. Go to **MCP Bridge > GitLab Connections**
2. Click **Add GitLab Connection**
3. Fill in:
   - **Name**: My GitLab
   - **Instance URL**: https://gitlab.com
   - **Client ID**: (leave blank for now)
   - **Client Secret**: (leave blank for now)
4. Click **Save**
5. **Note the Connection ID** from the URL (e.g., if URL shows `/admin/.../gitlabconnection/1/change/`, the ID is `1`)

### Step 2: Create GitLab OAuth Application

1. Go to https://gitlab.com/-/profile/applications (or your GitLab instance)
2. Click **Add new application**
3. Fill in:
   - **Name**: GitLab MCP Bridge
   - **Redirect URI**: `http://localhost:8000/mcp/gitlab/oauth/callback/<YOUR_CONNECTION_ID>/`
     - Replace `<YOUR_CONNECTION_ID>` with the ID from Step 1 (e.g., `1`)
     - Example: `http://localhost:8000/mcp/gitlab/oauth/callback/1/`
   - **Scopes**: Check `api` and `read_user`
4. Click **Save application**
5. Copy the **Application ID** and **Secret**

### Step 3: Complete GitLab Connection

1. Go back to Django Admin and edit your GitLab Connection
2. Fill in:
   - **Client ID**: Paste the Application ID
   - **Client Secret**: Paste the Secret
3. Click **Save**
4. Click **Connect to GitLab** button
5. Authorize the application
6. Repositories will sync automatically

### Step 2: Add AI Model

#### Option A: OpenAI
1. Go to **MCP Bridge > LLM Providers**
2. Add provider:
   - Name: OpenAI
   - Type: OpenAI
   - Base URL: https://api.openai.com/v1
   - API Key: sk-...
3. Go to **MCP Bridge > AI Models**
4. Add model:
   - Provider: OpenAI
   - Model ID: gpt-4o
   - Display Name: GPT-4o
   - Is Default: ✓

#### Option B: Ollama (Local)
1. Install Ollama: https://ollama.ai
2. Pull model: `ollama pull qwen2.5-coder:7b`
3. Add provider:
   - Name: Ollama
   - Type: Ollama (Local)
   - Base URL: http://localhost:11434
   - API Key: (leave blank)
4. Add model:
   - Model ID: qwen2.5-coder:7b
   - Display Name: Qwen2.5 Coder

### Step 3: Test the MCP Server

Run the MCP server:
```bash
python manage.py run_mcp
```

In another terminal, test it:
```bash
echo '{"jsonrpc":"2.0","method":"initialize","params":{},"id":1}' | python manage.py run_mcp
```

## Usage Example

### Analyze a Log File

1. Create a test log file:
   ```bash
   echo 'Traceback (most recent call last):
     File "app.py", line 10, in <module>
       result = 1 / 0
   ZeroDivisionError: division by zero' > /tmp/test.log
   ```

2. Use the MCP tool:
   ```bash
   echo '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"analyze_logs","arguments":{"file_path":"/tmp/test.log"}},"id":1}' | python manage.py run_mcp
   ```

### Generate a Fix

```bash
echo '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"generate_fix","arguments":{"log_file_path":"/tmp/test.log","connection_name":"My GitLab","repository_name":"my_project"}},"id":2}' | python manage.py run_mcp
```

## Next Steps

- Read the full [README.md](README.md) for detailed documentation
- Check [ARCHITECTURE.md](ARCHITECTURE.md) for system design details
- Configure notifications in Django Admin
- Set up multiple GitLab connections for different clients

## Troubleshooting

**MCP server not responding?**
- Check that migrations are applied: `python manage.py migrate`
- Verify all dependencies are installed: `pip install -r requirements.txt`

**GitLab OAuth fails?**
- Verify redirect URI in GitLab app settings matches exactly
- Check Client ID and Secret are correct

**AI model not working?**
- For Ollama: Ensure `ollama serve` is running
- For cloud providers: Verify API keys are correct and have credits

