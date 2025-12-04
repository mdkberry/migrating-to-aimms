"""
Utility Functions Module

Contains helper functions used across the migration tool.
"""

import uuid
import os
import shutil
from datetime import datetime
from typing import Optional, Dict, List, Any
import logging

logger = logging.getLogger('aimms_migration.utils')

def generate_uuid() -> str:
    """
    Generate a UUID string for take_id.
    
    Returns:
        UUID string
    """
    return str(uuid.uuid4())

def convert_date_to_utc(date_str: Optional[str]) -> str:
    """
    Convert date string to UTC ISO 8601 format.
    
    Args:
        date_str: Date string in various formats
        
    Returns:
        Date string in UTC ISO 8601 format with 'Z' suffix
    """
    if not date_str:
        return datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
    
    try:
        # Already in ISO format
        if date_str.endswith('Z'):
            return date_str
        
        # Try common formats
        for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%d']:
            try:
                dt = datetime.strptime(date_str, fmt)
                return dt.strftime('%Y-%m-%dT%H:%M:%SZ')
            except ValueError:
                continue
        
        # If all else fails, use current UTC time
        logger.warning(f"Could not parse date: {date_str}, using current time")
        return datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
        
    except Exception as e:
        logger.warning(f"Date conversion failed for {date_str}: {e}")
        return datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')

def update_file_path(file_path: str, shot_id: int, old_shot_name: Optional[str] = None) -> str:
    """
    Update file path to use shot_id instead of shot_name.
    
    Args:
        file_path: Original file path
        shot_id: New shot ID
        old_shot_name: Old shot name (optional, for explicit replacement)
        
    Returns:
        Updated file path
    """
    import re
    
    if old_shot_name:
        # Explicit replacement
        new_path = file_path.replace(f'media/{old_shot_name}', f'media/{shot_id}')
        return new_path
    
    # Pattern-based replacement
    match = re.search(r'media/([^/]+)', file_path)
    if match:
        old_name = match.group(1)
        new_path = file_path.replace(f'media/{old_name}', f'media/{shot_id}')
        return new_path
    
    return file_path

def safe_copy_file(src: str, dst: str, overwrite: bool = True) -> bool:
    """
    Safely copy a file with error handling.
    
    Args:
        src: Source file path
        dst: Destination file path
        overwrite: Whether to overwrite existing file
        
    Returns:
        True if copy successful, False otherwise
    """
    try:
        if os.path.exists(dst) and not overwrite:
            logger.warning(f"File already exists, skipping: {dst}")
            return False
        
        # Ensure destination directory exists
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        
        shutil.copy2(src, dst)
        return True
        
    except Exception as e:
        logger.error(f"Failed to copy {src} to {dst}: {e}")
        return False

def safe_copy_directory(src: str, dst: str, overwrite: bool = True) -> bool:
    """
    Safely copy a directory with error handling.
    
    Args:
        src: Source directory path
        dst: Destination directory path
        overwrite: Whether to overwrite existing files
        
    Returns:
        True if copy successful, False otherwise
    """
    try:
        if os.path.exists(dst) and not overwrite:
            logger.warning(f"Directory already exists, skipping: {dst}")
            return False
        
        shutil.copytree(src, dst, dirs_exist_ok=overwrite)
        return True
        
    except Exception as e:
        logger.error(f"Failed to copy directory {src} to {dst}: {e}")
        return False

def get_file_size_mb(file_path: str) -> float:
    """
    Get file size in megabytes.
    
    Args:
        file_path: Path to file
        
    Returns:
        File size in MB
    """
    try:
        size_bytes = os.path.getsize(file_path)
        return size_bytes / (1024 * 1024)
    except Exception:
        return 0.0

def is_file_zero_size(file_path: str) -> bool:
    """
    Check if file is zero size.
    
    Args:
        file_path: Path to file
        
    Returns:
        True if file is zero size
    """
    try:
        return os.path.getsize(file_path) == 0
    except Exception:
        return True

