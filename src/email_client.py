"""Email client implementation for IMAP and SMTP operations."""

import imaplib
import smtplib
import email
import asyncio
import tempfile
import os
import re
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header, decode_header
import logging
from dataclasses import dataclass
# Try to import markitdown, fallback to None if not available
try:
    from markitdown import MarkItDown
    MARKITDOWN_AVAILABLE = True
except ImportError:
    MarkItDown = None
    MARKITDOWN_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class EmailConfig:
    """Email server configuration."""
    host: str
    port: int = 993
    use_ssl: bool = True
    username: str = ""
    password: str = ""


@dataclass
class SMTPConfig:
    """SMTP server configuration for sending emails."""
    host: str
    port: int = 587
    use_tls: bool = True
    username: str = ""
    password: str = ""


@dataclass
class EmailFilter:
    """Email filtering parameters."""
    folder: str = "INBOX"
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    limit: int = 10
    start_uid: Optional[str] = None
    reverse_order: bool = False  # True for descending (newest first), False for ascending (oldest first)


@dataclass
class ParsedEmail:
    """Parsed email data structure."""
    uid: str
    sender: str
    recipients: List[str]
    cc: List[str]
    bcc: List[str]
    subject: str
    content: str
    date: datetime
    attachments: List[Dict[str, Any]]
    raw_message: bytes


