"""Utility functions for email MCP server."""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from dataclasses import asdict

logger = logging.getLogger(__name__)


def setup_logging(level: str = "INFO") -> None:
    """Setup logging configuration."""
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


def parse_datetime(date_string: str) -> Optional[datetime]:
    """Parse datetime string in various formats."""
    formats = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
        "%Y/%m/%d %H:%M:%S",
        "%Y/%m/%d",
        "%d-%m-%Y %H:%M:%S",
        "%d-%m-%Y",
        "%d/%m/%Y %H:%M:%S",
        "%d/%m/%Y",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%SZ",
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(date_string, fmt)
        except ValueError:
            continue
    
    logger.warning(f"Could not parse datetime: {date_string}")
    return None


def validate_email_request(request_data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate email fetch request parameters."""
    errors = []
    
    # Required fields
    if not request_data.get("email_address"):
        errors.append("email_address is required")
    
    # Optional fields with defaults
    folder = request_data.get("folder", "INBOX")
    limit = request_data.get("limit", 10)
    reverse_order = request_data.get("reverse_order", False)
    
    # Validate limit
    try:
        limit = int(limit)
        if limit <= 0 or limit > 1000:
            errors.append("limit must be between 1 and 1000")
    except (ValueError, TypeError):
        errors.append("limit must be a valid integer")
    
    # Validate reverse_order
    if not isinstance(reverse_order, bool):
        errors.append("reverse_order must be a boolean value")
    
    # Validate dates
    start_date = None
    end_date = None
    
    if request_data.get("start_date"):
        start_date = parse_datetime(request_data["start_date"])
        if not start_date:
            errors.append("start_date format is invalid")
    
    if request_data.get("end_date"):
        end_date = parse_datetime(request_data["end_date"])
        if not end_date:
            errors.append("end_date format is invalid")
    
    if start_date and end_date and start_date > end_date:
        errors.append("start_date must be before end_date")
    
    if errors:
        raise ValueError("; ".join(errors))
    
    return {
        "email_address": request_data["email_address"],
        "folder": folder,
        "start_date": start_date,
        "end_date": end_date,
        "limit": limit,
        "start_uid": request_data.get("start_uid"),
        "reverse_order": reverse_order
    }


def format_email_response(emails: List[Any]) -> Dict[str, Any]:
    """Format email list into standard JSON response."""
    formatted_emails = []
    
    for email in emails:
        # Convert dataclass to dict if needed
        if hasattr(email, '__dict__'):
            email_dict = asdict(email) if hasattr(email, '__dataclass_fields__') else email.__dict__
        else:
            email_dict = email
        
        # Remove raw_message for response (too large)
        email_dict.pop('raw_message', None)
        
        # Format datetime objects
        if 'date' in email_dict and isinstance(email_dict['date'], datetime):
            email_dict['date'] = email_dict['date'].isoformat()
        
        # Format attachments
        if 'attachments' in email_dict:
            for attachment in email_dict['attachments']:
                # Remove email part object
                attachment.pop('part', None)
        
        formatted_emails.append(email_dict)
    
    return {
        "status": "success",
        "total_emails": len(formatted_emails),
        "emails": formatted_emails,
        "timestamp": datetime.now().isoformat()
    }


def format_error_response(error: Exception, request_id: Optional[str] = None) -> Dict[str, Any]:
    """Format error into standard JSON response."""
    error_type = type(error).__name__
    error_message = str(error)
    
    response = {
        "status": "error",
        "error_type": error_type,
        "error_message": error_message,
        "timestamp": datetime.now().isoformat()
    }
    
    if request_id:
        response["request_id"] = request_id
    
    return response


def sanitize_filename(filename: str) -> str:
    """Sanitize filename for safe storage."""
    import re
    
    # Remove or replace dangerous characters
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    
    # Remove leading/trailing dots and spaces
    filename = filename.strip('. ')
    
    # Ensure filename is not empty
    if not filename:
        filename = "unnamed_file"
    
    # Limit length
    if len(filename) > 255:
        name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
        max_name_len = 255 - len(ext) - 1 if ext else 255
        filename = name[:max_name_len] + ('.' + ext if ext else '')
    
    return filename


def extract_email_config(request_data: Dict[str, Any]) -> Dict[str, Any]:
    """Extract email server configuration from request."""
    email_address = request_data["email_address"]
    
    # Extract domain from email
    domain = email_address.split('@')[1].lower()
    
    # Common email server configurations
    server_configs = {
        'gmail.com': {'host': 'imap.gmail.com', 'port': 993, 'use_ssl': True},
        'outlook.com': {'host': 'outlook.office365.com', 'port': 993, 'use_ssl': True},
        'hotmail.com': {'host': 'outlook.office365.com', 'port': 993, 'use_ssl': True},
        'yahoo.com': {'host': 'imap.mail.yahoo.com', 'port': 993, 'use_ssl': True},
        'icloud.com': {'host': 'imap.mail.me.com', 'port': 993, 'use_ssl': True},
    }
    
    # Get configuration or use defaults
    config = server_configs.get(domain, {
        'host': f'imap.{domain}',
        'port': 993,
        'use_ssl': True
    })
    
    # Add credentials
    config.update({
        'username': email_address,
        'password': request_data.get('password', ''),
    })
    
    return config


def create_success_response(data: Any, message: str = "Operation completed successfully") -> Dict[str, Any]:
    """Create a standard success response."""
    return {
        "status": "success",
        "message": message,
        "data": data,
        "timestamp": datetime.now().isoformat()
    }


def log_request(request_data: Dict[str, Any], request_id: Optional[str] = None) -> None:
    """Log incoming request (without sensitive data)."""
    safe_data = request_data.copy()
    
    # Remove sensitive information
    safe_data.pop('password', None)
    
    # Truncate email address for privacy
    if 'email_address' in safe_data:
        email = safe_data['email_address']
        if '@' in email:
            username, domain = email.split('@', 1)
            safe_data['email_address'] = f"{username[:3]}***@{domain}"
    
    log_msg = f"Request received: {safe_data}"
    if request_id:
        log_msg = f"[{request_id}] {log_msg}"
    
    logger.info(log_msg)