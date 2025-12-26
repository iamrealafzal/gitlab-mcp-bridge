#!/usr/bin/env python
"""
Script to send fix suggestion to Teams via Power Automate webhook
Usage:
    python send_to_teams.py <webhook_url> <json_output_file>
    OR
    echo '{"error_analyzed": {...}, "fix_suggestion": {...}}' | python send_to_teams.py <webhook_url>
"""
import json
import sys
import requests
import os

# Add the project directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gitlab_mcp_bridge.settings')
import django
django.setup()

from mcp_bridge.services.notification_service import NotificationService


def format_and_send(webhook_url: str, data: dict, repository_name: str = None, log_file_path: str = None):
    """Format and send notification to Teams"""
    # Extract data from the JSON structure
    error_analyzed = data.get('error_analyzed', {})
    fix_suggestion = data.get('fix_suggestion', {})
    
    if not error_analyzed or not fix_suggestion:
        print("Error: Missing 'error_analyzed' or 'fix_suggestion' in JSON data")
        return False
    
    # Send to Teams
    success = NotificationService.send_to_power_automate(
        webhook_url=webhook_url,
        error_analyzed=error_analyzed,
        fix_suggestion=fix_suggestion,
        repository_name=repository_name,
        log_file_path=log_file_path
    )
    
    return success


def main():
    if len(sys.argv) < 2:
        print("Usage: python send_to_teams.py <webhook_url> [json_file] [repository_name] [log_file_path]")
        print("\nExample:")
        print("  python send_to_teams.py 'https://...' output.json 'embibe-treasure_test_app_api' 'logs/mixed_errors.log'")
        print("\nOr pipe JSON directly:")
        print("  echo '{\"error_analyzed\": {...}, \"fix_suggestion\": {...}}' | python send_to_teams.py 'https://...'")
        sys.exit(1)
    
    webhook_url = sys.argv[1]
    # Clean up URL - remove escaped backslashes that might come from shell escaping
    # Remove literal backslashes before special characters
    webhook_url = webhook_url.replace('\\?', '?').replace('\\&', '&').replace('\\=', '=')
    # Remove URL-encoded backslashes (%5C) - they shouldn't be in URLs
    webhook_url = webhook_url.replace('%5C', '')
    
    # Read JSON from file or stdin
    # Check if stdin is available (piped input) or if file argument is empty
    is_piped = not sys.stdin.isatty()
    has_file_arg = len(sys.argv) >= 3 and sys.argv[2] and sys.argv[2].strip()
    
    if has_file_arg and not is_piped:
        # Read from file
        json_file = sys.argv[2]
        try:
            with open(json_file, 'r') as f:
                file_content = f.read()
        except FileNotFoundError:
            print(f"Error: File not found: {json_file}")
            sys.exit(1)
        
        # Try to find JSON in the file (might have warnings before JSON)
        # Look for the first line that starts with { or [
        lines = file_content.split('\n')
        json_start = None
        for i, line in enumerate(lines):
            line = line.strip()
            if line.startswith('{') or line.startswith('['):
                json_start = i
                break
        
        if json_start is not None:
            # Try to parse from the JSON start
            json_content = '\n'.join(lines[json_start:])
            try:
                data = json.loads(json_content)
            except json.JSONDecodeError:
                # If that fails, try parsing the whole file
                try:
                    data = json.loads(file_content)
                except json.JSONDecodeError as e:
                    print(f"Error: Invalid JSON in file: {e}")
                    print(f"First 200 chars: {file_content[:200]}")
                    sys.exit(1)
        else:
            # No JSON found, try parsing whole file
            try:
                data = json.loads(file_content)
            except json.JSONDecodeError as e:
                print(f"Error: No valid JSON found in file: {e}")
                print(f"First 200 chars: {file_content[:200]}")
                sys.exit(1)
    else:
        # Read from stdin (piped input)
        input_data = sys.stdin.read()
        if not input_data.strip():
            print("Error: No JSON data provided via stdin")
            sys.exit(1)
        
        # Try to find JSON in the input (might have warnings before JSON)
        lines = input_data.split('\n')
        json_start = None
        for i, line in enumerate(lines):
            line = line.strip()
            if line.startswith('{') or line.startswith('['):
                json_start = i
                break
        
        if json_start is not None:
            json_content = '\n'.join(lines[json_start:])
            try:
                data = json.loads(json_content)
            except json.JSONDecodeError:
                # If that fails, try parsing the whole input
                try:
                    data = json.loads(input_data)
                except json.JSONDecodeError as e:
                    print(f"Error: Invalid JSON in input: {e}")
                    sys.exit(1)
        else:
            try:
                data = json.loads(input_data)
            except json.JSONDecodeError as e:
                print(f"Error: Invalid JSON in input: {e}")
                sys.exit(1)
    
    # Extract repository name and log file path if provided
    # Skip empty arguments
    args = [arg for arg in sys.argv[3:] if arg and arg.strip()]
    repository_name = args[0] if len(args) >= 1 else None
    log_file_path = args[1] if len(args) >= 2 else None
    
    # If data is wrapped in a result structure (from MCP output)
    if 'result' in data and 'content' in data['result']:
        # Extract from MCP JSON-RPC response
        try:
            content_list = data['result']['content']
            if content_list and len(content_list) > 0:
                content = content_list[0].get('text', '')
                if content:
                    try:
                        data = json.loads(content)
                    except json.JSONDecodeError as e:
                        print(f"Error: Failed to parse JSON from MCP response text field: {e}")
                        print(f"Content preview: {content[:200]}")
                        sys.exit(1)
                else:
                    print("Error: MCP response content[0].text is empty")
                    sys.exit(1)
            else:
                print("Error: MCP response content list is empty")
                sys.exit(1)
        except (KeyError, IndexError, TypeError) as e:
            print(f"Error: Unexpected MCP response structure: {e}")
            print(f"Response keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
            sys.exit(1)
    
    # Send notification
    success = format_and_send(webhook_url, data, repository_name, log_file_path)
    
    if success:
        print("✅ Notification sent successfully to Teams!")
    else:
        print("❌ Failed to send notification")
        sys.exit(1)


if __name__ == '__main__':
    main()

