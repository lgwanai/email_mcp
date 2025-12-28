"""Email MCP Server implementation using FastMCP."""

import asyncio
import json
import logging
import os
from typing import Any, Dict, List, Optional
from datetime import datetime

from fastmcp import FastMCP
from email_client import EmailClient, EmailConfig, EmailFilter, SMTPConfig, ParsedEmail
from pop3_client import POP3Client
from email_client_factory import EmailClientFactory
from attachment_manager import AttachmentManager
from config_manager import ConfigManager
from email_index_service import EmailIndexService
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
        
        # Initialize Index Service
        db_path = os.getenv('EMAIL_DB_PATH', 'email_index.db')
        self.index_service = EmailIndexService(db_path, self.attachment_manager)
        
        self._setup_tools()
        
        # Setup logging
        setup_logging()
        logger.info(f"Initialized {name} with attachments directory: {base_path}")

    async def start_background_sync(self):
        """Start the background synchronization task."""
        sync_interval = int(os.getenv('EMAIL_SYNC_INTERVAL_SECONDS', '60'))
        logger.info(f"Starting background sync with interval {sync_interval}s")
        await self.index_service.start_background_sync(
            EmailClientFactory, 
            self.config_manager, 
            sync_interval
        )
    
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

                # Check if sync state exists for this folder
                sync_state = await self.index_service.get_sync_state(email_address, folder)
                
                if not sync_state:
                     logger.info(f"[{request_id}] No sync state found, result might be empty until background sync runs")

                logger.info(f"[{request_id}] Querying local index for {email_address}/{folder}")
                db_rows = await self.index_service.list_emails(
                    email_address, 
                    folder,
                    limit=validated_params["limit"],
                    start_uid=validated_params["start_uid"],
                    reverse_order=validated_params["reverse_order"],
                    start_date=validated_params["start_date"],
                    end_date=validated_params["end_date"]
                )
                
                emails = []
                client = None
                
                if db_rows:
                    for row in db_rows:
                        # Reconstruct attachments metadata
                        att_names = json.loads(row['attachment_names_json']) if row['attachment_names_json'] else []
                        attachments_list = []
                        missing_attachments = False
                        
                        current_att_dir = row['attachment_dir']
                        
                        for name in att_names:
                            is_downloaded = False
                            local_path = None
                            
                            if current_att_dir:
                                path = os.path.join(current_att_dir, name)
                                if os.path.exists(path):
                                    is_downloaded = True
                                    local_path = path
                            
                            if not is_downloaded:
                                missing_attachments = True
                                
                            attachments_list.append({
                                "filename": name, 
                                "download_status": "downloaded" if is_downloaded else "missing",
                                "local_path": local_path
                            })

                        parsed = ParsedEmail(
                            uid=row['uid'],
                            sender=row['sender'],
                            recipients=json.loads(row['recipients']),
                            cc=json.loads(row['cc']),
                            bcc=[], # Not stored in index currently
                            subject=row['subject'],
                            content=row['body'] or "",
                            date=datetime.fromisoformat(row['date']),
                            attachments=attachments_list,
                            raw_message=b"" # Not stored
                        )
                        
                        # Determine if we need to fetch from remote
                        missing_body = (row['body'] is None)
                        has_attachments_flag = (row['has_attachments'] == 1)
                        
                        # Only fetch if we have missing content that is expected
                        need_fetch = missing_body or (has_attachments_flag and missing_attachments)
                        
                        if need_fetch:
                            logger.info(f"[{request_id}] Fetching missing content for {row['uid']} (Body: {missing_body}, Attachments: {missing_attachments})")
                            
                            try:
                                if not client:
                                    client = EmailClientFactory.create_client(account_config)
                                    await client.connect()
                                
                                # Fetch full email
                                full_email = await client._fetch_and_parse_email(row['uid'])
                                
                                # Handle Body
                                if missing_body:
                                    await self.index_service.update_email_body(
                                        email_address, folder, row['uid'], full_email.content
                                    )
                                    parsed.content = full_email.content
                                
                                # Handle Attachments
                                if has_attachments_flag and missing_attachments:
                                    # Download attachments using AttachmentManager
                                    downloaded_atts = await self.attachment_manager.download_attachments(
                                        email_address, row['uid'], full_email.attachments
                                    )
                                    
                                    # Update parsed object
                                    parsed.attachments = downloaded_atts
                                    
                                    # Update DB attachment_dir if we successfully downloaded something
                                    if downloaded_atts:
                                        email_dir = self.attachment_manager._get_email_attachment_dir(email_address, row['uid'])
                                        await self.index_service.update_attachment_dir(
                                            email_address, folder, row['uid'], str(email_dir)
                                        )

                            except Exception as e:
                                logger.error(f"Failed to fetch remote content for {row['uid']}: {e}")
                                # Continue with what we have
                        
                        emails.append(parsed)
                
                if client:
                    await client.disconnect()

                # Format response
                response = format_email_response(emails)
                response["request_id"] = request_id
                response["source"] = "db"
                
                logger.info(f"[{request_id}] Successfully fetched {len(emails)} emails")
                return response
                
            except Exception as e:
                logger.error(f"[{request_id}] Error fetching emails: {e}")
                return format_error_response(e, request_id)
        
        @self.mcp.tool()
        async def search_emails(
            keywords: List[str],
            email_address: Optional[str] = None,
            search_type: str = "comprehensive",
            limit: int = 10,
            offset: int = 0
        ) -> Dict[str, Any]:
            """Search emails in local index.
            
            Args:
                keywords: List of keywords (OR logic, any match hits)
                email_address: Email account to search (Optional, if None searches all accounts)
                search_type: Search scope ("comprehensive", "sender", "recipient", "subject", "body")
                limit: Max results per page (default: 10)
                offset: Pagination offset (default: 0)
            """
            try:
                # Log request
                log_request("search_emails", {
                    "email_address": email_address, 
                    "keywords": keywords,
                    "search_type": search_type,
                    "limit": limit,
                    "offset": offset
                })
                
                # Check config only if email_address is provided
                if email_address:
                    account_config = self.config_manager.get_account_config(email_address)
                    if not account_config:
                        raise ValueError(f"No configuration found for email address: {email_address}")

                # Map search_type to fields
                search_fields = None
                if search_type != "comprehensive":
                    valid_types = ["sender", "recipient", "subject", "body"]
                    if search_type not in valid_types:
                        raise ValueError(f"Invalid search_type: {search_type}. Must be one of {valid_types} or 'comprehensive'")
                    search_fields = [search_type]

                # Perform search
                db_rows, total_count = await self.index_service.search_emails(
                    email_address,
                    keywords,
                    search_fields,
                    limit,
                    offset
                )
                
                # Convert to ParsedEmail objects and generate summaries
                emails = []
                import re
                
                # Pre-compile regex for keywords (case insensitive)
                # Escape keywords to avoid regex errors
                escaped_keywords = [re.escape(k) for k in keywords]
                keyword_pattern = re.compile(f"({'|'.join(escaped_keywords)})", re.IGNORECASE)

                for row in db_rows:
                    # Reconstruct attachments metadata
                    att_names = json.loads(row['attachment_names_json']) if row['attachment_names_json'] else []
                    attachments = []
                    for name in att_names:
                        att_info = {"filename": name, "download_status": "unknown"}
                        if row['attachment_dir']:
                            att_info["local_path"] = os.path.join(row['attachment_dir'], name)
                            att_info["download_status"] = "downloaded"
                        attachments.append(att_info)
                    
                    # Generate Summary for Content
                    content = row['body'] or ""
                    summary = []
                    if content:
                        # Find all matches
                        matches = list(keyword_pattern.finditer(content))
                        if matches:
                            for match in matches:
                                start = match.start()
                                end = match.end()
                                # Extract context: +/- 20 chars
                                ctx_start = max(0, start - 20)
                                ctx_end = min(len(content), end + 20)
                                snippet = content[ctx_start:ctx_end]
                                # Add ellipsis if truncated
                                if ctx_start > 0:
                                    snippet = "..." + snippet
                                if ctx_end < len(content):
                                    snippet = snippet + "..."
                                summary.append(snippet)
                        else:
                            # If no keyword in body (maybe matched in subject/sender), show beginning
                            summary.append(content[:100] + "..." if len(content) > 100 else content)
                    
                    parsed = ParsedEmail(
                        uid=row['uid'],
                        sender=row['sender'],
                        recipients=json.loads(row['recipients']),
                        cc=json.loads(row['cc']),
                        bcc=[], 
                        subject=row['subject'],
                        content=summary, # Replace content with summary array
                        date=datetime.fromisoformat(row['date']),
                        attachments=attachments,
                        raw_message=b"" 
                    )
                    emails.append(parsed)

                # Format basic response
                response = format_email_response(emails)
                
                # Add pagination info
                current_page = (offset // limit) + 1
                total_pages = (total_count + limit - 1) // limit if limit > 0 else 0
                
                response.update({
                    "source": "local_search",
                    "pagination": {
                        "total_items": total_count,
                        "total_pages": total_pages,
                        "current_page": current_page,
                        "page_size": limit
                    }
                })
                
                return response

            except Exception as e:
                logger.error(f"Error searching emails: {e}")
                return format_error_response(e)

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
        async def list_emails(
            email_address: str,
            folder: str = "INBOX",
            start_date: Optional[str] = None,
            end_date: Optional[str] = None,
            limit: int = 50,
            start_uid: Optional[str] = None,
            reverse_order: bool = True
        ) -> Dict[str, Any]:
            """List emails from local index efficiently (pure DB query).
            
            Args:
                email_address: Email address
                folder: Folder name (default: INBOX)
                start_date: Filter by start date (YYYY-MM-DD)
                end_date: Filter by end date (YYYY-MM-DD)
                limit: Max records (default: 50)
                start_uid: Pagination start UID
                reverse_order: Newest first (default: True)
            """
            try:
                # Parse dates
                start_dt = datetime.fromisoformat(start_date) if start_date else None
                end_dt = datetime.fromisoformat(end_date) if end_date else None
                
                rows = await self.index_service.list_emails(
                    email_address, folder, limit, start_uid, reverse_order, start_dt, end_dt
                )
                
                # Convert to simpler list
                emails = []
                for row in rows:
                    emails.append({
                        "uid": row['uid'],
                        "subject": row['subject'],
                        "sender": row['sender'],
                        "date": row['date'],
                        "snippet": row['snippet'],
                        "has_attachments": bool(row['has_attachments'])
                    })
                
                return create_success_response(emails, f"Listed {len(emails)} emails from index")
            except Exception as e:
                return format_error_response(e)

        @self.mcp.tool()
        async def sync_email_index(
            email_address: str,
            folder: str = "INBOX",
            mode: str = "incremental"
        ) -> Dict[str, Any]:
            """Trigger manual synchronization for email index.
            
            Args:
                email_address: Email address
                folder: Folder to sync
                mode: 'incremental' or 'full' (full = initial sync)
            """
            try:
                account_config = self.config_manager.get_account_config(email_address)
                if not account_config:
                    raise ValueError(f"Account {email_address} not found")
                
                client = EmailClientFactory.create_client(account_config)
                async with client:
                    if mode == "full":
                        await self.index_service.sync_initial(client, folder)
                    else:
                        await self.index_service.sync_incremental(client, folder)
                        
                return create_success_response({"status": "completed"}, "Sync completed")
            except Exception as e:
                return format_error_response(e)

        @self.mcp.tool()
        async def get_index_status(
            email_address: str,
            folder: str = "INBOX"
        ) -> Dict[str, Any]:
            """Get synchronization status for a folder."""
            try:
                state = await self.index_service.get_sync_state(email_address, folder)
                return create_success_response(state or {"status": "not_synced"}, "Index status retrieved")
            except Exception as e:
                return format_error_response(e)

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
    
    async def run_sse_async(self, host: str = "localhost", port: int = 8000) -> None:
        """Run the MCP server with SSE transport asynchronously."""
        logger.info(f"Starting Email MCP Server on {host}:{port} with SSE transport")
        try:
            await self.mcp.run_sse_async(host=host, port=port)
        except Exception as e:
            logger.error(f"Failed to start MCP server: {e}")
            raise

    async def run_stdio_async(self) -> None:
        """Run the MCP server with stdio transport asynchronously."""
        logger.info("Starting Email MCP Server with stdio transport")
        try:
            await self.mcp.run_stdio_async()
        except Exception as e:
            logger.error(f"Failed to start MCP server: {e}")
            raise

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