"""
Media Migration Module

Handles migration of media files from old folder structure to new structure.
"""

import os
import shutil
import logging
from pathlib import Path
from typing import Dict, List, NamedTuple, Optional
from datetime import datetime

from models import MediaResult, FileInfo, MediaFolderInfo
from utils import (
    safe_copy_file, safe_copy_directory, validate_media_file, 
    get_media_file_type, is_file_zero_size, format_file_size
)
from logger import create_migration_logger

logger = create_migration_logger('media')

class MediaMigrator:
    """Handles media file migration."""
    
    def __init__(self, source_media_path: str, target_media_path: str, shot_mapping: Dict[str, int]):
        """
        Initialize media migrator.
        
        Args:
            source_media_path: Path to source media directory
            target_media_path: Path to target media directory
            shot_mapping: Mapping of shot_name to shot_id
        """
        self.source_media_path = source_media_path
        self.target_media_path = target_media_path
        self.shot_mapping = shot_mapping
        self.logger = create_migration_logger('media.migrator')
        
    def migrate(self) -> bool:
        """
        Execute media migration.
        
        Returns:
            True if migration successful, False otherwise
        """
        errors = []
        warnings = []
        
        try:
            # ======== MEDIA MIGRATION PHASE START ========
            self.logger.info("=" * 60)
            self.logger.info("MEDIA MIGRATION PHASE STARTING")
            self.logger.info("=" * 60)
            self.logger.info("Starting media migration")
            
            # Create target media directory
            if not safe_copy_directory(self.target_media_path, self.target_media_path, overwrite=True):
                errors.append("Failed to create target media directory")
                return False
            
            # Migrate each shot folder
            total_shots = len(self.shot_mapping)
            migrated_shots = 0
            
            for shot_name, shot_id in self.shot_mapping.items():
                source_folder = os.path.join(self.source_media_path, shot_name)
                target_folder = os.path.join(self.target_media_path, str(shot_id))
                
                if os.path.exists(source_folder):
                    # Copy folder contents
                    migration_result = self._migrate_shot_folder(source_folder, target_folder)
                    errors.extend(migration_result.errors)
                    warnings.extend(migration_result.warnings)
                    
                    if migration_result.success:
                        migrated_shots += 1
                else:
                    warning_msg = f"Source folder not found: {source_folder}"
                    warnings.append(warning_msg)
                    self.logger.warning(warning_msg)
                
                # Log progress
                progress = (migrated_shots / total_shots) * 100
                self.logger.info(f"Shot folders migration progress: {progress:.1f}% ({migrated_shots}/{total_shots})")
            
            # Migrate asset folders (characters, locations, other)
            asset_migration_success = self.migrate_asset_folders()
            if not asset_migration_success:
                errors.append("Asset folder migration failed")
            
            # Validate video/thumbnail pairs
            validation_result = self._validate_media_files()
            errors.extend(validation_result.errors)
            warnings.extend(validation_result.warnings)
            
            # Log results
            if errors:
                self.logger.error(f"Media migration completed with {len(errors)} errors")
                for error in errors:
                    self.logger.error(f"  - {error}")
            
            if warnings:
                self.logger.warning(f"Media migration completed with {len(warnings)} warnings")
                for warning in warnings:
                    self.logger.warning(f"  - {warning}")
            
            success = len(errors) == 0
            self.logger.info(f"Media migration completed: {'SUCCESS' if success else 'FAILED'}")
            
            return success
            
        except Exception as e:
            error_msg = f"Media migration failed: {e}"
            self.logger.error(error_msg)
            return False
    
    def _migrate_shot_folder(self, source_folder: str, target_folder: str) -> MediaResult:
        """Migrate a single shot folder."""
        errors = []
        warnings = []
        
        try:
            self.logger.debug(f"Migrating shot folder: {source_folder} -> {target_folder}")
            
            # Create target folder
            os.makedirs(target_folder, exist_ok=True)
            
            # Copy all files and subdirectories
            file_count = 0
            for item in os.listdir(source_folder):
                source_item = os.path.join(source_folder, item)
                target_item = os.path.join(target_folder, item)
                
                if os.path.isfile(source_item):
                    # Validate file before copying
                    file_info = validate_media_file(source_item)
                    
                    if file_info['is_zero_size']:
                        warning_msg = f"Zero-size file: {source_item}"
                        warnings.append(warning_msg)
                        self.logger.warning(warning_msg)
                    
                    # Always attempt to copy files, including zero-size placeholders
                    if safe_copy_file(source_item, target_item):
                        file_count += 1
                        # Log zero-size files as warnings (not errors)
                        if file_info['is_zero_size']:
                            warning_msg = f"Copied zero-size placeholder file: {source_item}"
                            warnings.append(warning_msg)
                            self.logger.warning(warning_msg)
                    else:
                        error_msg = f"Failed to copy file: {source_item}"
                        errors.append(error_msg)
                        self.logger.error(error_msg)
                
                elif os.path.isdir(source_item):
                    # Copy directory
                    if safe_copy_directory(source_item, target_item):
                        # Count files in copied directory
                        for root, dirs, files in os.walk(target_item):
                            file_count += len(files)
                    else:
                        error_msg = f"Failed to copy directory: {source_item}"
                        errors.append(error_msg)
                        self.logger.error(error_msg)
            
            if file_count == 0:
                warning_msg = f"No files copied from {source_folder}"
                warnings.append(warning_msg)
                self.logger.warning(warning_msg)
            
            success = len(errors) == 0
            return MediaResult(success=success, errors=errors, warnings=warnings)
            
        except Exception as e:
            error_msg = f"Failed to migrate folder {source_folder}: {e}"
            errors.append(error_msg)
            self.logger.error(error_msg)
            return MediaResult(success=False, errors=errors, warnings=warnings)
    
    def migrate_asset_folders(self) -> bool:
        """Migrate asset folders (characters, locations, other) from source to target."""
        errors = []
        warnings = []
        
        try:
            self.logger.info("Migrating asset folders (characters, locations, other)")
            
            # Asset subdirectories to migrate
            asset_subdirs = ['characters', 'locations', 'other']
            
            for subdir in asset_subdirs:
                source_subdir = os.path.join(self.source_media_path, subdir)
                target_subdir = os.path.join(self.target_media_path, subdir)
                
                if os.path.exists(source_subdir):
                    # Copy the entire subdirectory
                    if safe_copy_directory(source_subdir, target_subdir):
                        # Count files in copied directory
                        file_count = 0
                        for root, dirs, files in os.walk(target_subdir):
                            file_count += len(files)
                        
                        self.logger.info(f"Successfully migrated {subdir} folder: {file_count} files")
                    else:
                        error_msg = f"Failed to migrate {subdir} folder"
                        errors.append(error_msg)
                        self.logger.error(error_msg)
                else:
                    warning_msg = f"Asset subdirectory not found: {source_subdir}"
                    warnings.append(warning_msg)
                    self.logger.warning(warning_msg)
            
            # Log results
            if errors:
                self.logger.error(f"Asset folder migration completed with {len(errors)} errors")
                for error in errors:
                    self.logger.error(f"  - {error}")
            
            if warnings:
                self.logger.warning(f"Asset folder migration completed with {len(warnings)} warnings")
                for warning in warnings:
                    self.logger.warning(f"  - {warning}")
            
            success = len(errors) == 0
            self.logger.info(f"Asset folder migration completed: {'SUCCESS' if success else 'FAILED'}")
            
            return success
            
        except Exception as e:
            error_msg = f"Asset folder migration failed: {e}"
            self.logger.error(error_msg)
            return False
    
    def _validate_media_files(self) -> MediaResult:
        """Validate media files for completeness."""
        errors = []
        warnings = []
        
        try:
            # ======== MEDIA VALIDATION PHASE START ========
            self.logger.info("=" * 60)
            self.logger.info("MEDIA VALIDATION PHASE STARTING")
            self.logger.info("=" * 60)
            self.logger.info("Validating media files")
            
            if not os.path.exists(self.target_media_path):
                error_msg = "Media directory does not exist"
                errors.append(error_msg)
                self.logger.error(error_msg)
                return MediaResult(success=False, errors=errors, warnings=warnings)
            
            # Get all media folders
            media_folders = []
            for item in os.listdir(self.target_media_path):
                item_path = os.path.join(self.target_media_path, item)
                if os.path.isdir(item_path):
                    media_folders.append(item)
            
            if not media_folders:
                warning_msg = "No media folders found"
                warnings.append(warning_msg)
                self.logger.warning(warning_msg)
                return MediaResult(success=True, errors=errors, warnings=warnings)
            
            # Validate each media folder
            total_folders = len(media_folders)
            validated_folders = 0
            
            for folder in media_folders:
                folder_path = os.path.join(self.target_media_path, folder)
                
                # Get folder validation result
                folder_result = self._validate_media_folder(folder_path)
                errors.extend(folder_result.errors)
                warnings.extend(folder_result.warnings)
                
                validated_folders += 1
                
                # Log progress
                if validated_folders % 10 == 0 or validated_folders == total_folders:
                    progress = (validated_folders / total_folders) * 100
                    self.logger.info(f"Media validation progress: {progress:.1f}% ({validated_folders}/{total_folders})")
            
            success = len(errors) == 0
            self.logger.info(f"Media validation completed: {'SUCCESS' if success else 'FAILED'}")
            
            return MediaResult(success=success, errors=errors, warnings=warnings)
            
        except Exception as e:
            error_msg = f"Media validation failed: {e}"
            errors.append(error_msg)
            self.logger.error(error_msg)
            return MediaResult(success=False, errors=errors, warnings=warnings)
    
    def _validate_media_folder(self, folder_path: str) -> MediaResult:
        """Validate a single media folder."""
        errors = []
        warnings = []
        
        try:
            # Get folder name (should be shot_id)
            folder_name = os.path.basename(folder_path)
            
            # Find corresponding shot_name from mapping
            shot_name = None
            for name, shot_id in self.shot_mapping.items():
                if str(shot_id) == folder_name:
                    shot_name = name
                    break
            
            # Get all files in folder
            files = []
            for item in os.listdir(folder_path):
                item_path = os.path.join(folder_path, item)
                if os.path.isfile(item_path):
                    files.append(item)
            
            # Categorize files
            video_files = [f for f in files if f.startswith('video_') and f.endswith('.mp4')]
            thumbnail_files = [f for f in files if f.startswith('video_') and f.endswith('.png')]
            image_files = [f for f in files if f.startswith('image_')]
            base_image_files = [f for f in files if f.startswith('base_') and f.endswith('.png')]
            asset_files = [f for f in files if f.startswith('asset_')]
            
            # Build context message
            context_msg = f" (Shot: {shot_name} → Folder: {folder_name})" if shot_name else f" (Folder: {folder_name})"
            
            # Enhanced video/thumbnail validation logic
            for video_file in video_files:
                video_path = os.path.join(folder_path, video_file)
                thumbnail_name = video_file.replace('.mp4', '.png')
                thumbnail_path = os.path.join(folder_path, thumbnail_name)
                
                # Check if video file has size
                video_is_placeholder = is_file_zero_size(video_path)
                
                if video_is_placeholder:
                    # Zero-size video placeholder - create matching zero-size PNG if needed
                    if thumbnail_name not in thumbnail_files:
                        # Create zero-size placeholder PNG
                        try:
                            with open(thumbnail_path, 'wb') as f:
                                f.write(b'')  # Create empty file
                            warning_msg = f"Created zero-size thumbnail placeholder for {video_file}{context_msg}"
                            warnings.append(warning_msg)
                            self.logger.warning(warning_msg)
                        except Exception as e:
                            error_msg = f"Failed to create thumbnail placeholder for {video_file}{context_msg}: {e}"
                            errors.append(error_msg)
                            self.logger.error(error_msg)
                    else:
                        # Thumbnail exists, ensure it's also zero-size
                        if not is_file_zero_size(thumbnail_path):
                            warning_msg = f"Video placeholder {video_file} has non-zero-size thumbnail{context_msg}"
                            warnings.append(warning_msg)
                            self.logger.warning(warning_msg)
                else:
                    # Valid video file - must have valid thumbnail
                    if thumbnail_name not in thumbnail_files:
                        error_msg = f"Missing thumbnail for valid video {video_file}{context_msg} - This is required for AIMMS app"
                        errors.append(error_msg)
                        self.logger.error(error_msg)
                    else:
                        # Check thumbnail is not zero size
                        if is_file_zero_size(thumbnail_path):
                            error_msg = f"Valid video {video_file} has zero-size thumbnail{context_msg} - This is required for AIMMS app"
                            errors.append(error_msg)
                            self.logger.error(error_msg)
                        else:
                            # Both video and thumbnail are valid
                            self.logger.debug(f"Valid video/thumbnail pair: {video_file}/{thumbnail_name}{context_msg}")
            
            # Check for orphaned thumbnails (not errors, just warnings)
            for thumbnail_file in thumbnail_files:
                video_name = thumbnail_file.replace('.png', '.mp4')
                if video_name not in video_files:
                    warning_msg = f"Orphaned thumbnail (no video): {thumbnail_file}{context_msg}"
                    warnings.append(warning_msg)
                    self.logger.warning(warning_msg)
            
            # Check for zero-size files (already handled above, but keep for other file types)
            for file_name in files:
                file_path = os.path.join(folder_path, file_name)
                if is_file_zero_size(file_path) and not file_name.startswith('video_'):
                    warning_msg = f"Zero-size file: {file_path}{context_msg}"
                    warnings.append(warning_msg)
                    self.logger.warning(warning_msg)
            
            # Log folder summary with context
            context_info = f"Shot: {shot_name} → Folder: {folder_name}" if shot_name else f"Folder: {folder_name}"
            self.logger.debug(f"Folder {context_info}: "
                            f"{len(video_files)} videos, "
                            f"{len(thumbnail_files)} thumbnails, "
                            f"{len(image_files)} images, "
                            f"{len(base_image_files)} base_images, "
                            f"{len(asset_files)} assets")
            
            success = len(errors) == 0
            return MediaResult(success=success, errors=errors, warnings=warnings)
            
        except Exception as e:
            error_msg = f"Failed to validate folder {folder_path}: {e}"
            errors.append(error_msg)
            self.logger.error(error_msg)
            return MediaResult(success=False, errors=errors, warnings=warnings)
    
    def get_media_info(self) -> Dict:
        """
        Get comprehensive information about media files.
        
        Returns:
            Dictionary with media information
        """
        try:
            media_info = {
                'source_path': self.source_media_path,
                'target_path': self.target_media_path,
                'shot_mapping': self.shot_mapping,
                'folders': {},
                'summary': {
                    'total_folders': 0,
                    'total_files': 0,
                    'total_size_mb': 0.0,
                    'video_files': 0,
                    'thumbnail_files': 0,
                    'image_files': 0,
                    'asset_files': 0
                }
            }
            
            if not os.path.exists(self.target_media_path):
                return media_info
            
            # Analyze each media folder
            for folder_name in os.listdir(self.target_media_path):
                folder_path = os.path.join(self.target_media_path, folder_name)
                
                if not os.path.isdir(folder_path):
                    continue
                
                folder_info = self._analyze_media_folder(folder_path)
                media_info['folders'][folder_name] = folder_info
                
                # Update summary
                media_info['summary']['total_folders'] += 1
                media_info['summary']['total_files'] += folder_info['file_count']
                media_info['summary']['total_size_mb'] += folder_info['total_size_mb']
                media_info['summary']['video_files'] += folder_info['video_count']
                media_info['summary']['thumbnail_files'] += folder_info['thumbnail_count']
                media_info['summary']['image_files'] += folder_info['image_count']
                media_info['summary']['base_image_files'] += folder_info['base_image_count']
                media_info['summary']['asset_files'] += folder_info['asset_count']
            
            return media_info
            
        except Exception as e:
            self.logger.error(f"Failed to get media info: {e}")
            return {}
    
    def _analyze_media_folder(self, folder_path: str) -> Dict:
        """Analyze a single media folder."""
        folder_info = {
            'path': folder_path,
            'file_count': 0,
            'total_size_mb': 0.0,
            'video_count': 0,
            'thumbnail_count': 0,
            'image_count': 0,
            'base_image_count': 0,
            'asset_count': 0,
            'files': []
        }
        
        try:
            for file_name in os.listdir(folder_path):
                file_path = os.path.join(folder_path, file_name)
                
                if not os.path.isfile(file_path):
                    continue
                
                # Get file info
                file_info = validate_media_file(file_path)
                
                folder_info['file_count'] += 1
                folder_info['total_size_mb'] += file_info['size_mb']
                
                # Categorize file
                file_type = get_media_file_type(file_name)
                
                if file_type == 'video':
                    folder_info['video_count'] += 1
                elif file_type == 'video_thumbnail':
                    folder_info['thumbnail_count'] += 1
                elif file_type == 'image':
                    folder_info['image_count'] += 1
                elif file_type == 'base_image':
                    folder_info['base_image_count'] += 1
                elif file_type == 'asset':
                    folder_info['asset_count'] += 1
                
                folder_info['files'].append({
                    'name': file_name,
                    'type': file_type,
                    'size_mb': file_info['size_mb'],
                    'is_zero_size': file_info['is_zero_size']
                })
            
            return folder_info
            
        except Exception as e:
            self.logger.error(f"Failed to analyze folder {folder_path}: {e}")
            return folder_info

