#!/usr/bin/env python3
"""
Test script to verify the database migration fix for missing tables.
"""

import sqlite3
import os
import tempfile
import shutil
from pathlib import Path

# Import the DatabaseMigrator
import sys
sys.path.append('.')
from database import DatabaseMigrator

def create_test_source_db(path: str, missing_tables: list = None):
    """Create a test source database with optional missing tables."""
    print(f"Creating test source database at: {path}")
    
    # Create the directory if it doesn't exist
    os.makedirs(os.path.dirname(path), exist_ok=True)
    
    with sqlite3.connect(path) as conn:
        # Always create shots table
        conn.execute('''
            CREATE TABLE shots (
                order_number INTEGER,
                shot_name TEXT PRIMARY KEY,
                section TEXT,
                description TEXT,
                created_date TEXT
            )
        ''')
        
        # Insert test data
        conn.execute('''
            INSERT INTO shots (order_number, shot_name, section, description, created_date)
            VALUES (1, 'test_shot_1', 'test_section', 'test_description', '2025-12-04 10:00:00')
        ''')
        
        # Always create takes table
        conn.execute('''
            CREATE TABLE takes (
                take_id TEXT PRIMARY KEY,
                shot_name TEXT,
                take_type TEXT,
                file_path TEXT,
                starred INTEGER DEFAULT 0,
                created_date TEXT,
                FOREIGN KEY (shot_name) REFERENCES shots(shot_name)
            )
        ''')
        
        # Insert test data
        conn.execute('''
            INSERT INTO takes (take_id, shot_name, take_type, file_path, starred, created_date)
            VALUES ('test-take-1', 'test_shot_1', 'video_workflow', 'media/test_shot_1/video_01.png', 0, '2025-12-04 10:00:00')
        ''')
        
        # Create missing tables if specified
        if missing_tables is None:
            missing_tables = []
        
        if 'assets' not in missing_tables:
            conn.execute('''
                CREATE TABLE assets (
                    id_key TEXT PRIMARY KEY,
                    asset_name TEXT,
                    asset_type TEXT,
                    file_path TEXT,
                    starred INTEGER DEFAULT 0,
                    created_date TEXT
                )
            ''')
        
        if 'meta' not in missing_tables:
            conn.execute('''
                CREATE TABLE meta (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            ''')
            # Insert some meta data
            conn.executemany('INSERT INTO meta (key, value) VALUES (?, ?)', [
                ('schema_version', '0.9'),
                ('app_version', '0.9'),
                ('created_at', '2025-12-04 09:00:00')
            ])
        
        conn.commit()
        print(f"Created test database with missing tables: {missing_tables}")

