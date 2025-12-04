#!/usr/bin/env python3
"""
AIMMS Migration Tool - Main Entry Point

Command-line interface for the AIMMS migration tool.
Usage:
  python main.py --mode option1 --source old_project --target transfer_folder
  python main.py --mode option2 --csv data.csv --target new_project
  python main.py --mode option3 --restore backup.aimms --target recovered_project
  python main.py --mode option4 --source media_folder --target new_project
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
  python main.py --mode option1 --source old_project --target transfer_folder
  python main.py --mode option2 --csv data.csv --target new_project
  python main.py --mode option3 --restore backup.aimms --target recovered_project
  python main.py --mode option4 --source media_folder --target new_project
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
        required=True,
        help='Target project directory'
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
    
    # Setup logging with automatic log file
    log_file = None
    if args.target:
        # Create log file in target directory
        log_file = os.path.join(args.target, 'migration.log')
    
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
            target_path=args.target,
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