"""
Migration Engine - Orchestrates the migration process
"""

import logging
import shutil
import os
import time
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
            
            # Create backup if requested
            if self.config.create_backup:
                self._create_backup()
            
            # Copy configuration files
            self._copy_config_files()
            
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
            # Initialize database migrator
            db_migrator = DatabaseMigrator(
                source_db_path=self.config.get_source_db_path(),
                target_db_path=self.config.get_target_db_path()
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
                    'end_time': datetime.now()
                })
                
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
                    'end_time': datetime.now()
                })
                
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
        
        # Create report directory
        report_dir = self.config.report_path
        os.makedirs(report_dir, exist_ok=True)
        self.logger.debug(f"Created report directory: {report_dir}")
    
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
    
    def _get_timestamp(self) -> str:
        """Get current timestamp for backup naming."""
        return datetime.now().strftime('%Y%m%d_%H%M%S')
    
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