#!/usr/bin/env python3
"""Test HTML cleaning functionality with and without markitdown."""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.email_client import EmailClient, EmailConfig
from email.message import EmailMessage

def test_html_cleaning():
    """Test HTML cleaning functionality."""
    
    # Create a dummy email client for testing
    config = EmailConfig(
        host="test.example.com",
        username="test@example.com",
        password="test_password"
    )
    client = EmailClient(config)
    
    # Test HTML content samples
    test_cases = [
        {
            "name": "Simple HTML with headers and paragraphs",
            "html": """
            <html>
            <body>
                <h1>Welcome to Our Newsletter</h1>
                <h2>Latest Updates</h2>
                <p>This is a <strong>bold</strong> statement with <em>italic</em> text.</p>
                <p>Visit our <a href="https://example.com">website</a> for more information.</p>
            </body>
            </html>
            """,
            "text": "Welcome to Our Newsletter\nLatest Updates\nThis is a bold statement with italic text.\nVisit our website for more information."
        },
        {
            "name": "HTML with lists and images",
            "html": """
            <div>
                <h3>Features:</h3>
                <ul>
                    <li>Easy to use</li>
                    <li>Fast performance</li>
                    <li>Secure</li>
                </ul>
                <img src="https://example.com/image.jpg" alt="Product Image" />
                <br/>
                <p>Contact us at <code>support@example.com</code></p>
            </div>
            """,
            "text": "Features: Easy to use, Fast performance, Secure. Contact us at support@example.com"
        },
        {
            "name": "Complex HTML with table and blockquote",
            "html": """
            <html>
            <head><style>body { font-family: Arial; }</style></head>
            <body>
                <blockquote>
                    <p>"Innovation distinguishes between a leader and a follower."</p>
                </blockquote>
                <table>
                    <tr>
                        <th>Name</th>
                        <th>Email</th>
                    </tr>
                    <tr>
                        <td>John Doe</td>
                        <td>john@example.com</td>
                    </tr>
                </table>
                <pre><code>def hello():\n    print("Hello World")</code></pre>
                <script>alert('test');</script>
            </body>
            </html>
            """,
            "text": "Innovation quote, Name: John Doe, Email: john@example.com, Python code example"
        },
        {
            "name": "HTML with entities",
            "html": """
            <p>Price: $100 &amp; up</p>
            <p>&ldquo;Hello&rdquo; &mdash; she said.</p>
            <p>Copyright &copy; 2024</p>
            <p>Spaces&nbsp;&nbsp;&nbsp;here</p>
            """,
            "text": "Price: $100 & up. Hello - she said. Copyright 2024. Spaces here."
        }
    ]
    
    print("=" * 60)
    print("Testing HTML Cleaning Functionality")
    print("=" * 60)
    
    # Check if markitdown is available
    try:
        from markitdown import MarkItDown
        markitdown_available = True
        print("✓ markitdown library is available")
    except ImportError:
        markitdown_available = False
        print("✗ markitdown library is NOT available")
    
    print(f"\nTesting with markitdown {'enabled' if markitdown_available else 'disabled'}...\n")
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"Test {i}: {test_case['name']}")
        print("-" * 40)
        
        # Create a mock email message
        email_msg = EmailMessage()
        email_msg.set_content(test_case['text'])
        email_msg.add_alternative(test_case['html'], subtype='html')
        
        # Test the content extraction
        try:
            result = client._extract_content(email_msg)
            
            print(f"Original HTML length: {len(test_case['html'])} characters")
            print(f"Cleaned content length: {len(result)} characters")
            print("\nCleaned content:")
            print(result[:200] + "..." if len(result) > 200 else result)
            print("\n" + "=" * 60 + "\n")
            
        except Exception as e:
            print(f"❌ Error processing test case: {e}")
            print("\n" + "=" * 60 + "\n")
    
    # Test custom HTML cleaning directly
    print("Testing custom HTML cleaning method directly...\n")
    
    simple_html = "<p>This is <strong>bold</strong> and <em>italic</em> text with a <a href='#'>link</a>.</p>"
    cleaned = client._clean_html_content(simple_html)
    print(f"Input: {simple_html}")
    print(f"Output: {cleaned}")
    
    print("\n" + "=" * 60)
    print("HTML Cleaning Test Complete!")
    print("=" * 60)

if __name__ == "__main__":
    test_html_cleaning()