#!/usr/bin/env python3
"""
Option 4: Import Non-AIMMS Media Files to New AIMMS Project

This module handles the migration of media files from non-AIMMS sources
into a valid AIMMS version 1.0 project structure.
"""

import os
import json
import logging
import shutil
import csv
import sqlite3
import uuid
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional
from datetime import datetime

from schema_manager import SchemaManager
from logger import create_migration_logger

logger = create_migration_logger('option4')

def generate_uuid() -> str:
    """
    Generate a UUID string for take_id.
    
    Returns:
        UUID string
    """
    return str(uuid.uuid4())

class Option4Migrator:
    """Handles migration of non-AIMMS media files to AIMMS project."""
    
    def __init__(self, source_path: str, target_path: str):
        """
        Initialize Option 4 migrator.
        
        Args:
            source_path: Path to aimms_import folder
            target_path: Path to create new AIMMS project
        """
        self.source_path = Path(source_path)
        self.target_path = Path(target_path)
        self.schema_manager = SchemaManager()
        self.shot_mapping: Dict[str, int] = {}
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.info: List[str] = []
        
        # Supported file types
        self.image_extensions = {'.png'}
        self.video_extensions = {'.mp4', '.mkv'}
        
    def migrate(self) -> bool:
        """
        Execute the complete Option 4 migration process.
        
        Returns:
            True if migration successful, False otherwise
        """
        try:
            logger.info("Starting Option 4: Import non-AIMMS media files to new AIMMS project")
            
            # Phase 0: Create project structure first so we can write logs
            self._create_project_structure()
            
            # Phase 1: Find and validate CSV file
            csv_file = self._find_csv_file()
            if not csv_file:
                self._generate_migration_log()
                return False
            
            # Phase 2: Validate media integrity
            if not self._validate_media_integrity():
                self._generate_migration_log()
                return False
            
            # Phase 3: Create database (already created structure)
            
            # Phase 4: Create database
            if not self._create_database(csv_file):
                self._generate_migration_log()
                return False
            
            # Phase 5: Migrate media files
            if not self._migrate_media_files():
                self._generate_migration_log()
                return False
            
            # Phase 6: Generate migration log
            self._generate_migration_log()
            
            logger.info("Option 4 migration completed successfully")
            return True
            
        except Exception as e:
            error_msg = f"Option 4 migration failed with error: {e}"
            logger.error(error_msg)
            self.errors.append(error_msg)
            self._generate_migration_log()
            return False
    
    def _find_csv_file(self) -> Optional[Path]:
        """Find the CSV file in the source directory."""
        try:
            # Look for CSV files in the source directory
            csv_files = list(self.source_path.glob("*.csv"))
            
            if not csv_files:
                error_msg = "No CSV file found in aimms_import directory"
                logger.error(error_msg)
                self.errors.append(error_msg)
                return None
            
            if len(csv_files) > 1:
                warning_msg = f"Multiple CSV files found, using: {csv_files[0].name}"
                logger.warning(warning_msg)
                self.warnings.append(warning_msg)
            
            csv_file = csv_files[0]
            logger.info(f"Using CSV file: {csv_file.name}")
            self.info.append(f"Using CSV file: {csv_file.name}")
            
            return csv_file
            
        except Exception as e:
            error_msg = f"Failed to find CSV file: {e}"
            logger.error(error_msg)
            self.errors.append(error_msg)
            return None
    
    def _validate_media_integrity(self) -> bool:
        """Validate media files integrity before migration."""
        try:
            logger.info("Validating media integrity...")
            
            image_storyboard = self.source_path / "image_storyboard"
            video_storyboard = self.source_path / "video_storyboard"
            
            # Check if storyboard directories exist
            if not image_storyboard.exists():
                error_msg = f"image_storyboard directory not found: {image_storyboard}"
                logger.error(error_msg)
                self.errors.append(error_msg)
                return False
            
            if not video_storyboard.exists():
                error_msg = f"video_storyboard directory not found: {video_storyboard}"
                logger.error(error_msg)
                self.errors.append(error_msg)
                return False
            
            # Get all shot folders
            image_shots = {d.name for d in image_storyboard.iterdir() if d.is_dir()}
            video_shots = {d.name for d in video_storyboard.iterdir() if d.is_dir()}
            all_shots = image_shots.union(video_shots)
            
            if not all_shots:
                error_msg = "No shot folders found in storyboard directories"
                logger.error(error_msg)
                self.errors.append(error_msg)
                return False
            
            # Get all shot names from CSV
            csv_shot_names = set()
            try:
                csv_file = self.source_path / "project_Footprints_25.csv"
                if csv_file.exists():
                    with open(csv_file, 'r', encoding='utf-8') as f:
                        reader = csv.DictReader(f)
                        csv_shot_names = {row.get('shot_name', '').strip() for row in reader if row.get('shot_name', '').strip()}
            except Exception as e:
                error_msg = f"Failed to read CSV file for shot validation: {e}"
                logger.error(error_msg)
                self.errors.append(error_msg)
                return False
            
            # Validate each shot from CSV
            for shot_name in csv_shot_names:
                image_folder = image_storyboard / shot_name
                video_folder = video_storyboard / shot_name
                
                # Check if shot folder exists in either storyboard
                image_exists = image_folder.exists()
                video_exists = video_folder.exists()
                
                if not image_exists and not video_exists:
                    # ERROR: Shot in CSV but no folder exists in either storyboard
                    error_msg = f"Shot '{shot_name}' in CSV but no corresponding folder found in storyboard directories"
                    logger.error(error_msg)
                    self.errors.append(error_msg)
                else:
                    # Folder exists, check if it's empty
                    image_empty = image_exists and not any(image_folder.iterdir())
                    video_empty = video_exists and not any(video_folder.iterdir())
                    
                    # Both folders empty - ERROR
                    if (image_exists and image_empty) and (video_exists and video_empty):
                        error_msg = f"Both storyboard folders empty for shot '{shot_name}'"
                        logger.error(error_msg)
                        self.errors.append(error_msg)
                    
                    # One folder empty - WARNING
                    elif (image_exists and image_empty) or (video_exists and video_empty):
                        warning_msg = f"One storyboard folder empty for shot '{shot_name}'"
                        logger.warning(warning_msg)
                        self.warnings.append(warning_msg)
                
                # Validate image files
                if image_folder.exists():
                    image_files = list(image_folder.glob("*.png"))
                    for img_file in image_files:
                        if img_file.suffix.lower() not in self.image_extensions:
                            error_msg = f"Invalid image file format in {shot_name}: {img_file.name}"
                            logger.error(error_msg)
                            self.errors.append(error_msg)
                
                # Validate video pairs
                if video_folder.exists():
                    video_files = [f for f in video_folder.iterdir() 
                                 if f.suffix.lower() in self.video_extensions]
                    png_files = [f for f in video_folder.iterdir() 
                               if f.suffix.lower() == '.png']
                    
                    # Check for orphaned files
                    video_names = {f.stem for f in video_files}
                    png_names = {f.stem for f in png_files}
                    
                    orphaned_videos = video_names - png_names
                    orphaned_pngs = png_names - video_names
                    
                    for orphan in orphaned_videos:
                        error_msg = f"Orphaned video file in {shot_name}: {orphan}"
                        logger.error(error_msg)
                        self.errors.append(error_msg)
                    
                    for orphan in orphaned_pngs:
                        error_msg = f"Orphaned PNG file in {shot_name}: {orphan}"
                        logger.error(error_msg)
                        self.errors.append(error_msg)
            
            # Check for errors
            if self.errors:
                error_msg = f"Media validation failed with {len(self.errors)} errors"
                logger.error(error_msg)
                return False
            
            logger.info("Media integrity validation passed")
            return True
            
        except Exception as e:
            error_msg = f"Media validation failed: {e}"
            logger.error(error_msg)
            self.errors.append(error_msg)
            return False
    
    def _create_project_structure(self):
        """Create the AIMMS project directory structure."""
        try:
            logger.info("Creating AIMMS project structure...")
            
            # Create main directories
            data_dir = self.target_path / "data"
            media_dir = self.target_path / "media"
            logs_dir = self.target_path / "logs"
            
            data_dir.mkdir(parents=True, exist_ok=True)
            media_dir.mkdir(parents=True, exist_ok=True)
            logs_dir.mkdir(parents=True, exist_ok=True)
            
            # Create data subdirectories
            (data_dir / "csv").mkdir(exist_ok=True)
            (data_dir / "backup").mkdir(exist_ok=True)
            (data_dir / "saves").mkdir(exist_ok=True)
            
            # Create asset directories
            (media_dir / "characters").mkdir(exist_ok=True)
            (media_dir / "locations").mkdir(exist_ok=True)
            (media_dir / "other").mkdir(exist_ok=True)
            
            # Create project_config.json
            self._create_project_config()
            
            # Create shot_name_mapping.json (root level)
            self._create_shot_name_mapping(root_level=True)
            
            # Create shot_name_mapping.json (data folder)
            self._create_shot_name_mapping(root_level=False)
            
            # Create empty project_log.log
            project_log = logs_dir / "project_log.log"
            project_log.touch()
            
            logger.info("Project structure created successfully")
            
        except Exception as e:
            error_msg = f"Failed to create project structure: {e}"
            logger.error(error_msg)
            self.errors.append(error_msg)
            raise
    
    def _create_project_config(self):
        """Create project_config.json with default values."""
        try:
            project_config = {
                "last_selected_workflow": "",
                "project_start_date": datetime.now().strftime('%Y-%m-%d'),
                "last_selected_section": "All Sections"
            }
            
            config_file = self.target_path / "project_config.json"
            with open(config_file, 'w') as f:
                json.dump(project_config, f, indent=2)
            
            logger.info("Created project_config.json")
            
        except Exception as e:
            error_msg = f"Failed to create project_config.json: {e}"
            logger.error(error_msg)
            self.errors.append(error_msg)
            raise
    
    def _create_shot_name_mapping(self, root_level: bool = True):
        """Create shot_name_mapping.json file."""
        try:
            mapping_data = {
                "version": "1.0",
                "created": datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'),
                "mapping": {}
            }
            
            if root_level:
                mapping_file = self.target_path / "shot_name_mapping.json"
            else:
                mapping_file = self.target_path / "data" / "shot_name_mapping.json"
            
            with open(mapping_file, 'w') as f:
                json.dump(mapping_data, f, indent=2)
            
            logger.info(f"Created shot_name_mapping.json ({'root' if root_level else 'data folder'})")
            
        except Exception as e:
            error_msg = f"Failed to create shot_name_mapping.json: {e}"
            logger.error(error_msg)
            self.errors.append(error_msg)
            raise
    
    def _create_database(self, csv_file: Path) -> bool:
        """Create the AIMMS database from CSV data."""
        try:
            logger.info("Creating AIMMS database...")
            
            # Load schema
            if not self.schema_manager.load_schema():
                error_msg = "Failed to load database schema"
                logger.error(error_msg)
                self.errors.append(error_msg)
                return False
            
            # Create database
            db_path = self.target_path / "data" / "shots.db"
            if not self.schema_manager.create_database_from_schema(str(db_path)):
                error_msg = "Failed to create database from schema"
                logger.error(error_msg)
                self.errors.append(error_msg)
                return False
            
            # Load meta entries and populate meta table
            if not self.schema_manager.load_meta_entries():
                error_msg = "Failed to load meta entries"
                logger.error(error_msg)
                self.errors.append(error_msg)
                return False
            
            # Create meta table with entries
            with sqlite3.connect(db_path) as conn:
                if not self.schema_manager.create_meta_table_with_entries(conn):
                    error_msg = "Failed to create meta table with entries"
                    logger.error(error_msg)
                    self.errors.append(error_msg)
                    return False
                
                # Insert shots from CSV
                if not self._insert_shots_from_csv(conn, csv_file):
                    return False
            
            logger.info("Database created successfully")
            return True
            
        except Exception as e:
            error_msg = f"Failed to create database: {e}"
            logger.error(error_msg)
            self.errors.append(error_msg)
            return False
    
    def _insert_shots_from_csv(self, conn, csv_file: Path) -> bool:
        """Insert shots data from CSV file into database."""
        try:
            logger.info("Inserting shots from CSV...")
            
            # Read CSV
            with open(csv_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                rows = list(reader)
            
            # Validate required columns
            required_columns = {'order_number', 'shot_name'}
            if not required_columns.issubset(set(reader.fieldnames or [])):
                error_msg = f"CSV missing required columns: {required_columns}"
                logger.error(error_msg)
                self.errors.append(error_msg)
                return False
            
            # Insert shots
            shot_count = 0
            for row in rows:
                order_number = row.get('order_number')
                shot_name = row.get('shot_name')
                
                if not order_number or not shot_name:
                    continue
                
                # Prepare shot data with defaults
                shot_data = {
                    'order_number': int(order_number),
                    'shot_name': shot_name,
                    'section': row.get('section', ''),
                    'description': row.get('description', ''),
                    'image_prompt': row.get('image_prompt', ''),
                    'colour_scheme_image': row.get('colour_scheme_image', ''),
                    'time_of_day': row.get('time_of_day', ''),
                    'location': row.get('location', ''),
                    'country': row.get('country', ''),
                    'year': row.get('year', ''),
                    'video_prompt': row.get('video_prompt', ''),
                    'created_date': datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
                }
                
                # Insert shot
                cursor = conn.execute('''
                    INSERT INTO shots (order_number, shot_name, section, description, 
                                     image_prompt, colour_scheme_image, time_of_day, 
                                     location, country, year, video_prompt, created_date)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    shot_data['order_number'], shot_data['shot_name'], shot_data['section'],
                    shot_data['description'], shot_data['image_prompt'], shot_data['colour_scheme_image'],
                    shot_data['time_of_day'], shot_data['location'], shot_data['country'],
                    shot_data['year'], shot_data['video_prompt'], shot_data['created_date']
                ))
                
                shot_id = cursor.lastrowid
                self.shot_mapping[shot_name] = shot_id
                shot_count += 1
            
            conn.commit()
            
            logger.info(f"Inserted {shot_count} shots from CSV")
            self.info.append(f"Inserted {shot_count} shots from CSV")
            
            return True
            
        except Exception as e:
            error_msg = f"Failed to insert shots from CSV: {e}"
            logger.error(error_msg)
            self.errors.append(error_msg)
            return False
    
    def _migrate_media_files(self) -> bool:
        """Migrate and organize media files."""
        try:
            logger.info("Migrating media files...")
            
            image_storyboard = self.source_path / "image_storyboard"
            video_storyboard = self.source_path / "video_storyboard"
            media_dir = self.target_path / "media"
            
            # Process image storyboard
            if image_storyboard.exists():
                if not self._process_image_storyboard(image_storyboard, media_dir):
                    return False
            
            # Process video storyboard
            if video_storyboard.exists():
                if not self._process_video_storyboard(video_storyboard, media_dir):
                    return False
            
            logger.info("Media files migrated successfully")
            return True
            
        except Exception as e:
            error_msg = f"Failed to migrate media files: {e}"
            logger.error(error_msg)
            self.errors.append(error_msg)
            return False
    
    def _process_image_storyboard(self, image_storyboard: Path, media_dir: Path) -> bool:
        """Process image storyboard files."""
        try:
            logger.info("Processing image storyboard...")
            
            for shot_folder in image_storyboard.iterdir():
                if not shot_folder.is_dir():
                    continue
                
                shot_name = shot_folder.name
                if shot_name not in self.shot_mapping:
                    warning_msg = f"Shot '{shot_name}' not found in CSV, skipping"
                    logger.warning(warning_msg)
                    self.warnings.append(warning_msg)
                    continue
                
                shot_id = self.shot_mapping[shot_name]
                target_shot_dir = media_dir / str(shot_id)
                target_shot_dir.mkdir(exist_ok=True)
                
                # Process PNG files
                png_files = list(shot_folder.glob("*.png"))
                png_files.sort()  # Ensure consistent ordering
                
                for i, png_file in enumerate(png_files, 1):
                    # Rename to base_XX.png
                    new_name = f"base_{i:02d}.png"
                    target_file = target_shot_dir / new_name
                    
                    # Copy file
                    shutil.copy2(png_file, target_file)
                    
                    # Insert take record
                    self._insert_take_record(shot_id, 'base_image', f"media/{shot_id}/{new_name}")
                    
                    logger.debug(f"Copied {png_file.name} -> {new_name}")
            
            logger.info("Image storyboard processed successfully")
            return True
            
        except Exception as e:
            error_msg = f"Failed to process image storyboard: {e}"
            logger.error(error_msg)
            self.errors.append(error_msg)
            return False
    
    def _process_video_storyboard(self, video_storyboard: Path, media_dir: Path) -> bool:
        """Process video storyboard files."""
        try:
            logger.info("Processing video storyboard...")
            
            for shot_folder in video_storyboard.iterdir():
                if not shot_folder.is_dir():
                    continue
                
                shot_name = shot_folder.name
                if shot_name not in self.shot_mapping:
                    warning_msg = f"Shot '{shot_name}' not found in CSV, skipping"
                    logger.warning(warning_msg)
                    self.warnings.append(warning_msg)
                    continue
                
                shot_id = self.shot_mapping[shot_name]
                target_shot_dir = media_dir / str(shot_id)
                target_shot_dir.mkdir(exist_ok=True)
                
                # Find video-PNG pairs
                video_files = [f for f in shot_folder.iterdir() 
                             if f.suffix.lower() in self.video_extensions]
                png_files = [f for f in shot_folder.iterdir() 
                           if f.suffix.lower() == '.png']
                
                # Group by stem name
                video_dict = {f.stem: f for f in video_files}
                png_dict = {f.stem: f for f in png_files}
                
                # Process pairs
                take_number = 1
                for stem in video_dict:
                    if stem in png_dict:
                        video_file = video_dict[stem]
                        png_file = png_dict[stem]
                        
                        # Rename files
                        video_name = f"video_{take_number:02d}{video_file.suffix}"
                        png_name = f"video_{take_number:02d}.png"
                        
                        target_video = target_shot_dir / video_name
                        target_png = target_shot_dir / png_name
                        
                        # Copy files
                        shutil.copy2(video_file, target_video)
                        shutil.copy2(png_file, target_png)
                        
                        # Insert take records
                        self._insert_take_record(shot_id, 'final_video', f"media/{shot_id}/{video_name}")
                        self._insert_take_record(shot_id, 'video_workflow', f"media/{shot_id}/{png_name}")
                        
                        logger.debug(f"Copied {video_file.name} -> {video_name}")
                        logger.debug(f"Copied {png_file.name} -> {png_name}")
                        
                        take_number += 1
                
                if take_number == 1:
                    warning_msg = f"No valid video-PNG pairs found for shot '{shot_name}'"
                    logger.warning(warning_msg)
                    self.warnings.append(warning_msg)
            
            logger.info("Video storyboard processed successfully")
            return True
            
        except Exception as e:
            error_msg = f"Failed to process video storyboard: {e}"
            logger.error(error_msg)
            self.errors.append(error_msg)
            return False
    
    def _insert_take_record(self, shot_id: int, take_type: str, file_path: str):
        """Insert a take record into the database."""
        try:
            db_path = self.target_path / "data" / "shots.db"
            
            with sqlite3.connect(db_path) as conn:
                # Generate UUID for take_id (matching Option 1 format)
                take_id = generate_uuid()
                
                conn.execute('''
                    INSERT OR REPLACE INTO takes (take_id, shot_id, take_type, file_path, created_date)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    take_id, shot_id, take_type, file_path,
                    datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
                ))
                
                conn.commit()
                
        except Exception as e:
            error_msg = f"Failed to insert take record: {e}"
            logger.error(error_msg)
            self.errors.append(error_msg)
    
    def _generate_migration_log(self):
        """Generate migration log with all messages."""
        try:
            log_file = self.target_path / "migration.log"
            
            with open(log_file, 'w', encoding='utf-8') as f:
                f.write(f"AIMMS Migration Tool - Option 4 Log\n")
                f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("=" * 60 + "\n\n")
                
                # Info messages
                if self.info:
                    f.write("INFO MESSAGES:\n")
                    f.write("-" * 30 + "\n")
                    for msg in self.info:
                        f.write(f"• {msg}\n")
                    f.write("\n")
                
                # Warning messages
                if self.warnings:
                    f.write("WARNING MESSAGES:\n")
                    f.write("-" * 30 + "\n")
                    for msg in self.warnings:
                        f.write(f"⚠ {msg}\n")
                    f.write("\n")
                
                # Error messages
                if self.errors:
                    f.write("ERROR MESSAGES:\n")
                    f.write("-" * 30 + "\n")
                    for msg in self.errors:
                        f.write(f"❌ {msg}\n")
                    f.write("\n")
                
                # Summary
                f.write("MIGRATION SUMMARY:\n")
                f.write("-" * 30 + "\n")
                f.write(f"Shots created: {len(self.shot_mapping)}\n")
                f.write(f"Errors: {len(self.errors)}\n")
                f.write(f"Warnings: {len(self.warnings)}\n")
                f.write(f"Info: {len(self.info)}\n")
                
                if self.errors:
                    f.write("\n❌ MIGRATION FAILED - Please fix the errors above and retry.\n")
                else:
                    f.write("\n✅ MIGRATION COMPLETED SUCCESSFULLY!\n")
            
            logger.info(f"Migration log generated: {log_file}")
            
        except Exception as e:
            logger.error(f"Failed to generate migration log: {e}")