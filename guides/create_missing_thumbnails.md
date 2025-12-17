# Create Missing Thumbnails Script

A Python script that scans through a target folder and its subfolders, checking for mp4 or mkv files and generating missing png thumbnails.

## Features

- Recursively scans directories for video files (mp4, mkv)
- Identifies missing png thumbnails for video files
- Generates thumbnails using ffmpeg with proper scaling
- Creates a timestamped report of all operations
- Handles errors gracefully and logs failures

## Requirements

- Python 3.6+
- ffmpeg installed and available in PATH

### Installing ffmpeg

**Windows:**
- Download from https://ffmpeg.org/download.html
- Add the bin directory to your PATH environment variable

**macOS:**
```bash
brew install ffmpeg
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt update
sudo apt install ffmpeg
```

## Usage

### Command Line Arguments

```bash
python create_missing_thumbnails.py [target_folder]
```

**Examples:**

```bash
# Scan a specific folder
python create_missing_thumbnails.py "Z:\Media_Productions\Davinci\Sirena_25\migrate_to_AIMMS\video_storyboard"

# Interactive mode (will prompt for folder)
python create_missing_thumbnails.py
```

## How It Works

1. **Scanning**: The script recursively scans the target folder for mp4 and mkv files
2. **Matching**: For each video file, it checks if a corresponding png file exists with the same base name
3. **Generation**: If a png is missing, it extracts a frame from 5 seconds into the video using ffmpeg
4. **Scaling**: Thumbnails are scaled to 320px width while maintaining aspect ratio
5. **Reporting**: A timestamped report is saved to the target folder

## Example

Given this folder structure:
```
video_storyboard/
├── UTW_00A_01A/
│   ├── UTW_00A_01A_T01_underwater.mp4
│   ├── UTW_00A_01A_T01_underwater.png  # ✓ Exists
│   ├── UTW_00A_01A_T03_underwater_120fps.mp4
│   └── UTW_00A_01A_T03_underwater_120fps.png  # ✗ Missing - will be created
```

The script will:
- Find `UTW_00A_01A_T03_underwater_120fps.mp4`
- Detect that the matching png is missing
- Generate a thumbnail and save it as `UTW_00A_01A_T03_underwater_120fps.png`
- Create a report file like `thumbnail_generation_report_20251217_182513.txt`

## Output

The script provides:
- Console output showing progress and results
- A timestamped text report saved in the target folder containing:
  - Summary statistics
  - List of successfully generated thumbnails
  - List of failed attempts (if any)

## Notes

- Thumbnails are captured from 5 seconds into each video
- Generated thumbnails are scaled to 320px width (height adjusted to maintain aspect ratio)
- The script will overwrite existing png files if they exist (use with caution)
- All file paths in the report are relative to the target folder for readability