"""
Database Migration Module

Handles migration of SQLite database from old schema to new schema.
"""

import sqlite3
import uuid
import os
import logging
from datetime import datetime
from typing import Dict, List, Optional, NamedTuple
from pathlib import Path

from models import MigrationResult, ShotInfo, TakeInfo, AssetInfo
from utils import convert_date_to_utc, update_file_path, generate_uuid
from logger import create_migration_logger
from schema_manager import SchemaManager

logger = create_migration_logger('database')

class DatabaseMigrator:
    """Handles database schema migration."""
    
    def __init__(self, source_db_path: str, target_db_path: str, schema_path: str = "schema/aimms-shot-db-schema.json", meta_entries_path: str = "schema/aimms-meta-entries.json"):
        """
        Initialize database migrator.
        
        Args:
            source_db_path: Path to source database
            target_db_path: Path to target database
            schema_path: Path to schema JSON file
            meta_entries_path: Path to meta entries JSON file
        """
        self.source_db_path = source_db_path
        self.target_db_path = target_db_path
        self.shot_mapping: Dict[str, int] = {}
        self.logger = create_migration_logger('database.migrator')
        
        # Initialize schema manager
        self.schema_manager = SchemaManager(schema_path, meta_entries_path)
        self.logger.info(f"Using schema file: {schema_path}")
        self.logger.info(f"Using meta entries file: {meta_entries_path}")
        
    def migrate(self) -> MigrationResult:
        """
        Execute complete database migration.
        
        Returns:
            MigrationResult with success status and shot mapping
        """
        errors = []
        warnings = []
        
        try:
            # ======== DATABASE MIGRATION PHASE START ========
            self.logger.info("=" * 60)
            self.logger.info("DATABASE MIGRATION PHASE STARTING")
            self.logger.info("=" * 60)
            self.logger.info("Starting database migration")
            
            # Validate source database
            if not self._validate_source_database():
                return MigrationResult(
                    success=False,
                    shot_mapping={},
                    errors=["Source database validation failed"],
                    warnings=[]
                )
            
            # Create target database using schema manager
            if not self.schema_manager.load_schema():
                return MigrationResult(
                    success=False,
                    shot_mapping={},
                    errors=["Failed to load schema from file"],
                    warnings=[]
                )
            
            if not self._create_target_database():
                return MigrationResult(
                    success=False,
                    shot_mapping={},
                    errors=["Failed to create target database from schema"],
                    warnings=[]
                )
            
            # Migrate tables
            with sqlite3.connect(self.source_db_path) as source_conn:
                with sqlite3.connect(self.target_db_path) as target_conn:
                    # Migrate shots table
                    shots_result = self._migrate_shots_table(source_conn, target_conn)
                    if not shots_result.success:
                        errors.extend(shots_result.errors)
                        warnings.extend(shots_result.warnings)
                    
                    # Migrate takes table
                    takes_result = self._migrate_takes_table(source_conn, target_conn)
                    if not takes_result.success:
                        errors.extend(takes_result.errors)
                        warnings.extend(takes_result.warnings)
                    
                    # Migrate assets table
                    assets_result = self._migrate_assets_table(source_conn, target_conn)
                    if not assets_result.success:
                        errors.extend(assets_result.errors)
                        warnings.extend(assets_result.warnings)
                    
                    # Migrate meta table
                    meta_result = self._migrate_meta_table(source_conn, target_conn)
                    if not meta_result.success:
                        errors.extend(meta_result.errors)
                        warnings.extend(meta_result.warnings)
                    
                    # Create indexes
                    self._create_indexes(target_conn)
            
            success = len(errors) == 0
            self.logger.info(f"Database migration completed: {'SUCCESS' if success else 'FAILED'}")
            
            return MigrationResult(
                success=success,
                shot_mapping=self.shot_mapping,
                errors=errors,
                warnings=warnings
            )
            
        except Exception as e:
            error_msg = f"Database migration failed: {e}"
            self.logger.error(error_msg)
            return MigrationResult(
                success=False,
                shot_mapping={},
                errors=[error_msg],
                warnings=[]
            )
    
    def _validate_source_database(self) -> bool:
        """Validate source database structure and create missing tables."""
        try:
            if not Path(self.source_db_path).exists():
                self.logger.error(f"Source database not found: {self.source_db_path}")
                return False
            
            with sqlite3.connect(self.source_db_path) as conn:
                # Check required tables
                required_tables = ['shots', 'takes', 'assets', 'meta']
                cursor = conn.execute("""
                    SELECT name FROM sqlite_master
                    WHERE type='table' AND name IN ({})
                """.format(','.join(['?'] * len(required_tables))), required_tables)
                
                existing_tables = {row[0] for row in cursor.fetchall()}
                
                missing_tables = set(required_tables) - existing_tables
                if missing_tables:
                    self.logger.warning(f"Missing required tables: {missing_tables}")
                    self.logger.info("Creating missing tables...")
                    
                    # Create missing tables
                    for table_name in missing_tables:
                        if table_name == 'assets':
                            self._create_assets_table(conn)
                        elif table_name == 'meta':
                            self._create_meta_table(conn)
                        elif table_name in ['shots', 'takes']:
                            self.logger.error(f"Critical table '{table_name}' is missing. Migration cannot continue.")
                            return False
                    
                    conn.commit()
                    self.logger.info(f"Created missing tables: {missing_tables}")
                
                # Validate table schemas and log schema mismatches
                self._validate_table_schemas(conn)
                
                self.logger.info("Source database validation passed")
                return True
                
        except Exception as e:
            self.logger.error(f"Source database validation failed: {e}")
            return False
    
    def _validate_table_schemas(self, conn) -> None:
        """
        Validate source database table schemas against target schema.
        Logs additional and missing columns as ERROR entries.
        """
        try:
            # Load target schema if not already loaded
            if not self.schema_manager.schema_data:
                if not self.schema_manager.load_schema():
                    self.logger.error("Failed to load target schema for validation")
                    return
            
            # Validate each table
            tables_to_validate = ['shots', 'takes', 'assets']
            
            for table_name in tables_to_validate:
                self._validate_table_schema(conn, table_name)
                
        except Exception as e:
            self.logger.error(f"Table schema validation failed: {e}")
    
    def _validate_table_schema(self, conn, table_name: str) -> None:
        """
        Validate a specific table schema against target schema.
        Logs additional and missing columns as ERROR entries.
        """
        try:
            # Get source table columns
            cursor = conn.execute(f"PRAGMA table_info({table_name})")
            source_columns = {row[1] for row in cursor.fetchall()}
            
            # Get target table columns from schema
            target_columns = self._get_target_table_columns(table_name)
            
            if not target_columns:
                self.logger.warning(f"Target schema not found for table: {table_name}")
                return
            
            # Find additional columns in source (not in target)
            additional_columns = source_columns - target_columns
            if additional_columns:
                self.logger.error(f"Table '{table_name}' has additional columns not in target schema: {', '.join(additional_columns)}")
                self.logger.error(f"ERROR: Additional columns in {table_name} table will be ignored during migration")
            
            # Find missing columns in source (in target but not in source)
            missing_columns = target_columns - source_columns
            if missing_columns:
                self.logger.error(f"Table '{table_name}' is missing required columns from target schema: {', '.join(missing_columns)}")
                self.logger.error(f"ERROR: Missing columns in {table_name} table will cause migration issues")
            
            # Log summary
            if additional_columns or missing_columns:
                self.logger.error(f"Schema mismatch detected in '{table_name}' table")
            else:
                self.logger.info(f"Schema validation passed for '{table_name}' table")
                
        except Exception as e:
            self.logger.error(f"Failed to validate schema for table '{table_name}': {e}")
    
    def _get_target_table_columns(self, table_name: str) -> set:
        """
        Get column names for a target table from schema.
        
        Args:
            table_name: Name of the table
            
        Returns:
            Set of column names
        """
        try:
            # Get columns from schema
            columns_key = f"{table_name}_columns"
            columns_data = self.schema_manager.schema_data['tables'].get(columns_key, [])
            
            # Extract column names
            column_names = {col['name'] for col in columns_data}
            
            return column_names
            
        except Exception as e:
            self.logger.error(f"Failed to get target columns for table '{table_name}': {e}")
            return set()
    
    def _create_assets_table(self, conn):
        """Create the assets table with correct schema."""
        self.logger.info("Creating assets table")
        conn.execute('''
            CREATE TABLE assets (
                id_key TEXT PRIMARY KEY,
                asset_name TEXT,
                asset_type TEXT,
                file_path TEXT,
                starred INTEGER DEFAULT 0,
                created_date TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now', 'utc'))
            )
        ''')
    
    # Note: _create_meta_table method removed - now handled by schema_manager.create_meta_table_with_entries()
    
    def _create_target_database(self) -> bool:
        """
        Create target database using schema from JSON file.
        
        Returns:
            True if successful, False otherwise
        """
        self.logger.info("Creating target database schema from JSON file")
        
        try:
            # Check if database already exists and has the correct schema
            if self._database_schema_exists():
                self.logger.info("Target database already exists with correct schema")
                return True
            
            # Ensure schema is loaded before creating database
            if not self.schema_manager.schema_data:
                if not self.schema_manager.load_schema():
                    self.logger.error("Failed to load schema")
                    return False
            
            # Use schema manager to create database
            success = self.schema_manager.create_database_from_schema(self.target_db_path)
            
            if success:
                self.logger.info("Target database schema created successfully from schema file")
                
                # Create meta table with entries using schema manager
                with sqlite3.connect(self.target_db_path) as conn:
                    meta_success = self.schema_manager.create_meta_table_with_entries(conn)
                    if not meta_success:
                        self.logger.error("Failed to create meta table with entries")
                        return False
                
                # Validate the created database
                validation_results = self.schema_manager.validate_database_schema(self.target_db_path)
                if not validation_results['valid']:
                    self.logger.warning("Database created but validation found issues:")
                    if validation_results['missing_tables']:
                        self.logger.warning(f"  Missing tables: {validation_results['missing_tables']}")
                    if validation_results['missing_indexes']:
                        self.logger.warning(f"  Missing indexes: {validation_results['missing_indexes']}")
                
                return True
            else:
                self.logger.error("Failed to create target database from schema")
                return False
                
        except Exception as e:
            self.logger.error(f"Error creating target database: {e}")
            return False
    
    def _database_schema_exists(self) -> bool:
        """
        Check if the target database already exists with the correct schema.
        
        Returns:
            True if database exists with correct schema, False otherwise
        """
        try:
            if not os.path.exists(self.target_db_path):
                return False
            
            # Validate the existing database schema
            validation_results = self.schema_manager.validate_database_schema(self.target_db_path)
            
            return validation_results['valid']
            
        except Exception as e:
            self.logger.warning(f"Could not validate existing database: {e}")
            return False
    
    def _migrate_shots_table(self, source_conn, target_conn) -> MigrationResult:
        """Migrate shots table with schema transformation."""
        errors = []
        warnings = []
        
        try:
            self.logger.info("Migrating shots table")
            
            # Get shots ordered by order_number
            cursor = source_conn.execute('''
                SELECT order_number, shot_name, section, description, 
                       image_prompt, colour_scheme_image, time_of_day,
                       location, country, year, video_prompt, created_date
                FROM shots 
                ORDER BY order_number
            ''')
            
            shots_data = cursor.fetchall()
            total_shots = len(shots_data)
            
            if total_shots == 0:
                warnings.append("No shots found in source database")
                return MigrationResult(success=True, shot_mapping={}, errors=[], warnings=warnings)
            
            # Insert into new table
            for i, row in enumerate(shots_data):
                order_number, shot_name, section, description, image_prompt, \
                colour_scheme_image, time_of_day, location, country, year, \
                video_prompt, created_date = row
                
                # Convert date format
                converted_date = convert_date_to_utc(created_date)
                
                try:
                    # Insert into new table
                    target_conn.execute('''
                        INSERT INTO shots (
                            order_number, shot_name, section, description,
                            image_prompt, colour_scheme_image, time_of_day,
                            location, country, year, video_prompt, created_date
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (order_number, shot_name, section, description,
                          image_prompt, colour_scheme_image, time_of_day,
                          location, country, year, video_prompt, converted_date))
                    
                    # Get the new shot_id
                    new_shot_id = target_conn.execute('SELECT last_insert_rowid()').fetchone()[0]
                    
                    # Store mapping
                    self.shot_mapping[shot_name] = new_shot_id
                    
                except Exception as e:
                    error_msg = f"Failed to migrate shot {shot_name}: {e}"
                    errors.append(error_msg)
                    self.logger.error(error_msg)
                
                # Log progress
                if (i + 1) % 50 == 0 or i == total_shots - 1:
                    progress = ((i + 1) / total_shots) * 100
                    self.logger.info(f"Shots migration progress: {progress:.1f}% ({i+1}/{total_shots})")
            
            target_conn.commit()
            
            success = len(errors) == 0
            self.logger.info(f"Shots table migration completed: {'SUCCESS' if success else 'FAILED'}")
            
            return MigrationResult(
                success=success,
                shot_mapping=self.shot_mapping,
                errors=errors,
                warnings=warnings
            )
            
        except Exception as e:
            error_msg = f"Failed to migrate shots table: {e}"
            errors.append(error_msg)
            self.logger.error(error_msg)
            return MigrationResult(success=False, shot_mapping={}, errors=errors, warnings=warnings)
    
    def _migrate_takes_table(self, source_conn, target_conn) -> MigrationResult:
        """Migrate takes table with new schema."""
        errors = []
        warnings = []
        
        try:
            self.logger.info("Migrating takes table")
            
            # Get takes from old table
            cursor = source_conn.execute('''
                SELECT shot_name, take_type, file_path, starred, created_date
                FROM takes
            ''')
            
            takes_data = cursor.fetchall()
            total_takes = len(takes_data)
            
            if total_takes == 0:
                warnings.append("No takes found in source database")
                return MigrationResult(success=True, shot_mapping={}, errors=[], warnings=warnings)
            
            # Insert into new table
            for i, row in enumerate(takes_data):
                shot_name, take_type, file_path, starred, created_date = row
                
                # Get shot_id from mapping
                if shot_name not in self.shot_mapping:
                    error_msg = f"Shot name {shot_name} not found in mapping"
                    errors.append(error_msg)
                    self.logger.warning(error_msg)
                    continue
                
                shot_id = self.shot_mapping[shot_name]
                
                # Generate UUID for take_id
                take_id = generate_uuid()
                
                # Convert date format
                converted_date = convert_date_to_utc(created_date)
                
                # Extract relative path from full file path
                relative_file_path = self._extract_relative_path(file_path)
                
                # Update file_path to use shot_id
                new_file_path = update_file_path(relative_file_path, shot_id, shot_name)
                
                try:
                    # Insert into new table
                    target_conn.execute('''
                        INSERT INTO takes (
                            take_id, shot_id, take_type, file_path, starred, created_date
                        ) VALUES (?, ?, ?, ?, ?, ?)
                    ''', (take_id, shot_id, take_type, new_file_path, starred, converted_date))
                    
                except Exception as e:
                    error_msg = f"Failed to migrate take for shot {shot_name}: {e}"
                    errors.append(error_msg)
                    self.logger.error(error_msg)
                
                # Log progress
                if (i + 1) % 100 == 0 or i == total_takes - 1:
                    progress = ((i + 1) / total_takes) * 100
                    self.logger.info(f"Takes migration progress: {progress:.1f}% ({i+1}/{total_takes})")
            
            target_conn.commit()
            
            success = len(errors) == 0
            self.logger.info(f"Takes table migration completed: {'SUCCESS' if success else 'FAILED'}")
            
            return MigrationResult(
                success=success,
                shot_mapping=self.shot_mapping,
                errors=errors,
                warnings=warnings
            )
            
        except Exception as e:
            error_msg = f"Failed to migrate takes table: {e}"
            errors.append(error_msg)
            self.logger.error(error_msg)
            return MigrationResult(success=False, shot_mapping={}, errors=errors, warnings=warnings)
    
    def _migrate_assets_table(self, source_conn, target_conn) -> MigrationResult:
        """Migrate assets table."""
        errors = []
        warnings = []
        
        try:
            self.logger.info("Migrating assets table")
            
            # Get assets from old table
            cursor = source_conn.execute('''
                SELECT id_key, asset_name, asset_type, file_path, starred, created_date
                FROM assets
            ''')
            
            assets_data = cursor.fetchall()
            total_assets = len(assets_data)
            
            if total_assets == 0:
                warnings.append("No assets found in source database")
                return MigrationResult(success=True, shot_mapping={}, errors=[], warnings=warnings)
            
            # Insert into new table
            for i, row in enumerate(assets_data):
                id_key, asset_name, asset_type, file_path, starred, created_date = row
                
                # Extract relative path from full file path
                relative_file_path = self._extract_relative_path(file_path)
                
                # Convert date format
                converted_date = convert_date_to_utc(created_date)
                
                try:
                    # Insert into new table
                    target_conn.execute('''
                        INSERT INTO assets (
                            id_key, asset_name, asset_type, file_path, starred, created_date
                        ) VALUES (?, ?, ?, ?, ?, ?)
                    ''', (id_key, asset_name, asset_type, relative_file_path, starred, converted_date))
                    
                except Exception as e:
                    error_msg = f"Failed to migrate asset {id_key}: {e}"
                    errors.append(error_msg)
                    self.logger.error(error_msg)
                
                # Log progress
                if (i + 1) % 50 == 0 or i == total_assets - 1:
                    progress = ((i + 1) / total_assets) * 100
                    self.logger.info(f"Assets migration progress: {progress:.1f}% ({i+1}/{total_assets})")
            
            target_conn.commit()
            
            success = len(errors) == 0
            self.logger.info(f"Assets table migration completed: {'SUCCESS' if success else 'FAILED'}")
            
            return MigrationResult(
                success=success,
                shot_mapping=self.shot_mapping,
                errors=errors,
                warnings=warnings
            )
            
        except Exception as e:
            error_msg = f"Failed to migrate assets table: {e}"
            errors.append(error_msg)
            self.logger.error(error_msg)
            return MigrationResult(success=False, shot_mapping={}, errors=errors, warnings=warnings)
    
    def _migrate_meta_table(self, source_conn, target_conn) -> MigrationResult:
        """Migrate meta table with version validation."""
        errors = []
        warnings = []
        
        try:
            self.logger.info("Migrating meta table")
            
            # Load meta entries from schema manager
            if not self.schema_manager.meta_entries_data:
                if not self.schema_manager.load_meta_entries():
                    error_msg = "Failed to load meta entries from schema manager"
                    errors.append(error_msg)
                    self.logger.error(error_msg)
                    return MigrationResult(success=False, shot_mapping={}, errors=errors, warnings=warnings)
            
            # Get meta data from old table
            cursor = source_conn.execute('SELECT key, value FROM meta')
            meta_data = cursor.fetchall()
            
            # Process existing meta data
            existing_meta = {}
            for key, value in meta_data:
                existing_meta[key] = value
            
            # Get meta entries configuration
            meta_entries_config = self.schema_manager.meta_entries_data['meta_entries']
            
            # Process each meta entry based on configuration
            for key, config in meta_entries_config.items():
                if key in existing_meta:
                    # Handle existing entries
                    value = existing_meta[key]
                    
                    # Validate version numbers
                    if key == 'schema_version':
                        value = '1'  # Force to 1
                    elif key == 'app_version':
                        value = '1.0'  # Force to 1.0
                    
                    # Convert created_at date format
                    if key == 'created_at':
                        value = convert_date_to_utc(value)
                    
                    try:
                        target_conn.execute('''
                            INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)
                        ''', (key, value))
                        self.logger.info(f"Migrated meta entry: {key} = {value}")
                        
                    except Exception as e:
                        error_msg = f"Failed to migrate meta key {key}: {e}"
                        errors.append(error_msg)
                        self.logger.error(error_msg)
                
                else:
                    # Handle missing entries based on configuration
                    if config.get('create_if_missing', False):
                        value = config['value']
                        
                        # Handle dynamic values
                        if config.get('dynamic', False) and value == 'CURRENT_UTC_ISO8601':
                            value = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
                        
                        try:
                            target_conn.execute('''
                                INSERT OR IGNORE INTO meta (key, value) VALUES (?, ?)
                            ''', (key, value))
                            self.logger.info(f"Created missing meta entry: {key} = {value}")
                            
                        except Exception as e:
                            error_msg = f"Failed to create meta key {key}: {e}"
                            errors.append(error_msg)
                            self.logger.error(error_msg)
            
            # Always update migration_date (overwrite existing)
            migration_date = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
            try:
                target_conn.execute('''
                    INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)
                ''', ('migration_date', migration_date))
                self.logger.info(f"Updated migration_date: {migration_date}")
                
            except Exception as e:
                error_msg = f"Failed to update migration_date: {e}"
                errors.append(error_msg)
                self.logger.error(error_msg)
            
            target_conn.commit()
            
            success = len(errors) == 0
            self.logger.info(f"Meta table migration completed: {'SUCCESS' if success else 'FAILED'}")
            
            return MigrationResult(
                success=success,
                shot_mapping=self.shot_mapping,
                errors=errors,
                warnings=warnings
            )
            
        except Exception as e:
            error_msg = f"Failed to migrate meta table: {e}"
            errors.append(error_msg)
            self.logger.error(error_msg)
            return MigrationResult(success=False, shot_mapping={}, errors=errors, warnings=warnings)
    
    def _create_indexes(self, conn):
        """Create performance indexes."""
        self.logger.info("Creating database indexes")
        
        indexes = [
            'CREATE INDEX IF NOT EXISTS idx_shots_shot_name ON shots(shot_name)',
            'CREATE INDEX IF NOT EXISTS idx_shots_order ON shots(order_number)',
            'CREATE INDEX IF NOT EXISTS idx_takes_shot_id ON takes(shot_id)',
            'CREATE INDEX IF NOT EXISTS idx_takes_type ON takes(take_type)',
            'CREATE INDEX IF NOT EXISTS idx_takes_starred ON takes(starred)',
            'CREATE INDEX IF NOT EXISTS idx_takes_shot_type ON takes(shot_id, take_type)',
            'CREATE INDEX IF NOT EXISTS idx_deleted_shots_old_id ON deleted_shots(old_shot_id)'
        ]
        
        for index_sql in indexes:
            try:
                conn.execute(index_sql)
            except Exception as e:
                self.logger.warning(f"Failed to create index: {e}")
        
        conn.commit()
        self.logger.info("Database indexes created successfully")
    
    def create_video_workflow_entries(self, media_path: str, shot_mapping: Dict[str, int]) -> bool:
        """
        Create missing video_workflow entries for video thumbnails.
        
        Args:
            media_path: Path to media directory
            shot_mapping: Shot name to ID mapping
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.logger.info("Creating missing video_workflow entries for video thumbnails")
            
            with sqlite3.connect(self.target_db_path) as conn:
                # Get all existing video thumbnails from media folders
                for shot_name, shot_id in shot_mapping.items():
                    media_folder = os.path.join(media_path, str(shot_id))
                    
                    if not os.path.exists(media_folder):
                        continue
                    
                    # Find video thumbnails in this folder
                    for item in os.listdir(media_folder):
                        if item.startswith('video_') and item.endswith('.png'):
                            video_name = item.replace('.png', '.mp4')
                            file_path = os.path.join(media_folder, item)
                            
                            # Create relative path for database storage
                            # Convert: C:\...\media\1\video_01.png -> /media/1/video_01.png
                            relative_path = os.path.join('media', str(shot_id), item)
                            # Ensure forward slashes for database storage
                            db_file_path = relative_path.replace('\\', '/')
                            
                            # Extract relative path from full file path (in case it was full path)
                            db_file_path = self._extract_relative_path(db_file_path)
                            
                            # Check if corresponding video exists
                            video_path = os.path.join(media_folder, video_name)
                            if not os.path.exists(video_path):
                                self.logger.warning(f"Video thumbnail {item} has no corresponding video in shot {shot_name}")
                                continue
                            
                            # Check if video_workflow entry already exists
                            cursor = conn.execute('''
                                SELECT COUNT(*) FROM takes
                                WHERE shot_id = ? AND file_path = ? AND take_type = 'video_workflow'
                            ''', (shot_id, db_file_path))
                            
                            if cursor.fetchone()[0] == 0:
                                # Create video_workflow entry
                                take_id = generate_uuid()
                                created_date = convert_date_to_utc(None)  # Current time
                                
                                conn.execute('''
                                    INSERT INTO takes (
                                        take_id, shot_id, take_type, file_path, starred, created_date
                                    ) VALUES (?, ?, ?, ?, ?, ?)
                                ''', (take_id, shot_id, 'video_workflow', db_file_path, 0, created_date))
                                
                                self.logger.info(f"Created video_workflow entry for {item} in shot {shot_name}")
                
                conn.commit()
                self.logger.info("Video workflow entries creation completed")
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to create video workflow entries: {e}")
            return False
    
    def _extract_relative_path(self, file_path: str) -> str:
        """
        Extract relative path from full file path by finding 'media' directory.
        
        Args:
            file_path: Full or relative file path
            
        Returns:
            Relative path starting from 'media' directory, or original path if 'media' not found
        """
        try:
            # Handle both forward and backward slashes
            normalized_path = file_path.replace('\\', '/')
            
            # Find the 'media' directory in the path
            media_index = normalized_path.lower().find('/media/')
            
            if media_index != -1:
                # Extract path from 'media' onwards
                relative_path = normalized_path[media_index + 1:]  # Remove leading '/'
                return relative_path
            else:
                # If 'media' not found, log error and return original path
                self.logger.error(f"ERROR: Could not find 'media' directory in file path: {file_path}")
                return file_path
                
        except Exception as e:
            self.logger.error(f"ERROR: Failed to extract relative path from {file_path}: {e}")
            return file_path
    
    def get_database_info(self, db_path: Optional[str] = None) -> Optional[Dict]:
        """
        Get information about a database.
        
        Args:
            db_path: Path to database (uses target if not specified)
            
        Returns:
            Dictionary with database information
        """
        path = db_path or self.target_db_path
        
        try:
            with sqlite3.connect(path) as conn:
                # Get table counts
                cursor = conn.execute("""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name IN ('shots', 'takes', 'assets', 'meta')
                """)
                tables = [row[0] for row in cursor.fetchall()]
                
                table_counts = {}
                for table in tables:
                    cursor = conn.execute(f"SELECT COUNT(*) FROM {table}")
                    table_counts[table] = cursor.fetchone()[0]
                
                # Get version info
                cursor = conn.execute("SELECT value FROM meta WHERE key='schema_version'")
                schema_version = cursor.fetchone()
                
                cursor = conn.execute("SELECT value FROM meta WHERE key='app_version'")
                app_version = cursor.fetchone()
                
                return {
                    'path': path,
                    'exists': True,
                    'schema_version': schema_version[0] if schema_version else None,
                    'app_version': app_version[0] if app_version else None,
                    'table_counts': table_counts,
                    'shot_mapping': self.shot_mapping
                }
                
        except Exception as e:
            self.logger.error(f"Failed to get database info: {e}")
            return None