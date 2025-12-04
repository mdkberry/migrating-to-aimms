"""
Validation Module

Handles validation of migration completeness and correctness.
"""

import sqlite3
import os
import logging
from typing import Dict, List, NamedTuple, Optional

from models import ValidationResult, DatabaseInfo, ShotInfo, TakeInfo, AssetInfo
from utils import validate_media_file, get_media_file_type, is_file_zero_size
from logger import create_migration_logger

logger = create_migration_logger('validation')

class Validator:
    """Handles migration validation."""
    
    def __init__(self, db_path: str, media_path: str, shot_mapping: Dict[str, int]):
        """
        Initialize validator.
        
        Args:
            db_path: Path to target database
            media_path: Path to target media directory
            shot_mapping: Shot name to ID mapping
        """
        self.db_path = db_path
        self.media_path = media_path
        self.shot_mapping = shot_mapping
        self.logger = create_migration_logger('validation.validator')
        
    def validate(self) -> ValidationResult:
        """
        Execute complete validation.
        
        Returns:
            ValidationResult with success status and issues
        """
        errors = []
        warnings = []
        
        try:
            # ======== VALIDATION PHASE START ========
            self.logger.info("=" * 60)
            self.logger.info("VALIDATION PHASE STARTING")
            self.logger.info("=" * 60)
            self.logger.info("Starting validation process")
            
            # Database validation
            db_result = self._validate_database()
            errors.extend(db_result.errors)
            warnings.extend(db_result.warnings)
            
            # Media validation
            media_result = self._validate_media()
            errors.extend(media_result.errors)
            warnings.extend(media_result.warnings)
            
            # Cross-validation
            cross_result = self._validate_cross_consistency()
            errors.extend(cross_result.errors)
            warnings.extend(cross_result.warnings)
            
            # Check for orphaned asset files
            orphaned_result = self._check_orphaned_asset_files()
            errors.extend(orphaned_result.errors)
            warnings.extend(orphaned_result.warnings)
            
            success = len(errors) == 0
            self.logger.info(f"Validation completed: {'SUCCESS' if success else 'FAILED'}")
            
            return ValidationResult(success=success, errors=errors, warnings=warnings)
            
        except Exception as e:
            error_msg = f"Validation failed: {e}"
            self.logger.error(error_msg)
            return ValidationResult(success=False, errors=[error_msg], warnings=[])
    
    def _validate_database(self) -> ValidationResult:
        """Validate database structure and data."""
        errors = []
        warnings = []
        
        try:
            self.logger.info("Validating database")
            
            if not os.path.exists(self.db_path):
                error_msg = f"Database file not found: {self.db_path}"
                errors.append(error_msg)
                self.logger.error(error_msg)
                return ValidationResult(success=False, errors=errors, warnings=warnings)
            
            with sqlite3.connect(self.db_path) as conn:
                # Check table existence
                required_tables = ['shots', 'takes', 'assets', 'meta', 'deleted_shots']
                for table in required_tables:
                    cursor = conn.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
                    if not cursor.fetchone():
                        error_msg = f"Missing table: {table}"
                        errors.append(error_msg)
                        self.logger.error(error_msg)
                
                if errors:
                    return ValidationResult(success=False, errors=errors, warnings=warnings)
                
                # Check shots table data
                cursor = conn.execute("SELECT COUNT(*) FROM shots")
                shot_count = cursor.fetchone()[0]
                if shot_count == 0:
                    warning_msg = "No shots found in database"
                    warnings.append(warning_msg)
                    self.logger.warning(warning_msg)
                
                # Check takes table data
                cursor = conn.execute("SELECT COUNT(*) FROM takes")
                takes_count = cursor.fetchone()[0]
                if takes_count == 0:
                    warning_msg = "No takes found in database"
                    warnings.append(warning_msg)
                    self.logger.warning(warning_msg)
                
                # Check foreign key relationships
                cursor = conn.execute('''
                    SELECT COUNT(*) FROM takes t 
                    LEFT JOIN shots s ON t.shot_id = s.shot_id 
                    WHERE s.shot_id IS NULL
                ''')
                orphaned_takes = cursor.fetchone()[0]
                if orphaned_takes > 0:
                    error_msg = f"Found {orphaned_takes} takes with invalid shot_id references"
                    errors.append(error_msg)
                    self.logger.error(error_msg)
                
                # Check assets foreign key relationships
                cursor = conn.execute('''
                    SELECT COUNT(*) FROM assets a
                    WHERE a.id_key NOT LIKE 'asset_%'
                ''')
                invalid_assets = cursor.fetchone()[0]
                if invalid_assets > 0:
                    warning_msg = f"Found {invalid_assets} assets with non-standard ID format"
                    warnings.append(warning_msg)
                    self.logger.warning(warning_msg)
                
                # Check version numbers
                cursor = conn.execute("SELECT value FROM meta WHERE key='schema_version'")
                schema_version = cursor.fetchone()
                if schema_version and schema_version[0] != '1':
                    warning_msg = f"Unexpected schema_version: {schema_version[0]}"
                    warnings.append(warning_msg)
                    self.logger.warning(warning_msg)
                
                cursor = conn.execute("SELECT value FROM meta WHERE key='app_version'")
                app_version = cursor.fetchone()
                if app_version and app_version[0] != '1.0':
                    warning_msg = f"Unexpected app_version: {app_version[0]}"
                    warnings.append(warning_msg)
                    self.logger.warning(warning_msg)
                
                # Check for duplicate shot names
                cursor = conn.execute('''
                    SELECT shot_name, COUNT(*) 
                    FROM shots 
                    GROUP BY shot_name 
                    HAVING COUNT(*) > 1
                ''')
                duplicates = cursor.fetchall()
                if duplicates:
                    warning_msg = f"Found duplicate shot names: {[d[0] for d in duplicates]}"
                    warnings.append(warning_msg)
                    self.logger.warning(warning_msg)
                
                # Check date formats
                cursor = conn.execute("SELECT created_date FROM shots LIMIT 10")
                date_samples = [row[0] for row in cursor.fetchall()]
                
                for date_str in date_samples:
                    if date_str and not date_str.endswith('Z'):
                        warning_msg = f"Non-UTC date format found: {date_str}"
                        warnings.append(warning_msg)
                        self.logger.warning(warning_msg)
                        break
                
                self.logger.info("Database validation completed successfully")
                return ValidationResult(success=True, errors=errors, warnings=warnings)
                
        except Exception as e:
            error_msg = f"Database validation failed: {e}"
            errors.append(error_msg)
            self.logger.error(error_msg)
            return ValidationResult(success=False, errors=errors, warnings=warnings)
    
    def _validate_media(self) -> ValidationResult:
        """Validate media files."""
        errors = []
        warnings = []
        
        try:
            self.logger.info("Validating media files")
            
            if not os.path.exists(self.media_path):
                error_msg = "Media directory does not exist"
                errors.append(error_msg)
                self.logger.error(error_msg)
                return ValidationResult(success=False, errors=errors, warnings=warnings)
            
            # Check for media folders
            media_folders = [f for f in os.listdir(self.media_path)
                           if os.path.isdir(os.path.join(self.media_path, f))]
            
            if not media_folders:
                warning_msg = "No media folders found"
                warnings.append(warning_msg)
                self.logger.warning(warning_msg)
                return ValidationResult(success=True, errors=errors, warnings=warnings)
            
            # Check for asset subdirectories (characters, locations, other)
            asset_subdirs = ['characters', 'locations', 'other']
            for subdir in asset_subdirs:
                subdir_path = os.path.join(self.media_path, subdir)
                if os.path.exists(subdir_path):
                    self.logger.info(f"Found asset subdirectory: {subdir}")
            
            # Validate each media folder
            total_folders = len(media_folders)
            validated_folders = 0
            
            # Asset subdirectories to exclude from shot validation
            asset_subdirs = {'characters', 'locations', 'other'}
            
            for folder in media_folders:
                folder_path = os.path.join(self.media_path, folder)
                
                # Skip asset folders - they don't need to correspond to shot_ids
                # Asset folders (characters, locations, other) are validated separately
                if folder in asset_subdirs:
                    self.logger.info(f"Asset folder '{folder}' - validated separately (contains 3D models/textures)")
                    validated_folders += 1
                    continue
                
                # Check if folder corresponds to a shot_id
                try:
                    shot_id = int(folder)
                    if str(shot_id) not in [str(v) for v in self.shot_mapping.values()]:
                        warning_msg = f"Media folder {folder} does not correspond to any shot_id"
                        warnings.append(warning_msg)
                        self.logger.warning(warning_msg)
                except ValueError:
                    warning_msg = f"Media folder {folder} is not a valid shot_id"
                    warnings.append(warning_msg)
                    self.logger.warning(warning_msg)
                
                # Check for files in folder
                files = os.listdir(folder_path)
                if not files:
                    warning_msg = f"Empty media folder: {folder}"
                    warnings.append(warning_msg)
                    self.logger.warning(warning_msg)
                
                # Validate individual files
                folder_result = self._validate_media_folder(folder_path)
                errors.extend(folder_result.errors)
                warnings.extend(folder_result.warnings)
                
                validated_folders += 1
                
                # Log progress
                if validated_folders % 10 == 0 or validated_folders == total_folders:
                    progress = (validated_folders / total_folders) * 100
                    self.logger.info(f"Media validation progress: {progress:.1f}% ({validated_folders}/{total_folders})")
            
            self.logger.info("Media validation completed successfully")
            return ValidationResult(success=True, errors=errors, warnings=warnings)
            
        except Exception as e:
            error_msg = f"Media validation failed: {e}"
            errors.append(error_msg)
            self.logger.error(error_msg)
            return ValidationResult(success=False, errors=errors, warnings=warnings)
    
    def _validate_media_folder(self, folder_path: str) -> ValidationResult:
        """Validate a single media folder."""
        errors = []
        warnings = []
        
        try:
            files = []
            for item in os.listdir(folder_path):
                item_path = os.path.join(folder_path, item)
                if os.path.isfile(item_path):
                    files.append(item)
            
            # Categorize files
            video_files = [f for f in files if f.startswith('video_') and f.endswith('.mp4')]
            thumbnail_files = [f for f in files if f.startswith('video_') and f.endswith('.png')]
            image_files = [f for f in files if f.startswith('image_')]
            asset_files = [f for f in files if f.startswith('asset_')]
            
            # Check each video has a thumbnail
            for video_file in video_files:
                video_path = os.path.join(folder_path, video_file)
                thumbnail_name = video_file.replace('.mp4', '.png')
                thumbnail_path = os.path.join(folder_path, thumbnail_name)
                
                if thumbnail_name not in thumbnail_files:
                    error_msg = f"Missing thumbnail for {video_file} in folder {folder_path}"
                    errors.append(error_msg)
                    self.logger.error(error_msg)
                else:
                    # Check thumbnail size based on video size
                    video_is_placeholder = is_file_zero_size(video_path)
                    thumbnail_is_placeholder = is_file_zero_size(thumbnail_path)
                    
                    if video_is_placeholder:
                        # Zero-size video should have zero-size thumbnail (warning, not error)
                        if not thumbnail_is_placeholder:
                            warning_msg = f"Video placeholder {video_file} has non-zero-size thumbnail in {folder_path}"
                            warnings.append(warning_msg)
                            self.logger.warning(warning_msg)
                        else:
                            # Both are placeholders - this is correct
                            self.logger.debug(f"Valid placeholder pair: {video_file}/{thumbnail_name} in {folder_path}")
                    else:
                        # Valid video should have valid thumbnail (error if zero-size)
                        if thumbnail_is_placeholder:
                            error_msg = f"Valid video {video_file} has zero-size thumbnail in {folder_path}"
                            errors.append(error_msg)
                            self.logger.error(error_msg)
                        else:
                            # Both are valid - this is correct
                            self.logger.debug(f"Valid video/thumbnail pair: {video_file}/{thumbnail_name} in {folder_path}")
            
            # Check for orphaned thumbnails
            for thumbnail_file in thumbnail_files:
                video_name = thumbnail_file.replace('.png', '.mp4')
                if video_name not in video_files:
                    warning_msg = f"Orphaned thumbnail (no video): {thumbnail_file} in folder {folder_path}"
                    warnings.append(warning_msg)
                    self.logger.warning(warning_msg)
            
            # Check for zero-size files
            for file_name in files:
                file_path = os.path.join(folder_path, file_name)
                if is_file_zero_size(file_path):
                    warning_msg = f"Zero-size file: {file_path}"
                    warnings.append(warning_msg)
                    self.logger.warning(warning_msg)
            
            # Validate file types
            for file_name in files:
                file_path = os.path.join(folder_path, file_name)
                file_type = get_media_file_type(file_path)
                
                if file_type == 'unknown':
                    warning_msg = f"Unknown file type: {file_path}"
                    warnings.append(warning_msg)
                    self.logger.warning(warning_msg)
            
            return ValidationResult(success=len(errors) == 0, errors=errors, warnings=warnings)
            
        except Exception as e:
            error_msg = f"Failed to validate media folder {folder_path}: {e}"
            errors.append(error_msg)
            self.logger.error(error_msg)
            return ValidationResult(success=False, errors=errors, warnings=[])
    
    def _validate_cross_consistency(self) -> ValidationResult:
        """Validate consistency between database and media."""
        errors = []
        warnings = []
        
        try:
            self.logger.info("Validating cross-consistency")
            
            with sqlite3.connect(self.db_path) as conn:
                # Check shots have corresponding media folders
                cursor = conn.execute("SELECT shot_id FROM shots")
                db_shot_ids = {str(row[0]) for row in cursor.fetchall()}
                
                media_folders = set(os.listdir(self.media_path))
                
                # Asset subdirectories to exclude from shot validation
                asset_subdirs = {'characters', 'locations', 'other'}
                
                # Filter out asset folders from media folders
                shot_media_folders = media_folders - asset_subdirs
                
                # Shots without media folders
                missing_media = db_shot_ids - shot_media_folders
                if missing_media:
                    warning_msg = f"Shots without media folders: {', '.join(missing_media)}"
                    warnings.append(warning_msg)
                    self.logger.warning(warning_msg)
                
                # Media folders without shots (excluding asset folders)
                extra_media = shot_media_folders - db_shot_ids
                if extra_media:
                    warning_msg = f"Media folders without corresponding shots: {', '.join(extra_media)}"
                    warnings.append(warning_msg)
                    self.logger.warning(warning_msg)
                
                # Check takes have corresponding files
                cursor = conn.execute("SELECT shot_id, file_path FROM takes")
                takes_data = cursor.fetchall()
                
                for shot_id, file_path in takes_data:
                    # Resolve relative file path to absolute path
                    # file_path is typically like "media/2/base_01.png"
                    # We need to resolve it against the target media directory
                    if file_path.startswith('media/'):
                        # Extract the relative path after 'media/'
                        relative_path = file_path[6:]  # Remove 'media/' prefix
                        
                        # Use os.path.normpath to handle path separators correctly across platforms
                        # This will automatically use the correct separators for the current platform
                        normalized_path = os.path.normpath(relative_path)
                        absolute_path = os.path.join(self.media_path, normalized_path)
                    else:
                        # If it's already absolute or different format, normalize it
                        absolute_path = os.path.normpath(file_path)
                    
                    # Check if file exists
                    if not os.path.exists(absolute_path):
                        error_msg = f"Take file not found: {file_path} (resolved to: {absolute_path})"
                        errors.append(error_msg)
                        self.logger.error(error_msg)
                    else:
                        # Check file size
                        if is_file_zero_size(absolute_path):
                            warning_msg = f"Zero-size take file: {file_path} (resolved to: {absolute_path})"
                            warnings.append(warning_msg)
                            self.logger.warning(warning_msg)
                
                # Check assets have corresponding files
                cursor = conn.execute("SELECT id_key, file_path FROM assets")
                assets_data = cursor.fetchall()
                
                for id_key, file_path in assets_data:
                    if file_path:
                        # Resolve relative file path to absolute path
                        # file_path is typically like "media/characters/Alicia_Winters/Alicia_Winters.png"
                        # We need to resolve it against the target media directory
                        if file_path.startswith('media/'):
                            # Extract the relative path after 'media/'
                            relative_path = file_path[6:]  # Remove 'media/' prefix
                            
                            # Use os.path.normpath to handle path separators correctly across platforms
                            normalized_path = os.path.normpath(relative_path)
                            absolute_path = os.path.join(self.media_path, normalized_path)
                        else:
                            # If it's already absolute or different format, normalize it
                            absolute_path = os.path.normpath(file_path)
                        
                        if not os.path.exists(absolute_path):
                            error_msg = f"Asset file not found: {file_path} (resolved to: {absolute_path})"
                            errors.append(error_msg)
                            self.logger.error(error_msg)
                        elif is_file_zero_size(absolute_path):
                            warning_msg = f"Zero-size asset file: {file_path} (resolved to: {absolute_path})"
                            warnings.append(warning_msg)
                            self.logger.warning(warning_msg)
            
            self.logger.info("Cross-consistency validation completed successfully")
            return ValidationResult(success=len(errors) == 0, errors=errors, warnings=warnings)
            
        except Exception as e:
            error_msg = f"Cross-consistency validation failed: {e}"
            errors.append(error_msg)
            self.logger.error(error_msg)
            return ValidationResult(success=False, errors=errors, warnings=[])
    
    def _check_orphaned_asset_files(self) -> ValidationResult:
        """Check for asset files that exist but aren't tracked in the assets table."""
        errors = []
        warnings = []
        
        try:
            self.logger.info("Checking for orphaned asset files")
            
            # Asset subdirectories to check
            asset_subdirs = ['characters', 'locations', 'other']
            
            with sqlite3.connect(self.db_path) as conn:
                # Get all asset file paths from database and resolve to absolute paths
                cursor = conn.execute("SELECT file_path FROM assets WHERE file_path IS NOT NULL")
                db_asset_absolute_paths = set()
                
                for row in cursor.fetchall():
                    file_path = row[0]
                    # Resolve relative file path to absolute path (same logic as cross-validation)
                    if file_path.startswith('media/'):
                        relative_path = file_path[6:]  # Remove 'media/' prefix
                        # Use os.path.normpath for cross-platform compatibility
                        normalized_path = os.path.normpath(relative_path)
                        absolute_path = os.path.join(self.media_path, normalized_path)
                        db_asset_absolute_paths.add(absolute_path)
                    else:
                        # Normalize absolute paths too
                        db_asset_absolute_paths.add(os.path.normpath(file_path))
                
                # Check each asset subdirectory for files not in database
                thumbnail_files_found = []
                
                for subdir in asset_subdirs:
                    subdir_path = os.path.join(self.media_path, subdir)
                    
                    if not os.path.exists(subdir_path):
                        continue
                    
                    # Find all files in this subdirectory
                    for root, dirs, files in os.walk(subdir_path):
                        for file_name in files:
                            file_path = os.path.join(root, file_name)
                            
                            # Track thumbnail files under asset directories - they are valid
                            # Thumbnails are used for previewing 3D asset files
                            if 'thumbnails' in file_path.lower():
                                thumbnail_files_found.append(file_path)
                                continue
                            
                            # Check if this file is tracked in the database
                            if file_path not in db_asset_absolute_paths:
                                # Log the full absolute path for clarity with normalized separators
                                if os.name == 'nt':  # Windows
                                    file_path = file_path.replace('/', '\\')
                                warning_msg = f"Orphaned asset file (not in assets table): {file_path}"
                                warnings.append(warning_msg)
                                self.logger.warning(warning_msg)
                
                # Log thumbnail files found in asset directories
                if thumbnail_files_found:
                    self.logger.info(f"Found {len(thumbnail_files_found)} thumbnail files in asset directories (these are valid for 3D asset previews):")
                    for thumbnail_file in thumbnail_files_found:
                        if os.name == 'nt':  # Windows
                            thumbnail_file = thumbnail_file.replace('/', '\\')
                        self.logger.info(f"  - {thumbnail_file}")
            
            self.logger.info(f"Orphaned asset check completed: {len(warnings)} orphaned files found")
            return ValidationResult(success=True, errors=errors, warnings=warnings)
            
        except Exception as e:
            error_msg = f"Orphaned asset check failed: {e}"
            errors.append(error_msg)
            self.logger.error(error_msg)
            return ValidationResult(success=False, errors=errors, warnings=[])
    
    def get_database_info(self) -> Optional[Dict]:
        """Get comprehensive database information."""
        try:
            if not os.path.exists(self.db_path):
                return None
            
            with sqlite3.connect(self.db_path) as conn:
                # Get table counts
                tables = ['shots', 'takes', 'assets', 'meta', 'deleted_shots']
                table_counts = {}
                
                for table in tables:
                    cursor = conn.execute(f"SELECT COUNT(*) FROM {table}")
                    table_counts[table] = cursor.fetchone()[0]
                
                # Get version info
                cursor = conn.execute("SELECT value FROM meta WHERE key='schema_version'")
                schema_version = cursor.fetchone()
                
                cursor = conn.execute("SELECT value FROM meta WHERE key='app_version'")
                app_version = cursor.fetchone()
                
                # Get shot statistics
                cursor = conn.execute("SELECT MIN(order_number), MAX(order_number), COUNT(*) FROM shots")
                shot_stats = cursor.fetchone()
                
                return {
                    'path': self.db_path,
                    'exists': True,
                    'schema_version': schema_version[0] if schema_version else None,
                    'app_version': app_version[0] if app_version else None,
                    'table_counts': table_counts,
                    'shot_stats': {
                        'min_order': shot_stats[0],
                        'max_order': shot_stats[1],
                        'total_shots': shot_stats[2]
                    }
                }
                
        except Exception as e:
            self.logger.error(f"Failed to get database info: {e}")
            return None
    
    def get_media_info(self) -> Dict:
        """Get comprehensive media information."""
        try:
            media_info = {
                'path': self.media_path,
                'exists': os.path.exists(self.media_path),
                'total_folders': 0,
                'total_files': 0,
                'total_size_mb': 0.0,
                'folders': {}
            }
            
            if not media_info['exists']:
                return media_info
            
            for folder_name in os.listdir(self.media_path):
                folder_path = os.path.join(self.media_path, folder_name)
                
                if not os.path.isdir(folder_path):
                    continue
                
                folder_info = {
                    'path': folder_path,
                    'file_count': 0,
                    'total_size_mb': 0.0,
                    'files': []
                }
                
                for file_name in os.listdir(folder_path):
                    file_path = os.path.join(folder_path, file_name)
                    
                    if not os.path.isfile(file_path):
                        continue
                    
                    file_info = validate_media_file(file_path)
                    
                    folder_info['file_count'] += 1
                    folder_info['total_size_mb'] += file_info['size_mb']
                    
                    folder_info['files'].append({
                        'name': file_name,
                        'size_mb': file_info['size_mb'],
                        'is_zero_size': file_info['is_zero_size']
                    })
                
                media_info['total_folders'] += 1
                media_info['total_files'] += folder_info['file_count']
                media_info['total_size_mb'] += folder_info['total_size_mb']
                media_info['folders'][folder_name] = folder_info
            
            return media_info
            
        except Exception as e:
            self.logger.error(f"Failed to get media info: {e}")
            return {}