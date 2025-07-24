"""SMTP client implementation for email sending only."""

import smtplib
import asyncio
import logging
import os
import mimetypes
from typing import List, Optional
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.header import Header
from email import encoders
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class SMTPConfig:
    """SMTP server configuration for sending emails."""
    host: str
    port: int = 587
    use_tls: bool = True
    username: str = ""
    password: str = ""


class SMTPClient:
    """SMTP-only email client for sending emails."""
    
    def __init__(self, smtp_config: SMTPConfig):
        """Initialize SMTP client.
        
        Args:
            smtp_config: SMTP server configuration
        """
        self.smtp_config = smtp_config
        self._server = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect()
    
    async def connect(self):
        """Connect to SMTP server."""
        try:
            logger.info(f"Connecting to SMTP server {self.smtp_config.host}:{self.smtp_config.port}")
            
            # Run SMTP operations in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            
            def _connect():
                if self.smtp_config.use_tls:
                    server = smtplib.SMTP(self.smtp_config.host, self.smtp_config.port)
                    server.starttls()
                else:
                    server = smtplib.SMTP_SSL(self.smtp_config.host, self.smtp_config.port)
                
                if self.smtp_config.username and self.smtp_config.password:
                    server.login(self.smtp_config.username, self.smtp_config.password)
                
                return server
            
            self._server = await loop.run_in_executor(None, _connect)
            logger.info("Successfully connected to SMTP server")
            
        except Exception as e:
            logger.error(f"Failed to connect to SMTP server: {e}")
            raise
    
    async def disconnect(self):
        """Disconnect from SMTP server."""
        if self._server:
            try:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, self._server.quit)
                logger.info("Disconnected from SMTP server")
            except Exception as e:
                logger.warning(f"Error during SMTP disconnect: {e}")
            finally:
                self._server = None
    
    async def send_email(
        self,
        to_addresses: List[str],
        subject: str,
        body: str,
        cc_addresses: Optional[List[str]] = None,
        bcc_addresses: Optional[List[str]] = None,
        html_body: Optional[str] = None,
        attachment_paths: Optional[List[str]] = None
    ) -> bool:
        """Send an email.
        
        Args:
            to_addresses: List of recipient email addresses
            subject: Email subject
            body: Plain text email body
            cc_addresses: List of CC email addresses
            bcc_addresses: List of BCC email addresses
            html_body: HTML email body (optional)
            attachment_paths: List of file paths to attach (optional)
        
        Returns:
            True if email was sent successfully, False otherwise
        """
        try:
            if not self._server:
                await self.connect()
            
            # Create message
            if html_body or attachment_paths:
                # Use mixed multipart for attachments, or alternative for HTML
                if attachment_paths:
                    msg = MIMEMultipart('mixed')
                    if html_body:
                        # Create alternative part for text/html
                        alt_part = MIMEMultipart('alternative')
                        alt_part.attach(MIMEText(body, 'plain', 'utf-8'))
                        alt_part.attach(MIMEText(html_body, 'html', 'utf-8'))
                        msg.attach(alt_part)
                    else:
                        msg.attach(MIMEText(body, 'plain', 'utf-8'))
                else:
                    msg = MIMEMultipart('alternative')
                    msg.attach(MIMEText(body, 'plain', 'utf-8'))
                    msg.attach(MIMEText(html_body, 'html', 'utf-8'))
            else:
                msg = MIMEText(body, 'plain', 'utf-8')
            
            # Set headers
            msg['Subject'] = Header(subject, 'utf-8')
            msg['From'] = self.smtp_config.username
            msg['To'] = ', '.join(to_addresses)
            
            if cc_addresses:
                msg['Cc'] = ', '.join(cc_addresses)
            
            # Add attachments if provided
            if attachment_paths:
                for file_path in attachment_paths:
                    try:
                        await self._add_attachment(msg, file_path)
                    except Exception as e:
                        logger.warning(f"Failed to attach file {file_path}: {e}")
                        # Continue with other attachments
            
            # Prepare recipient list
            all_recipients = to_addresses.copy()
            if cc_addresses:
                all_recipients.extend(cc_addresses)
            if bcc_addresses:
                all_recipients.extend(bcc_addresses)
            
            # Send email
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                self._server.send_message,
                msg,
                self.smtp_config.username,
                all_recipients
            )
            
            logger.info(f"Email sent successfully to {len(all_recipients)} recipients")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False
    
    async def _add_attachment(self, msg: MIMEMultipart, file_path: str) -> None:
        """Add an attachment to the email message.
        
        Args:
            msg: The email message to add attachment to
            file_path: Path to the file to attach
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"Attachment file not found: {file_path}")
        
        if not file_path.is_file():
            raise ValueError(f"Attachment path is not a file: {file_path}")
        
        # Get file info
        filename = file_path.name
        file_size = file_path.stat().st_size
        
        # Check file size (limit to 25MB)
        max_size = 25 * 1024 * 1024  # 25MB
        if file_size > max_size:
            raise ValueError(f"Attachment file too large: {filename} ({file_size} bytes, max {max_size} bytes)")
        
        # Guess content type
        content_type, encoding = mimetypes.guess_type(str(file_path))
        if content_type is None or encoding is not None:
            content_type = 'application/octet-stream'
        
        main_type, sub_type = content_type.split('/', 1)
        
        # Read file content in executor to avoid blocking
        loop = asyncio.get_event_loop()
        
        def _read_file():
            with open(file_path, 'rb') as f:
                return f.read()
        
        file_data = await loop.run_in_executor(None, _read_file)
        
        # Create attachment
        attachment = MIMEBase(main_type, sub_type)
        attachment.set_payload(file_data)
        
        # Encode the payload using Base64
        encoders.encode_base64(attachment)
        
        # Add header with filename
        attachment.add_header(
            'Content-Disposition',
            f'attachment; filename="{filename}"'
        )
        
        # Attach to message
        msg.attach(attachment)
        
        logger.info(f"Added attachment: {filename} ({file_size} bytes)")
    
    # Compatibility methods for unified interface
    async def fetch_emails(self, *args, **kwargs):
        """SMTP client doesn't support fetching emails."""
        raise NotImplementedError("SMTP client only supports sending emails, not fetching")
    
    async def search_emails(self, *args, **kwargs):
        """SMTP client doesn't support searching emails."""
        raise NotImplementedError("SMTP client only supports sending emails, not searching")