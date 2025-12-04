"""
Database Migration Module

Handles migration of SQLite database from old schema to new schema.
"""

import sqlite3
import uuid
import logging
from datetime import datetime
from typing import Dict, List, Optional, NamedTuple
from pathlib import Path

from models import MigrationResult, ShotInfo, TakeInfo, AssetInfo
from utils import convert_date_to_utc, update_file_path, generate_uuid
from logger import create_migration_logger

logger = create_migration_logger('database')

class DatabaseMigrator:
    """Handles database schema migration."""
    
    def __init__(self, source_db_path: str, target_db_path: str):
        """
        Initialize database migrator.
        
        Args:
            source_db_path: Path to source database
            target_db_path: Path to target database
        """
        self.source_db_path = source_db_path
        self.target_db_path = target_db_path
        self.shot_mapping: Dict[str, int] = {}
        self.logger = create_migration_logger('database.migrator')
        
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
            
            # Create target database
            self._create_target_database()
            
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
        """Validate source database structure."""
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
                    self.logger.error(f"Missing required tables: {missing_tables}")
                    return False
                
                # Check shots table structure
                cursor = conn.execute("PRAGMA table_info(shots)")
                shots_columns = {row[1] for row in cursor.fetchall()}
                
                required_shot_columns = {'shot_name', 'order_number'}
                if not required_shot_columns.issubset(shots_columns):
                    self.logger.error(f"Shots table missing required columns: {required_shot_columns - shots_columns}")
                    return False
                
                self.logger.info("Source database validation passed")
                return True
                
        except Exception as e:
            self.logger.error(f"Source database validation failed: {e}")
            return False
    
    def _create_target_database(self):
        """Create target database with new schema."""
        self.logger.info("Creating target database schema")
        
        with sqlite3.connect(self.target_db_path) as conn:
            # Create shots table
            conn.execute('''
                CREATE TABLE shots (
                    shot_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    order_number INTEGER,
                    shot_name TEXT,
                    section TEXT,
                    description TEXT,
                    image_prompt TEXT,
                    colour_scheme_image TEXT,
                    time_of_day TEXT,
                    location TEXT,
                    country TEXT,
                    year TEXT,
                    video_prompt TEXT,
                    created_date TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now', 'utc'))
                )
            ''')
            
            # Create takes table
            conn.execute('''
                CREATE TABLE takes (
                    take_id TEXT PRIMARY KEY,
                    shot_id INTEGER,
                    take_type TEXT,
                    file_path TEXT,
                    starred INTEGER DEFAULT 0,
                    created_date TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now', 'utc')),
                    FOREIGN KEY (shot_id) REFERENCES shots(shot_id)
                )
            ''')
            
            # Create assets table
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
            
            # Create meta table
            conn.execute('''
                CREATE TABLE meta (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            ''')
            
            # Create deleted_shots table
            conn.execute('''
                CREATE TABLE deleted_shots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    old_shot_id INTEGER NOT NULL,
                    shot_name TEXT,
                    created_date TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now', 'utc'))
                )
            ''')
            
            conn.commit()
            self.logger.info("Target database schema created successfully")
    
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
                
                # Update file_path to use shot_id
                new_file_path = update_file_path(file_path, shot_id, shot_name)
                
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
                
                # Convert date format
                converted_date = convert_date_to_utc(created_date)
                
                try:
                    # Insert into new table
                    target_conn.execute('''
                        INSERT INTO assets (
                            id_key, asset_name, asset_type, file_path, starred, created_date
                        ) VALUES (?, ?, ?, ?, ?, ?)
                    ''', (id_key, asset_name, asset_type, file_path, starred, converted_date))
                    
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
            
            # Get meta data from old table
            cursor = source_conn.execute('SELECT key, value FROM meta')
            meta_data = cursor.fetchall()
            
            # Insert into new table
            for key, value in meta_data:
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
                        INSERT INTO meta (key, value) VALUES (?, ?)
                    ''', (key, value))
                    
                except Exception as e:
                    error_msg = f"Failed to migrate meta key {key}: {e}"
                    errors.append(error_msg)
                    self.logger.error(error_msg)
            
            # Add migration timestamp
            target_conn.execute('''
                INSERT OR REPLACE INTO meta (key, value) 
                VALUES (?, ?)
            ''', ('migration_date', datetime.utcnow().isoformat()))
            
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