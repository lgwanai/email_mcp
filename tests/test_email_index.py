import unittest
import asyncio
import shutil
import tempfile
import os
from datetime import datetime
from unittest.mock import MagicMock, AsyncMock

from src.email_index_service import EmailIndexService, IndexedEmail
from src.email_client import ParsedEmail

class TestEmailIndexService(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.test_dir, "test_index.db")
        self.service = EmailIndexService(self.db_path)
        
    def tearDown(self):
        shutil.rmtree(self.test_dir)
        
    def test_init_db(self):
        """Test database initialization."""
        conn = self.service._get_connection()
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        self.assertIn('emails', tables)
        self.assertIn('sync_state', tables)
        self.assertIn('emails_fts', tables)
        conn.close()
        
    def test_save_and_list_emails(self):
        """Test saving and listing emails."""
        emails = [
            IndexedEmail(
                uid="1", account="test@example.com", folder="INBOX",
                date=datetime(2023, 1, 1), sender="sender@example.com",
                recipients=["me@example.com"], cc=[], subject="Test 1",
                snippet="Snippet 1", has_attachments=False, attachment_names=[],
                body="Body 1", flags=[]
            ),
            IndexedEmail(
                uid="2", account="test@example.com", folder="INBOX",
                date=datetime(2023, 1, 2), sender="sender@example.com",
                recipients=["me@example.com"], cc=[], subject="Test 2",
                snippet="Snippet 2", has_attachments=True, attachment_names=["file.txt"],
                body=None, flags=[]
            )
        ]
        
        asyncio.run(self.service.save_emails(emails))
        
        # List all
        result = asyncio.run(self.service.list_emails("test@example.com", "INBOX"))
        self.assertEqual(len(result), 2)
        # reverse_order=True default, sort by UID DESC. "2" > "1". So "2" should be first.
        self.assertEqual(result[0]['uid'], "2")
        self.assertEqual(result[1]['uid'], "1")
        
        # Test pagination
        result = asyncio.run(self.service.list_emails("test@example.com", "INBOX", limit=1))
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['uid'], "2")
        
        # Test start_uid
        result = asyncio.run(self.service.list_emails("test@example.com", "INBOX", start_uid="2"))
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['uid'], "1")

    def test_search_emails(self):
        """Test FTS search."""
        emails = [
            IndexedEmail(
                uid="1", account="test@example.com", folder="INBOX",
                date=datetime(2023, 1, 1), sender="alice@example.com",
                recipients=["me@example.com"], cc=[], subject="Hello World",
                snippet="This is a test", has_attachments=False, attachment_names=[],
                body="Some body content", flags=[]
            ),
            IndexedEmail(
                uid="2", account="test@example.com", folder="INBOX",
                date=datetime(2023, 1, 2), sender="bob@example.com",
                recipients=["me@example.com"], cc=[], subject="Urgent Meeting",
                snippet="Please reply", has_attachments=False, attachment_names=[],
                body="Important stuff", flags=[]
            )
        ]
        asyncio.run(self.service.save_emails(emails))
        
        # Search "Hello"
        result = asyncio.run(self.service.search_emails("test@example.com", "Hello"))
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['uid'], "1")
        
        # Search "Important"
        result = asyncio.run(self.service.search_emails("test@example.com", "Important"))
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['uid'], "2")

    def test_sync_state(self):
        """Test sync state operations."""
        asyncio.run(self.service.update_sync_state("test@example.com", "INBOX", "100", "12345"))
        
        state = asyncio.run(self.service.get_sync_state("test@example.com", "INBOX"))
        self.assertEqual(state['last_seen_uid'], "100")
        self.assertEqual(state['uidvalidity'], "12345")
        
        # Update without uidvalidity
        asyncio.run(self.service.update_sync_state("test@example.com", "INBOX", "101"))
        state = asyncio.run(self.service.get_sync_state("test@example.com", "INBOX"))
        self.assertEqual(state['last_seen_uid'], "101")
        self.assertEqual(state['uidvalidity'], "12345") # Preserved

if __name__ == '__main__':
    unittest.main()
