#!/usr/bin/env python3
"""
AIMMS Migration Tool - Main Entry Point

Command-line interface for the AIMMS migration tool.
Usage:
  python main.py --mode option1 --source old_project --project-name project_The_Highwayman
  python main.py --mode option1 --source old_project --target transfer_folder
  python main.py --mode option2 --csv data.csv --project-name project_MyProject
  python main.py --mode option3 --restore backup.aimms --project-name project_Recovered
  python main.py --mode option4 --source media_folder --project-name project_MediaImport
"""

import argparse
import sys
import os
import logging
from migration_engine import MigrationEngine
from config import MigrationConfig
from logger import setup_logging

def main():
    """Main entry point for the migration tool."""
    parser = argparse.ArgumentParser(
        description='AIMMS Project Migration Tool',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --mode option1 --source old_project --project-name project_The_Highwayman
  python main.py --mode option1 --source old_project --target transfer_folder
  python main.py --mode option2 --csv data.csv --project-name project_MyProject
  python main.py --mode option3 --restore backup.aimms --project-name project_Recovered
  python main.py --mode option4 --source media_folder --project-name project_MediaImport
        """
    )
    
    parser.add_argument(
        '--mode', 
        choices=['option1', 'option2', 'option3', 'option4'],
        required=True,
        help='Migration mode to use'
    )
    
    parser.add_argument(
        '--source',
        help='Source project directory'
    )
    
    parser.add_argument(
        '--target',
        help='Target project directory (alternative to --project-name)'
    )
    
    parser.add_argument(
        '--csv',
        help='CSV file for option2'
    )
    
    parser.add_argument(
        '--restore',
        help='Restore file for option3'
    )
    
    parser.add_argument(
        '--project-name',
        help='Project name for target folder (e.g., project_The_Highwayman)'
    )
    
    parser.add_argument(
        '--backup',
        action='store_true',
        help='Create backup before migration'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    # Determine target path based on project name or use provided target
    if args.project_name:
        target_path = args.project_name
        print(f"Using project name as target: {target_path}")
    elif args.target:
        target_path = args.target
        print(f"Using provided target path: {target_path}")
    else:
        # Default to transfer_folder if neither is provided
        target_path = "transfer_folder"
        print(f"No target specified, using default: {target_path}")
    
    # Setup logging with automatic log file
    log_file = None
    if target_path:
        # Create log file in target directory
        log_file = os.path.join(target_path, 'migration.log')
    
    setup_logging(verbose=args.verbose, log_file=log_file)
    logger = logging.getLogger(__name__)
    
    # Log file location info
    if log_file:
        logger.info(f"Detailed logs will be saved to: {log_file}")
    
    try:
        # Load configuration
        config = MigrationConfig(
            mode=args.mode,
            source_path=args.source,
            target_path=target_path,
            csv_path=args.csv,
            restore_path=args.restore,
            create_backup=args.backup
        )
        
        # Initialize migration engine
        engine = MigrationEngine(config)
        
        # Execute migration
        success = engine.run_migration()
        
        if success:
            logger.info("Migration completed successfully!")
            sys.exit(0)
        else:
            logger.error("Migration failed!")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"Migration failed with error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()