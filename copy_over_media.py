#!/usr/bin/env python3
"""
Copy Over Images/Videos Script

This script copies images or videos from a source directory to target folders
based on shot names from a CSV file.

Usage:
    python copy_over_media.py {location to save the files to} {file type} {csv location with shot_name column} {folder with subfolders to scan through}

Arguments:
    location_to_save: Target directory where shot_name folders will be created
    file_type: 'image' for .png files, 'video' for .mp4/.mkv files
    csv_location: Path to CSV file containing shot_name column
    source_folder: Source directory to scan for files
"""

import os
import sys
import csv
import shutil
import argparse
from datetime import datetime
from pathlib import Path
from typing import List, Tuple, Dict, Set


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Copy images or videos to shot_name folders based on CSV",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python copy_over_images.py "Z:\\Media_Productions\\Davinci\\Sirena_25\\migrate_to_AIMMS\\image_storyboard" image "Z:\\Media_Productions\\Davinci\\Sirena_25\\migrate_to_AIMMS\\project_Sirena_25.csv" "Z:\\Media_Productions\\Davinci\\Sirena_25\\Raw_footage"
    
    python copy_over_images.py "Z:\\Media_Productions\\Davinci\\Sirena_25\\migrate_to_AIMMS\\video_storyboard" video "Z:\\Media_Productions\\Davinci\\Sirena_25\\migrate_to_AIMMS\\project_Sirena_25.csv" "Z:\\Media_Productions\\Davinci\\Sirena_25\\Raw_footage"
        """
    )
    
    parser.add_argument("location_to_save", help="Target directory where shot_name folders will be created")
    parser.add_argument("file_type", choices=["image", "video"], help="Type of files to copy: 'image' for .png, 'video' for .mp4/.mkv")
    parser.add_argument("csv_location", help="Path to CSV file containing shot_name column")
    parser.add_argument("source_folder", help="Source directory to scan for files")
    
    return parser.parse_args()


def read_shot_names_from_csv(csv_path: str) -> List[str]:
    """Read shot names from CSV file."""
    shot_names = []
    
    try:
        # Try multiple common delimiters
        delimiters_to_try = [',', ';', '\t', '|']
        
        with open(csv_path, 'r', newline='', encoding='utf-8') as csvfile:
            # Try to detect delimiter first
            sample = csvfile.read(1024)
            csvfile.seek(0)
            
            delimiter = None
            try:
                sniffer = csv.Sniffer()
                delimiter = sniffer.sniff(sample).delimiter
            except:
                # If sniffing fails, try common delimiters
                pass
            
            # If delimiter detection failed, try common ones
            if delimiter is None:
                for test_delimiter in delimiters_to_try:
                    try:
                        csvfile.seek(0)
                        reader = csv.DictReader(csvfile, delimiter=test_delimiter)
                        if 'shot_name' in reader.fieldnames:
                            delimiter = test_delimiter
                            break
                    except:
                        continue
            
            if delimiter is None:
                print(f"Error: Could not determine CSV delimiter. Tried: {delimiters_to_try}")
                sys.exit(1)
            
            csvfile.seek(0)
            reader = csv.DictReader(csvfile, delimiter=delimiter)
            
            # Check if shot_name column exists
            if 'shot_name' not in reader.fieldnames:
                print(f"Error: 'shot_name' column not found in CSV. Available columns: {reader.fieldnames}")
                sys.exit(1)
            
            for row in reader:
                shot_name = row['shot_name'].strip()
                if shot_name:  # Skip empty shot names
                    shot_names.append(shot_name)
    
    except FileNotFoundError:
        print(f"Error: CSV file not found: {csv_path}")
        sys.exit(1)
    except Exception as e:
        print(f"Error reading CSV file: {e}")
        sys.exit(1)
    
    print(f"Found {len(shot_names)} shot names in CSV")
    return shot_names


def find_files_for_shot(source_folder: Path, shot_name: str, file_type: str) -> List[Tuple[Path, Path]]:
    """Find all files matching the shot name in the source folder."""
    found_files = []
    
    if file_type == "image":
        # Look for .png files
        pattern = f"**/*{shot_name}*.png"
        for file_path in source_folder.glob(pattern):
            if file_path.is_file():
                found_files.append((file_path, file_path.name))
    
    elif file_type == "video":
        # Look for .mp4 and .mkv files
        video_patterns = [f"**/*{shot_name}*.mp4", f"**/*{shot_name}*.mkv"]
        
        for pattern in video_patterns:
            for video_path in source_folder.glob(pattern):
                if video_path.is_file():
                    # Look for matching .png file in the same directory
                    png_path = video_path.with_suffix('.png')
                    
                    if png_path.exists() and png_path.is_file():
                        # Found matching video and image pair
                        found_files.append((video_path, video_path.name))
                        found_files.append((png_path, png_path.name))
                    else:
                        print(f"Warning: Found video {video_path} but no matching PNG file")
                        found_files.append((video_path, video_path.name))
    
    return found_files


def copy_file_with_rename(source_path: Path, target_dir: Path, original_name: str, copy_count: Dict[str, int]) -> Tuple[Path, str]:
    """Copy file to target directory, renaming if necessary to avoid overwrites."""
    target_path = target_dir / original_name
    
    # Check if file already exists
    if target_path.exists():
        # Increment counter for this filename
        if original_name not in copy_count:
            copy_count[original_name] = 1
        
        copy_count[original_name] += 1
        name_parts = original_name.rsplit('.', 1)
        new_name = f"{name_parts[0]}_copy{copy_count[original_name]}.{name_parts[1]}"
        target_path = target_dir / new_name
        
        return source_path, new_name
    
    return source_path, original_name


def create_report(report_path: Path, copy_log: List[Dict], errors: List[str]):
    """Create a detailed report of the copying process."""
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("COPY OVER FILES REPORT\n")
        f.write("=" * 80 + "\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"File Type: {copy_log[0]['file_type'] if copy_log else 'N/A'}\n")
        f.write("\n")
        
        if errors:
            f.write("ERRORS:\n")
            f.write("-" * 40 + "\n")
            for error in errors:
                f.write(f"• {error}\n")
            f.write("\n")
        
        f.write("COPY LOG:\n")
        f.write("-" * 40 + "\n")
        
        for entry in copy_log:
            f.write(f"\nShot Name: {entry['shot_name']}\n")
            f.write(f"Files Found: {len(entry['files'])}\n")
            
            for file_info in entry['files']:
                f.write(f"  • {file_info['original_path']} -> {file_info['target_path']}\n")
                if file_info['renamed']:
                    f.write(f"    (Renamed from: {file_info['original_name']})\n")
        
        f.write("\n" + "=" * 80 + "\n")
        f.write("SUMMARY:\n")
        f.write(f"Total shots processed: {len(copy_log)}\n")
        total_files = sum(len(entry['files']) for entry in copy_log)
        f.write(f"Total files copied: {total_files}\n")
        f.write(f"Errors encountered: {len(errors)}\n")
        f.write("=" * 80 + "\n")


def main():
    """Main execution function."""
    args = parse_arguments()
    
    # Convert paths to Path objects
    location_to_save = Path(args.location_to_save)
    csv_location = Path(args.csv_location)
    source_folder = Path(args.source_folder)
    
    # Validate inputs
    if not source_folder.exists():
        print(f"Error: Source folder does not exist: {source_folder}")
        sys.exit(1)
    
    if not csv_location.exists():
        print(f"Error: CSV file does not exist: {csv_location}")
        sys.exit(1)
    
    # Create target directory if it doesn't exist
    location_to_save.mkdir(parents=True, exist_ok=True)
    
    # Read shot names from CSV
    shot_names = read_shot_names_from_csv(str(csv_location))
    
    # Prepare report
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_filename = f"copy_report_{args.file_type}_{timestamp}.txt"
    report_path = location_to_save / report_filename
    
    # Initialize logging
    copy_log = []
    errors = []
    total_copied = 0
    total_renamed = 0
    
    print(f"\nStarting copy process...")
    print(f"Target location: {location_to_save}")
    print(f"File type: {args.file_type}")
    print(f"Source folder: {source_folder}")
    print(f"Report will be saved to: {report_path}")
    print("-" * 80)
    
    # Process each shot name
    for i, shot_name in enumerate(shot_names, 1):
        print(f"\n[{i}/{len(shot_names)}] Processing shot: {shot_name}")
        
        # Create target directory for this shot
        shot_target_dir = location_to_save / shot_name
        shot_target_dir.mkdir(exist_ok=True)
        
        # Find files for this shot
        found_files = find_files_for_shot(source_folder, shot_name, args.file_type)
        
        if not found_files:
            print(f"  No files found for {shot_name}")
            continue
        
        print(f"  Found {len(found_files)} file(s)")
        
        # Copy files with rename handling
        shot_files = []
        copy_count = {}
        
        for source_path, original_name in found_files:
            try:
                # Copy file with potential rename
                source_file, target_name = copy_file_with_rename(
                    source_path, shot_target_dir, original_name, copy_count
                )
                
                # Perform actual copy
                target_path = shot_target_dir / target_name
                shutil.copy2(source_path, target_path)
                
                # Log the copy
                is_renamed = target_name != original_name
                if is_renamed:
                    total_renamed += 1
                
                shot_files.append({
                    'original_path': str(source_path),
                    'original_name': original_name,
                    'target_path': str(target_path),
                    'renamed': is_renamed
                })
                
                total_copied += 1
                
                if is_renamed:
                    print(f"    ✓ Copied (renamed): {original_name} -> {target_name}")
                else:
                    print(f"    ✓ Copied: {target_name}")
                
            except Exception as e:
                error_msg = f"Failed to copy {source_path}: {str(e)}"
                print(f"    ✗ {error_msg}")
                errors.append(error_msg)
        
        # Add to copy log
        if shot_files:
            copy_log.append({
                'shot_name': shot_name,
                'file_type': args.file_type,
                'files': shot_files
            })
    
    # Create report
    create_report(report_path, copy_log, errors)
    
    # Print summary
    print("\n" + "=" * 80)
    print("COPY PROCESS COMPLETE")
    print("=" * 80)
    print(f"Shots processed: {len(shot_names)}")
    print(f"Shots with files: {len(copy_log)}")
    print(f"Total files copied: {total_copied}")
    print(f"Files renamed: {total_renamed}")
    print(f"Errors: {len(errors)}")
    print(f"Report saved to: {report_path}")
    print("=" * 80)


if __name__ == "__main__":
    main()