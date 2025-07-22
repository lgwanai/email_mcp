"""Attachment management for email MCP server."""

import os
import asyncio
import aiofiles
from pathlib import Path
from typing import List, Dict, Any, Optional
import logging
import json
from datetime import datetime
from email.message import EmailMessage

logger = logging.getLogger(__name__)


class AttachmentManager:
    """Manages email attachment download and storage."""
    
    def __init__(self, base_path: str = "attachments"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(exist_ok=True)
        
    async def download_attachments(self, email_uid: str, attachments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Download all attachments for an email."""
        if not attachments:
            return []
        
        # Create directory for this email's attachments
        email_dir = self.base_path / email_uid
        email_dir.mkdir(exist_ok=True)
        
        downloaded_attachments = []
        
        for i, attachment in enumerate(attachments):
            try:
                downloaded_info = await self._download_single_attachment(
                    email_dir, attachment, i
                )
                downloaded_attachments.append(downloaded_info)
            except Exception as e:
                logger.error(f"Failed to download attachment {attachment.get('filename', 'unknown')}: {e}")
                # Add error info to attachment
                error_info = attachment.copy()
                error_info.update({
                    "download_status": "failed",
                    "error": str(e),
                    "local_path": None
                })
                # Remove the email part object for JSON serialization
                error_info.pop("part", None)
                downloaded_attachments.append(error_info)
        
        # Save attachment metadata
        await self._save_attachment_metadata(email_uid, downloaded_attachments)
        
        logger.info(f"Downloaded {len([a for a in downloaded_attachments if a.get('download_status') == 'success'])} attachments for email {email_uid}")
        return downloaded_attachments
    
    async def _download_single_attachment(self, email_dir: Path, attachment: Dict[str, Any], index: int) -> Dict[str, Any]:
        """Download a single attachment."""
        # Use decoded filename for storage, fallback to index-based name if not available
        filename = attachment.get("filename", f"attachment_{index}")
        original_filename = attachment.get("original_filename", filename)
        part = attachment.get("part")
        
        if not part:
            raise ValueError("No email part found for attachment")
        
        # Sanitize filename for safe storage
        from utils import sanitize_filename
        safe_filename = sanitize_filename(filename)
        
        # Check if file already exists
        local_path = email_dir / safe_filename
        
        # If file already exists, check if it's the same content
        if local_path.exists():
            try:
                # Get attachment data to compare
                attachment_data = part.get_payload(decode=True)
                if not attachment_data:
                    raise ValueError("No attachment data found")
                
                # Read existing file and compare
                async with aiofiles.open(local_path, 'rb') as f:
                    existing_data = await f.read()
                
                if existing_data == attachment_data:
                    # File already exists with same content, skip download
                    logger.debug(f"Attachment already exists with same content: {filename} -> {local_path}")
                    return {
                        "filename": filename,
                        "original_filename": original_filename,
                        "safe_filename": safe_filename,
                        "content_type": attachment.get("content_type"),
                        "size": len(attachment_data),
                        "local_path": str(local_path),
                        "download_status": "skipped_existing",
                        "download_time": datetime.now().isoformat()
                    }
                else:
                    # File exists but content is different, create new filename
                    counter = 1
                    original_path = local_path
                    while local_path.exists():
                        stem = original_path.stem
                        suffix = original_path.suffix
                        local_path = email_dir / f"{stem}_{counter}{suffix}"
                        counter += 1
            except Exception as e:
                logger.warning(f"Error checking existing file {local_path}: {e}")
                # If we can't read the existing file, create a new one with different name
                counter = 1
                original_path = local_path
                while local_path.exists():
                    stem = original_path.stem
                    suffix = original_path.suffix
                    local_path = email_dir / f"{stem}_{counter}{suffix}"
                    counter += 1
        
        # Get attachment data if not already retrieved
        if 'attachment_data' not in locals():
            attachment_data = part.get_payload(decode=True)
            if not attachment_data:
                raise ValueError("No attachment data found")
        
        # Write file asynchronously
        async with aiofiles.open(local_path, 'wb') as f:
            await f.write(attachment_data)
        
        # Prepare return info
        download_info = {
            "filename": filename,  # Decoded filename
            "original_filename": original_filename,  # Original encoded filename
            "safe_filename": safe_filename,  # Sanitized filename used for storage
            "content_type": attachment.get("content_type"),
            "size": len(attachment_data),
            "local_path": str(local_path),
            "download_status": "success",
            "download_time": datetime.now().isoformat()
        }
        
        logger.debug(f"Downloaded attachment: {filename} -> {local_path}")
        return download_info
    
    async def _save_attachment_metadata(self, email_uid: str, attachments: List[Dict[str, Any]]) -> None:
        """Save attachment metadata to JSON file."""
        metadata_file = self.base_path / email_uid / "attachments.json"
        
        metadata = {
            "email_uid": email_uid,
            "download_time": datetime.now().isoformat(),
            "total_attachments": len(attachments),
            "successful_downloads": len([a for a in attachments if a.get("download_status") == "success"]),
            "attachments": attachments
        }
        
        async with aiofiles.open(metadata_file, 'w', encoding='utf-8') as f:
            await f.write(json.dumps(metadata, indent=2, ensure_ascii=False))
    
    async def get_attachment_info(self, email_uid: str) -> Optional[Dict[str, Any]]:
        """Get attachment metadata for an email."""
        metadata_file = self.base_path / email_uid / "attachments.json"
        
        if not metadata_file.exists():
            return None
        
        try:
            async with aiofiles.open(metadata_file, 'r', encoding='utf-8') as f:
                content = await f.read()
                return json.loads(content)
        except Exception as e:
            logger.error(f"Failed to read attachment metadata for {email_uid}: {e}")
            return None
    
    async def read_attachment(self, email_uid: str, filename: str, parse_content: bool = False) -> Optional[bytes]:
        """Read attachment content by filename.
        
        Args:
            email_uid: Email UID containing the attachment
            filename: Name of the attachment file
            parse_content: If True, try to parse document content using markitdown
            
        Returns:
            Raw file content as bytes, or None if not found
        """
        email_dir = self.base_path / email_uid
        
        if not email_dir.exists():
            logger.warning(f"Email directory {email_uid} not found")
            return None
        
        # Find the actual file path
        actual_file_path = None
        
        # First try exact filename
        file_path = email_dir / filename
        if file_path.exists():
            actual_file_path = file_path
        else:
            # Try sanitized filename
            from .utils import sanitize_filename
            safe_filename = sanitize_filename(filename)
            safe_file_path = email_dir / safe_filename
            if safe_file_path.exists():
                actual_file_path = safe_file_path
            else:
                # Try to find file by checking metadata
                metadata = await self.get_attachment_info(email_uid)
                if metadata and 'attachments' in metadata:
                    for att in metadata['attachments']:
                        # Check if the requested filename matches any stored filename variants
                        if (filename == att.get('filename') or 
                            filename == att.get('original_filename') or 
                            filename == att.get('safe_filename')):
                            local_path = Path(att.get('local_path', ''))
                            if local_path.exists():
                                actual_file_path = local_path
                                break
                
                # Try to find file with similar name (handle renamed files)
                if not actual_file_path:
                    for file in email_dir.glob("*"):
                        if file.is_file() and file.name != "attachments.json":
                            if file.name.startswith(filename.split('.')[0]):
                                actual_file_path = file
                                break
        
        if not actual_file_path:
            logger.warning(f"Attachment {filename} not found for email {email_uid}")
            return None
        
        # Read file content
        async with aiofiles.open(actual_file_path, 'rb') as f:
            return await f.read()
    
    async def read_attachment_with_parsing(self, email_uid: str, filename: str) -> Dict[str, Any]:
        """Read attachment and optionally parse content using markitdown.
        
        Args:
            email_uid: Email UID containing the attachment
            filename: Name of the attachment file
            
        Returns:
            Dict containing file info and content (parsed or raw)
        """
        email_dir = self.base_path / email_uid
        
        if not email_dir.exists():
            logger.warning(f"Email directory {email_uid} not found")
            return {"error": f"Email directory {email_uid} not found"}
        
        # Find the actual file path
        actual_file_path = None
        
        # First try exact filename
        file_path = email_dir / filename
        if file_path.exists():
            actual_file_path = file_path
        else:
            # Try sanitized filename
            from .utils import sanitize_filename
            safe_filename = sanitize_filename(filename)
            safe_file_path = email_dir / safe_filename
            if safe_file_path.exists():
                actual_file_path = safe_file_path
            else:
                # Try to find file by checking metadata
                metadata = await self.get_attachment_info(email_uid)
                if metadata and 'attachments' in metadata:
                    for att in metadata['attachments']:
                        # Check if the requested filename matches any stored filename variants
                        if (filename == att.get('filename') or 
                            filename == att.get('original_filename') or 
                            filename == att.get('safe_filename')):
                            local_path = Path(att.get('local_path', ''))
                            if local_path.exists():
                                actual_file_path = local_path
                                break
                
                # Try to find file with similar name (handle renamed files)
                if not actual_file_path:
                    for file in email_dir.glob("*"):
                        if file.is_file() and file.name != "attachments.json":
                            if file.name.startswith(filename.split('.')[0]):
                                actual_file_path = file
                                break
        
        if not actual_file_path:
            logger.warning(f"Attachment {filename} not found for email {email_uid}")
            return {"error": f"Attachment {filename} not found"}
        
        # Get file extension to determine if we should try parsing
        file_extension = actual_file_path.suffix.lower()
        parseable_extensions = {'.pdf', '.docx', '.doc', '.xlsx', '.xls', '.pptx', '.ppt', '.txt', '.md', '.rtf', '.csv'}
        
        result = {
            "filename": filename,
            "email_uid": email_uid,
            "actual_path": str(actual_file_path),
            "file_size": actual_file_path.stat().st_size,
            "file_extension": file_extension
        }
        
        # Try to parse content if it's a supported document format
        if file_extension in parseable_extensions:
            try:
                # Check if markitdown is available
                from markitdown import MarkItDown
                
                # Initialize MarkItDown
                md = MarkItDown()
                
                # Convert file to markdown
                markdown_result = md.convert(str(actual_file_path))
                
                result.update({
                    "content_type": "parsed",
                    "parsed_content": markdown_result.text_content,
                    "parsing_status": "success",
                    "parser_used": "markitdown"
                })
                
                logger.info(f"Successfully parsed {filename} using markitdown")
                
            except ImportError:
                logger.warning("markitdown not available, returning raw file content")
                # Fall back to raw content
                async with aiofiles.open(actual_file_path, 'rb') as f:
                    raw_content = await f.read()
                
                import base64
                result.update({
                    "content_type": "raw",
                    "raw_content": base64.b64encode(raw_content).decode('utf-8'),
                    "encoding": "base64",
                    "parsing_status": "failed",
                    "error": "markitdown not available"
                })
                
            except Exception as e:
                logger.error(f"Error parsing {filename} with markitdown: {e}")
                # Fall back to raw content
                async with aiofiles.open(actual_file_path, 'rb') as f:
                    raw_content = await f.read()
                
                import base64
                result.update({
                    "content_type": "raw",
                    "raw_content": base64.b64encode(raw_content).decode('utf-8'),
                    "encoding": "base64",
                    "parsing_status": "failed",
                    "error": str(e)
                })
        else:
            # For non-parseable files, return raw content
            async with aiofiles.open(actual_file_path, 'rb') as f:
                raw_content = await f.read()
            
            import base64
            result.update({
                "content_type": "raw",
                "raw_content": base64.b64encode(raw_content).decode('utf-8'),
                "encoding": "base64",
                "parsing_status": "not_applicable",
                "note": f"File type {file_extension} not supported for parsing"
            })
        
        return result
    
    async def list_attachments(self, email_uid: str) -> List[str]:
        """List all attachment filenames for an email."""
        email_dir = self.base_path / email_uid
        
        if not email_dir.exists():
            return []
        
        attachments = []
        for file in email_dir.iterdir():
            if file.is_file() and file.name != "attachments.json":
                attachments.append(file.name)
        
        return attachments
    
    async def cleanup_old_attachments(self, days: int = 30) -> int:
        """Clean up attachments older than specified days."""
        cutoff_time = datetime.now().timestamp() - (days * 24 * 60 * 60)
        cleaned_count = 0
        
        for email_dir in self.base_path.iterdir():
            if email_dir.is_dir():
                # Check if directory is old enough
                if email_dir.stat().st_mtime < cutoff_time:
                    try:
                        # Remove entire email directory
                        import shutil
                        shutil.rmtree(email_dir)
                        cleaned_count += 1
                        logger.info(f"Cleaned up old attachments for email {email_dir.name}")
                    except Exception as e:
                        logger.error(f"Failed to cleanup {email_dir}: {e}")
        
        return cleaned_count
    
    def get_storage_stats(self) -> Dict[str, Any]:
        """Get storage statistics."""
        total_size = 0
        total_files = 0
        email_count = 0
        
        for email_dir in self.base_path.iterdir():
            if email_dir.is_dir():
                email_count += 1
                for file in email_dir.iterdir():
                    if file.is_file():
                        total_files += 1
                        total_size += file.stat().st_size
        
        return {
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "total_files": total_files,
            "email_directories": email_count,
            "base_path": str(self.base_path)
        }