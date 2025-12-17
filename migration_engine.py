"""
Migration Engine - Orchestrates the migration process
"""

import logging
import shutil
import os
import time
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from config import MigrationConfig
from database import DatabaseMigrator
from media import MediaMigrator
from validation import Validator
from reporting import ReportGenerator
from logger import (
    log_migration_start, log_migration_end, MigrationLogger,
    create_migration_logger
)
from models import MigrationResult, ValidationResult, MediaResult
from import_non_aimms_media import Option4Migrator

logger = create_migration_logger('engine')

class MigrationEngine:
    """Main migration orchestrator."""
    
    def __init__(self, config: MigrationConfig):
        """
        Initialize migration engine.
        
        Args:
            config: Migration configuration
        """
        self.config = config
        self.logger = create_migration_logger('engine.migration')
        self.shot_mapping: Dict[str, int] = {}
        self.migration_stats = {
            'start_time': None,
            'end_time': None,
            'phases': [],
            'errors': [],
            'warnings': []
        }
        
    def run_migration(self) -> bool:
        """
        Execute the complete migration process.
        
        Returns:
            True if migration successful, False otherwise
        """
        start_time = datetime.now()
        self.migration_stats['start_time'] = start_time
        
        try:
            log_migration_start(self.config)
            self.logger.info(f"Migration mode: {self.config.get_migration_mode_description()}")
            
            # Handle Option 4 separately
            if self.config.mode == 'option4':
                return self._run_option4_migration()
            
            # Phase 1: Preparation
            if not self._prepare_migration():
                return False
            
            # Phase 2: Database Migration
            if not self._migrate_database():
                return False
            
            # Phase 3: Media Migration
            if not self._migrate_media():
                return False
            
            # Phase 4: Validation
            if not self._validate_migration():
                return False
            
            # Phase 5: Reporting
            self._generate_reports()
            
            end_time = datetime.now()
            self.migration_stats['end_time'] = end_time
            
            duration = (end_time - start_time).total_seconds()
            log_migration_end(True, duration)
            
            self.logger.info("Migration completed successfully!")
            return True
            
        except Exception as e:
            end_time = datetime.now()
            self.migration_stats['end_time'] = end_time
            
            duration = (end_time - start_time).total_seconds()
            log_migration_end(False, duration)
            
            error_msg = f"Migration failed with error: {e}"
            self.logger.error(error_msg)
            self.migration_stats['errors'].append(error_msg)
            
            # Generate reports even on early failure
            try:
                self._generate_reports_on_failure()
            except Exception as report_error:
                self.logger.error(f"Failed to generate failure reports: {report_error}")
            
            return False
    
    def _prepare_migration(self) -> bool:
        """Prepare for migration."""
        phase_logger = MigrationLogger('engine.prepare')
        phase_logger.start_operation("Preparation Phase")
        
        start_time = datetime.now()
        
        try:
            # Validate configuration
            self.config.validate_source_exists()
            self.config.validate_target_writable()
            self.config.validate_csv_file()
            self.config.validate_restore_file()
            
            # Create target directory structure
            self._create_target_directories()
            
            # Copy configuration files first (before creating clean structure)
            self._copy_config_files()
            
            # Create project structure and supporting files
            self._create_project_structure()
            
            # Create backup if requested
            if self.config.create_backup:
                self._create_backup()
            
            # Log preparation summary
            duration = (datetime.now() - start_time).total_seconds()
            phase_logger.end_operation("Preparation Phase", True, f"Duration: {duration:.2f} seconds")
            
            self.migration_stats['phases'].append({
                'name': 'Preparation',
                'status': 'SUCCESS',
                'duration': duration,
                'start_time': start_time,
                'end_time': datetime.now()
            })
            
            return True
            
        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            phase_logger.end_operation("Preparation Phase", False, f"Error: {e}")
            
            self.migration_stats['phases'].append({
                'name': 'Preparation',
                'status': 'FAILED',
                'duration': duration,
                'start_time': start_time,
                'end_time': datetime.now(),
                'error': str(e)
            })
            
            self.migration_stats['errors'].append(f"Preparation failed: {e}")
            return False
    
    def _migrate_database(self) -> bool:
        """Migrate database from old to new schema."""
        phase_logger = MigrationLogger('engine.database')
        phase_logger.start_operation("Database Migration Phase")
        
        start_time = datetime.now()
        
        try:
            # Initialize database migrator with schema path
            db_migrator = DatabaseMigrator(
                source_db_path=self.config.get_source_db_path(),
                target_db_path=self.config.get_target_db_path(),
                schema_path="schema/aimms-shot-db-schema.json"
            )
            
            # Execute database migration
            migration_result = db_migrator.migrate()
            
            # Store shot mapping for media migration
            self.shot_mapping = migration_result.shot_mapping
            
            # Log results
            duration = (datetime.now() - start_time).total_seconds()
            
            if migration_result.success:
                phase_logger.end_operation(
                    "Database Migration Phase", 
                    True, 
                    f"Duration: {duration:.2f} seconds, "
                    f"Shots migrated: {len(self.shot_mapping)}"
                )
                
                self.migration_stats['phases'].append({
                    'name': 'Database Migration',
                    'status': 'SUCCESS',
                    'duration': duration,
                    'start_time': start_time,
                    'end_time': datetime.now(),
                    'shot_mapping': self.shot_mapping,
                    'errors': migration_result.errors,
                    'warnings': migration_result.warnings
                })
                
                # Store errors and warnings
                self.migration_stats['errors'].extend(migration_result.errors)
                self.migration_stats['warnings'].extend(migration_result.warnings)
                
                return True
            else:
                phase_logger.end_operation(
                    "Database Migration Phase", 
                    False, 
                    f"Duration: {duration:.2f} seconds, "
                    f"Errors: {len(migration_result.errors)}"
                )
                
                self.migration_stats['phases'].append({
                    'name': 'Database Migration',
                    'status': 'FAILED',
                    'duration': duration,
                    'start_time': start_time,
                    'end_time': datetime.now(),
                    'errors': migration_result.errors,
                    'warnings': migration_result.warnings
                })
                
                self.migration_stats['errors'].extend(migration_result.errors)
                self.migration_stats['warnings'].extend(migration_result.warnings)
                
                return False
            
        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            phase_logger.end_operation("Database Migration Phase", False, f"Error: {e}")
            
            self.migration_stats['phases'].append({
                'name': 'Database Migration',
                'status': 'FAILED',
                'duration': duration,
                'start_time': start_time,
                'end_time': datetime.now(),
                'error': str(e)
            })
            
            self.migration_stats['errors'].append(f"Database migration failed: {e}")
            return False
    
    def _migrate_media(self) -> bool:
        """Migrate media files."""
        phase_logger = MigrationLogger('engine.media')
        phase_logger.start_operation("Media Migration Phase")
        
        start_time = datetime.now()
        
        try:
            # Initialize media migrator
            media_migrator = MediaMigrator(
                source_media_path=self.config.get_source_media_path(),
                target_media_path=self.config.get_target_media_path(),
                shot_mapping=self.shot_mapping
            )
            
            # Execute media migration
            success = media_migrator.migrate()
            
            # Get asset migration information
            asset_info = self._get_asset_migration_info(media_migrator)
            
            duration = (datetime.now() - start_time).total_seconds()
            
            if success:
                phase_logger.end_operation(
                    "Media Migration Phase",
                    True,
                    f"Duration: {duration:.2f} seconds"
                )
                
                self.migration_stats['phases'].append({
                    'name': 'Media Migration',
                    'status': 'SUCCESS',
                    'duration': duration,
                    'start_time': start_time,
                    'end_time': datetime.now(),
                    'asset_info': asset_info
                })
                
                # Store asset info in migration stats
                self.migration_stats['asset_info'] = asset_info
                
                return True
            else:
                phase_logger.end_operation(
                    "Media Migration Phase",
                    False,
                    f"Duration: {duration:.2f} seconds"
                )
                
                self.migration_stats['phases'].append({
                    'name': 'Media Migration',
                    'status': 'FAILED',
                    'duration': duration,
                    'start_time': start_time,
                    'end_time': datetime.now(),
                    'asset_info': asset_info
                })
                
                # Store asset info even on failure
                self.migration_stats['asset_info'] = asset_info
                
                return False
            
        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            phase_logger.end_operation("Media Migration Phase", False, f"Error: {e}")
            
            self.migration_stats['phases'].append({
                'name': 'Media Migration',
                'status': 'FAILED',
                'duration': duration,
                'start_time': start_time,
                'end_time': datetime.now(),
                'error': str(e)
            })
            
            self.migration_stats['errors'].append(f"Media migration failed: {e}")
            return False
    
    def _get_asset_migration_info(self, media_migrator: MediaMigrator) -> Dict:
        """Get asset migration information."""
        try:
            # Get media info from the migrator
            media_info = media_migrator.get_media_info()
            
            asset_info = {
                'characters': 0,
                'locations': 0,
                'other': 0,
                'total': 0,
                'characters_files': [],
                'locations_files': [],
                'other_files': []
            }
            
            # Count files in asset directories by scanning the media path directly
            media_path = self.config.get_target_media_path()
            
            if os.path.exists(media_path):
                for item in os.listdir(media_path):
                    item_path = os.path.join(media_path, item)
                    
                    # Check if it's a directory and matches asset directory names
                    if os.path.isdir(item_path) and item.lower() in ['characters', 'locations', 'other']:
                        try:
                            # Count all files recursively in this directory and collect filenames
                            file_count = 0
                            file_list = []
                            
                            for root, dirs, files in os.walk(item_path):
                                for file in files:
                                    file_count += 1
                                    # Get relative path from media directory
                                    rel_path = os.path.relpath(os.path.join(root, file), media_path)
                                    file_list.append(rel_path)
                            
                            if item.lower() == 'characters':
                                asset_info['characters'] = file_count
                                asset_info['characters_files'] = sorted(file_list)
                            elif item.lower() == 'locations':
                                asset_info['locations'] = file_count
                                asset_info['locations_files'] = sorted(file_list)
                            elif item.lower() == 'other':
                                asset_info['other'] = file_count
                                asset_info['other_files'] = sorted(file_list)
                            
                            self.logger.debug(f"Asset directory '{item}': {file_count} files")
                            
                        except Exception as e:
                            self.logger.warning(f"Failed to count files in {item_path}: {e}")
            
            asset_info['total'] = asset_info['characters'] + asset_info['locations'] + asset_info['other']
            
            # Log total asset count
            self.logger.info(f"Total asset files migrated: {asset_info['total']}")
            
            return asset_info
            
        except Exception as e:
            self.logger.warning(f"Failed to get asset migration info: {e}")
            return {
                'characters': 0,
                'locations': 0,
                'other': 0,
                'total': 0,
                'characters_files': [],
                'locations_files': [],
                'other_files': []
            }
    
    def _validate_migration(self) -> bool:
        """Validate migration completeness and correctness."""
        phase_logger = MigrationLogger('engine.validation')
        phase_logger.start_operation("Validation Phase")
        
        start_time = datetime.now()
        
        try:
            # Initialize validator
            validator = Validator(
                db_path=self.config.get_target_db_path(),
                media_path=self.config.get_target_media_path(),
                shot_mapping=self.shot_mapping
            )
            
            # Execute validation
            validation_result = validator.validate()
            
            # Create missing video_workflow entries after media validation
            if validation_result.success or len([e for e in validation_result.errors if 'thumbnail' not in e]) == 0:
                # Only create workflow entries if validation mostly passed or only thumbnail issues
                db_migrator = DatabaseMigrator(
                    source_db_path=self.config.get_source_db_path(),
                    target_db_path=self.config.get_target_db_path(),
                    schema_path="schema/aimms-shot-db-schema.json"
                )
                db_migrator.create_video_workflow_entries(
                    media_path=self.config.get_target_media_path(),
                    shot_mapping=self.shot_mapping
                )
            
            duration = (datetime.now() - start_time).total_seconds()
            
            if validation_result.success:
                phase_logger.end_operation(
                    "Validation Phase",
                    True,
                    f"Duration: {duration:.2f} seconds"
                )
                
                self.migration_stats['phases'].append({
                    'name': 'Validation',
                    'status': 'SUCCESS',
                    'duration': duration,
                    'start_time': start_time,
                    'end_time': datetime.now(),
                    'errors': validation_result.errors,
                    'warnings': validation_result.warnings
                })
                
                # Store validation errors and warnings
                self.migration_stats['errors'].extend(validation_result.errors)
                self.migration_stats['warnings'].extend(validation_result.warnings)
                
                return True
            else:
                phase_logger.end_operation(
                    "Validation Phase",
                    False,
                    f"Duration: {duration:.2f} seconds, "
                    f"Errors: {len(validation_result.errors)}"
                )
                
                self.migration_stats['phases'].append({
                    'name': 'Validation',
                    'status': 'FAILED',
                    'duration': duration,
                    'start_time': start_time,
                    'end_time': datetime.now(),
                    'errors': validation_result.errors,
                    'warnings': validation_result.warnings
                })
                
                self.migration_stats['errors'].extend(validation_result.errors)
                self.migration_stats['warnings'].extend(validation_result.warnings)
                
                return False
            
        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            phase_logger.end_operation("Validation Phase", False, f"Error: {e}")
            
            self.migration_stats['phases'].append({
                'name': 'Validation',
                'status': 'FAILED',
                'duration': duration,
                'start_time': start_time,
                'end_time': datetime.now(),
                'error': str(e)
            })
            
            self.migration_stats['errors'].append(f"Validation failed: {e}")
            return False
    
    def _generate_reports(self):
        """Generate migration reports."""
        phase_logger = MigrationLogger('engine.reporting')
        phase_logger.start_operation("Report Generation Phase")
        
        start_time = datetime.now()
        
        try:
            # Initialize report generator
            report_generator = ReportGenerator(
                target_path=self.config.target_path,
                shot_mapping=self.shot_mapping,
                migration_stats=self.migration_stats
            )
            
            # Generate reports
            report_generator.generate_reports()
            
            duration = (datetime.now() - start_time).total_seconds()
            phase_logger.end_operation(
                "Report Generation Phase", 
                True, 
                f"Duration: {duration:.2f} seconds"
            )
            
            self.migration_stats['phases'].append({
                'name': 'Report Generation',
                'status': 'SUCCESS',
                'duration': duration,
                'start_time': start_time,
                'end_time': datetime.now()
            })
            
        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            phase_logger.end_operation("Report Generation Phase", False, f"Error: {e}")
            
            self.migration_stats['phases'].append({
                'name': 'Report Generation',
                'status': 'FAILED',
                'duration': duration,
                'start_time': start_time,
                'end_time': datetime.now(),
                'error': str(e)
            })
            
            self.migration_stats['errors'].append(f"Report generation failed: {e}")
    
    def _generate_reports_on_failure(self):
        """Generate reports even when migration fails early."""
        try:
            # Create report directory if it doesn't exist
            os.makedirs(self.config.report_path, exist_ok=True)
            
            # Initialize report generator with available data
            report_generator = ReportGenerator(
                target_path=self.config.target_path,
                shot_mapping=self.shot_mapping,
                migration_stats=self.migration_stats
            )
            
            # Generate basic reports
            report_generator.generate_reports()
            
            self.logger.info("Failure reports generated successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to generate failure reports: {e}")
            # Try to create a simple error file
            try:
                error_file = os.path.join(self.config.report_path, 'migration_error.txt')
                with open(error_file, 'w') as f:
                    f.write(f"Migration failed with error: {e}\n")
                    f.write(f"Migration stats: {self.migration_stats}\n")
                self.logger.info(f"Error details saved to: {error_file}")
            except Exception as write_error:
                self.logger.error(f"Failed to write error file: {write_error}")
    
    def _create_target_directories(self):
        """Create target directory structure."""
        self.logger.info("Creating target directory structure")
        
        # Create data directory
        data_dir = self.config.data_path
        os.makedirs(data_dir, exist_ok=True)
        self.logger.debug(f"Created data directory: {data_dir}")
        
        # Create media directory
        media_dir = self.config.media_path
        os.makedirs(media_dir, exist_ok=True)
        self.logger.debug(f"Created media directory: {media_dir}")
        
        # Note: Report directory is now created by the reporting module
        # in the logs folder, so we don't create it here anymore
    
    def _create_backup(self):
        """Create backup of source project."""
        if not self.config.source_path:
            return
        
        backup_path = f"{self.config.source_path}_backup_{self._get_timestamp()}"
        
        self.logger.info(f"Creating backup: {backup_path}")
        
        try:
            shutil.copytree(self.config.source_path, backup_path)
            self.logger.info(f"Backup created successfully at: {backup_path}")
        except Exception as e:
            self.logger.error(f"Backup creation failed: {e}")
            raise
    
    def _copy_config_files(self):
        """Copy configuration files to target."""
        if not self.config.source_path:
            return
        
        source_config = os.path.join(self.config.source_path, 'project_config.json')
        target_config = os.path.join(self.config.target_path, 'project_config.json')
        
        if os.path.exists(source_config):
            try:
                shutil.copy2(source_config, target_config)
                self.logger.debug(f"Copied config file: {source_config} -> {target_config}")
            except Exception as e:
                self.logger.warning(f"Failed to copy config file: {e}")
    
    def _create_project_structure(self):
        """Create project structure and supporting files."""
        self.logger.info("Creating project structure and supporting files")
        
        try:
            # Create project_config.json
            self._create_project_config()
            
            # Create data subfolders
            self._create_data_subfolders()
            
            # Create shot_name_mapping.json in data folder
            self._create_shot_name_mapping()
            
            # Create logs folder and files
            self._create_logs_structure()
            
            self.logger.info("Project structure created successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to create project structure: {e}")
            raise
    
    def _create_project_config(self):
        """Create or update project_config.json."""
        project_config_path = os.path.join(self.config.target_path, 'project_config.json')
        
        # Default project config - ONLY these three fields
        default_config = {
            "last_selected_workflow": "",
            "project_start_date": datetime.now().strftime('%Y-%m-%d'),
            "last_selected_section": "All Sections"
        }
        
        # If file exists, load and preserve ONLY project_start_date
        if os.path.exists(project_config_path):
            try:
                with open(project_config_path, 'r') as f:
                    existing_config = json.load(f)
                
                # Preserve existing project_start_date if it exists
                if 'project_start_date' in existing_config:
                    default_config['project_start_date'] = existing_config['project_start_date']
                    self.logger.info(f"Preserved existing project_start_date: {default_config['project_start_date']}")
                
                # Log the fields that are being removed
                existing_keys = set(existing_config.keys())
                required_keys = set(default_config.keys())
                removed_keys = existing_keys - required_keys
                
                if removed_keys:
                    self.logger.info(f"Removed unwanted fields from existing project_config.json: {', '.join(removed_keys)}")
                else:
                    self.logger.info("No unwanted fields found in existing project_config.json")
                
                # Debug logging to show what will be written
                self.logger.debug(f"Final project_config.json content will contain: {list(default_config.keys())}")
                
            except Exception as e:
                self.logger.warning(f"Failed to read existing project_config.json, using defaults: {e}")
        
        # Write the config - ONLY the three required fields
        with open(project_config_path, 'w') as f:
            json.dump(default_config, f, indent=2)
        
        self.logger.info(f"Created project_config.json at {project_config_path}")
    
    def _create_shot_name_mapping(self):
        """Create shot_name_mapping.json file in data folder."""
        mapping_path = os.path.join(self.config.data_path, 'shot_name_mapping.json')
        
        mapping_data = {
            "version": "1.0",
            "created": datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'),
            "mapping": {}
        }
        
        with open(mapping_path, 'w') as f:
            json.dump(mapping_data, f, indent=2)
        
        self.logger.info(f"Created shot_name_mapping.json in data folder: {mapping_path}")
    
    def _create_data_subfolders(self):
        """Create csv, backup, and saved subfolders in data directory."""
        subfolders = ['csv', 'backup', 'saves']
        
        for subfolder in subfolders:
            subfolder_path = os.path.join(self.config.data_path, subfolder)
            os.makedirs(subfolder_path, exist_ok=True)
            self.logger.debug(f"Created data subfolder: {subfolder_path}")
        
        self.logger.info(f"Created data subfolders: {subfolders}")
    
    def _create_logs_structure(self):
        """Create logs folder and project_log.log file."""
        logs_path = os.path.join(self.config.target_path, 'logs')
        os.makedirs(logs_path, exist_ok=True)
        
        # Create project_log.log file
        project_log_path = os.path.join(logs_path, 'project_log.log')
        with open(project_log_path, 'w') as f:
            f.write('')  # Create empty file
        
        self.logger.info(f"Created logs folder and project_log.log: {logs_path}")
    
    def _get_timestamp(self) -> str:
        """Get current timestamp for backup naming."""
        return datetime.now().strftime('%Y%m%d_%H%M%S')
    
    def _run_option4_migration(self) -> bool:
        """Run Option 4 migration (import non-AIMMS media files)."""
        try:
            self.logger.info("Starting Option 4: Import non-AIMMS media files")
            
            # Initialize Option 4 migrator
            option4_migrator = Option4Migrator(
                source_path=self.config.source_path,
                target_path=self.config.target_path
            )
            
            # Execute migration
            success = option4_migrator.migrate()
            
            # Store results
            self.shot_mapping = option4_migrator.shot_mapping
            self.migration_stats['errors'].extend(option4_migrator.errors)
            self.migration_stats['warnings'].extend(option4_migrator.warnings)
            
            if success:
                self.logger.info("Option 4 migration completed successfully!")
                
                # Generate reports for Option 4
                self._generate_option4_reports(option4_migrator)
                
                return True
            else:
                self.logger.error("Option 4 migration failed!")
                return False
                
        except Exception as e:
            error_msg = f"Option 4 migration failed with error: {e}"
            self.logger.error(error_msg)
            self.migration_stats['errors'].append(error_msg)
            return False
    
    def _generate_option4_reports(self, option4_migrator):
        """Generate reports for Option 4 migration."""
        try:
            # Create report directory
            os.makedirs(self.config.report_path, exist_ok=True)
            
            # Generate basic reports
            report_generator = ReportGenerator(
                target_path=self.config.target_path,
                shot_mapping=self.shot_mapping,
                migration_stats=self.migration_stats
            )
            
            report_generator.generate_reports()
            
            self.logger.info("Option 4 reports generated successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to generate Option 4 reports: {e}")
    
    def get_migration_stats(self) -> Dict:
        """Get comprehensive migration statistics."""
        return self.migration_stats
    
    def get_summary(self) -> Dict:
        """Get migration summary."""
        total_duration = 0
        if self.migration_stats['start_time'] and self.migration_stats['end_time']:
            total_duration = (self.migration_stats['end_time'] - self.migration_stats['start_time']).total_seconds()
        
        phase_summary = []
        for phase in self.migration_stats['phases']:
            phase_summary.append({
                'name': phase['name'],
                'status': phase['status'],
                'duration': phase['duration']
            })
        
        return {
            'total_duration': total_duration,
            'phases': phase_summary,
            'total_errors': len(self.migration_stats['errors']),
            'total_warnings': len(self.migration_stats['warnings']),
            'shot_mapping': self.shot_mapping
        }