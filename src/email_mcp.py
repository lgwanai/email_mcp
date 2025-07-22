"""Email MCP Server implementation using FastMCP."""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime

from fastmcp import FastMCP
from .email_client import EmailClient, EmailConfig, EmailFilter, SMTPConfig
from .attachment_manager import AttachmentManager
from .utils import (
    validate_email_request,
    format_email_response,
    format_error_response,
    extract_email_config,
    create_success_response,
    log_request,
    setup_logging
)

logger = logging.getLogger(__name__)


class EmailMCPServer:
    """Email MCP Server for fetching emails and managing attachments."""
    
    def __init__(self, name: str = "Email MCP Server"):
        self.mcp = FastMCP(name)
        self.attachment_manager = AttachmentManager()
        self._setup_tools()
        
        # Setup logging
        setup_logging()
        logger.info(f"Initialized {name}")
    
    def _setup_tools(self) -> None:
        """Setup MCP tools."""
        
        @self.mcp.tool()
        async def fetch_emails(
            email_address: str,
            password: str,
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
                password: Email account password
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
                    "password": password,
                    "folder": folder,
                    "start_date": start_date,
                    "end_date": end_date,
                    "limit": limit,
                    "start_uid": start_uid,
                    "reverse_order": reverse_order
                }
                
                # Log request (without sensitive data)
                log_request(request_data, request_id)
                
                # Validate request
                validated_params = validate_email_request(request_data)
                
                # Extract email server configuration
                email_config_dict = extract_email_config(request_data)
                email_config = EmailConfig(**email_config_dict)
                
                # Create email filter
                email_filter = EmailFilter(
                    folder=validated_params["folder"],
                    start_date=validated_params["start_date"],
                    end_date=validated_params["end_date"],
                    limit=validated_params["limit"],
                    start_uid=validated_params["start_uid"],
                    reverse_order=validated_params["reverse_order"]
                )
                
                # Fetch emails
                async with EmailClient(email_config) as client:
                    emails = await client.fetch_emails(email_filter)
                
                # Download attachments for each email
                for email in emails:
                    if email.attachments:
                        try:
                            downloaded_attachments = await self.attachment_manager.download_attachments(
                                email.uid, email.attachments
                            )
                            email.attachments = downloaded_attachments
                        except Exception as e:
                            logger.error(f"Failed to download attachments for email {email.uid}: {e}")
                            # Keep original attachment info but mark as failed
                            for attachment in email.attachments:
                                attachment.pop('part', None)  # Remove email part
                                attachment['download_status'] = 'failed'
                                attachment['error'] = str(e)
                
                # Format response
                response = format_email_response(emails)
                response["request_id"] = request_id
                
                logger.info(f"[{request_id}] Successfully fetched {len(emails)} emails")
                return response
                
            except Exception as e:
                logger.error(f"[{request_id}] Error fetching emails: {e}")
                return format_error_response(e, request_id)
        
        @self.mcp.tool()
        async def get_attachment_info(email_uid: str) -> Dict[str, Any]:
            """Get attachment information for a specific email.
            
            Args:
                email_uid: Email UID to get attachment info for
            
            Returns:
                JSON response with attachment metadata
            """
            try:
                attachment_info = await self.attachment_manager.get_attachment_info(email_uid)
                
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
        async def read_attachment(email_uid: str, filename: str, parse_content: bool = True) -> Dict[str, Any]:
            """Read attachment content from local storage with optional parsing.
            
            Args:
                email_uid: Email UID containing the attachment
                filename: Name of the attachment file
                parse_content: If True, try to parse document content using markitdown
            
            Returns:
                JSON response with attachment content (parsed or base64 encoded)
            """
            try:
                if parse_content:
                    # Use the new parsing method
                    result = await self.attachment_manager.read_attachment_with_parsing(email_uid, filename)
                    return create_success_response(result, f"Successfully read and parsed attachment {filename}")
                else:
                    # Use the original method for raw content
                    import base64
                    
                    content = await self.attachment_manager.read_attachment(email_uid, filename)
                    
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
        async def list_attachments(email_uid: str) -> Dict[str, Any]:
            """List all attachments for a specific email.
            
            Args:
                email_uid: Email UID to list attachments for
            
            Returns:
                JSON response with list of attachment filenames
            """
            try:
                attachments = await self.attachment_manager.list_attachments(email_uid)
                
                return create_success_response({
                    "email_uid": email_uid,
                    "attachments": attachments,
                    "count": len(attachments)
                }, f"Found {len(attachments)} attachments for email {email_uid}")
                
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
                 
                 # Create email client and perform search
                email_config = EmailConfig(
                     host=self.config.imap_host,
                     port=self.config.imap_port,
                     username=self.config.username,
                     password=self.config.password,
                     use_ssl=self.config.use_ssl
                )
                 
                async with EmailClient(email_config) as client:
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
                                email_dict["uid"], email_dict["attachments"]
                            )
                            email_dict["attachments"] = downloaded_attachments
                        except Exception as e:
                            logger.error(f"Failed to download attachments for email {email_dict['uid']}: {e}")
                            # Keep original attachment info but mark as failed
                            for attachment in email_dict["attachments"]:
                                attachment.pop('part', None)  # Remove email part
                                attachment['download_status'] = 'failed'
                                attachment['error'] = str(e)
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
            smtp_host: str,
            smtp_port: int,
            smtp_username: str,
            smtp_password: str,
            to_addresses: str,
            subject: str,
            body: str,
            smtp_use_tls: bool = True,
            cc_addresses: Optional[str] = None,
            bcc_addresses: Optional[str] = None,
            html_body: Optional[str] = None
        ) -> Dict[str, Any]:
            """Send an email using SMTP.
            
            Args:
                smtp_host: SMTP server hostname
                smtp_port: SMTP server port
                smtp_username: SMTP username (usually email address)
                smtp_password: SMTP password or authorization code
                to_addresses: Recipient email addresses (comma-separated)
                subject: Email subject
                body: Email body (plain text)
                smtp_use_tls: Whether to use TLS encryption (default: True)
                cc_addresses: CC email addresses (comma-separated, optional)
                bcc_addresses: BCC email addresses (comma-separated, optional)
                html_body: Email body in HTML format (optional)
            
            Returns:
                JSON response with send status
            """
            request_id = f"send_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
            
            try:
                # Parse email addresses
                to_list = [addr.strip() for addr in to_addresses.split(',') if addr.strip()]
                cc_list = [addr.strip() for addr in cc_addresses.split(',') if cc_addresses and addr.strip()] if cc_addresses else None
                bcc_list = [addr.strip() for addr in bcc_addresses.split(',') if bcc_addresses and addr.strip()] if bcc_addresses else None
                
                if not to_list:
                    raise ValueError("At least one recipient email address is required")
                
                # Create SMTP configuration
                smtp_config = SMTPConfig(
                    host=smtp_host,
                    port=smtp_port,
                    use_tls=smtp_use_tls,
                    username=smtp_username,
                    password=smtp_password
                )
                
                # Create email client with SMTP config
                email_config = EmailConfig(
                    host="dummy",  # Not used for sending
                    username=smtp_username,
                    password=smtp_password
                )
                
                client = EmailClient(email_config, smtp_config)
                
                # Send email
                success = await client.send_email(
                    to_addresses=to_list,
                    subject=subject,
                    body=body,
                    cc_addresses=cc_list,
                    bcc_addresses=bcc_list,
                    html_body=html_body
                )
                
                if success:
                    return create_success_response({
                        "request_id": request_id,
                        "to_addresses": to_list,
                        "cc_addresses": cc_list,
                        "bcc_addresses": bcc_list,
                        "subject": subject,
                        "sent_at": datetime.now().isoformat(),
                        "smtp_server": f"{smtp_host}:{smtp_port}"
                    }, f"Email sent successfully to {', '.join(to_list)}")
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