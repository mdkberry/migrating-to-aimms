#!/usr/bin/env python3
"""
AIMMS Project Integrity Test Tool

Standalone script to validate the integrity of a migrated AIMMS project.
Generates a comprehensive report without modifying any project files.

Usage:
    python integrity_test.py project_folder_path --verbose
"""

import argparse
import json
import os
import sqlite3
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, NamedTuple, Optional, Set
from dataclasses import dataclass
from collections import defaultdict

# Import existing migration tool modules
from schema_manager import SchemaManager
from utils import validate_media_file, get_media_file_type, is_file_zero_size


@dataclass
class ValidationResult:
    """Result of an integrity check."""
    success: bool
    errors: List[str]
    warnings: List[str]
    info: List[str]


@dataclass
class IntegrityReport:
    """Complete integrity test report."""
    project_path: str
    timestamp: str
    schema_validation: ValidationResult
    database_validation: ValidationResult
    media_validation: ValidationResult
    cross_validation: ValidationResult
    structure_validation: ValidationResult
    summary: Dict[str, int]


class IntegrityTester:
    """Main integrity testing class."""
    
    def __init__(self, project_path: str, verbose: bool = False):
        """
        Initialize integrity tester.
        
        Args:
            project_path: Path to the migrated AIMMS project
            verbose: Enable verbose logging
        """
        self.project_path = Path(project_path).resolve()
        self.verbose = verbose
        self.db_path = self.project_path / "data" / "shots.db"
        self.media_path = self.project_path / "media"
        self.data_path = self.project_path / "data"
        
        # Initialize schema manager
        self.schema_manager = SchemaManager(
            "schema/aimms-shot-db-schema.json",
            "schema/aimms-meta-entries.json"
        )
        
        # Setup logging
        self._setup_logging()
        
        # Results storage
        self.shot_mapping: Dict[str, int] = {}
        self.db_shot_ids: Set[int] = set()
        self.media_folders: Set[str] = set()
        
    def _setup_logging(self):
        """Setup logging configuration."""
        log_level = logging.DEBUG if self.verbose else logging.INFO
        
        # Create logger
        self.logger = logging.getLogger('integrity_test')
        self.logger.setLevel(log_level)
        
        # Clear any existing handlers
        self.logger.handlers.clear()
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)
        console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)
        
        # File handler (optional, for detailed logs)
        log_file = self.project_path / "integrity_test.log"
        if self.verbose:
            file_handler = logging.FileHandler(log_file, mode='w')
            file_handler.setLevel(logging.DEBUG)
            file_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            file_handler.setFormatter(file_formatter)
            self.logger.addHandler(file_handler)
    
    def run_test(self) -> IntegrityReport:
        """
        Execute complete integrity test.
        
        Returns:
            IntegrityReport with all test results
        """
        self.logger.info("=" * 80)
        self.logger.info("AIMMS PROJECT INTEGRITY TEST STARTING")
        self.logger.info("=" * 80)
        self.logger.info(f"Testing project: {self.project_path}")
        
        # Initialize results
        schema_result = ValidationResult(True, [], [], [])
        database_result = ValidationResult(True, [], [], [])
        media_result = ValidationResult(True, [], [], [])
        cross_result = ValidationResult(True, [], [], [])
        structure_result = ValidationResult(True, [], [], [])
        
        # 1. Validate project structure
        self.logger.info("1. Validating project structure...")
        structure_result = self._validate_project_structure()
        
        # 2. Validate database schema
        if structure_result.success:
            self.logger.info("2. Validating database schema...")
            schema_result = self._validate_database_schema()
            
            # 3. Validate database content
            if schema_result.success:
                self.logger.info("3. Validating database content...")
                database_result = self._validate_database_content()
                
                # 4. Validate media files
                self.logger.info("4. Validating media files...")
                media_result = self._validate_media_files()
                
                # 5. Cross-validation
                self.logger.info("5. Performing cross-validation...")
                cross_result = self._validate_cross_consistency()
        
        # Generate summary
        summary = self._generate_summary([
            schema_result, database_result, media_result, 
            cross_result, structure_result
        ])
        
        # Create report
        report = IntegrityReport(
            project_path=str(self.project_path),
            timestamp=datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC'),
            schema_validation=schema_result,
            database_validation=database_result,
            media_validation=media_result,
            cross_validation=cross_result,
            structure_validation=structure_result,
            summary=summary
        )
        
        self.logger.info("=" * 80)
        self.logger.info("INTEGRITY TEST COMPLETED")
        self.logger.info("=" * 80)
        
        return report
    
    def _validate_project_structure(self) -> ValidationResult:
        """Validate the project directory structure."""
        errors = []
        warnings = []
        info = []
        
        try:
            # Check required directories
            required_dirs = [
                self.project_path,
                self.data_path,
                self.media_path
            ]
            
            for directory in required_dirs:
                if not directory.exists():
                    errors.append(f"Required directory missing: {directory}")
                else:
                    info.append(f"Directory exists: {directory}")
            
            # Check required files
            required_files = [
                self.project_path / "project_config.json",
                self.project_path / "shot_name_mapping.json",
                self.data_path / "shots.db",
                self.data_path / "shot_name_mapping.json"
            ]
            
            for file_path in required_files:
                if not file_path.exists():
                    errors.append(f"Required file missing: {file_path}")
                else:
                    info.append(f"File exists: {file_path}")
            
            # Check optional directories
            optional_dirs = [
                self.data_path / "csv",
                self.data_path / "backup",
                self.data_path / "saves",
                self.project_path / "logs"
            ]
            
            for directory in optional_dirs:
                if directory.exists():
                    info.append(f"Optional directory exists: {directory}")
                else:
                    warnings.append(f"Optional directory missing: {directory}")
            
            # Check asset subdirectories
            asset_subdirs = ["characters", "locations", "other"]
            for subdir in asset_subdirs:
                subdir_path = self.media_path / subdir
                if subdir_path.exists():
                    info.append(f"Asset subdirectory exists: {subdir_path}")
                else:
                    warnings.append(f"Asset subdirectory missing: {subdir_path}")
            
            success = len(errors) == 0
            if success:
                self.logger.info("Project structure validation: PASSED")
            else:
                self.logger.error("Project structure validation: FAILED")
                
            return ValidationResult(success, errors, warnings, info)
            
        except Exception as e:
            error_msg = f"Project structure validation failed: {e}"
            self.logger.error(error_msg)
            return ValidationResult(False, [error_msg], [], [])
    
    def _validate_database_schema(self) -> ValidationResult:
        """Validate database schema against schema file."""
        errors = []
        warnings = []
        info = []
        
        try:
            # Load schema
            if not self.schema_manager.load_schema():
                errors.append("Failed to load schema from schema file")
                return ValidationResult(False, errors, warnings, info)
            
            # Validate database schema
            validation_results = self.schema_manager.validate_database_schema(str(self.db_path))
            
            if not validation_results['valid']:
                if validation_results['missing_tables']:
                    errors.append(f"Missing tables: {', '.join(validation_results['missing_tables'])}")
                
                if validation_results['missing_indexes']:
                    errors.append(f"Missing indexes: {', '.join(validation_results['missing_indexes'])}")
                
                if validation_results['missing_columns']:
                    for table, columns in validation_results['missing_columns'].items():
                        errors.append(f"Missing columns in {table}: {', '.join(columns)}")
                
                if validation_results['extra_columns']:
                    for table, columns in validation_results['extra_columns'].items():
                        warnings.append(f"Extra columns in {table}: {', '.join(columns)}")
            else:
                info.append("Database schema validation: PASSED")
            
            success = len(errors) == 0
            return ValidationResult(success, errors, warnings, info)
            
        except Exception as e:
            error_msg = f"Database schema validation failed: {e}"
            self.logger.error(error_msg)
            return ValidationResult(False, [error_msg], [], [])
    
    def _validate_database_content(self) -> ValidationResult:
        """Validate database content and data integrity."""
        errors = []
        warnings = []
        info = []
        
        try:
            if not self.db_path.exists():
                errors.append(f"Database file not found: {self.db_path}")
                return ValidationResult(False, errors, warnings, info)
            
            with sqlite3.connect(self.db_path) as conn:
                # Get shot mapping and IDs
                cursor = conn.execute("SELECT shot_name, shot_id FROM shots")
                self.shot_mapping = {row[0]: row[1] for row in cursor.fetchall()}
                self.db_shot_ids = set(self.shot_mapping.values())
                
                info.append(f"Found {len(self.shot_mapping)} shots in database")
                
                # Check for duplicate shot names
                cursor = conn.execute('''
                    SELECT shot_name, COUNT(*) 
                    FROM shots 
                    GROUP BY shot_name 
                    HAVING COUNT(*) > 1
                ''')
                duplicates = cursor.fetchall()
                if duplicates:
                    warnings.append(f"Duplicate shot names found: {[d[0] for d in duplicates]}")
                
                # Check takes table
                cursor = conn.execute("SELECT COUNT(*) FROM takes")
                takes_count = cursor.fetchone()[0]
                info.append(f"Found {takes_count} takes in database")
                
                # Check for orphaned takes
                cursor = conn.execute('''
                    SELECT COUNT(*) FROM takes t 
                    LEFT JOIN shots s ON t.shot_id = s.shot_id 
                    WHERE s.shot_id IS NULL
                ''')
                orphaned_takes = cursor.fetchone()[0]
                if orphaned_takes > 0:
                    errors.append(f"Found {orphaned_takes} takes with invalid shot_id references")
                
                # Check assets table
                cursor = conn.execute("SELECT COUNT(*) FROM assets")
                assets_count = cursor.fetchone()[0]
                info.append(f"Found {assets_count} assets in database")
                
                # Check meta table
                cursor = conn.execute("SELECT key, value FROM meta")
                meta_data = dict(cursor.fetchall())
                
                # Validate version numbers
                if meta_data.get('schema_version') != '1':
                    warnings.append(f"Unexpected schema_version: {meta_data.get('schema_version')}")
                
                if meta_data.get('app_version') != '1.0':
                    warnings.append(f"Unexpected app_version: {meta_data.get('app_version')}")
                
                # Check date formats
                cursor = conn.execute("SELECT created_date FROM shots LIMIT 10")
                date_samples = [row[0] for row in cursor.fetchall()]
                
                for date_str in date_samples:
                    if date_str and not date_str.endswith('Z'):
                        warnings.append(f"Non-UTC date format found: {date_str}")
                        break
                
                # Check for invalid asset IDs
                cursor = conn.execute('''
                    SELECT COUNT(*) FROM assets a
                    WHERE a.id_key NOT LIKE 'asset_%'
                ''')
                invalid_assets = cursor.fetchone()[0]
                if invalid_assets > 0:
                    warnings.append(f"Found {invalid_assets} assets with non-standard ID format")
            
            success = len(errors) == 0
            if success:
                self.logger.info("Database content validation: PASSED")
            else:
                self.logger.error("Database content validation: FAILED")
                
            return ValidationResult(success, errors, warnings, info)
            
        except Exception as e:
            error_msg = f"Database content validation failed: {e}"
            self.logger.error(error_msg)
            return ValidationResult(False, [error_msg], [], [])
    
    def _validate_media_files(self) -> ValidationResult:
        """Validate media files and their integrity."""
        errors = []
        warnings = []
        info = []
        
        try:
            if not self.media_path.exists():
                errors.append("Media directory does not exist")
                return ValidationResult(False, errors, warnings, info)
            
            # Get media folders
            media_folders = [f for f in os.listdir(self.media_path)
                           if (self.media_path / f).is_dir()]
            
            self.media_folders = set(media_folders)
            
            if not media_folders:
                warnings.append("No media folders found")
                return ValidationResult(True, errors, warnings, info)
            
            # Asset subdirectories to exclude from shot validation
            asset_subdirs = {'characters', 'locations', 'other'}
            
            # Validate each media folder
            total_folders = len(media_folders)
            validated_folders = 0
            
            for folder in media_folders:
                folder_path = self.media_path / folder
                
                # Skip asset folders for shot validation
                if folder in asset_subdirs:
                    validated_folders += 1
                    continue
                
                # Check if folder corresponds to a shot_id
                try:
                    shot_id = int(folder)
                    if shot_id not in self.db_shot_ids:
                        warnings.append(f"Media folder {folder} does not correspond to any shot_id")
                except ValueError:
                    warnings.append(f"Media folder {folder} is not a valid shot_id")
                
                # Validate files in folder
                folder_result = self._validate_media_folder(folder_path)
                errors.extend(folder_result.errors)
                warnings.extend(folder_result.warnings)
                info.extend(folder_result.info)
                
                validated_folders += 1
                
                # Log progress
                if validated_folders % 10 == 0 or validated_folders == total_folders:
                    progress = (validated_folders / total_folders) * 100
                    self.logger.info(f"Media validation progress: {progress:.1f}% ({validated_folders}/{total_folders})")
            
            # Validate asset subdirectories
            for subdir in asset_subdirs:
                subdir_path = self.media_path / subdir
                if subdir_path.exists():
                    subdir_result = self._validate_asset_directory(subdir_path)
                    errors.extend(subdir_result.errors)
                    warnings.extend(subdir_result.warnings)
                    info.extend(subdir_result.info)
            
            success = len(errors) == 0
            if success:
                self.logger.info("Media files validation: PASSED")
            else:
                self.logger.error("Media files validation: FAILED")
                
            return ValidationResult(success, errors, warnings, info)
            
        except Exception as e:
            error_msg = f"Media files validation failed: {e}"
            self.logger.error(error_msg)
            return ValidationResult(False, [error_msg], [], [])
    
    def _validate_media_folder(self, folder_path: Path) -> ValidationResult:
        """Validate a single media folder."""
        errors = []
        warnings = []
        info = []
        
        try:
            # Get files in folder
            files = []
            for item in folder_path.iterdir():
                if item.is_file():
                    files.append(item.name)
            
            if not files:
                warnings.append(f"Empty media folder: {folder_path}")
                return ValidationResult(True, errors, warnings, info)
            
            # Categorize files
            video_files = [f for f in files if f.startswith('video_') and f.endswith('.mp4')]
            thumbnail_files = [f for f in files if f.startswith('video_') and f.endswith('.png')]
            image_files = [f for f in files if f.startswith('image_')]
            asset_files = [f for f in files if f.startswith('asset_')]
            
            info.append(f"Folder {folder_path.name}: {len(files)} files "
                       f"({len(video_files)} videos, {len(thumbnail_files)} thumbnails, "
                       f"{len(image_files)} images, {len(asset_files)} assets)")
            
            # Check each video has a thumbnail
            for video_file in video_files:
                video_path = folder_path / video_file
                thumbnail_name = video_file.replace('.mp4', '.png')
                thumbnail_path = folder_path / thumbnail_name
                
                if thumbnail_name not in thumbnail_files:
                    errors.append(f"Missing thumbnail for {video_file} in folder {folder_path}")
                else:
                    # Check thumbnail size based on video size
                    video_is_placeholder = is_file_zero_size(str(video_path))
                    thumbnail_is_placeholder = is_file_zero_size(str(thumbnail_path))
                    
                    if video_is_placeholder:
                        # Zero-size video should have zero-size thumbnail (warning, not error)
                        if not thumbnail_is_placeholder:
                            warnings.append(f"Video placeholder {video_file} has non-zero-size thumbnail in {folder_path}")
                    else:
                        # Valid video should have valid thumbnail (error if zero-size)
                        if thumbnail_is_placeholder:
                            errors.append(f"Valid video {video_file} has zero-size thumbnail in {folder_path}")
            
            # Check for orphaned thumbnails
            for thumbnail_file in thumbnail_files:
                video_name = thumbnail_file.replace('.png', '.mp4')
                if video_name not in video_files:
                    warnings.append(f"Orphaned thumbnail (no video): {thumbnail_file} in folder {folder_path}")
            
            # Check for zero-size files
            for file_name in files:
                file_path = folder_path / file_name
                if is_file_zero_size(str(file_path)):
                    warnings.append(f"Zero-size file: {file_path}")
            
            # Validate file types
            for file_name in files:
                file_path = folder_path / file_name
                file_type = get_media_file_type(str(file_path))
                
                if file_type == 'unknown':
                    warnings.append(f"Unknown file type: {file_path}")
            
            return ValidationResult(len(errors) == 0, errors, warnings, info)
            
        except Exception as e:
            error_msg = f"Failed to validate media folder {folder_path}: {e}"
            self.logger.error(error_msg)
            return ValidationResult(False, [error_msg], [], [])
    
    def _validate_asset_directory(self, asset_path: Path) -> ValidationResult:
        """Validate an asset directory (characters, locations, other)."""
        errors = []
        warnings = []
        info = []
        
        try:
            asset_files = []
            for root, dirs, files in os.walk(asset_path):
                for file_name in files:
                    asset_files.append(Path(root) / file_name)
            
            if not asset_files:
                info.append(f"Empty asset directory: {asset_path}")
                return ValidationResult(True, errors, warnings, info)
            
            # Check for thumbnail files (valid for 3D asset previews)
            thumbnail_files = [f for f in asset_files if 'thumbnail' in f.name.lower()]
            
            info.append(f"Asset directory {asset_path.name}: {len(asset_files)} files "
                       f"({len(thumbnail_files)} thumbnails)")
            
            # Check for zero-size files
            for file_path in asset_files:
                if is_file_zero_size(str(file_path)):
                    warnings.append(f"Zero-size asset file: {file_path}")
            
            # Validate file types
            for file_path in asset_files:
                file_type = get_media_file_type(str(file_path))
                
                if file_type == 'unknown':
                    warnings.append(f"Unknown asset file type: {file_path}")
            
            return ValidationResult(True, errors, warnings, info)
            
        except Exception as e:
            error_msg = f"Failed to validate asset directory {asset_path}: {e}"
            self.logger.error(error_msg)
            return ValidationResult(False, [error_msg], [], [])
    
    def _validate_cross_consistency(self) -> ValidationResult:
        """Validate consistency between database and media."""
        errors = []
        warnings = []
        info = []
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Check shots have corresponding media folders
                db_shot_ids_str = {str(sid) for sid in self.db_shot_ids}
                media_folders = self.media_folders
                
                # Asset subdirectories to exclude
                asset_subdirs = {'characters', 'locations', 'other'}
                shot_media_folders = media_folders - asset_subdirs
                
                # Shots without media folders
                missing_media = db_shot_ids_str - shot_media_folders
                if missing_media:
                    warnings.append(f"Shots without media folders: {', '.join(sorted(missing_media, key=int))}")
                
                # Media folders without shots
                extra_media = shot_media_folders - db_shot_ids_str
                if extra_media:
                    warnings.append(f"Media folders without corresponding shots: {', '.join(sorted(extra_media, key=int))}")
                
                # Check takes have corresponding files
                cursor = conn.execute("SELECT shot_id, file_path FROM takes")
                takes_data = cursor.fetchall()
                
                for shot_id, file_path in takes_data:
                    # Resolve relative file path to absolute path
                    if file_path.startswith('media/'):
                        relative_path = file_path[6:]  # Remove 'media/' prefix
                        absolute_path = self.media_path / relative_path
                    else:
                        absolute_path = Path(file_path)
                    
                    # Normalize path separators
                    absolute_path = absolute_path.resolve()
                    
                    if not absolute_path.exists():
                        errors.append(f"Take file not found: {file_path} (resolved to: {absolute_path})")
                    else:
                        if is_file_zero_size(str(absolute_path)):
                            warnings.append(f"Zero-size take file: {file_path} (resolved to: {absolute_path})")
                
                # Check assets have corresponding files
                cursor = conn.execute("SELECT id_key, file_path FROM assets")
                assets_data = cursor.fetchall()
                
                for id_key, file_path in assets_data:
                    if file_path:
                        # Resolve relative file path to absolute path
                        if file_path.startswith('media/'):
                            relative_path = file_path[6:]  # Remove 'media/' prefix
                            absolute_path = self.media_path / relative_path
                        else:
                            absolute_path = Path(file_path)
                        
                        # Normalize path separators
                        absolute_path = absolute_path.resolve()
                        
                        if not absolute_path.exists():
                            errors.append(f"Asset file not found: {file_path} (resolved to: {absolute_path})")
                        elif is_file_zero_size(str(absolute_path)):
                            warnings.append(f"Zero-size asset file: {file_path} (resolved to: {absolute_path})")
                
                # Check for orphaned asset files
                self._check_orphaned_asset_files(conn, errors, warnings, info)
            
            success = len(errors) == 0
            if success:
                self.logger.info("Cross-consistency validation: PASSED")
            else:
                self.logger.error("Cross-consistency validation: FAILED")
                
            return ValidationResult(success, errors, warnings, info)
            
        except Exception as e:
            error_msg = f"Cross-consistency validation failed: {e}"
            self.logger.error(error_msg)
            return ValidationResult(False, [error_msg], [], [])
    
    def _check_orphaned_asset_files(self, conn, errors: List[str], warnings: List[str], info: List[str]):
        """Check for asset files that exist but aren't tracked in the assets table."""
        try:
            # Asset subdirectories to check
            asset_subdirs = ['characters', 'locations', 'other']
            
            # Get all asset file paths from database and resolve to absolute paths
            cursor = conn.execute("SELECT file_path FROM assets WHERE file_path IS NOT NULL")
            db_asset_absolute_paths = set()
            
            for row in cursor.fetchall():
                file_path = row[0]
                # Resolve relative file path to absolute path
                if file_path.startswith('media/'):
                    relative_path = file_path[6:]  # Remove 'media/' prefix
                    absolute_path = self.media_path / relative_path
                    db_asset_absolute_paths.add(absolute_path.resolve())
                else:
                    db_asset_absolute_paths.add(Path(file_path).resolve())
            
            # Check each asset subdirectory for files not in database
            thumbnail_files_found = []
            
            for subdir in asset_subdirs:
                subdir_path = self.media_path / subdir
                
                if not subdir_path.exists():
                    continue
                
                # Find all files in this subdirectory
                for root, dirs, files in os.walk(subdir_path):
                    for file_name in files:
                        file_path = Path(root) / file_name
                        
                        # Track thumbnail files under asset directories - they are valid
                        # Thumbnails are used for previewing 3D asset files
                        if 'thumbnail' in file_path.name.lower():
                            thumbnail_files_found.append(file_path)
                            continue
                        
                        # Check if this file is tracked in the database
                        if file_path.resolve() not in db_asset_absolute_paths:
                            warnings.append(f"Orphaned asset file (not in assets table): {file_path}")
            
            # Log thumbnail files found in asset directories
            if thumbnail_files_found:
                info.append(f"Found {len(thumbnail_files_found)} thumbnail files in asset directories "
                           f"(these are valid for 3D asset previews)")
                for thumbnail_file in thumbnail_files_found:
                    info.append(f"  - {thumbnail_file}")
            
        except Exception as e:
            error_msg = f"Orphaned asset check failed: {e}"
            self.logger.error(error_msg)
            errors.append(error_msg)
    
    def _generate_summary(self, results: List[ValidationResult]) -> Dict[str, int]:
        """Generate summary statistics."""
        summary = {
            'total_errors': 0,
            'total_warnings': 0,
            'total_info': 0,
            'sections_passed': 0,
            'sections_failed': 0
        }
        
        for result in results:
            summary['total_errors'] += len(result.errors)
            summary['total_warnings'] += len(result.warnings)
            summary['total_info'] += len(result.info)
            
            if result.success:
                summary['sections_passed'] += 1
            else:
                summary['sections_failed'] += 1
        
        return summary


