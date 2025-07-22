#!/usr/bin/env python3
"""Test HTML to Markdown conversion functionality."""

import asyncio
import sys
import os
from datetime import datetime, timedelta

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from email_client import EmailClient, EmailConfig, EmailFilter

async def test_html_conversion():
    """Test HTML to Markdown conversion in email content."""
    print("Testing HTML to Markdown conversion...")
    
    # Create email configuration (you may need to update these values)
    email_config = EmailConfig(
        host="imap.gmail.com",  # Update with your email server
        port=993,
        use_ssl=True,
        username="your_email@gmail.com",  # Update with your email
        password="your_password"  # Update with your password
    )
    
    print("Note: Please update the email configuration in the test script with your actual credentials.")
    print("Skipping actual email fetch for security reasons...")
    return
    
    # Create email client
    client = EmailClient(email_config)
    
    try:
        # Connect to email server
        await client.connect()
        print("Connected to email server")
        
        # Define filter for recent emails
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)
        
        email_filter = EmailFilter(
            folder="INBOX",
            start_date=start_date,
            end_date=end_date,
            limit=5,
            reverse_order=True  # Get newest first
        )
        
        # Fetch emails
        print(f"Fetching emails from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}...")
        emails = await client.fetch_emails(email_filter)
        
        print(f"Found {len(emails)} emails")
        
        # Display email content to verify HTML conversion
        for i, email in enumerate(emails, 1):
            print(f"\n=== Email {i} ===")
            print(f"From: {email.sender}")
            print(f"Subject: {email.subject}")
            print(f"Date: {email.date}")
            print(f"Content length: {len(email.content)} characters")
            
            # Show first 200 characters of content
            content_preview = email.content[:200] if email.content else "(No content)"
            print(f"Content preview: {content_preview}...")
            
            # Check if content looks like markdown (contains markdown syntax)
            has_markdown_syntax = any(marker in email.content for marker in ['**', '*', '#', '`', '[', ']', '(', ')']) if email.content else False
            print(f"Contains markdown syntax: {has_markdown_syntax}")
            
            print("-" * 50)
        
        print("\nHTML to Markdown conversion test completed successfully!")
        
    except Exception as e:
        print(f"Error during test: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Disconnect from email server
        await client.disconnect()
        print("Disconnected from email server")

if __name__ == "__main__":
    asyncio.run(test_html_conversion())