def validate_file_path(file_path: str) -> bool:
    """
    Validate that file path is safe and within expected directory.
    
    Args:
        file_path: File path to validate
        
    Returns:
        True if path is valid
    """
    try:
        # Check for absolute path
        if not os.path.isabs(file_path):
            return False
        
        # Check for dangerous patterns
        dangerous_patterns = ['..', '/etc/', '/root/', '/home/']
        for pattern in dangerous_patterns:
            if pattern in file_path:
                return False
        
        return True
        
    except Exception:
        return False

def create_directory_if_not_exists(path: str) -> bool:
    """
    Create directory if it doesn't exist.
    
    Args:
        path: Directory path
        
    Returns:
        True if directory exists or created successfully
    """
    try:
        os.makedirs(path, exist_ok=True)
        return True
    except Exception as e:
        logger.error(f"Failed to create directory {path}: {e}")
        return False

def get_timestamp() -> str:
    """
    Get current timestamp for naming files.
    
    Returns:
        Timestamp string in YYYYMMDD_HHMMSS format
    """
    return datetime.now().strftime('%Y%m%d_%H%M%S')

def format_file_size(size_bytes: int) -> str:
    """
    Format file size in human-readable format.
    
    Args:
        size_bytes: Size in bytes
        
    Returns:
        Human-readable size string
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} PB"

def validate_media_file(file_path: str) -> Dict[str, Any]:
    """
    Validate media file and return metadata.
    
    Args:
        file_path: Path to media file
        
    Returns:
        Dictionary with validation results
    """
    result = {
        'exists': False,
        'size': 0,
        'size_mb': 0.0,
        'is_zero_size': True,
        'is_valid': False
    }
    
    try:
        if not os.path.exists(file_path):
            return result
        
        result['exists'] = True
        result['size'] = os.path.getsize(file_path)
        result['size_mb'] = get_file_size_mb(file_path)
        result['is_zero_size'] = result['size'] == 0
        result['is_valid'] = result['size'] > 0
        
    except Exception as e:
        logger.error(f"Failed to validate file {file_path}: {e}")
    
    return result

def get_media_file_type(file_path: str) -> str:
    """
    Determine media file type based on extension and naming pattern.
    
    Args:
        file_path: Path to media file
        
    Returns:
        File type string
    """
    filename = os.path.basename(file_path).lower()
    
    if filename.startswith('video_'):
        if filename.endswith('.mp4'):
            return 'video'
        elif filename.endswith('.png'):
            return 'video_thumbnail'
    elif filename.startswith('image_'):
        if filename.endswith('.png'):
            return 'image'
        elif filename.endswith('.jpg') or filename.endswith('.jpeg'):
            return 'image'
    elif filename.startswith('asset_'):
        return 'asset'
    
    return 'unknown'

def batch_process_items(items: List[Any], batch_size: int = 100) -> List[List[Any]]:
    """
    Split items into batches for processing.
    
    Args:
        items: List of items to batch
        batch_size: Maximum size of each batch
        
    Returns:
        List of batches
    """
    if batch_size <= 0:
        return [items]
    
    return [items[i:i + batch_size] for i in range(0, len(items), batch_size)]

def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """
    Safely divide two numbers.
    
    Args:
        numerator: Numerator value
        denominator: Denominator value
        default: Default value if division fails
        
    Returns:
        Division result or default value
    """
    try:
        if denominator == 0:
            return default
        return numerator / denominator
    except (TypeError, ValueError):
        return default

def format_duration(seconds: float) -> str:
    """
    Format duration in seconds to human-readable format.
    
    Args:
        seconds: Duration in seconds
        
    Returns:
        Human-readable duration string
    """
    if seconds < 60:
        return f"{seconds:.1f}s"
    
    minutes = seconds / 60
    if minutes < 60:
        return f"{minutes:.1f}m"
    
    hours = minutes / 60
    return f"{hours:.1f}h"

def check_disk_space(path: str, required_mb: int = 100) -> bool:
    """
    Check if there's enough disk space available.
    
    Args:
        path: Path to check disk space for
        required_mb: Required space in MB
        
    Returns:
        True if enough space available
    """
    try:
        import shutil
        total, used, free = shutil.disk_usage(path)
        free_mb = free // (1024 * 1024)
        return free_mb >= required_mb
    except Exception as e:
        logger.error(f"Failed to check disk space: {e}")
        return False