#!/usr/bin/env python3
"""
Test script for email search functionality.
"""

import asyncio
import sys
import os
from datetime import datetime

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from email_client import EmailClient, EmailConfig

async def test_search_functionality():
    """Test the email search functionality."""
    print("Testing Email Search Functionality")
    print("=" * 50)
    
    # Test configuration (using dummy values for testing)
    config = EmailConfig(
        host="imap.example.com",
        port=993,
        username="test@example.com",
        password="dummy_password",
        use_ssl=True
    )
    
    # Test search criteria matching logic
    from email_client import ParsedEmail
    
    # Create sample email data for testing
    sample_email = ParsedEmail(
        uid="123",
        sender="john.doe@example.com",
        recipients=["jane.smith@example.com", "bob@company.com"],
        cc=["manager@company.com"],
        bcc=[],
        subject="Important Meeting Tomorrow",
        content="Please join us for the quarterly review meeting. We will discuss the project progress and future plans.",
        date=datetime.now(),
        attachments=[
            {"filename": "agenda.pdf", "content_type": "application/pdf", "size": 1024},
            {"filename": "presentation.pptx", "content_type": "application/vnd.openxmlformats-officedocument.presentationml.presentation", "size": 2048}
        ],
        raw_message=b"dummy"
    )
    
    # Create EmailClient instance for testing search criteria
    client = EmailClient(config)
    
    # Test different search types
    test_cases = [
        ("john", "sender", True, "Should find email by sender"),
        ("jane", "recipient", True, "Should find email by recipient"),
        ("manager", "cc", True, "Should find email by CC"),
        ("meeting", "subject", True, "Should find email by subject"),
        ("quarterly", "content", True, "Should find email by content"),
        ("agenda", "attachment", True, "Should find email by attachment name"),
        ("project", "all", True, "Should find email in all fields"),
        ("nonexistent", "sender", False, "Should not find non-existent keyword"),
        ("JOHN", "sender", True, "Should be case-insensitive"),
        ("john doe", "all", True, "Should handle multiple keywords"),
    ]
    
    print("Testing search criteria matching:")
    print("-" * 40)
    
    for keywords, search_type, expected, description in test_cases:
        keyword_list = [kw.strip() for kw in keywords.split() if kw.strip()]
        result = client._matches_search_criteria(sample_email, keyword_list, search_type)
        status = "✓ PASS" if result == expected else "✗ FAIL"
        print(f"{status}: {description}")
        print(f"  Keywords: '{keywords}', Type: {search_type}, Expected: {expected}, Got: {result}")
        if result != expected:
            print(f"  ERROR: Test failed for '{keywords}' in {search_type}")
    
    print("\nTesting email to dict conversion:")
    print("-" * 40)
    
    email_dict = client._email_to_dict(sample_email)
    expected_keys = ["uid", "sender", "recipients", "cc", "bcc", "subject", "content", "date", "attachments"]
    
    for key in expected_keys:
        if key in email_dict:
            print(f"✓ PASS: Key '{key}' present in email dict")
        else:
            print(f"✗ FAIL: Key '{key}' missing from email dict")
    
    print(f"\nEmail dict structure:")
    for key, value in email_dict.items():
        if key == "content":
            print(f"  {key}: {str(value)[:50]}...")
        elif key == "attachments":
            print(f"  {key}: {len(value)} attachments")
        else:
            print(f"  {key}: {value}")
    
    print("\n" + "=" * 50)
    print("Email search functionality tests completed!")
    print("Note: Full integration tests require actual email server connection.")

if __name__ == "__main__":
    asyncio.run(test_search_functionality())