def generate_report_markdown(report: IntegrityReport) -> str:
    """
    Generate a markdown report from the integrity test results.
    
    Args:
        report: IntegrityReport object
        
    Returns:
        Markdown formatted report string
    """
    lines = []
    
    # Header
    lines.append("# AIMMS Project Integrity Test Report")
    lines.append("")
    lines.append(f"**Project:** {report.project_path}")
    lines.append(f"**Test Date:** {report.timestamp}")
    lines.append("")
    
    # Executive Summary
    lines.append("## Executive Summary")
    lines.append("")
    
    total_sections = (report.summary['sections_passed'] + 
                     report.summary['sections_failed'])
    
    lines.append(f"- **Sections Passed:** {report.summary['sections_passed']}/{total_sections}")
    lines.append(f"- **Sections Failed:** {report.summary['sections_failed']}/{total_sections}")
    lines.append(f"- **Total Errors:** {report.summary['total_errors']}")
    lines.append(f"- **Total Warnings:** {report.summary['total_warnings']}")
    lines.append("")
    
    if report.summary['total_errors'] == 0:
        lines.append("✅ **STATUS: PROJECT INTEGRITY TEST PASSED**")
    else:
        lines.append("❌ **STATUS: PROJECT INTEGRITY TEST FAILED**")
    
    lines.append("")
    
    # Detailed Results
    lines.append("## Detailed Results")
    lines.append("")
    
    # Project Structure
    lines.append("### 1. Project Structure")
    lines.append("")
    if report.structure_validation.success:
        lines.append("✅ **PASSED**")
    else:
        lines.append("❌ **FAILED**")
    lines.append("")
    
    if report.structure_validation.info:
        lines.append("**Info:**")
        for info in report.structure_validation.info:
            lines.append(f"- {info}")
        lines.append("")
    
    if report.structure_validation.warnings:
        lines.append("**Warnings:**")
        for warning in report.structure_validation.warnings:
            lines.append(f"- {warning}")
        lines.append("")
    
    if report.structure_validation.errors:
        lines.append("**Errors:**")
        for error in report.structure_validation.errors:
            lines.append(f"- {error}")
        lines.append("")
    
    # Database Schema
    lines.append("### 2. Database Schema")
    lines.append("")
    if report.schema_validation.success:
        lines.append("✅ **PASSED**")
    else:
        lines.append("❌ **FAILED**")
    lines.append("")
    
    if report.schema_validation.info:
        lines.append("**Info:**")
        for info in report.schema_validation.info:
            lines.append(f"- {info}")
        lines.append("")
    
    if report.schema_validation.warnings:
        lines.append("**Warnings:**")
        for warning in report.schema_validation.warnings:
            lines.append(f"- {warning}")
        lines.append("")
    
    if report.schema_validation.errors:
        lines.append("**Errors:**")
        for error in report.schema_validation.errors:
            lines.append(f"- {error}")
        lines.append("")
    
    # Database Content
    lines.append("### 3. Database Content")
    lines.append("")
    if report.database_validation.success:
        lines.append("✅ **PASSED**")
    else:
        lines.append("❌ **FAILED**")
    lines.append("")
    
    if report.database_validation.info:
        lines.append("**Info:**")
        for info in report.database_validation.info:
            lines.append(f"- {info}")
        lines.append("")
    
    if report.database_validation.warnings:
        lines.append("**Warnings:**")
        for warning in report.database_validation.warnings:
            lines.append(f"- {warning}")
        lines.append("")
    
    if report.database_validation.errors:
        lines.append("**Errors:**")
        for error in report.database_validation.errors:
            lines.append(f"- {error}")
        lines.append("")
    
    # Media Files
    lines.append("### 4. Media Files")
    lines.append("")
    if report.media_validation.success:
        lines.append("✅ **PASSED**")
    else:
        lines.append("❌ **FAILED**")
    lines.append("")
    
    if report.media_validation.info:
        lines.append("**Info:**")
        for info in report.media_validation.info:
            lines.append(f"- {info}")
        lines.append("")
    
    if report.media_validation.warnings:
        lines.append("**Warnings:**")
        for warning in report.media_validation.warnings:
            lines.append(f"- {warning}")
        lines.append("")
    
    if report.media_validation.errors:
        lines.append("**Errors:**")
        for error in report.media_validation.errors:
            lines.append(f"- {error}")
        lines.append("")
    
    # Cross-Consistency
    lines.append("### 5. Cross-Consistency")
    lines.append("")
    if report.cross_validation.success:
        lines.append("✅ **PASSED**")
    else:
        lines.append("❌ **FAILED**")
    lines.append("")
    
    if report.cross_validation.info:
        lines.append("**Info:**")
        for info in report.cross_validation.info:
            lines.append(f"- {info}")
        lines.append("")
    
    if report.cross_validation.warnings:
        lines.append("**Warnings:**")
        for warning in report.cross_validation.warnings:
            lines.append(f"- {warning}")
        lines.append("")
    
    if report.cross_validation.errors:
        lines.append("**Errors:**")
        for error in report.cross_validation.errors:
            lines.append(f"- {error}")
        lines.append("")
    
    # Recommendations
    lines.append("## Recommendations")
    lines.append("")
    
    if report.summary['total_errors'] == 0:
        lines.append("✅ **No critical issues found. The project appears to be valid.**")
    else:
        lines.append("❌ **Critical errors were found that need to be addressed:**")
        lines.append("")
        lines.append("1. Review and fix all ERROR messages above")
        lines.append("2. Ensure all required files and directories exist")
        lines.append("3. Verify database schema matches the expected structure")
        lines.append("4. Check that all media files referenced in the database exist")
        lines.append("5. Re-run the integrity test after making corrections")
    
    if report.summary['total_warnings'] > 0:
        lines.append("")
        lines.append("⚠️ **Warnings were found that should be reviewed:**")
        lines.append("")
        lines.append("Warnings indicate potential issues that may not prevent")
        lines.append("the project from working but should be reviewed for optimal")
        lines.append("project health.")
    
    lines.append("")
    lines.append("---")
    lines.append("*This report was generated by the AIMMS Integrity Test Tool*")
    
    return "\n".join(lines)