def test_missing_tables():
    """Test the migration with missing tables."""
    print("=" * 60)
    print("TESTING DATABASE MIGRATION WITH MISSING TABLES")
    print("=" * 60)
    
    # Create temporary directories
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"Using temporary directory: {temp_dir}")
        
        source_db = os.path.join(temp_dir, 'source', 'shots.db')
        target_db = os.path.join(temp_dir, 'target', 'shots.db')
        
        # Test case 1: Missing both assets and meta tables
        print("\n--- Test Case 1: Missing assets and meta tables ---")
        create_test_source_db(source_db, missing_tables=['assets', 'meta'])
        
        # Create target directory
        os.makedirs(os.path.dirname(target_db), exist_ok=True)
        
        # Run migration
        migrator = DatabaseMigrator(source_db, target_db)
        result = migrator.migrate()
        
        print(f"Migration result: {'SUCCESS' if result.success else 'FAILED'}")
        print(f"Errors: {result.errors}")
        print(f"Warnings: {result.warnings}")
        print(f"Shot mapping: {result.shot_mapping}")
        
        # Verify the target database
        if result.success and os.path.exists(target_db):
            print("\nVerifying target database...")
            with sqlite3.connect(target_db) as conn:
                # Check tables
                cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = [row[0] for row in cursor.fetchall()]
                print(f"Tables in target DB: {tables}")
                
                # Check meta table contents
                cursor = conn.execute("SELECT key, value FROM meta")
                meta_data = cursor.fetchall()
                print(f"Meta table contents: {meta_data}")
                
                # Check assets table
                cursor = conn.execute("SELECT COUNT(*) FROM assets")
                asset_count = cursor.fetchone()[0]
                print(f"Assets table count: {asset_count}")
        
        # Test case 2: Missing only assets table
        print("\n--- Test Case 2: Missing only assets table ---")
        source_db2 = os.path.join(temp_dir, 'source2', 'shots.db')
        target_db2 = os.path.join(temp_dir, 'target2', 'shots.db')
        
        create_test_source_db(source_db2, missing_tables=['assets'])
        os.makedirs(os.path.dirname(target_db2), exist_ok=True)
        
        migrator2 = DatabaseMigrator(source_db2, target_db2)
        result2 = migrator2.migrate()
        
        print(f"Migration result: {'SUCCESS' if result2.success else 'FAILED'}")
        print(f"Errors: {result2.errors}")
        print(f"Warnings: {result2.warnings}")
        
        # Test case 3: Missing only meta table
        print("\n--- Test Case 3: Missing only meta table ---")
        source_db3 = os.path.join(temp_dir, 'source3', 'shots.db')
        target_db3 = os.path.join(temp_dir, 'target3', 'shots.db')
        
        create_test_source_db(source_db3, missing_tables=['meta'])
        os.makedirs(os.path.dirname(target_db3), exist_ok=True)
        
        migrator3 = DatabaseMigrator(source_db3, target_db3)
        result3 = migrator3.migrate()
        
        print(f"Migration result: {'SUCCESS' if result3.success else 'FAILED'}")
        print(f"Errors: {result3.errors}")
        print(f"Warnings: {result3.warnings}")
        
        # Test case 4: Missing critical shots table (should fail)
        print("\n--- Test Case 4: Missing critical shots table (should fail) ---")
        source_db4 = os.path.join(temp_dir, 'source4', 'shots.db')
        target_db4 = os.path.join(temp_dir, 'target4', 'shots.db')
        
        # Create database with only takes table (missing shots)
        os.makedirs(os.path.dirname(source_db4), exist_ok=True)
        with sqlite3.connect(source_db4) as conn:
            conn.execute('''
                CREATE TABLE takes (
                    take_id TEXT PRIMARY KEY,
                    shot_name TEXT,
                    take_type TEXT,
                    file_path TEXT,
                    starred INTEGER DEFAULT 0,
                    created_date TEXT
                )
            ''')
            conn.commit()
        
        os.makedirs(os.path.dirname(target_db4), exist_ok=True)
        
        migrator4 = DatabaseMigrator(source_db4, target_db4)
        result4 = migrator4.migrate()
        
        print(f"Migration result: {'SUCCESS' if result4.success else 'FAILED'}")
        print(f"Errors: {result4.errors}")
        print(f"Warnings: {result4.warnings}")

def test_schema_comparison():
    """Test that the created schema matches the current project schema."""
    print("\n" + "=" * 60)
    print("TESTING SCHEMA COMPARISON WITH CURRENT PROJECT")
    print("=" * 60)
    
    # Check if current_project/data/shots.db exists
    current_db = 'current_project/data/shots.db'
    if not os.path.exists(current_db):
        print(f"Current project database not found at: {current_db}")
        return
    
    print(f"Comparing with current project schema at: {current_db}")
    
    with sqlite3.connect(current_db) as conn:
        # Get schema from current project
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        current_tables = [row[0] for row in cursor.fetchall()]
        print(f"Tables in current project: {current_tables}")
        
        # Get column info for each table
        for table in current_tables:
            cursor = conn.execute(f"PRAGMA table_info({table})")
            columns = cursor.fetchall()
            print(f"\nTable '{table}' columns:")
            for col in columns:
                print(f"  - {col[1]} ({col[2]}) {'PRIMARY KEY' if col[5] else ''}")

if __name__ == '__main__':
    try:
        test_missing_tables()
        test_schema_comparison()
        print("\n" + "=" * 60)
        print("ALL TESTS COMPLETED")
        print("=" * 60)
    except Exception as e:
        print(f"Test failed with error: {e}")
        import traceback
        traceback.print_exc()