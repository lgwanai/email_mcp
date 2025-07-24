"""Archive management for automatic extraction of compressed attachments."""

import os
import asyncio
import aiofiles
from pathlib import Path
from typing import List, Dict, Any, Optional, Set
import logging
import json
import zipfile
import tarfile
import gzip
import bz2
import lzma
from datetime import datetime

logger = logging.getLogger(__name__)


class ArchiveManager:
    """Manages automatic extraction of compressed attachments."""
    
    # Supported archive formats
    ARCHIVE_EXTENSIONS = {
        '.zip': 'zip',
        '.rar': 'rar',
        '.7z': '7z',
        '.tar': 'tar',
        '.tar.gz': 'tar.gz',
        '.tgz': 'tar.gz',
        '.tar.bz2': 'tar.bz2',
        '.tbz2': 'tar.bz2',
        '.tar.xz': 'tar.xz',
        '.txz': 'tar.xz',
        '.gz': 'gz',
        '.bz2': 'bz2',
        '.xz': 'xz'
    }
    
    def __init__(self):
        self.extracted_files = set()  # Track extracted files to avoid infinite loops
    
    def is_archive(self, file_path: Path) -> bool:
        """Check if a file is a supported archive format."""
        file_path_str = str(file_path).lower()
        
        # Check for compound extensions first (e.g., .tar.gz)
        for ext in ['.tar.gz', '.tar.bz2', '.tar.xz']:
            if file_path_str.endswith(ext):
                return True
        
        # Check for single extensions
        suffix = file_path.suffix.lower()
        return suffix in self.ARCHIVE_EXTENSIONS
    
    def get_archive_type(self, file_path: Path) -> Optional[str]:
        """Get the archive type for a file."""
        file_path_str = str(file_path).lower()
        
        # Check for compound extensions first
        for ext in ['.tar.gz', '.tar.bz2', '.tar.xz']:
            if file_path_str.endswith(ext):
                return self.ARCHIVE_EXTENSIONS[ext]
        
        # Check for single extensions
        suffix = file_path.suffix.lower()
        return self.ARCHIVE_EXTENSIONS.get(suffix)
    
    def generate_unique_name(self, base_path: Path, desired_name: str) -> str:
        """Generate a unique name if the desired name already exists."""
        if not (base_path / desired_name).exists():
            return desired_name
        
        # Extract name and extension
        path_obj = Path(desired_name)
        stem = path_obj.stem
        suffix = path_obj.suffix
        
        counter = 1
        while True:
            new_name = f"{stem}_{counter}{suffix}"
            if not (base_path / new_name).exists():
                return new_name
            counter += 1
    
    async def extract_zip(self, archive_path: Path, extract_to: Path) -> List[Path]:
        """Extract ZIP archive."""
        extracted_files = []
        
        try:
            with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                for member in zip_ref.namelist():
                    # Sanitize member name
                    safe_name = self.sanitize_path(member)
                    if not safe_name:
                        continue
                    
                    # Generate unique name if needed
                    unique_name = self.generate_unique_name(extract_to, safe_name)
                    target_path = extract_to / unique_name
                    
                    # Create parent directories
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    # Extract file
                    with zip_ref.open(member) as source:
                        async with aiofiles.open(target_path, 'wb') as target:
                            await target.write(source.read())
                    
                    extracted_files.append(target_path)
                    logger.debug(f"Extracted: {member} -> {target_path}")
        
        except Exception as e:
            logger.error(f"Failed to extract ZIP archive {archive_path}: {e}")
            raise
        
        return extracted_files
    
    async def extract_tar(self, archive_path: Path, extract_to: Path, mode: str = 'r') -> List[Path]:
        """Extract TAR archive (including compressed variants)."""
        extracted_files = []
        
        try:
            with tarfile.open(archive_path, mode) as tar_ref:
                for member in tar_ref.getmembers():
                    if not member.isfile():
                        continue
                    
                    # Sanitize member name
                    safe_name = self.sanitize_path(member.name)
                    if not safe_name:
                        continue
                    
                    # Generate unique name if needed
                    unique_name = self.generate_unique_name(extract_to, safe_name)
                    target_path = extract_to / unique_name
                    
                    # Create parent directories
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    # Extract file
                    source = tar_ref.extractfile(member)
                    if source:
                        async with aiofiles.open(target_path, 'wb') as target:
                            await target.write(source.read())
                        source.close()
                    
                    extracted_files.append(target_path)
                    logger.debug(f"Extracted: {member.name} -> {target_path}")
        
        except Exception as e:
            logger.error(f"Failed to extract TAR archive {archive_path}: {e}")
            raise
        
        return extracted_files
    
    async def extract_single_compressed(self, archive_path: Path, extract_to: Path, compression_type: str) -> List[Path]:
        """Extract single compressed files (gz, bz2, xz)."""
        extracted_files = []
        
        try:
            # Determine output filename (remove compression extension)
            output_name = archive_path.stem
            if not output_name:
                output_name = "extracted_file"
            
            # Generate unique name if needed
            unique_name = self.generate_unique_name(extract_to, output_name)
            target_path = extract_to / unique_name
            
            # Open compressed file based on type
            if compression_type == 'gz':
                source_file = gzip.open(archive_path, 'rb')
            elif compression_type == 'bz2':
                source_file = bz2.open(archive_path, 'rb')
            elif compression_type == 'xz':
                source_file = lzma.open(archive_path, 'rb')
            else:
                raise ValueError(f"Unsupported compression type: {compression_type}")
            
            # Extract content
            async with aiofiles.open(target_path, 'wb') as target:
                content = source_file.read()
                await target.write(content)
            
            source_file.close()
            extracted_files.append(target_path)
            logger.debug(f"Extracted: {archive_path} -> {target_path}")
        
        except Exception as e:
            logger.error(f"Failed to extract compressed file {archive_path}: {e}")
            raise
        
        return extracted_files
    
    def sanitize_path(self, path: str) -> str:
        """Sanitize extracted file path to prevent directory traversal."""
        # Remove leading slashes and resolve path
        path = path.lstrip('/')
        
        # Split path and sanitize each component
        parts = []
        for part in Path(path).parts:
            # Skip dangerous parts
            if part in ['.', '..'] or not part.strip():
                continue
            
            # Sanitize filename
            from .utils import sanitize_filename
            safe_part = sanitize_filename(part)
            if safe_part:
                parts.append(safe_part)
        
        return '/'.join(parts) if parts else ''
    
    async def extract_archive(self, archive_path: Path, extract_to: Path) -> List[Path]:
        """Extract an archive file to the specified directory."""
        archive_type = self.get_archive_type(archive_path)
        
        if not archive_type:
            raise ValueError(f"Unsupported archive type: {archive_path}")
        
        logger.info(f"Extracting {archive_type} archive: {archive_path}")
        
        # Create extraction directory
        extract_to.mkdir(parents=True, exist_ok=True)
        
        # Extract based on archive type
        if archive_type == 'zip':
            return await self.extract_zip(archive_path, extract_to)
        elif archive_type == 'tar':
            return await self.extract_tar(archive_path, extract_to, 'r')
        elif archive_type == 'tar.gz':
            return await self.extract_tar(archive_path, extract_to, 'r:gz')
        elif archive_type == 'tar.bz2':
            return await self.extract_tar(archive_path, extract_to, 'r:bz2')
        elif archive_type == 'tar.xz':
            return await self.extract_tar(archive_path, extract_to, 'r:xz')
        elif archive_type in ['gz', 'bz2', 'xz']:
            return await self.extract_single_compressed(archive_path, extract_to, archive_type)
        elif archive_type in ['rar', '7z']:
            # These require external tools - log warning and skip
            logger.warning(f"Archive type {archive_type} requires external tools, skipping: {archive_path}")
            return []
        else:
            raise ValueError(f"Unsupported archive type: {archive_type}")
    
    async def extract_recursively(self, directory: Path, max_depth: int = 10) -> Dict[str, Any]:
        """Recursively extract all archives in a directory until no more archives are found."""
        extraction_log = {
            "total_extracted": 0,
            "extraction_rounds": [],
            "errors": []
        }
        
        depth = 0
        while depth < max_depth:
            # Find all archive files in the directory
            archive_files = []
            for file_path in directory.rglob('*'):
                if file_path.is_file() and self.is_archive(file_path):
                    # Skip if already processed
                    if str(file_path) not in self.extracted_files:
                        archive_files.append(file_path)
            
            if not archive_files:
                logger.info(f"No more archives found after {depth} rounds")
                break
            
            round_log = {
                "round": depth + 1,
                "archives_found": len(archive_files),
                "extracted_files": [],
                "errors": []
            }
            
            # Extract each archive
            for archive_path in archive_files:
                try:
                    # Mark as processed to avoid infinite loops
                    self.extracted_files.add(str(archive_path))
                    
                    # Extract to the same directory as the archive
                    extract_to = archive_path.parent
                    
                    extracted_files = await self.extract_archive(archive_path, extract_to)
                    
                    round_log["extracted_files"].extend([
                        {
                            "archive": str(archive_path),
                            "extracted_to": str(extract_to),
                            "files": [str(f) for f in extracted_files]
                        }
                    ])
                    
                    extraction_log["total_extracted"] += len(extracted_files)
                    
                    logger.info(f"Extracted {len(extracted_files)} files from {archive_path}")
                
                except Exception as e:
                    error_msg = f"Failed to extract {archive_path}: {e}"
                    logger.error(error_msg)
                    round_log["errors"].append(error_msg)
                    extraction_log["errors"].append(error_msg)
            
            extraction_log["extraction_rounds"].append(round_log)
            depth += 1
        
        if depth >= max_depth:
            warning_msg = f"Reached maximum extraction depth ({max_depth}), stopping to prevent infinite loops"
            logger.warning(warning_msg)
            extraction_log["errors"].append(warning_msg)
        
        return extraction_log
    
    async def process_email_attachments(self, email_dir: Path) -> Dict[str, Any]:
        """Process all attachments in an email directory, extracting archives recursively."""
        logger.info(f"Processing attachments in {email_dir}")
        
        if not email_dir.exists():
            return {"error": f"Email directory {email_dir} does not exist"}
        
        # Reset extracted files tracking for this email
        self.extracted_files.clear()
        
        # Start recursive extraction
        extraction_log = await self.extract_recursively(email_dir)
        
        # Save extraction log
        log_file = email_dir / "extraction_log.json"
        async with aiofiles.open(log_file, 'w', encoding='utf-8') as f:
            await f.write(json.dumps({
                "email_uid": email_dir.name,
                "extraction_time": datetime.now().isoformat(),
                "extraction_log": extraction_log
            }, indent=2, ensure_ascii=False))
        
        return extraction_log