def main():
    """Main entry point for the integrity test tool."""
    parser = argparse.ArgumentParser(
        description='AIMMS Project Integrity Test Tool',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python integrity_test.py project_folder_path
  python integrity_test.py project_folder_path --verbose
        """
    )
    
    parser.add_argument(
        'project_path',
        help='Path to the migrated AIMMS project'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    try:
        # Initialize tester
        tester = IntegrityTester(args.project_path, args.verbose)
        
        # Run test
        report = tester.run_test()
        
        # Generate markdown report
        markdown_report = generate_report_markdown(report)
        
        # Save report to integrity_reports directory
        reports_dir = Path("integrity_reports")
        reports_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        project_name = Path(args.project_path).name
        report_filename = f"integrity_report_{project_name}_{timestamp}.md"
        report_path = reports_dir / report_filename
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(markdown_report)
        
        # Print summary to console
        print("\n" + "=" * 80)
        print("INTEGRITY TEST SUMMARY")
        print("=" * 80)
        print(f"Project: {report.project_path}")
        print(f"Report: {report_path}")
        print(f"Errors: {report.summary['total_errors']}")
        print(f"Warnings: {report.summary['total_warnings']}")
        print(f"Status: {'PASSED' if report.summary['total_errors'] == 0 else 'FAILED'}")
        print("=" * 80)
        
        # Exit with appropriate code
        sys.exit(0 if report.summary['total_errors'] == 0 else 1)
        
    except Exception as e:
        print(f"Integrity test failed: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()