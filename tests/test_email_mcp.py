import unittest
import asyncio
import json
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime

# Mock FastMCP before importing EmailMCPServer because it uses decorators
class MockFastMCP:
    def __init__(self, name=None):
        self.tools = {}
    
    def tool(self):
        def decorator(func):
            self.tools[func.__name__] = func
            return func
        return decorator
    
    def run(self, *args, **kwargs):
        pass

# Patch fastmcp module
import sys
sys.modules['fastmcp'] = MagicMock()
sys.modules['fastmcp'].FastMCP = MockFastMCP

from src.email_mcp import EmailMCPServer
from src.email_client import ParsedEmail

class TestEmailMCPServer(unittest.TestCase):
    def setUp(self):
        # Mock dependencies
        self.mock_index_service = AsyncMock()
        self.mock_config_manager = MagicMock()
        self.mock_attachment_manager = AsyncMock()
        
        # Patch dependencies in EmailMCPServer
        with patch('src.email_mcp.EmailIndexService', return_value=self.mock_index_service), \
             patch('src.email_mcp.ConfigManager', return_value=self.mock_config_manager), \
             patch('src.email_mcp.AttachmentManager', return_value=self.mock_attachment_manager):
            
            self.server = EmailMCPServer(attachments_dir="/tmp/test_attachments")
            
        # Helper to get tool function
        self.tools = self.server.mcp.tools
        
        # Setup default account config
        self.mock_account_config = MagicMock()
        self.mock_account_config.email_address = "test@example.com"
        self.mock_config_manager.get_account_config.return_value = self.mock_account_config
        self.mock_config_manager.get_default_account.return_value = self.mock_account_config

    def test_list_emails(self):
        """Test list_emails tool."""
        # Setup mock return
        self.mock_index_service.list_emails.return_value = [
            {
                "uid": "1",
                "subject": "Test Subject",
                "sender": "sender@example.com",
                "date": "2023-01-01T12:00:00",
                "snippet": "Test Snippet",
                "has_attachments": 0
            }
        ]
        
        # Run tool
        result = asyncio.run(self.tools['list_emails'](
            email_address="test@example.com",
            folder="INBOX"
        ))
        
        # Verify
        self.mock_index_service.list_emails.assert_called_once()
        emails = result['data']
        
        self.assertEqual(len(emails), 1)
        self.assertEqual(emails[0]['uid'], "1")
        self.assertEqual(emails[0]['subject'], "Test Subject")

    @patch('src.email_mcp.EmailClientFactory')
    def test_fetch_emails_cache_hit(self, mock_client_factory):
        """Test fetch_emails when data is in DB."""
        # Setup sync state to indicate index exists
        self.mock_index_service.get_sync_state.return_value = {"last_seen_uid": "100"}
        
        # Setup DB return with body
        self.mock_index_service.list_emails.return_value = [
            {
                "uid": "1",
                "sender": "sender@example.com",
                "recipients": '["me@example.com"]',
                "cc": '[]',
                "subject": "Test",
                "body": "Test Body",
                "date": "2023-01-01T12:00:00",
                "attachment_names_json": '[]',
                "snippet": "Test",
                "has_attachments": 0
            }
        ]
        
        # Run tool
        result = asyncio.run(self.tools['fetch_emails'](
            email_address="test@example.com",
            limit=1
        ))
        
        # Verify
        self.mock_index_service.list_emails.assert_called_once()
        # Should NOT call IMAP client
        mock_client_factory.create_client.assert_not_called()
        
        # fetch_emails uses format_email_response which returns dict with 'emails' directly
        self.assertIn("emails", result)
        self.assertEqual(len(result["emails"]), 1)
        self.assertEqual(result["emails"][0]["content"], "Test Body")
        self.assertEqual(result["source"], "db")

    @patch('src.email_mcp.EmailClientFactory')
    def test_fetch_emails_cache_miss_body(self, mock_client_factory):
        """Test fetch_emails when DB has header but no body."""
        self.mock_index_service.get_sync_state.return_value = {"last_seen_uid": "100"}
        
        # DB returns row with body=None
        self.mock_index_service.list_emails.return_value = [
            {
                "uid": "1",
                "sender": "sender@example.com",
                "recipients": '["me@example.com"]',
                "cc": '[]',
                "subject": "Test",
                "body": None, # Missing body
                "date": "2023-01-01T12:00:00",
                "attachment_names_json": '[]',
                "snippet": "Test",
                "has_attachments": 0
            }
        ]
        
        # Mock IMAP client for body fetch
        mock_client = AsyncMock()
        mock_client_factory.create_client.return_value = mock_client
        mock_client._fetch_and_parse_email.return_value = ParsedEmail(
            uid="1", sender="sender", recipients=[], cc=[], bcc=[], 
            subject="Test", content="Fetched Body", date=datetime.now(), 
            attachments=[], raw_message=b""
        )
        
        # Run tool
        result = asyncio.run(self.tools['fetch_emails'](
            email_address="test@example.com",
            limit=1
        ))
        
        # Verify
        mock_client._fetch_and_parse_email.assert_called_with("1")
        self.mock_index_service.update_email_body.assert_called_with(
            "test@example.com", "INBOX", "1", "Fetched Body"
        )
        
        self.assertEqual(result["emails"][0]["content"], "Fetched Body")

    @patch('src.email_mcp.EmailClientFactory')
    def test_search_emails_fts(self, mock_client_factory):
        """Test search_emails using FTS."""
        self.mock_index_service.get_sync_state.return_value = {"last_seen_uid": "100"}
        
        self.mock_index_service.search_emails.return_value = [
            {
                "uid": "1",
                "sender": "sender@example.com",
                "recipients": '[]',
                "cc": '[]',
                "subject": "Found It",
                "body": "Content",
                "snippet": "Snippet",
                "date": "2023-01-01T12:00:00",
                "attachment_names_json": '[]'
            }
        ]
        
        result = asyncio.run(self.tools['search_emails'](
            keywords="Found"
        ))
        
        self.mock_index_service.search_emails.assert_called()
        self.assertEqual(result['data']['emails'][0]['subject'], "Found It")
        self.assertEqual(result['data']['source'], "db")

    @patch('src.email_mcp.EmailClientFactory')
    def test_sync_email_index(self, mock_client_factory):
        """Test manual sync trigger."""
        mock_client = AsyncMock()
        mock_client_factory.create_client.return_value = mock_client
        
        result = asyncio.run(self.tools['sync_email_index'](
            email_address="test@example.com",
            mode="incremental"
        ))
        
        self.mock_index_service.sync_incremental.assert_called_with(mock_client, "INBOX")
        self.assertEqual(result['data']['status'], "completed")

    @patch('src.email_mcp.EmailClientFactory')
    def test_send_email(self, mock_client_factory):
        """Test send_email tool."""
        mock_client = AsyncMock()
        mock_client_factory.create_client.return_value = mock_client
        mock_client.send_email.return_value = True
        
        # Setup config for sender
        self.mock_config_manager.get_account_config.return_value = self.mock_account_config
        self.mock_account_config.smtp_host = "smtp.example.com"
        self.mock_account_config.smtp_port = 587
        
        result = asyncio.run(self.tools['send_email'](
            from_address="test@example.com",
            to_addresses="recipient@example.com",
            subject="Test Subject",
            body="Test Body"
        ))
        
        mock_client.send_email.assert_called_once()
        self.assertEqual(result['status'], "success")
        self.assertIn("sent_at", result['data'])

if __name__ == '__main__':
    unittest.main()
