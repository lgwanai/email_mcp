"""Utility functions for email MCP server."""

import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
from dataclasses import asdict

logger = logging.getLogger(__name__)


def setup_logging(level: str = "DEBUG") -> None:
    """Setup logging configuration."""
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


# 东八区时区对象
CHINA_TZ = timezone(timedelta(hours=8))

def parse_datetime(date_string: str) -> Optional[datetime]:
    """Parse datetime string in various formats and convert to China timezone (UTC+8)."""
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
            dt = datetime.strptime(date_string, fmt)
            # 如果解析的日期没有时区信息，假设为东八区时间
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=CHINA_TZ)
            else:
                # 如果有时区信息，转换为东八区时间
                dt = dt.astimezone(CHINA_TZ)
            return dt
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
    
    for i, email in enumerate(emails):
        try:
            logger.debug(f"Processing email {i}: type={type(email)}, has_dict={hasattr(email, '__dict__')}, has_dataclass_fields={hasattr(email, '__dataclass_fields__')}")
            
            # Convert dataclass to dict if needed
            if hasattr(email, '__dataclass_fields__'):
                # This is a dataclass, manually convert to avoid part object serialization issues
                # Create a clean copy of attachments without 'part' field
                clean_attachments = []
                if hasattr(email, 'attachments') and email.attachments:
                    for attachment in email.attachments:
                        if isinstance(attachment, dict):
                            # Remove any non-serializable fields including 'part'
                            clean_attachment = {}
                            for k, v in attachment.items():
                                if k != 'part':  # Skip part field which contains EmailMessage objects
                                    try:
                                        # Test if the value is JSON serializable
                                        import json
                                        json.dumps(v)
                                        clean_attachment[k] = v
                                    except (TypeError, ValueError):
                                        # Skip non-serializable values
                                        logger.debug(f"Skipping non-serializable field {k} in attachment")
                                        continue
                            clean_attachments.append(clean_attachment)
                        else:
                            # Try to convert non-dict attachments to dict
                            try:
                                if hasattr(attachment, '__dict__'):
                                    att_dict = {k: v for k, v in attachment.__dict__.items() if k != 'part'}
                                    clean_attachments.append(att_dict)
                                else:
                                    clean_attachments.append(str(attachment))
                            except Exception as att_err:
                                logger.warning(f"Could not process attachment: {att_err}")
                                continue
                
                email_dict = {
                    'uid': getattr(email, 'uid', None),
                    'sender': getattr(email, 'sender', None),
                    'recipients': getattr(email, 'recipients', []),
                    'cc': getattr(email, 'cc', []),
                    'bcc': getattr(email, 'bcc', []),
                    'subject': getattr(email, 'subject', ''),
                    'content': getattr(email, 'content', ''),
                    'date': getattr(email, 'date', None),
                    'attachments': clean_attachments
                    # Deliberately exclude raw_message and any part objects in attachments
                }
                logger.debug(f"Manually converted dataclass to dict for email {i}")
            elif hasattr(email, '__dict__'):
                # This has __dict__, copy it
                email_dict = email.__dict__.copy()
                logger.debug(f"Copied __dict__ for email {i}")
            elif hasattr(email, 'copy'):
                # This has copy method
                email_dict = email.copy()
                logger.debug(f"Used copy() method for email {i}")
            elif isinstance(email, dict):
                # This is already a dict
                email_dict = email.copy()
                logger.debug(f"Copied dict for email {i}")
            else:
                # Try to convert to dict
                logger.warning(f"Email {i} is type {type(email)}, attempting dict conversion")
                email_dict = dict(email)
            
            # Remove raw_message for response (too large)
            email_dict.pop('raw_message', None)
            
            # Format datetime objects
            if 'date' in email_dict and isinstance(email_dict['date'], datetime):
                email_dict['date'] = email_dict['date'].isoformat()
            
            # Format attachments - only remove 'part' field if it exists
            if 'attachments' in email_dict and email_dict['attachments']:
                formatted_attachments = []
                for j, attachment in enumerate(email_dict['attachments']):
                    try:
                        logger.debug(f"Processing attachment {j} for email {i}: type={type(attachment)}")
                        # Create a new dict, removing 'part' field only if it exists
                        if isinstance(attachment, dict):
                            formatted_attachment = {k: v for k, v in attachment.items() if k != 'part'}
                            formatted_attachments.append(formatted_attachment)
                        else:
                            # Handle case where attachment might not be a dict
                            logger.warning(f"Attachment {j} is not a dict: {type(attachment)} - {attachment}")
                            formatted_attachments.append(str(attachment))
                    except Exception as att_error:
                        logger.error(f"Error formatting attachment {j} for email {i}: {att_error}")
                        continue
                email_dict['attachments'] = formatted_attachments
            
            formatted_emails.append(email_dict)
            logger.debug(f"Successfully formatted email {i}")
            
        except Exception as e:
            logger.error(f"Error formatting email {i}: {e} - Email type: {type(email)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            # Skip this email and continue
            continue
    
    return {
        "status": "success",
        "total_emails": len(formatted_emails),
        "emails": formatted_emails,
        "timestamp": datetime.now(CHINA_TZ).isoformat()
    }


def format_error_response(error: Exception, request_id: Optional[str] = None) -> Dict[str, Any]:
    """Format error into standard JSON response."""
    error_type = type(error).__name__
    error_message = str(error)
    
    response = {
        "status": "error",
        "error_type": error_type,
        "error_message": error_message,
        "timestamp": datetime.now(CHINA_TZ).isoformat()
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


# extract_email_config function removed - now using ConfigManager


def create_success_response(data: Any, message: str = "Operation completed successfully") -> Dict[str, Any]:
    """Create a standard success response."""
    return {
        "status": "success",
        "message": message,
        "data": data,
        "timestamp": datetime.now(CHINA_TZ).isoformat()
    }


def log_request(tool_name: str, arguments: Dict[str, Any], request_id: Optional[str] = None) -> None:
    """Log incoming request (without sensitive data)."""
    safe_data = arguments.copy()
    
    # Remove sensitive information (passwords should no longer be in arguments)
    safe_data.pop('password', None)
    
    # Truncate email address for privacy
    if 'email_address' in safe_data:
        email = safe_data['email_address']
        if '@' in email:
            username, domain = email.split('@', 1)
            safe_data['email_address'] = f"{username[:3]}***@{domain}"
    
    if 'from_address' in safe_data:
        email = safe_data['from_address']
        if '@' in email:
            username, domain = email.split('@', 1)
            safe_data['from_address'] = f"{username[:3]}***@{domain}"
    
    log_msg = f"Tool '{tool_name}' called with: {safe_data}"
    if request_id:
        log_msg = f"[{request_id}] {log_msg}"
    
    logger.info(log_msg)