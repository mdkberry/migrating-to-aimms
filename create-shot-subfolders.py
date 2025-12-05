#!/usr/bin/env python3
"""
Create Shot Subfolders Script

This script reads shot names from a CSV file and creates subfolders for each shot
under a specified target directory.

Usage:
    python create-shot-subfolders.py csv-file-location target-folder

Example:
    python create-shot-subfolders.py shots.csv C:\\Users\\admin\\Documents\\shots
"""

import argparse
import csv
import os
import sys
from pathlib import Path


def create_shot_folders(csv_file_path, target_folder):
    """
    Read shot names from CSV and create corresponding folders.
    
    Args:
        csv_file_path (str): Path to the CSV file containing shot names
        target_folder (str): Path to the target folder where subfolders will be created
    
    Returns:
        tuple: (success_count, error_count, errors_list)
    """
    success_count = 0
    error_count = 0
    errors = []
    
    # Convert to Path objects for better handling
    csv_path = Path(csv_file_path)
    target_path = Path(target_folder)
    
    # Validate CSV file exists
    if not csv_path.exists():
        print(f"Error: CSV file '{csv_file_path}' does not exist.")
        return 0, 1, [f"CSV file not found: {csv_file_path}"]
    
    # Create target folder if it doesn't exist
    try:
        target_path.mkdir(parents=True, exist_ok=True)
        print(f"Target folder: {target_path}")
    except Exception as e:
        print(f"Error: Cannot create target folder '{target_folder}': {e}")
        return 0, 1, [f"Target folder creation failed: {e}"]
    
    # Read CSV and create folders
    try:
        with open(csv_path, mode='r', newline='', encoding='utf-8') as csvfile:
            # Try to detect the delimiter
            sample = csvfile.read(1024)
            csvfile.seek(0)
            
            # Common delimiters to try
            sniffer = csv.Sniffer()
            try:
                delimiter = sniffer.sniff(sample).delimiter
            except:
                delimiter = ','  # Default to comma if detection fails
            
            reader = csv.DictReader(csvfile, delimiter=delimiter)
            
            # Check if 'shot_name' column exists
            if 'shot_name' not in reader.fieldnames:
                print(f"Error: 'shot_name' column not found in CSV. Available columns: {reader.fieldnames}")
                return 0, 1, [f"'shot_name' column not found. Available: {reader.fieldnames}"]
            
            print(f"CSV columns found: {reader.fieldnames}")
            print(f"Processing shots...")
            
            for row_num, row in enumerate(reader, start=2):  # Start at 2 because header is row 1
                shot_name = row.get('shot_name', '').strip()
                
                if not shot_name:
                    print(f"Warning: Empty shot_name in row {row_num}")
                    continue
                
                # Create folder path
                folder_path = target_path / shot_name
                
                try:
                    # Create the folder
                    folder_path.mkdir(exist_ok=True)
                    print(f"✓ Created folder: {shot_name}")
                    success_count += 1
                except Exception as e:
                    error_msg = f"Failed to create folder '{shot_name}': {e}"
                    print(f"✗ {error_msg}")
                    errors.append(error_msg)
                    error_count += 1
    
    except Exception as e:
        error_msg = f"Error reading CSV file: {e}"
        print(f"✗ {error_msg}")
        errors.append(error_msg)
        error_count += 1
    
    return success_count, error_count, errors


def main():
    """Main function to parse arguments and execute the script."""
    parser = argparse.ArgumentParser(
        description="Create subfolders for each shot name from a CSV file.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python create-shot-subfolders.py shots.csv C:\\Users\\admin\\Documents\\shots
  python create-shot-subfolders.py data/shot_list.csv ./output/shots
        """
    )
    
    parser.add_argument(
        'csv_file',
        help='Path to the CSV file containing shot names (must have "shot_name" column)'
    )
    
    parser.add_argument(
        'target_folder',
        help='Path to the target folder where subfolders will be created'
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("Create Shot Subfolders")
    print("=" * 60)
    print(f"CSV file: {args.csv_file}")
    print(f"Target folder: {args.target_folder}")
    print("-" * 60)
    
    # Create the folders
    success_count, error_count, errors = create_shot_folders(
        args.csv_file, 
        args.target_folder
    )
    
    # Print summary
    print("-" * 60)
    print("Summary:")
    print(f"  Successful: {success_count}")
    print(f"  Failed: {error_count}")
    
    if errors:
        print("\nErrors:")
        for error in errors:
            print(f"  - {error}")
    
    # Exit with appropriate code
    if error_count > 0:
        print(f"\nCompleted with {error_count} error(s).")
        sys.exit(1)
    else:
        print(f"\nCompleted successfully! Created {success_count} folders.")
        sys.exit(0)


if __name__ == "__main__":
    main()