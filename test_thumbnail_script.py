#!/usr/bin/env python3
"""
test_thumbnail_script.py

A simple test script to verify create_missing_thumbnails.py works correctly.
This creates a test directory structure with some sample files.
"""

import os
import sys
import tempfile
import shutil
from pathlib import Path


def create_test_structure():
    """Create a test directory structure with sample files."""
    # Create a temporary directory
    test_dir = Path(tempfile.mkdtemp(prefix="thumbnail_test_"))
    print(f"Creating test directory: {test_dir}")
    
    # Create subdirectories
    subdir1 = test_dir / "UTW_00A_01A"
    subdir2 = test_dir / "UTW_00A_01B"
    subdir1.mkdir()
    subdir2.mkdir()
    
    # Create some dummy video files (empty files for testing)
    video_files = [
        subdir1 / "UTW_00A_01A_T01_underwater.mp4",
        subdir1 / "UTW_00A_01A_T03_underwater_120fps.mp4",
        subdir2 / "UTW_00A_01B_T02_surface.mkv",
        subdir2 / "UTW_00A_01B_T04_surface_60fps.mp4",
    ]
    
    for video_file in video_files:
        video_file.touch()
        print(f"Created: {video_file}")
    
    # Create some png files (existing thumbnails)
    existing_pngs = [
        subdir1 / "UTW_00A_01A_T01_underwater.png",
        subdir2 / "UTW_00A_01B_T02_surface.png",
    ]
    
    for png_file in existing_pngs:
        png_file.touch()
        print(f"Created existing thumbnail: {png_file}")
    
    return test_dir


def main():
    """Main test function."""
    print("Testing create_missing_thumbnails.py")
    print("=" * 50)
    
    # Create test structure
    test_dir = create_test_structure()
    
    try:
        # Run the thumbnail script
        print(f"\nRunning create_missing_thumbnails.py on {test_dir}")
        print("-" * 50)
        
        # Import and run the main function
        sys.path.insert(0, str(Path(__file__).parent))
        from create_missing_thumbnails import main as thumbnail_main
        
        # Run with our test directory
        thumbnail_main(str(test_dir))
        
        print("\n" + "=" * 50)
        print("Test completed! Checking results...")
        
        # Check what files were created
        all_files = list(test_dir.rglob("*"))
        print(f"\nAll files in test directory:")
        for file in sorted(all_files):
            if file.is_file():
                print(f"  {file.relative_to(test_dir)}")
        
        # Look for the report file
        report_files = list(test_dir.glob("thumbnail_generation_report_*.txt"))
        if report_files:
            print(f"\nReport file created: {report_files[0].name}")
            print("\nReport contents:")
            print("-" * 30)
            with open(report_files[0], 'r') as f:
                print(f.read())
        else:
            print("\nNo report file found!")
            
    except Exception as e:
        print(f"Error during test: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Clean up
        print(f"\nCleaning up test directory: {test_dir}")
        shutil.rmtree(test_dir)


if __name__ == "__main__":
    main()