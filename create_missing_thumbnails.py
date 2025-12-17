#!/usr/bin/env python3
"""
create_missing_thumbnails.py

A script to scan through a target folder and its subfolders,
checking for mp4 or mkv files and generating missing png thumbnails.

Usage:
    python create_missing_thumbnails.py [target_folder]

If no target folder is provided, it will prompt for one.
"""

import os
import sys
import subprocess
import datetime
import argparse
from pathlib import Path
from typing import List, Tuple, Set


def get_video_files(directory: Path) -> List[Path]:
    """Get all mp4 and mkv files in the directory and subdirectories."""
    video_files = []
    for ext in ['*.mp4', '*.mkv']:
        video_files.extend(directory.rglob(ext))
    return sorted(video_files)


def get_png_files(directory: Path) -> Set[Path]:
    """Get all png files in the directory and subdirectories."""
    png_files = set()
    for png_file in directory.rglob('*.png'):
        png_files.add(png_file)
    return png_files


def generate_thumbnail(video_path: Path, output_path: Path, duration: int = 5) -> bool:
    """
    Generate a thumbnail from a video file using ffmpeg.
    
    Args:
        video_path: Path to the video file
        output_path: Path where the thumbnail should be saved
        duration: Time in seconds from the start to capture the thumbnail
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Use ffmpeg to extract a frame from the video
        # -ss specifies the time to seek to (in seconds)
        # -vframes 1 captures only one frame
        # -vf "scale=320:-1" scales the image to width 320 while maintaining aspect ratio
        cmd = [
            'ffmpeg',
            '-y',  # Overwrite output file if it exists
            '-i', str(video_path),
            '-ss', str(duration),
            '-vframes', '1',
            '-vf', 'scale=320:-1',
            str(output_path)
        ]
        
        # Run the command
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )
        
        # Check if the output file was created and has content
        if output_path.exists() and output_path.stat().st_size > 0:
            return True
        else:
            return False
            
    except subprocess.CalledProcessError as e:
        print(f"Error generating thumbnail for {video_path}: {e}")
        print(f"FFmpeg stderr: {e.stderr}")
        return False
    except Exception as e:
        print(f"Unexpected error generating thumbnail for {video_path}: {e}")
        return False


def main(target_folder: str = None):
    """Main function to scan and generate missing thumbnails."""
    
    # Get target folder
    if not target_folder:
        if len(sys.argv) > 1:
            target_folder = sys.argv[1]
        else:
            target_folder = input("Enter the target folder path: ").strip()
    
    target_path = Path(target_folder)
    
    if not target_path.exists():
        print(f"Error: Target folder '{target_folder}' does not exist.")
        sys.exit(1)
    
    if not target_path.is_dir():
        print(f"Error: '{target_folder}' is not a directory.")
        sys.exit(1)
    
    print(f"Scanning folder: {target_path}")
    print("=" * 60)
    
    # Get all video and png files
    video_files = get_video_files(target_path)
    png_files = get_png_files(target_path)
    
    print(f"Found {len(video_files)} video files")
    print(f"Found {len(png_files)} png files")
    print()
    
    # Track results
    missing_thumbnails = []
    generated_thumbnails = []
    failed_thumbnails = []
    
    # Check each video file for a matching png
    for video_file in video_files:
        # Get the base name without extension
        base_name = video_file.stem
        expected_png_path = video_file.parent / f"{base_name}.png"
        
        # Check if the png exists
        if expected_png_path not in png_files:
            missing_thumbnails.append((video_file, expected_png_path))
    
    print(f"Found {len(missing_thumbnails)} missing thumbnails")
    print()
    
    # Generate thumbnails for missing ones
    if missing_thumbnails:
        print("Generating missing thumbnails...")
        for video_file, png_path in missing_thumbnails:
            print(f"  Generating: {png_path.name}")
            success = generate_thumbnail(video_file, png_path)
            
            if success:
                generated_thumbnails.append((video_file, png_path))
                print(f"    ✓ Success")
            else:
                failed_thumbnails.append((video_file, png_path))
                print(f"    ✗ Failed")
        print()
    else:
        print("No missing thumbnails found!")
        print()
    
    # Generate report
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = target_path / f"thumbnail_generation_report_{timestamp}.txt"
    
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("Thumbnail Generation Report\n")
        f.write("=" * 60 + "\n")
        f.write(f"Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Target Folder: {target_path}\n")
        f.write("\n")
        
        f.write(f"Summary:\n")
        f.write(f"  Video files found: {len(video_files)}\n")
        f.write(f"  PNG files found: {len(png_files)}\n")
        f.write(f"  Missing thumbnails: {len(missing_thumbnails)}\n")
        f.write(f"  Successfully generated: {len(generated_thumbnails)}\n")
        f.write(f"  Failed to generate: {len(failed_thumbnails)}\n")
        f.write("\n")
        
        if generated_thumbnails:
            f.write("Successfully generated thumbnails:\n")
            for video_file, png_path in generated_thumbnails:
                f.write(f"  {video_file.relative_to(target_path)} -> {png_path.relative_to(target_path)}\n")
            f.write("\n")
        
        if failed_thumbnails:
            f.write("Failed to generate thumbnails:\n")
            for video_file, png_path in failed_thumbnails:
                f.write(f"  {video_file.relative_to(target_path)} -> {png_path.relative_to(target_path)}\n")
            f.write("\n")
        
        if missing_thumbnails and not generated_thumbnails:
            f.write("No thumbnails were generated (no missing pairs found).\n")
            f.write("\n")
    
    print(f"Report saved to: {report_path}")
    print()
    print("Summary:")
    print(f"  Video files found: {len(video_files)}")
    print(f"  PNG files found: {len(png_files)}")
    print(f"  Missing thumbnails: {len(missing_thumbnails)}")
    print(f"  Successfully generated: {len(generated_thumbnails)}")
    print(f"  Failed to generate: {len(failed_thumbnails)}")


if __name__ == "__main__":
    main()