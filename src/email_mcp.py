"""Email MCP Server implementation using FastMCP."""

import asyncio
import json
import logging
import os
from typing import Any, Dict, List, Optional
from datetime import datetime

from fastmcp import FastMCP
from email_client import EmailClient, EmailConfig, EmailFilter, SMTPConfig
from pop3_client import POP3Client
from email_client_factory import EmailClientFactory
from attachment_manager import AttachmentManager
from config_manager import ConfigManager
from utils import (
    validate_email_request,
    format_email_response,
    format_error_response,
    create_success_response,
    log_request,
    setup_logging
)

logger = logging.getLogger(__name__)


class EmailMCPServer:
    """Email MCP Server for fetching emails and managing attachments."""
    
    def __init__(self, name: str = "Email MCP Server", attachments_dir: Optional[str] = None):
        self.mcp = FastMCP(name)
        # Use provided attachments_dir or get from environment variable
        base_path = attachments_dir or os.getenv('ATTACHMENTS_DIR', 'attachments')
        self.attachment_manager = AttachmentManager(base_path)
        self.config_manager = ConfigManager()
        self._setup_tools()
        
        # Setup logging
        setup_logging()
        logger.info(f"Initialized {name} with attachments directory: {base_path}")
    
    def _setup_tools(self) -> None:
        """Setup MCP tools."""
        
        @self.mcp.tool()
        async def fetch_emails(
            email_address: str,
            folder: str = "INBOX",
            start_date: Optional[str] = None,
            end_date: Optional[str] = None,
            limit: int = 10,
            start_uid: Optional[str] = None,
            reverse_order: bool = False
        ) -> Dict[str, Any]:
            """Fetch emails from specified email account.
            
            Args:
                email_address: Email address to connect to
                folder: Email folder to fetch from (default: INBOX)
                start_date: Start date for email range (YYYY-MM-DD or YYYY-MM-DD HH:MM:SS)
                end_date: End date for email range (YYYY-MM-DD or YYYY-MM-DD HH:MM:SS)
                limit: Maximum number of emails to fetch (1-1000, default: 10)
                start_uid: Start fetching from this email UID
                reverse_order: Sort order (True for newest first, False for oldest first, default: False)
            
            Returns:
                JSON response with email list and metadata
            """
            request_id = f"req_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
            
            try:
                # Prepare request data
                request_data = {
                    "email_address": email_address,
                    "folder": folder,
                    "start_date": start_date,
                    "end_date": end_date,
                    "limit": limit,
                    "start_uid": start_uid,
                    "reverse_order": reverse_order
                }
                
                # Log request (without sensitive data)
                log_request("fetch_emails", request_data, request_id)
                
                # Validate request
                validated_params = validate_email_request(request_data)
                
                # Get email configuration from config manager
                account_config = self.config_manager.get_account_config(email_address)
                if not account_config:
                    raise ValueError(f"No configuration found for email address: {email_address}")
                
                # Create email filter
                email_filter = EmailFilter(
                    folder=validated_params["folder"],
                    start_date=validated_params["start_date"],
                    end_date=validated_params["end_date"],
                    limit=validated_params["limit"],
                    start_uid=validated_params["start_uid"],
                    reverse_order=validated_params["reverse_order"]
                )
                
                # Create email client using factory (supports both IMAP and POP3)
                client = EmailClientFactory.create_client(account_config)
                
                # Fetch emails
                async with client:
                    emails = await client.fetch_emails(email_filter)
                
                # Download attachments for each email
                for email in emails:
                    if email.attachments:
                        try:
                            # Keep original attachments with part objects for download
                            # Use shallow copy to preserve part objects
                            original_attachments = []
                            for att in email.attachments:
                                if isinstance(att, dict):
                                    # Create a shallow copy to preserve the part object
                                    att_copy = att.copy()
                                    original_attachments.append(att_copy)
                                else:
                                    original_attachments.append(att)
                            
                            # Debug: Check if part objects exist
                            for i, att in enumerate(original_attachments):
                                has_part = 'part' in att if isinstance(att, dict) else False
                                logger.debug(f"Attachment {i} has part: {has_part}, keys: {list(att.keys()) if isinstance(att, dict) else 'not dict'}")
                            
                            downloaded_attachments = await self.attachment_manager.download_attachments(
                                email_address, email.uid, original_attachments
                            )
                            # Keep the original attachments with part field intact, but create serializable version for response
                            # The downloaded_attachments already have the download status and local_path info
                            # We need to merge this info back to the original attachments while preserving part field
                            for i, downloaded_att in enumerate(downloaded_attachments):
                                if i < len(original_attachments) and isinstance(original_attachments[i], dict):
                                    # Update original attachment with download info while preserving part field
                                    original_attachments[i].update({
                                        k: v for k, v in downloaded_att.items() 
                                        if k not in ['part']  # Don't overwrite part field
                                    })
                            
                            # Create serializable version for JSON response (without part field)
                            serializable_attachments = []
                            for attachment in original_attachments:
                                if isinstance(attachment, dict):
                                    # Create a copy without the 'part' field for serialization
                                    serializable_attachment = {k: v for k, v in attachment.items() if k != 'part'}
                                    serializable_attachments.append(serializable_attachment)
                                else:
                                    serializable_attachments.append(attachment)
                            email.attachments = serializable_attachments
                        except Exception as e:
                            logger.error(f"Failed to download attachments for email {email.uid}: {e}")
                            # Keep original attachment info but mark as failed
                            try:
                                new_attachments = []
                                for attachment in email.attachments:
                                    if isinstance(attachment, dict):
                                        # Create a copy without the 'part' field
                                        new_attachment = {k: v for k, v in attachment.items() if k != 'part'}
                                        new_attachment['download_status'] = 'failed'
                                        new_attachment['error'] = str(e)
                                        new_attachments.append(new_attachment)
                                    else:
                                        # Convert to dict if it's not already
                                        new_attachments.append({
                                            'filename': getattr(attachment, 'filename', 'unknown'),
                                            'content_type': getattr(attachment, 'content_type', 'unknown'),
                                            'size': getattr(attachment, 'size', 0),
                                            'download_status': 'failed',
                                            'error': str(e)
                                        })
                                email.attachments = new_attachments
                            except Exception as attachment_error:
                                logger.error(f"Error processing attachments for email {email.uid}: {attachment_error}")
                                # Clear attachments if processing fails
                                email.attachments = []
                
                # Format response
                response = format_email_response(emails)
                response["request_id"] = request_id
                
                logger.info(f"[{request_id}] Successfully fetched {len(emails)} emails")
                return response
                
            except Exception as e:
                logger.error(f"[{request_id}] Error fetching emails: {e}")
                return format_error_response(e, request_id)
        
        @self.mcp.tool()
        async def get_attachment_info(email_address: str, email_uid: str) -> Dict[str, Any]:
            """Get attachment information for a specific email.
            
            Args:
                email_address: Email address that owns the email
                email_uid: Email UID to get attachment info for
            
            Returns:
                JSON response with attachment metadata
            """
            try:
                attachment_info = await self.attachment_manager.get_attachment_info(email_address, email_uid)
                
                if attachment_info:
                    return create_success_response(
                        attachment_info,
                        f"Found attachment info for email {email_uid}"
                    )
                else:
                    return create_success_response(
                        None,
                        f"No attachments found for email {email_uid}"
                    )
                    
            except Exception as e:
                logger.error(f"Error getting attachment info for {email_uid}: {e}")
                return format_error_response(e)
        
        @self.mcp.tool()
        async def read_attachment(email_address: str, email_uid: str, filename: str, parse_content: bool = True) -> Dict[str, Any]:
            """Read attachment content from local storage with optional parsing.
            
            Args:
                email_address: Email address that owns the email
                email_uid: Email UID containing the attachment
                filename: Name of the attachment file
                parse_content: If True, try to parse document content using markitdown
            
            Returns:
                JSON response with attachment content (parsed or base64 encoded)
            """
            try:
                if parse_content:
                    # Use the new parsing method
                    result = await self.attachment_manager.read_attachment_with_parsing(email_address, email_uid, filename)
                    return create_success_response(result, f"Successfully read and parsed attachment {filename}")
                else:
                    # Use the original method for raw content
                    import base64
                    
                    content = await self.attachment_manager.read_attachment(email_address, email_uid, filename)
                    
                    if content:
                        # Encode content as base64 for JSON transport
                        encoded_content = base64.b64encode(content).decode('utf-8')
                        
                        return create_success_response({
                            "filename": filename,
                            "email_uid": email_uid,
                            "content": encoded_content,
                            "size": len(content),
                            "encoding": "base64"
                        }, f"Successfully read attachment {filename}")
                    else:
                        return create_success_response(
                            None,
                            f"Attachment {filename} not found for email {email_uid}"
                        )
                    
            except Exception as e:
                logger.error(f"Error reading attachment {filename} for {email_uid}: {e}")
                return format_error_response(e)
        
        @self.mcp.tool()
        async def list_attachments(email_address: str, email_uid: str) -> Dict[str, Any]:
            """List all attachments for a specific email, including directory structure after extraction.
            
            Args:
                email_address: Email address that owns the email
                email_uid: Email UID to list attachments for
            
            Returns:
                JSON response with attachment structure including files, directories, and extraction info
            """
            try:
                attachment_structure = await self.attachment_manager.list_attachments(email_address, email_uid)
                
                return create_success_response(
                    attachment_structure,
                    f"Found {attachment_structure['total_files']} files and {attachment_structure['total_directories']} directories for email {email_uid}"
                )
                
            except Exception as e:
                logger.error(f"Error listing attachments for {email_uid}: {e}")
                return format_error_response(e)
        
        @self.mcp.tool()
        async def get_storage_stats() -> Dict[str, Any]:
            """Get attachment storage statistics.
            
            Returns:
                JSON response with storage statistics
            """
            try:
                stats = self.attachment_manager.get_storage_stats()
                return create_success_response(stats, "Storage statistics retrieved")
                
            except Exception as e:
                logger.error(f"Error getting storage stats: {e}")
                return format_error_response(e)
        
        @self.mcp.tool()
        async def cleanup_old_attachments(days: int = 30) -> Dict[str, Any]:
            """Clean up attachments older than specified days.
            
            Args:
                days: Number of days (attachments older than this will be deleted)
            
            Returns:
                JSON response with cleanup results
            """
            try:
                cleaned_count = await self.attachment_manager.cleanup_old_attachments(days)
                
                return create_success_response({
                    "cleaned_directories": cleaned_count,
                    "days_threshold": days
                }, f"Cleaned up {cleaned_count} old attachment directories")
                
            except Exception as e:
                logger.error(f"Error during cleanup: {e}")
                return format_error_response(e)
        
        @self.mcp.tool()
        async def extract_archives(email_address: str, email_uid: str) -> Dict[str, Any]:
            """Manually extract archives for a specific email.
            
            Args:
                email_address: Email address that owns the email
                email_uid: Email UID to extract archives for
            
            Returns:
                JSON response with extraction results
            """
            try:
                email_dir = self.attachment_manager.base_path / email_address / email_uid
                
                if not email_dir.exists():
                    return create_success_response(
                        {"error": f"Email directory {email_uid} not found"},
                        f"Email directory {email_uid} not found"
                    )
                
                # Process archives
                extraction_log = await self.attachment_manager.archive_manager.process_email_attachments(email_dir)
                
                return create_success_response(
                    extraction_log,
                    f"Archive extraction completed for email {email_uid}: {extraction_log.get('total_extracted', 0)} files extracted"
                )
                
            except Exception as e:
                logger.error(f"Error extracting archives for {email_uid}: {e}")
                return format_error_response(e)
        
        @self.mcp.tool()
        async def search_emails(
            keywords: str,
            search_type: str = "all",
            page_size: int = 5,
            last_uid: Optional[str] = None
        ) -> Dict[str, Any]:
            """Search emails by keywords and search type with pagination support.
            
            Args:
                keywords: Space-separated keywords to search for
                search_type: Type of search (sender, recipient, cc, subject, content, attachment, all)
                page_size: Number of emails per page (1-50, default: 5)
                last_uid: UID of the last email from previous page for pagination
            
            Returns:
                JSON response with search results
            """
            request_id = f"search_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
            
            try:
                # Validate search parameters
                if not keywords or not keywords.strip():
                    raise ValueError("Keywords cannot be empty")
                
                if search_type not in ["sender", "recipient", "cc", "subject", "content", "attachment", "all"]:
                    raise ValueError(f"Invalid search_type: {search_type}")
                
                if page_size < 1 or page_size > 50:
                    raise ValueError("page_size must be between 1 and 50")
                
                # Log search request
                logger.info(f"[{request_id}] Searching emails with keywords: '{keywords}', type: {search_type}")
                 
                 # Get default email configuration from config manager
                default_account = self.config_manager.get_default_account()
                if not default_account:
                    raise ValueError("No default email account configured for search")
                
                # Create email client using factory (supports both IMAP and POP3)
                client = EmailClientFactory.create_client(default_account)
                 
                async with client:
                     search_result = await client.search_emails(
                         keywords=keywords,
                         search_type=search_type,
                         page_size=page_size,
                         last_uid=last_uid
                    )
                
                # Process attachments for search results
                emails_with_attachments = []
                for email_dict in search_result["emails"]:
                    if email_dict.get("attachments"):
                        try:
                            # Download attachments with existence check
                            downloaded_attachments = await self.attachment_manager.download_attachments(
                                default_account.email_address, email_dict["uid"], email_dict["attachments"]
                            )
                            # Remove 'part' field from downloaded attachments for serialization
                            # Create a copy without the part field to avoid modifying the original
                            serializable_attachments = []
                            for attachment in downloaded_attachments:
                                if isinstance(attachment, dict):
                                    # Create a copy without the 'part' field for serialization
                                    serializable_attachment = {k: v for k, v in attachment.items() if k != 'part'}
                                    serializable_attachments.append(serializable_attachment)
                                else:
                                    serializable_attachments.append(attachment)
                            email_dict["attachments"] = serializable_attachments
                        except Exception as e:
                            logger.error(f"Failed to download attachments for email {email_dict['uid']}: {e}")
                            # Keep original attachment info but mark as failed
                            # Create a copy without the part field to avoid modifying the original
                            failed_attachments = []
                            for attachment in email_dict["attachments"]:
                                if isinstance(attachment, dict):
                                    # Create a copy without the 'part' field
                                    failed_attachment = {k: v for k, v in attachment.items() if k != 'part'}
                                    failed_attachment['download_status'] = 'failed'
                                    failed_attachment['error'] = str(e)
                                    failed_attachments.append(failed_attachment)
                                else:
                                    failed_attachments.append(attachment)
                            email_dict["attachments"] = failed_attachments
                    emails_with_attachments.append(email_dict)
                 
                search_results = {
                     "emails": emails_with_attachments,
                     "total_found": len(emails_with_attachments),
                     "page_size": page_size,
                     "has_more": search_result["has_more"],
                     "last_uid": search_result["last_uid"],
                     "search_params": {
                         "keywords": keywords,
                         "search_type": search_type,
                         "last_uid": last_uid
                     }
                }
                
                return create_success_response(
                    search_results,
                    f"Search completed for keywords: '{keywords}'"
                )
                
            except Exception as e:
                logger.error(f"[{request_id}] Error searching emails: {e}")
                return format_error_response(e, request_id)
        
        @self.mcp.tool()
        async def send_email(
            from_address: str,
            to_addresses: str,
            subject: str,
            body: str,
            cc_addresses: Optional[str] = None,
            bcc_addresses: Optional[str] = None,
            html_body: Optional[str] = None,
            attachment_paths: Optional[List[str]] = None,
            is_html: bool = False
        ) -> Dict[str, Any]:
            """Send an email using SMTP.
            
            Args:
                from_address: Sender email address (must be configured in config file)
                to_addresses: Recipient email addresses (comma-separated)
                subject: Email subject
                body: Email body (plain text or HTML based on is_html parameter)
                cc_addresses: CC email addresses (comma-separated, optional)
                bcc_addresses: BCC email addresses (comma-separated, optional)
                html_body: Email body in HTML format (optional, deprecated - use is_html instead)
                attachment_paths: List of absolute file paths to attach (optional)
                is_html: Whether the body parameter contains HTML content (default: False)
            
            Returns:
                JSON response with send status
            """
            request_id = f"send_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
            
            try:
                # Get email configuration from config manager
                account_config = self.config_manager.get_account_config(from_address)
                if not account_config:
                    raise ValueError(f"No configuration found for email address: {from_address}")
                
                # Parse email addresses
                to_list = [addr.strip() for addr in to_addresses.split(',') if addr.strip()]
                cc_list = [addr.strip() for addr in cc_addresses.split(',') if cc_addresses and addr.strip()] if cc_addresses else None
                bcc_list = [addr.strip() for addr in bcc_addresses.split(',') if bcc_addresses and addr.strip()] if bcc_addresses else None
                
                if not to_list:
                    raise ValueError("At least one recipient email address is required")
                
                # Create email client using factory (supports both IMAP and POP3)
                client = EmailClientFactory.create_client(account_config)
                
                # Validate attachment paths if provided
                validated_attachments = None
                if attachment_paths:
                    validated_attachments = []
                    for path in attachment_paths:
                        if not path or not isinstance(path, str):
                            raise ValueError(f"Invalid attachment path: {path}")
                        
                        # Convert to absolute path if needed
                        abs_path = os.path.abspath(path)
                        if not os.path.exists(abs_path):
                            raise ValueError(f"Attachment file not found: {abs_path}")
                        
                        if not os.path.isfile(abs_path):
                            raise ValueError(f"Attachment path is not a file: {abs_path}")
                        
                        validated_attachments.append(abs_path)
                
                # Determine HTML content based on parameters
                final_html_body = None
                final_body = body
                
                if is_html:
                    # If is_html is True, treat body as HTML content
                    final_html_body = body
                    final_body = body  # Keep original body as fallback
                elif html_body:
                    # Use html_body parameter if provided (for backward compatibility)
                    final_html_body = html_body
                
                # Send email
                success = await client.send_email(
                    to_addresses=to_list,
                    subject=subject,
                    body=final_body,
                    cc_addresses=cc_list,
                    bcc_addresses=bcc_list,
                    html_body=final_html_body,
                    attachment_paths=validated_attachments
                )
                
                if success:
                    response_data = {
                        "request_id": request_id,
                        "from_address": from_address,
                        "to_addresses": to_list,
                        "cc_addresses": cc_list,
                        "bcc_addresses": bcc_list,
                        "subject": subject,
                        "sent_at": datetime.now().isoformat(),
                        "smtp_server": f"{account_config.smtp_host}:{account_config.smtp_port}"
                    }
                    
                    if validated_attachments:
                        response_data["attachments"] = [
                            {
                                "path": path,
                                "filename": os.path.basename(path),
                                "size": os.path.getsize(path)
                            }
                            for path in validated_attachments
                        ]
                        response_data["attachment_count"] = len(validated_attachments)
                    
                    message = f"Email sent successfully to {', '.join(to_list)}"
                    if validated_attachments:
                        message += f" with {len(validated_attachments)} attachment(s)"
                    
                    return create_success_response(response_data, message)
                else:
                    raise Exception("Failed to send email")
                    
            except Exception as e:
                logger.error(f"[{request_id}] Error sending email: {e}")
                return format_error_response(e, request_id)
    
    def get_mcp_server(self) -> FastMCP:
        """Get the FastMCP server instance."""
        return self.mcp
    
    def run_sse(self, host: str = "localhost", port: int = 8000) -> None:
        """Run the MCP server with SSE transport."""
        logger.info(f"Starting Email MCP Server on {host}:{port} with SSE transport")
        
        try:
            # Run the FastMCP server with SSE
            self.mcp.run(transport="sse", host=host, port=port)
        except Exception as e:
            logger.error(f"Failed to start MCP server: {e}")
            raise
    
    def run_stdio(self) -> None:
        """Run the MCP server with stdio transport."""
        logger.info("Starting Email MCP Server with stdio transport")
        
        try:
            # Run the FastMCP server with stdio
            self.mcp.run(transport="stdio")
        except Exception as e:
            logger.error(f"Failed to start MCP server: {e}")
            raise