def validate_media_consistency(source_media_path: str, target_media_path: str, shot_mapping: Dict[str, int]) -> MediaResult:
    """
    Validate consistency between source and target media.
    
    Args:
        source_media_path: Source media path
        target_media_path: Target media path
        shot_mapping: Shot name to ID mapping
        
    Returns:
        Validation result
    """
    errors = []
    warnings = []
    
    try:
        logger.info("Validating media consistency")
        
        # Check source folders exist
        for shot_name in shot_mapping.keys():
            source_folder = os.path.join(source_media_path, shot_name)
            if not os.path.exists(source_folder):
                warning_msg = f"Source folder missing: {source_folder}"
                warnings.append(warning_msg)
                logger.warning(warning_msg)
        
        # Check target folders exist
        for shot_id in shot_mapping.values():
            target_folder = os.path.join(target_media_path, str(shot_id))
            if not os.path.exists(target_folder):
                error_msg = f"Target folder missing: {target_folder}"
                errors.append(error_msg)
                logger.error(error_msg)
        
        success = len(errors) == 0
        return MediaResult(success=success, errors=errors, warnings=warnings)
        
    except Exception as e:
        error_msg = f"Media consistency validation failed: {e}"
        errors.append(error_msg)
        logger.error(error_msg)
        return MediaResult(success=False, errors=errors, warnings=warnings)