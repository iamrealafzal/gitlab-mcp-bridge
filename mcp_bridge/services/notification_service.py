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

