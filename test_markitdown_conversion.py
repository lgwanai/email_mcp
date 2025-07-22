#!/usr/bin/env python3
"""Test HTML to Markdown conversion functionality without email server."""

import sys
import os
import tempfile
from markitdown import MarkItDown

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_html_to_markdown_conversion():
    """Test HTML to Markdown conversion using markitdown."""
    print("Testing HTML to Markdown conversion...")
    
    # Sample HTML content that might be found in emails
    test_html_samples = [
        {
            "name": "Simple HTML",
            "html": "<h1>Hello World</h1><p>This is a <strong>test</strong> email with <em>formatting</em>.</p>"
        },
        {
            "name": "HTML with links",
            "html": "<p>Visit our website at <a href='https://example.com'>example.com</a> for more information.</p>"
        },
        {
            "name": "HTML with list",
            "html": "<h2>Features:</h2><ul><li>Feature 1</li><li>Feature 2</li><li>Feature 3</li></ul>"
        },
        {
            "name": "Complex HTML",
            "html": """
            <html>
            <body>
                <h1>Newsletter</h1>
                <p>Dear Customer,</p>
                <p>We are excited to announce our <strong>new product</strong>!</p>
                <h2>Key Benefits:</h2>
                <ul>
                    <li>Easy to use</li>
                    <li>Cost effective</li>
                    <li>24/7 support</li>
                </ul>
                <p>For more information, visit <a href="https://example.com">our website</a>.</p>
                <p>Best regards,<br>The Team</p>
            </body>
            </html>
            """
        }
    ]
    
    md = MarkItDown()
    
    for i, sample in enumerate(test_html_samples, 1):
        print(f"\n=== Test {i}: {sample['name']} ===")
        print(f"Original HTML:")
        print(sample['html'][:100] + "..." if len(sample['html']) > 100 else sample['html'])
        
        try:
            # Create temporary HTML file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as tmp_file:
                tmp_file.write(sample['html'])
                tmp_file_path = tmp_file.name
            
            try:
                # Convert HTML to Markdown
                result = md.convert(tmp_file_path)
                markdown_content = result.text_content
                
                print(f"\nConverted Markdown:")
                print(markdown_content)
                print(f"\nConversion successful! Length: {len(markdown_content)} characters")
                
                # Check if conversion looks reasonable
                if len(markdown_content) > 0:
                    print("✓ Conversion produced content")
                else:
                    print("⚠ Conversion produced empty content")
                    
            finally:
                # Clean up temporary file
                os.unlink(tmp_file_path)
                
        except Exception as e:
            print(f"❌ Conversion failed: {e}")
        
        print("-" * 60)
    
    print("\n🎉 HTML to Markdown conversion test completed!")

def test_email_content_extraction_simulation():
    """Simulate the email content extraction process."""
    print("\n" + "=" * 60)
    print("Testing email content extraction simulation...")
    
    # Simulate different email content scenarios
    scenarios = [
        {
            "name": "Plain text email",
            "text_content": "Hello, this is a plain text email.\n\nBest regards,\nSender",
            "html_content": ""
        },
        {
            "name": "HTML email with fallback text",
            "text_content": "Hello, this is the text version.",
            "html_content": "<h1>Hello</h1><p>This is the <strong>HTML</strong> version.</p>"
        },
        {
            "name": "HTML-only email",
            "text_content": "",
            "html_content": "<div><h2>Important Notice</h2><p>This email only has HTML content.</p></div>"
        }
    ]
    
    md = MarkItDown()
    
    for i, scenario in enumerate(scenarios, 1):
        print(f"\n--- Scenario {i}: {scenario['name']} ---")
        
        text_content = scenario['text_content']
        html_content = scenario['html_content']
        
        # Simulate the logic from _extract_content method
        if html_content:
            try:
                # Create temporary HTML file
                with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as tmp_file:
                    tmp_file.write(html_content)
                    tmp_file_path = tmp_file.name
                
                try:
                    result = md.convert(tmp_file_path)
                    final_content = result.text_content
                    print(f"✓ Used HTML content converted to Markdown")
                finally:
                    os.unlink(tmp_file_path)
            except Exception as e:
                print(f"⚠ HTML conversion failed: {e}")
                final_content = text_content if text_content else html_content
                print(f"✓ Fallback to text content")
        else:
            final_content = text_content
            print(f"✓ Used plain text content")
        
        print(f"Final content length: {len(final_content)} characters")
        print(f"Content preview: {final_content[:100]}..." if len(final_content) > 100 else f"Content: {final_content}")
    
    print("\n🎉 Email content extraction simulation completed!")

if __name__ == "__main__":
    test_html_to_markdown_conversion()
    test_email_content_extraction_simulation()