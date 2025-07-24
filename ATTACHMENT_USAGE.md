# Email Attachment Usage Guide

## Overview

The Email MCP Server now supports sending emails with attachments. This guide explains how to use the attachment functionality.

## Features

✅ **Multiple Attachments**: Send multiple files in a single email  
✅ **File Validation**: Automatic validation of file paths and existence  
✅ **MIME Type Detection**: Automatic detection of file types  
✅ **Size Limits**: Maximum 25MB per attachment  
✅ **Error Handling**: Comprehensive error handling and validation  

## Usage

### MCP Tool: `send_email`

```json
{
  "tool": "send_email",
  "arguments": {
    "from_address": "sender@example.com",
    "to_addresses": "recipient1@example.com,recipient2@example.com",
    "subject": "Email with Attachments",
    "body": "Please find the attached files.",
    "cc_addresses": "cc@example.com",
    "bcc_addresses": "bcc@example.com",
    "html_body": "<p>Please find the <strong>attached files</strong>.</p>",
    "attachment_paths": [
      "/absolute/path/to/document.pdf",
      "/absolute/path/to/spreadsheet.xlsx",
      "/absolute/path/to/image.png"
    ]
  }
}
```

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `from_address` | string | ✅ | Sender email address (must be configured) |
| `to_addresses` | string | ✅ | Recipient email addresses (comma-separated) |
| `subject` | string | ✅ | Email subject |
| `body` | string | ✅ | Email body (plain text) |
| `cc_addresses` | string | ❌ | CC email addresses (comma-separated) |
| `bcc_addresses` | string | ❌ | BCC email addresses (comma-separated) |
| `html_body` | string | ❌ | Email body in HTML format |
| `attachment_paths` | array | ❌ | List of absolute file paths to attach |

### Attachment Requirements

1. **File Paths**: Must be absolute paths to existing files
2. **File Size**: Maximum 25MB per attachment
3. **File Types**: All file types supported (MIME type auto-detected)
4. **File Validation**: Files must exist and be readable

### Response Format

```json
{
  "success": true,
  "message": "Email sent successfully to recipient1@example.com, recipient2@example.com with 3 attachment(s)",
  "data": {
    "request_id": "send_20250124_061141_123456",
    "from_address": "sender@example.com",
    "to_addresses": ["recipient1@example.com", "recipient2@example.com"],
    "cc_addresses": ["cc@example.com"],
    "bcc_addresses": ["bcc@example.com"],
    "subject": "Email with Attachments",
    "sent_at": "2025-01-24T06:11:41.123456",
    "smtp_server": "smtp.example.com:587",
    "attachments": [
      {
        "path": "/absolute/path/to/document.pdf",
        "filename": "document.pdf",
        "size": 1024000
      },
      {
        "path": "/absolute/path/to/spreadsheet.xlsx",
        "filename": "spreadsheet.xlsx",
        "size": 512000
      },
      {
        "path": "/absolute/path/to/image.png",
        "filename": "image.png",
        "size": 256000
      }
    ],
    "attachment_count": 3
  }
}
```

## Error Handling

### Common Errors

1. **File Not Found**
   ```json
   {
     "success": false,
     "error": "Attachment file not found: /path/to/missing/file.pdf"
   }
   ```

2. **Invalid File Path**
   ```json
   {
     "success": false,
     "error": "Attachment path is not a file: /path/to/directory"
   }
   ```

3. **File Too Large**
   ```json
   {
     "success": false,
     "error": "Attachment file too large: /path/to/large/file.zip (30MB > 25MB limit)"
   }
   ```

4. **Permission Denied**
   ```json
   {
     "success": false,
     "error": "Permission denied reading attachment: /path/to/protected/file.pdf"
   }
   ```

## Examples

### Simple Email with One Attachment

```json
{
  "tool": "send_email",
  "arguments": {
    "from_address": "john@company.com",
    "to_addresses": "client@example.com",
    "subject": "Monthly Report",
    "body": "Please find the monthly report attached.",
    "attachment_paths": ["/Users/john/Documents/monthly_report.pdf"]
  }
}
```

### Email with Multiple Attachments and HTML Body

```json
{
  "tool": "send_email",
  "arguments": {
    "from_address": "support@company.com",
    "to_addresses": "customer@example.com",
    "subject": "Support Documents",
    "body": "Please find the requested support documents attached.",
    "html_body": "<h2>Support Documents</h2><p>Please find the requested <strong>support documents</strong> attached.</p><ul><li>User Manual</li><li>Installation Guide</li><li>FAQ</li></ul>",
    "attachment_paths": [
      "/Users/support/Documents/user_manual.pdf",
      "/Users/support/Documents/installation_guide.pdf",
      "/Users/support/Documents/faq.txt"
    ]
  }
}
```

### Email with CC, BCC, and Attachments

```json
{
  "tool": "send_email",
  "arguments": {
    "from_address": "manager@company.com",
    "to_addresses": "team@company.com",
    "cc_addresses": "supervisor@company.com,hr@company.com",
    "bcc_addresses": "archive@company.com",
    "subject": "Project Update with Files",
    "body": "Team,\n\nPlease review the attached project files.\n\nBest regards,\nManager",
    "attachment_paths": [
      "/Users/manager/Projects/project_plan.xlsx",
      "/Users/manager/Projects/budget.pdf",
      "/Users/manager/Projects/timeline.png"
    ]
  }
}
```

## Best Practices

1. **Use Absolute Paths**: Always provide absolute file paths for attachments
2. **Check File Sizes**: Ensure attachments are under 25MB limit
3. **Validate Files**: Verify files exist and are readable before sending
4. **Handle Errors**: Implement proper error handling for attachment failures
5. **Security**: Be cautious with file paths to prevent unauthorized access

## Technical Details

- **MIME Type Detection**: Uses Python's `mimetypes` module for automatic detection
- **Encoding**: Files are base64 encoded for email transmission
- **Memory Efficient**: Large files are processed in chunks to minimize memory usage
- **Error Recovery**: Detailed error messages help identify and resolve issues

## Configuration

Ensure your email account is properly configured with SMTP settings:

```json
{
  "accounts": {
    "your@email.com": {
      "email_address": "your@email.com",
      "protocol": "smtp",
      "smtp_host": "smtp.gmail.com",
      "smtp_port": 587,
      "smtp_use_tls": true,
      "password": "your_password"
    }
  },
  "default_account": "your@email.com"
}
```

---

**Note**: This attachment functionality is now fully integrated into the Email MCP Server and ready for production use.