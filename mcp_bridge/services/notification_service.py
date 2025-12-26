"""
Notification Service for Slack and Microsoft Teams
"""
import requests
import json
from typing import Dict, Optional, Any
from ..models import NotificationChannel, NotificationRule
import logging

logger = logging.getLogger(__name__)


class NotificationService:
    """Service for sending notifications to Slack and Teams"""
    
    def __init__(self, channel: NotificationChannel):
        self.channel = channel
    
    def send_notification(
        self,
        title: str,
        message: str,
        error_details: Optional[Dict[str, Any]] = None,
        fix_suggestion: Optional[str] = None
    ) -> bool:
        """
        Send a notification to the configured channel
        
        Args:
            title: Notification title
            message: Main notification message
            error_details: Optional error details dict
            fix_suggestion: Optional fix suggestion text
        
        Returns:
            True if sent successfully, False otherwise
        """
        if self.channel.channel_type == 'slack':
            return self._send_slack(title, message, error_details, fix_suggestion)
        elif self.channel.channel_type == 'teams':
            return self._send_teams(title, message, error_details, fix_suggestion)
        else:
            logger.warning(f"Unsupported channel type: {self.channel.channel_type}")
            return False
    
    def _send_slack(
        self,
        title: str,
        message: str,
        error_details: Optional[Dict[str, Any]],
        fix_suggestion: Optional[str]
    ) -> bool:
        """Send notification to Slack via webhook"""
        try:
            webhook_url = self.channel.webhook_url
            
            # Build Slack message blocks
            blocks = [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": title,
                        "emoji": True
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": message
                    }
                }
            ]
            
            # Add error details if available
            if error_details:
                error_text = f"*Error Type:* {error_details.get('type', 'Unknown')}\n"
                if 'file_path' in error_details:
                    error_text += f"*File:* `{error_details['file_path']}`\n"
                if 'line_number' in error_details:
                    error_text += f"*Line:* {error_details['line_number']}\n"
                if 'raw_line' in error_details:
                    error_text += f"*Error:* `{error_details['raw_line'][:200]}`"
                
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": error_text
                    }
                })
            
            # Add fix suggestion if available
            if fix_suggestion:
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Suggested Fix:*\n```{fix_suggestion[:1000]}```"
                    }
                })
            
            payload = {
                "blocks": blocks
            }
            
            response = requests.post(webhook_url, json=payload, timeout=10)
            response.raise_for_status()
            
            logger.info(f"Slack notification sent successfully to {self.channel.name}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending Slack notification: {e}")
            return False
    
    def _send_teams(
        self,
        title: str,
        message: str,
        error_details: Optional[Dict[str, Any]],
        fix_suggestion: Optional[str]
    ) -> bool:
        """Send notification to Microsoft Teams via webhook"""
        try:
            webhook_url = self.channel.webhook_url
            
            # Build Teams adaptive card
            facts = [
                {"name": "Title", "value": title},
                {"name": "Message", "value": message}
            ]
            
            if error_details:
                if 'file_path' in error_details:
                    facts.append({"name": "File", "value": error_details['file_path']})
                if 'line_number' in error_details:
                    facts.append({"name": "Line", "value": str(error_details['line_number'])})
            
            card = {
                "@type": "MessageCard",
                "@context": "https://schema.org/extensions",
                "summary": title,
                "themeColor": "0078D4",
                "title": title,
                "sections": [
                    {
                        "activityTitle": "GitLab MCP Bridge",
                        "facts": facts,
                        "text": message
                    }
                ]
            }
            
            if fix_suggestion:
                card["sections"].append({
                    "title": "Suggested Fix",
                    "text": fix_suggestion[:2000]
                })
            
            payload = card
            
            response = requests.post(webhook_url, json=payload, timeout=10)
            response.raise_for_status()
            
            logger.info(f"Teams notification sent successfully to {self.channel.name}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending Teams notification: {e}")
            return False
    
    @staticmethod
    def send_for_rule(
        rule: NotificationRule,
        title: str,
        message: str,
        error_details: Optional[Dict[str, Any]] = None,
        fix_suggestion: Optional[str] = None
    ) -> bool:
        """Send notification based on a notification rule"""
        if not rule.is_active:
            return False
        
        service = NotificationService(rule.channel)
        return service.send_notification(title, message, error_details, fix_suggestion)
    
    @staticmethod
    def trigger_notifications(
        trigger_type: str,
        title: str,
        message: str,
        error_details: Optional[Dict[str, Any]] = None,
        fix_suggestion: Optional[str] = None
    ):
        """Trigger all active notifications for a given trigger type"""
        rules = NotificationRule.objects.filter(
            trigger_type=trigger_type,
            is_active=True
        )
        
        results = []
        for rule in rules:
            success = NotificationService.send_for_rule(
                rule, title, message, error_details, fix_suggestion
            )
            results.append((rule.name, success))
        
        return results
    
    @staticmethod
    def send_to_power_automate(
        webhook_url: str,
        error_analyzed: Dict[str, Any],
        fix_suggestion: Dict[str, Any],
        repository_name: Optional[str] = None,
        log_file_path: Optional[str] = None
    ) -> bool:
        """
        Send formatted fix suggestion to Power Automate webhook (Teams)
        
        Args:
            webhook_url: Power Automate webhook URL
            error_analyzed: Error details dict from generate_fix
            fix_suggestion: Fix suggestion dict from generate_fix
            repository_name: Optional repository name
            log_file_path: Optional log file path
            
        Returns:
            True if sent successfully, False otherwise
        """
        try:
            # Clean up URL - remove escaped backslashes and decode URL-encoded backslashes
            # Remove literal backslashes before special characters
            webhook_url = webhook_url.replace('\\?', '?').replace('\\&', '&').replace('\\=', '=')
            # Remove URL-encoded backslashes (%5C) - they shouldn't be in URLs
            webhook_url = webhook_url.replace('%5C', '')
            
            # Format the error details
            error_type = error_analyzed.get('type', 'Unknown')
            file_path = error_analyzed.get('file_path', 'N/A')
            line_number = error_analyzed.get('line_number', 'N/A')
            raw_line = error_analyzed.get('raw_line', 'N/A')
            
            # Extract fix suggestion text
            suggestion_text = fix_suggestion.get('suggestion', 'No suggestion available')
            model_used = fix_suggestion.get('model', 'Unknown')
            provider = fix_suggestion.get('provider', 'Unknown')
            
            # Build title
            title = f"🔧 Fix Suggestion Generated - {file_path}"
            if line_number != 'N/A':
                title += f" (Line {line_number})"
            
            # Build message with formatted content
            message_parts = [
                f"**Repository:** {repository_name or 'N/A'}",
                f"**Log File:** {log_file_path or 'N/A'}",
                "",
                "### Error Details",
                f"- **Type:** {error_type}",
                f"- **File:** `{file_path}`",
                f"- **Line:** {line_number}",
                f"- **Error:** `{raw_line[:200]}`",
                "",
                "### Fix Suggestion",
                "",
            ]
            
            # Add the suggestion (format code blocks nicely)
            suggestion_lines = suggestion_text.split('\n')
            formatted_suggestion = []
            in_code_block = False
            
            for line in suggestion_lines:
                if line.strip().startswith('```'):
                    in_code_block = not in_code_block
                    formatted_suggestion.append(line)
                elif in_code_block:
                    formatted_suggestion.append(line)
                else:
                    formatted_suggestion.append(line)
            
            message_parts.append('\n'.join(formatted_suggestion))
            message_parts.append("")
            message_parts.append(f"**Generated by:** {provider} ({model_used})")
            
            message = '\n'.join(message_parts)
            
            # Build Adaptive Card for Power Automate
            # Power Automate expects Adaptive Card v1.0+ format
            adaptive_card = {
                "type": "AdaptiveCard",
                "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                "version": "1.4",
                "body": [
                    {
                        "type": "TextBlock",
                        "text": title,
                        "weight": "Bolder",
                        "size": "Large",
                        "wrap": True
                    },
                    {
                        "type": "FactSet",
                        "facts": [
                            {
                                "title": "Repository:",
                                "value": repository_name or 'N/A'
                            },
                            {
                                "title": "Error Type:",
                                "value": error_type
                            },
                            {
                                "title": "File:",
                                "value": file_path
                            },
                            {
                                "title": "Line:",
                                "value": str(line_number)
                            },
                            {
                                "title": "Model:",
                                "value": f"{provider} ({model_used})"
                            }
                        ]
                    },
                    {
                        "type": "TextBlock",
                        "text": "**Error Details**",
                        "weight": "Bolder",
                        "size": "Medium",
                        "wrap": True,
                        "separator": True
                    },
                    {
                        "type": "TextBlock",
                        "text": f"`{raw_line[:200]}`",
                        "wrap": True,
                        "fontType": "Monospace"
                    },
                    {
                        "type": "TextBlock",
                        "text": "**Fix Suggestion**",
                        "weight": "Bolder",
                        "size": "Medium",
                        "wrap": True,
                        "separator": True
                    },
                    {
                        "type": "TextBlock",
                        "text": suggestion_text[:4000],  # Limit to 4000 chars for Teams
                        "wrap": True
                    }
                ]
            }
            
            # Power Automate webhook might expect the card in different formats
            # Try sending as direct adaptive card first
            payload = {
                "type": "message",
                "attachments": [
                    {
                        "contentType": "application/vnd.microsoft.card.adaptive",
                        "content": adaptive_card
                    }
                ]
            }
            
            # Send to Power Automate webhook
            # Try adaptive card format first
            try:
                response = requests.post(webhook_url, json=payload, timeout=30)
                response.raise_for_status()
                logger.info(f"Power Automate notification sent successfully")
                return True
            except requests.exceptions.HTTPError as e:
                # If adaptive card format fails, try sending just the data
                # Power Automate flow can construct the card itself
                if response.status_code == 400:
                    logger.warning(f"Adaptive card format failed, trying simple data format: {e}")
                    simple_payload = {
                        "title": title,
                        "repository": repository_name or 'N/A',
                        "error_type": error_type,
                        "file_path": file_path,
                        "line_number": str(line_number),
                        "raw_line": raw_line[:500],
                        "suggestion": suggestion_text[:4000],
                        "model": model_used,
                        "provider": provider,
                        "log_file": log_file_path or 'N/A'
                    }
                    response = requests.post(webhook_url, json=simple_payload, timeout=30)
                    response.raise_for_status()
                    logger.info(f"Power Automate notification sent successfully (simple format)")
                    return True
                else:
                    raise
            
        except Exception as e:
            logger.error(f"Error sending Power Automate notification: {e}")
            return False