class EmailClient:
    """Async IMAP and SMTP email client."""
    
    def __init__(self, config: EmailConfig, smtp_config: Optional[SMTPConfig] = None):
        self.config = config
        self.smtp_config = smtp_config
        self._connection: Optional[imaplib.IMAP4_SSL] = None
        
    async def connect(self) -> None:
        """Establish connection to email server."""
        try:
            if self.config.use_ssl:
                self._connection = imaplib.IMAP4_SSL(self.config.host, self.config.port)
            else:
                self._connection = imaplib.IMAP4(self.config.host, self.config.port)
            
            # Login
            await asyncio.get_event_loop().run_in_executor(
                None, self._connection.login, self.config.username, self.config.password
            )
            logger.info(f"Connected to {self.config.host} as {self.config.username}")
            
        except Exception as e:
            logger.error(f"Failed to connect to email server: {e}")
            raise ConnectionError(f"Email connection failed: {e}")
    
    async def disconnect(self) -> None:
        """Close connection to email server."""
        if self._connection:
            try:
                await asyncio.get_event_loop().run_in_executor(
                    None, self._connection.logout
                )
                logger.info("Disconnected from email server")
            except Exception as e:
                logger.warning(f"Error during disconnect: {e}")
            finally:
                self._connection = None
    
    async def fetch_emails(self, filter_params: EmailFilter) -> List[ParsedEmail]:
        """Fetch emails based on filter parameters."""
        if not self._connection:
            await self.connect()
        
        try:
            # Select folder
            await asyncio.get_event_loop().run_in_executor(
                None, self._connection.select, filter_params.folder
            )
            
            # Build search criteria
            search_criteria = self._build_search_criteria(filter_params)
            logger.info(f"IMAP search criteria: {search_criteria}")
            
            # Search for emails
            typ, message_numbers = await asyncio.get_event_loop().run_in_executor(
                None, self._connection.search, None, search_criteria
            )
            
            if typ != 'OK':
                raise Exception(f"Search failed: {message_numbers}")
            
            # Get message UIDs
            message_ids = message_numbers[0].split()
            logger.info(f"Found {len(message_ids)} messages matching criteria: {message_ids[:10] if len(message_ids) > 10 else message_ids}")
            
            # Apply sorting (reverse order if requested)
            if filter_params.reverse_order:
                message_ids = message_ids[::-1]  # Reverse the list for newest first
            
            # Apply start_uid filter if specified
            if filter_params.start_uid:
                try:
                    start_index = message_ids.index(filter_params.start_uid.encode())
                    message_ids = message_ids[start_index:]
                except ValueError:
                    logger.warning(f"Start UID {filter_params.start_uid} not found")
            
            # Apply limit
            if filter_params.limit > 0:
                message_ids = message_ids[:filter_params.limit]
            
            # Fetch and parse emails
            emails = []
            for msg_id in message_ids:
                try:
                    parsed_email = await self._fetch_and_parse_email(msg_id.decode())
                    emails.append(parsed_email)
                except Exception as e:
                    logger.error(f"Failed to parse email {msg_id}: {e}")
                    continue
            
            logger.info(f"Fetched {len(emails)} emails from {filter_params.folder}")
            return emails
            
        except Exception as e:
            logger.error(f"Failed to fetch emails: {e}")
            raise
    
    def _build_search_criteria(self, filter_params: EmailFilter) -> str:
        """Build IMAP search criteria string."""
        criteria = ["ALL"]
        
        if filter_params.start_date:
            # IMAP SINCE includes the specified date
            date_str = filter_params.start_date.strftime("%d-%b-%Y")
            criteria.append(f"SINCE {date_str}")
        
        if filter_params.end_date:
            # IMAP BEFORE excludes the specified date
            # For end_date like 2025-07-22 00:00:00, we want emails before 2025-07-22
            # But since BEFORE excludes the date, we need to add 1 day to include the end_date
            end_date_plus_one = filter_params.end_date + timedelta(days=1)
            date_str = end_date_plus_one.strftime("%d-%b-%Y")
            criteria.append(f"BEFORE {date_str}")
        
        return " ".join(criteria)
    
    async def _fetch_and_parse_email(self, uid: str) -> ParsedEmail:
        """Fetch and parse a single email."""
        # Fetch email data
        typ, msg_data = await asyncio.get_event_loop().run_in_executor(
            None, self._connection.fetch, uid, '(RFC822)'
        )
        
        if typ != 'OK':
            raise Exception(f"Failed to fetch email {uid}")
        
        # Parse email
        raw_email = msg_data[0][1]
        email_message = email.message_from_bytes(raw_email)
        
        # Extract basic information
        sender = self._decode_header(email_message.get('From', ''))
        recipients = self._parse_addresses(email_message.get('To', ''))
        cc = self._parse_addresses(email_message.get('Cc', ''))
        bcc = self._parse_addresses(email_message.get('Bcc', ''))
        subject = self._decode_header(email_message.get('Subject', ''))
        date_str = email_message.get('Date', '')
        
        # Parse date and convert to China timezone (UTC+8)
        try:
            email_date = email.utils.parsedate_to_datetime(date_str)
            # Convert to China timezone
            china_tz = timezone(timedelta(hours=8))
            if email_date.tzinfo is None:
                # If no timezone info, assume it's already in China timezone
                email_date = email_date.replace(tzinfo=china_tz)
            else:
                # Convert to China timezone
                email_date = email_date.astimezone(china_tz)
        except Exception:
            # Use current time in China timezone as fallback
            china_tz = timezone(timedelta(hours=8))
            email_date = datetime.now(china_tz)
        
        # Extract content
        content = self._extract_content(email_message)
        
        # Extract attachments info
        attachments = self._extract_attachment_info(email_message)
        
        return ParsedEmail(
            uid=uid,
            sender=sender,
            recipients=recipients,
            cc=cc,
            bcc=bcc,
            subject=subject,
            content=content,
            date=email_date,
            attachments=attachments,
            raw_message=raw_email
        )
    
    def _decode_header(self, header_value: str) -> str:
        """Decode email header that may contain encoded text."""
        if not header_value:
            return ""
        
        try:
            decoded_parts = decode_header(header_value)
            decoded_string = ""
            
            for part, encoding in decoded_parts:
                if isinstance(part, bytes):
                    if encoding:
                        decoded_string += part.decode(encoding)
                    else:
                        decoded_string += part.decode('utf-8', errors='ignore')
                else:
                    decoded_string += part
            
            return decoded_string.strip()
        except Exception as e:
            logger.warning(f"Failed to decode header '{header_value}': {e}")
            return header_value
    
    def _parse_addresses(self, address_string: str) -> List[str]:
        """Parse email addresses from string."""
        if not address_string:
            return []
        
        # Decode the address string first
        decoded_addresses = self._decode_header(address_string)
        
        addresses = []
        for addr in decoded_addresses.split(','):
            addr = addr.strip()
            if addr:
                addresses.append(addr)
        return addresses
    
    def _extract_content(self, email_message: EmailMessage) -> str:
        """Extract and convert email content to markdown format."""
        text_content = ""
        html_content = ""
        
        if email_message.is_multipart():
            for part in email_message.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition", ""))
                
                # Skip attachments
                if "attachment" in content_disposition:
                    continue
                
                if content_type == "text/plain":
                    text_content += part.get_payload(decode=True).decode('utf-8', errors='ignore')
                elif content_type == "text/html":
                    html_content += part.get_payload(decode=True).decode('utf-8', errors='ignore')
        else:
            content_type = email_message.get_content_type()
            payload = email_message.get_payload(decode=True)
            if payload:
                content = payload.decode('utf-8', errors='ignore')
                if content_type == "text/html":
                    html_content = content
                else:
                    text_content = content
        
        # Convert HTML to markdown if HTML content exists
        if html_content:
            if MARKITDOWN_AVAILABLE:
                # Use markitdown library if available
                try:
                    md = MarkItDown()
                    # Create a temporary HTML file-like object for markitdown
                    with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as tmp_file:
                        tmp_file.write(html_content)
                        tmp_file_path = tmp_file.name
                    
                    try:
                        result = md.convert(tmp_file_path)
                        return result.text_content
                    finally:
                        os.unlink(tmp_file_path)
                except Exception as e:
                    logger.warning(f"Failed to convert HTML to markdown using markitdown: {e}")
                    # Fallback to custom HTML cleaning
                    return self._clean_html_content(html_content, text_content)
            else:
                # Use custom HTML cleaning if markitdown is not available
                logger.info("markitdown not available, using custom HTML cleaning")
                return self._clean_html_content(html_content, text_content)
        
        return text_content
    
    def _clean_html_content(self, html_content: str, text_content: str = "") -> str:
        """Clean HTML content and convert to readable markdown-like format."""
        if not html_content:
            return text_content
        
        try:
            # Start with the HTML content
            content = html_content
            
            # Remove script and style elements completely
            content = re.sub(r'<script[^>]*>.*?</script>', '', content, flags=re.DOTALL | re.IGNORECASE)
            content = re.sub(r'<style[^>]*>.*?</style>', '', content, flags=re.DOTALL | re.IGNORECASE)
            
            # Convert common HTML elements to markdown-like format
            # Headers
            content = re.sub(r'<h1[^>]*>(.*?)</h1>', r'# \1\n', content, flags=re.DOTALL | re.IGNORECASE)
            content = re.sub(r'<h2[^>]*>(.*?)</h2>', r'## \1\n', content, flags=re.DOTALL | re.IGNORECASE)
            content = re.sub(r'<h3[^>]*>(.*?)</h3>', r'### \1\n', content, flags=re.DOTALL | re.IGNORECASE)
            content = re.sub(r'<h4[^>]*>(.*?)</h4>', r'#### \1\n', content, flags=re.DOTALL | re.IGNORECASE)
            content = re.sub(r'<h5[^>]*>(.*?)</h5>', r'##### \1\n', content, flags=re.DOTALL | re.IGNORECASE)
            content = re.sub(r'<h6[^>]*>(.*?)</h6>', r'###### \1\n', content, flags=re.DOTALL | re.IGNORECASE)
            
            # Bold and italic
            content = re.sub(r'<(strong|b)[^>]*>(.*?)</\1>', r'**\2**', content, flags=re.DOTALL | re.IGNORECASE)
            content = re.sub(r'<(em|i)[^>]*>(.*?)</\1>', r'*\2*', content, flags=re.DOTALL | re.IGNORECASE)
            
            # Links
            content = re.sub(r'<a[^>]*href=["\']([^"\'>]*)["\'][^>]*>(.*?)</a>', r'[\2](\1)', content, flags=re.DOTALL | re.IGNORECASE)
            
            # Images
            content = re.sub(r'<img[^>]*src=["\']([^"\'>]*)["\'][^>]*alt=["\']([^"\'>]*)["\'][^>]*/?>', r'![\2](\1)', content, flags=re.DOTALL | re.IGNORECASE)
            content = re.sub(r'<img[^>]*alt=["\']([^"\'>]*)["\'][^>]*src=["\']([^"\'>]*)["\'][^>]*/?>', r'![\1](\2)', content, flags=re.DOTALL | re.IGNORECASE)
            content = re.sub(r'<img[^>]*src=["\']([^"\'>]*)["\'][^>]*/?>', r'![Image](\1)', content, flags=re.DOTALL | re.IGNORECASE)
            
            # Lists
            content = re.sub(r'<ul[^>]*>', '\n', content, flags=re.IGNORECASE)
            content = re.sub(r'</ul>', '\n', content, flags=re.IGNORECASE)
            content = re.sub(r'<ol[^>]*>', '\n', content, flags=re.IGNORECASE)
            content = re.sub(r'</ol>', '\n', content, flags=re.IGNORECASE)
            content = re.sub(r'<li[^>]*>(.*?)</li>', r'- \1\n', content, flags=re.DOTALL | re.IGNORECASE)
            
            # Paragraphs and line breaks
            content = re.sub(r'<p[^>]*>', '\n', content, flags=re.IGNORECASE)
            content = re.sub(r'</p>', '\n', content, flags=re.IGNORECASE)
            content = re.sub(r'<br[^>]*/?>', '\n', content, flags=re.IGNORECASE)
            content = re.sub(r'<div[^>]*>', '\n', content, flags=re.IGNORECASE)
            content = re.sub(r'</div>', '\n', content, flags=re.IGNORECASE)
            
            # Tables (basic conversion)
            content = re.sub(r'<table[^>]*>', '\n', content, flags=re.IGNORECASE)
            content = re.sub(r'</table>', '\n', content, flags=re.IGNORECASE)
            content = re.sub(r'<tr[^>]*>', '', content, flags=re.IGNORECASE)
            content = re.sub(r'</tr>', '\n', content, flags=re.IGNORECASE)
            content = re.sub(r'<(th|td)[^>]*>(.*?)</\1>', r'\2 | ', content, flags=re.DOTALL | re.IGNORECASE)
            
            # Code blocks
            content = re.sub(r'<pre[^>]*><code[^>]*>(.*?)</code></pre>', r'```\n\1\n```', content, flags=re.DOTALL | re.IGNORECASE)
            content = re.sub(r'<code[^>]*>(.*?)</code>', r'`\1`', content, flags=re.DOTALL | re.IGNORECASE)
            content = re.sub(r'<pre[^>]*>(.*?)</pre>', r'```\n\1\n```', content, flags=re.DOTALL | re.IGNORECASE)
            
            # Blockquotes
            content = re.sub(r'<blockquote[^>]*>(.*?)</blockquote>', r'> \1\n', content, flags=re.DOTALL | re.IGNORECASE)
            
            # Remove remaining HTML tags
            content = re.sub(r'<[^>]+>', '', content)
            
            # Clean up HTML entities
            html_entities = {
                '&nbsp;': ' ',
                '&amp;': '&',
                '&lt;': '<',
                '&gt;': '>',
                '&quot;': '"',
                '&#39;': "'",
                '&apos;': "'",
                '&copy;': '©',
                '&reg;': '®',
                '&trade;': '™',
                '&hellip;': '...',
                '&mdash;': '—',
                '&ndash;': '–',
                '&ldquo;': '"',
                '&rdquo;': '"',
                '&lsquo;': ''',
                '&rsquo;': '''
            }
            
            for entity, replacement in html_entities.items():
                content = content.replace(entity, replacement)
            
            # Clean up extra whitespace and newlines
            content = re.sub(r'\n\s*\n\s*\n', '\n\n', content)  # Multiple newlines to double
            content = re.sub(r'^\s+|\s+$', '', content, flags=re.MULTILINE)  # Trim lines
            content = content.strip()
            
            # If the cleaned content is too short or empty, fallback to text content
            if len(content.strip()) < 10 and text_content:
                return text_content
            
            return content if content.strip() else text_content
            
        except Exception as e:
            logger.warning(f"Failed to clean HTML content: {e}")
            # Return text content if available, otherwise return original HTML
            return text_content if text_content else html_content
    
    def _extract_attachment_info(self, email_message: EmailMessage) -> List[Dict[str, Any]]:
        """Extract attachment information from email."""
        attachments = []
        
        if email_message.is_multipart():
            for part in email_message.walk():
                content_disposition = str(part.get("Content-Disposition", ""))
                
                if "attachment" in content_disposition:
                    filename = part.get_filename()
                    if filename:
                        # Decode the filename if it's encoded
                        decoded_filename = self._decode_header(filename)
                        attachments.append({
                            "filename": decoded_filename,
                            "original_filename": decoded_filename,  # Use decoded filename for consistency
                            "content_type": part.get_content_type(),
                            "size": len(part.get_payload(decode=True) or b''),
                            "part": part  # Re-add part field for attachment download
                        })
        
        return attachments
    
    async def send_email(self, to_addresses: List[str], subject: str, body: str, 
                        cc_addresses: Optional[List[str]] = None, 
                        bcc_addresses: Optional[List[str]] = None,
                        html_body: Optional[str] = None,
                        attachment_paths: Optional[List[str]] = None) -> bool:
        """Send an email using SMTP.
        
        Args:
            to_addresses: List of recipient email addresses
            subject: Email subject
            body: Plain text email body
            cc_addresses: List of CC email addresses
            bcc_addresses: List of BCC email addresses
            html_body: HTML email body (optional)
            attachment_paths: List of file paths to attach (optional)
        
        Returns:
            True if email was sent successfully
        """
        if not self.smtp_config:
            raise ValueError("SMTP configuration not provided")
        
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['From'] = self.smtp_config.username
            msg['To'] = ', '.join(to_addresses)
            msg['Subject'] = Header(subject, 'utf-8')
            
            if cc_addresses:
                msg['Cc'] = ', '.join(cc_addresses)
            
            # Add text content
            text_part = MIMEText(body, 'plain', 'utf-8')
            msg.attach(text_part)
            
            # Add HTML content if provided
            if html_body:
                html_part = MIMEText(html_body, 'html', 'utf-8')
                msg.attach(html_part)
            
            # Prepare recipient list
            recipients = to_addresses.copy()
            if cc_addresses:
                recipients.extend(cc_addresses)
            if bcc_addresses:
                recipients.extend(bcc_addresses)
            
            # Send email
            await asyncio.get_event_loop().run_in_executor(
                None, self._send_smtp_message, msg, recipients
            )
            
            logger.info(f"Email sent successfully to {', '.join(to_addresses)}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            raise
    
    def _send_smtp_message(self, msg: MIMEMultipart, recipients: List[str]) -> None:
        """Send SMTP message synchronously."""
        if self.smtp_config.use_tls:
            server = smtplib.SMTP(self.smtp_config.host, self.smtp_config.port)
            server.starttls()
        else:
            server = smtplib.SMTP_SSL(self.smtp_config.host, self.smtp_config.port)
        
        try:
            server.login(self.smtp_config.username, self.smtp_config.password)
            text = msg.as_string()
            server.sendmail(self.smtp_config.username, recipients, text)
        finally:
            server.quit()
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self
    
    async def search_emails(self, keywords: str, search_type: str = "all", 
                           page_size: int = 5, last_uid: Optional[str] = None) -> Dict[str, Any]:
        """Search emails by keywords and search type with pagination.
        
        Args:
            keywords: Space-separated keywords to search for
            search_type: Type of search - 'sender', 'recipient', 'cc', 'subject', 'content', 'attachment', 'all'
            page_size: Number of emails per page (default: 5)
            last_uid: UID of last email from previous page for pagination
            
        Returns:
            Dict containing emails, has_more flag, and last_uid for next page
        """
        if not self._connection:
            raise Exception("Not connected to email server")
        
        # Select INBOX folder first to ensure proper IMAP state
        await asyncio.get_event_loop().run_in_executor(
            None, self._connection.select, "INBOX"
        )
        
        # Split keywords by space
        keyword_list = [kw.strip() for kw in keywords.split() if kw.strip()]
        if not keyword_list:
            return {"emails": [], "has_more": False, "last_uid": None}
        
        # Get all email UIDs
        typ, data = await asyncio.get_event_loop().run_in_executor(
            None, self._connection.search, None, 'ALL'
        )
        
        if typ != 'OK':
            raise Exception("Failed to search emails")
        
        all_uids = data[0].split()
        if not all_uids:
            return {"emails": [], "has_more": False, "last_uid": None}
        
        # Convert UIDs to strings and sort in descending order (newest first)
        all_uids = [uid.decode('utf-8') for uid in all_uids]
        all_uids.sort(key=int, reverse=True)
        
        # Find starting position if last_uid is provided
        start_index = 0
        if last_uid:
            try:
                start_index = all_uids.index(last_uid) + 1
            except ValueError:
                # If last_uid not found, start from beginning
                start_index = 0
        
        # Search through emails starting from the specified position
        matching_emails = []
        checked_count = 0
        max_check = min(len(all_uids) - start_index, page_size * 10)  # Limit search scope
        
        for i in range(start_index, len(all_uids)):
            if len(matching_emails) >= page_size:
                break
            
            if checked_count >= max_check:
                break
                
            uid = all_uids[i]
            checked_count += 1
            
            try:
                # Fetch and parse email
                email_data = await self._fetch_and_parse_email(uid)
                
                # Check if email matches search criteria
                if self._matches_search_criteria(email_data, keyword_list, search_type):
                    matching_emails.append(email_data)
                    
            except Exception as e:
                logger.warning(f"Failed to process email {uid}: {e}")
                continue
        
        # Determine if there are more emails
        has_more = False
        last_checked_index = start_index + checked_count - 1
        if last_checked_index < len(all_uids) - 1:
            # Check if there might be more matching emails
            has_more = True
        
        # Get the last UID for pagination
        result_last_uid = None
        if matching_emails:
            result_last_uid = matching_emails[-1].uid
        elif checked_count > 0 and last_checked_index < len(all_uids) - 1:
            # If no matches found but there are more emails to check
            result_last_uid = all_uids[last_checked_index]
        
        return {
            "emails": [self._email_to_dict(email) for email in matching_emails],
            "has_more": has_more,
            "last_uid": result_last_uid
        }
    
    def _matches_search_criteria(self, email_data: ParsedEmail, keywords: List[str], search_type: str) -> bool:
        """Check if email matches the search criteria."""
        # Convert all text to lowercase for case-insensitive search
        def contains_any_keyword(text: str) -> bool:
            if not text:
                return False
            text_lower = text.lower()
            return any(keyword.lower() in text_lower for keyword in keywords)
        
        if search_type == "sender":
            return contains_any_keyword(email_data.sender)
        elif search_type == "recipient":
            recipient_text = " ".join(email_data.recipients)
            return contains_any_keyword(recipient_text)
        elif search_type == "cc":
            cc_text = " ".join(email_data.cc)
            return contains_any_keyword(cc_text)
        elif search_type == "subject":
            return contains_any_keyword(email_data.subject)
        elif search_type == "content":
            return contains_any_keyword(email_data.content)
        elif search_type == "attachment":
            attachment_names = [att.get("filename", "") for att in email_data.attachments]
            attachment_text = " ".join(attachment_names)
            return contains_any_keyword(attachment_text)
        elif search_type == "all":
            # Search in all fields
            all_text = " ".join([
                email_data.sender,
                " ".join(email_data.recipients),
                " ".join(email_data.cc),
                email_data.subject,
                email_data.content,
                " ".join([att.get("filename", "") for att in email_data.attachments])
            ])
            return contains_any_keyword(all_text)
        else:
            return False
    
    def _email_to_dict(self, email_data: ParsedEmail) -> Dict[str, Any]:
        """Convert ParsedEmail to dictionary format."""
        return {
            "uid": email_data.uid,
            "sender": email_data.sender,
            "recipients": email_data.recipients,
            "cc": email_data.cc,
            "bcc": email_data.bcc,
            "subject": email_data.subject,
            "content": email_data.content,
            "date": email_data.date.isoformat(),
            "attachments": email_data.attachments
        }

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect()