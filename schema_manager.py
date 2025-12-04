#!/usr/bin/env python3
"""
Schema Manager for AIMMS Migration Tool

Manages database schema loading from JSON files and provides methods
to create tables and indexes dynamically based on the schema.
"""

import json
import sqlite3
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional, NamedTuple
from datetime import datetime

class SchemaInfo(NamedTuple):
    """Schema information container."""
    version: str
    extracted_at: str
    tables: List[str]
    indexes: List[str]
    sqlite_version: str

class SchemaManager:
    """Manages database schema operations using JSON schema files."""
    
    def __init__(self, schema_path: str = "schema/aimms-shot-db-schema.json"):
        """
        Initialize schema manager.
        
        Args:
            schema_path: Path to schema JSON file
        """
        self.schema_path = schema_path
        self.schema_data = None
        self.logger = logging.getLogger(__name__)
        
    def load_schema(self) -> bool:
        """
        Load schema from JSON file.
        
        Returns:
            True if schema loaded successfully, False otherwise
        """
        try:
            if not Path(self.schema_path).exists():
                self.logger.error(f"Schema file not found: {self.schema_path}")
                return False
            
            with open(self.schema_path, 'r', encoding='utf-8') as f:
                self.schema_data = json.load(f)
            
            self.logger.info(f"Schema loaded successfully from: {self.schema_path}")
            self.logger.info(f"Schema version: {self.schema_data['metadata']['extracted_at']}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to load schema: {e}")
            return False
    
    def get_schema_info(self) -> Optional[SchemaInfo]:
        """
        Get schema information.
        
        Returns:
            SchemaInfo namedtuple or None if schema not loaded
        """
        if not self.schema_data:
            return None
        
        metadata = self.schema_data['metadata']
        tables = list(self.schema_data['tables'].keys())
        indexes = list(self.schema_data['indexes'].keys())
        
        return SchemaInfo(
            version=metadata['extracted_at'],
            extracted_at=metadata['extracted_at'],
            tables=tables,
            indexes=indexes,
            sqlite_version=metadata['sqlite_version']
        )
    
    def create_database_from_schema(self, db_path: str) -> bool:
        """
        Create database with schema from JSON file.
        
        Args:
            db_path: Path to create the database
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(db_path), exist_ok=True)
            
            with sqlite3.connect(db_path) as conn:
                # Create tables
                table_creation_result = self._create_tables(conn)
                if not table_creation_result:
                    return False
                
                # Create indexes
                index_creation_result = self._create_indexes(conn)
                if not index_creation_result:
                    return False
                
                conn.commit()
                self.logger.info(f"Database created successfully at: {db_path}")
                
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to create database: {e}")
            return False
    
    def _create_tables(self, conn) -> bool:
        """Create all tables from schema."""
        try:
            self.logger.info("Creating tables from schema...")
            
            # Get tables (excluding column info entries)
            table_names = [name for name in self.schema_data['tables'].keys() 
                          if not name.endswith('_columns')]
            
            for table_name in table_names:
                create_sql = self.schema_data['tables'][table_name]
                
                # Skip sqlite_sequence as it's automatically created
                if table_name == 'sqlite_sequence':
                    continue
                
                try:
                    conn.execute(create_sql)
                    self.logger.info(f"Created table: {table_name}")
                except Exception as e:
                    self.logger.error(f"Failed to create table {table_name}: {e}")
                    return False
            
            self.logger.info(f"Successfully created {len(table_names)} tables")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to create tables: {e}")
            return False
    
    def _create_indexes(self, conn) -> bool:
        """Create all indexes from schema."""
        try:
            self.logger.info("Creating indexes from schema...")
            
            index_count = 0
            for index_name, create_sql in self.schema_data['indexes'].items():
                # Skip auto-generated indexes (they start with sqlite_autoindex)
                if index_name.startswith('sqlite_autoindex'):
                    continue
                
                if create_sql:  # Only create if SQL is provided
                    try:
                        conn.execute(create_sql)
                        self.logger.info(f"Created index: {index_name}")
                        index_count += 1
                    except Exception as e:
                        self.logger.error(f"Failed to create index {index_name}: {e}")
                        return False
            
            self.logger.info(f"Successfully created {index_count} indexes")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to create indexes: {e}")
            return False
    
    def get_table_schema(self, table_name: str) -> Optional[Dict]:
        """
        Get schema information for a specific table.
        
        Args:
            table_name: Name of the table
            
        Returns:
            Dictionary with table schema or None if not found
        """
        if not self.schema_data:
            return None
        
        # Check if table exists
        if table_name not in self.schema_data['tables']:
            return None
        
        # Get CREATE TABLE SQL
        create_sql = self.schema_data['tables'][table_name]
        
        # Get column information
        columns_key = f"{table_name}_columns"
        columns = self.schema_data['tables'].get(columns_key, [])
        
        return {
            'table_name': table_name,
            'create_sql': create_sql,
            'columns': columns,
            'column_count': len(columns)
        }
    
    def validate_database_schema(self, db_path: str) -> Dict[str, any]:
        """
        Validate that a database matches the schema.
        
        Args:
            db_path: Path to database to validate
            
        Returns:
            Dictionary with validation results
        """
        results = {
            'valid': True,
            'missing_tables': [],
            'missing_indexes': [],
            'extra_tables': [],
            'extra_indexes': [],
            'table_validations': {}
        }
        
        try:
            with sqlite3.connect(db_path) as conn:
                # Get existing tables and indexes
                cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
                existing_tables = {row[0] for row in cursor.fetchall()}
                
                cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='index'")
                existing_indexes = {row[0] for row in cursor.fetchall()}
                
                # Check tables
                required_tables = set([name for name in self.schema_data['tables'].keys() 
                                     if not name.endswith('_columns') and name != 'sqlite_sequence'])
                
                missing_tables = required_tables - existing_tables
                extra_tables = existing_tables - required_tables
                
                if missing_tables:
                    results['missing_tables'] = list(missing_tables)
                    results['valid'] = False
                
                if extra_tables:
                    results['extra_tables'] = list(extra_tables)
                
                # Check indexes
                required_indexes = set(self.schema_data['indexes'].keys())
                missing_indexes = required_indexes - existing_indexes
                extra_indexes = existing_indexes - required_indexes
                
                # Filter out auto-generated indexes from missing list
                missing_indexes = {idx for idx in missing_indexes 
                                 if not idx.startswith('sqlite_autoindex')}
                
                if missing_indexes:
                    results['missing_indexes'] = list(missing_indexes)
                    results['valid'] = False
                
                if extra_indexes:
                    results['extra_indexes'] = list(extra_indexes)
                
                # Validate table structures
                for table_name in required_tables:
                    table_validation = self._validate_table_structure(conn, table_name)
                    results['table_validations'][table_name] = table_validation
                    
                    if not table_validation['valid']:
                        results['valid'] = False
            
            return results
            
        except Exception as e:
            self.logger.error(f"Failed to validate database schema: {e}")
            results['valid'] = False
            results['error'] = str(e)
            return results
    
    def _validate_table_structure(self, conn, table_name: str) -> Dict[str, any]:
        """Validate structure of a specific table."""
        validation = {
            'valid': True,
            'missing_columns': [],
            'extra_columns': [],
            'column_count_match': False
        }
        
        try:
            # Get expected columns from schema
            expected_columns = self.schema_data['tables'].get(f"{table_name}_columns", [])
            expected_column_names = {col['name'] for col in expected_columns}
            
            # Get actual columns from database
            cursor = conn.execute(f"PRAGMA table_info({table_name})")
            actual_columns = cursor.fetchall()
            actual_column_names = {row[1] for row in actual_columns}
            
            # Check for missing columns
            missing_columns = expected_column_names - actual_column_names
            if missing_columns:
                validation['missing_columns'] = list(missing_columns)
                validation['valid'] = False
            
            # Check for extra columns
            extra_columns = actual_column_names - expected_column_names
            if extra_columns:
                validation['extra_columns'] = list(extra_columns)
            
            # Check column count
            validation['column_count_match'] = len(expected_columns) == len(actual_columns)
            if not validation['column_count_match']:
                validation['valid'] = False
            
            return validation
            
        except Exception as e:
            self.logger.error(f"Failed to validate table {table_name}: {e}")
            validation['valid'] = False
            validation['error'] = str(e)
            return validation
    
    def get_create_table_sql(self, table_name: str) -> Optional[str]:
        """
        Get CREATE TABLE SQL for a specific table.
        
        Args:
            table_name: Name of the table
            
        Returns:
            CREATE TABLE SQL string or None if not found
        """
        if not self.schema_data:
            return None
        
        return self.schema_data['tables'].get(table_name)
    
    def get_create_index_sql(self, index_name: str) -> Optional[str]:
        """
        Get CREATE INDEX SQL for a specific index.
        
        Args:
            index_name: Name of the index
            
        Returns:
            CREATE INDEX SQL string or None if not found
        """
        if not self.schema_data:
            return None
        
        return self.schema_data['indexes'].get(index_name)
    
    def list_tables(self) -> List[str]:
        """Get list of all table names in the schema."""
        if not self.schema_data:
            return []
        
        return [name for name in self.schema_data['tables'].keys() 
                if not name.endswith('_columns') and name != 'sqlite_sequence']
    
    def list_indexes(self) -> List[str]:
        """Get list of all index names in the schema."""
        if not self.schema_data:
            return []
        
        return list(self.schema_data['indexes'].keys())


def create_default_schema_manager() -> SchemaManager:
    """
    Create a schema manager with default settings.
    
    Returns:
        SchemaManager instance
    """
    return SchemaManager()


def validate_schema_file(schema_path: str) -> bool:
    """
    Validate that a schema file is properly formatted.
    
    Args:
        schema_path: Path to schema JSON file
        
    Returns:
        True if schema is valid, False otherwise
    """
    try:
        if not Path(schema_path).exists():
            logging.error(f"Schema file not found: {schema_path}")
            return False
        
        with open(schema_path, 'r', encoding='utf-8') as f:
            schema_data = json.load(f)
        
        # Check required sections
        required_sections = ['metadata', 'tables', 'indexes', 'views', 'triggers']
        for section in required_sections:
            if section not in schema_data:
                logging.error(f"Missing required section: {section}")
                return False
        
        # Check metadata
        metadata = schema_data['metadata']
        required_metadata = ['extracted_at', 'database_path', 'sqlite_version']
        for key in required_metadata:
            if key not in metadata:
                logging.error(f"Missing required metadata: {key}")
                return False
        
        logging.info("Schema file validation passed")
        return True
        
    except Exception as e:
        logging.error(f"Schema file validation failed: {e}")
        return False