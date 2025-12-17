# Copy Over Media Guide

This guide explains how to use the `copy_over_media.py` script to organize and copy media files based on shot names from a CSV file.

## Overview

The `copy_over_media.py` script automates the process of:
- Reading shot names from a CSV file
- Scanning a source directory for matching media files
- Copying files to organized shot-specific folders
- Handling naming conflicts and creating detailed reports

## Prerequisites

- Python 3.12 or higher
- Access to the source and target directories
- A CSV file containing shot names in a column named `shot_name`

## Usage

### Basic Command Structure

```bash
python copy_over_media.py {target_location} {file_type} {csv_file} {source_folder}
```

### Parameters

1. **target_location** (required)
   - The directory where shot-specific folders will be created
   - Example: `Z:\Media_Productions\Davinci\Sirena_25\migrate_to_AIMMS\image_storyboard`

2. **file_type** (required)
   - Type of files to process: `image` or `video`
   - `image`: Copies `.png` files
   - `video`: Copies `.mp4` and `.mkv` files along with their matching `.png` files

3. **csv_file** (required)
   - Path to CSV file containing shot names
   - Must have a column named `shot_name`
   - Supports common delimiters: comma (,), semicolon (;), tab (\t), pipe (|)

4. **source_folder** (required)
   - Directory to scan for media files
   - Script will search recursively through all subdirectories

## Examples

### Copying Images

```bash
python copy_over_media.py "Z:\Media_Productions\Davinci\Sirena_25\migrate_to_AIMMS\image_storyboard" image "Z:\Media_Productions\Davinci\Sirena_25\migrate_to_AIMMS\project_Sirena_25.csv" "Z:\Media_Productions\Davinci\Sirena_25\Raw_footage"
```

This will:
- Read shot names from the CSV file
- Create folders like `image_storyboard\UTW_00A_01A`
- Find all `.png` files containing each shot name
- Copy them to the appropriate shot folders

### Copying Videos

```bash
python copy_over_media.py "Z:\Media_Productions\Davinci\Sirena_25\migrate_to_AIMMS\video_storyboard" video "Z:\Media_Productions\Davinci\Sirena_25\migrate_to_AIMMS\project_Sirena_25.csv" "Z:\Media_Productions\Davinci\Sirena_25\Raw_footage"
```

This will:
- Read shot names from the CSV file
- Create folders like `video_storyboard\UTW_00A_01A`
- Find all `.mp4` and `.mkv` files containing each shot name
- Look for matching `.png` files in the same directory
- Copy both video and image files together

## How It Works

### File Matching Logic

**For Images (`file_type = image`):**
- Searches for files with pattern: `**/*{shot_name}*.png`
- Example: For shot `UTW_00A_01A`, finds files like:
  - `UTW_00A_01A_T01_underwater_00005_.png`
  - `UTW_00A_01A_scene1.png`

**For Videos (`file_type = video`):**
- Searches for files with patterns: `**/*{shot_name}*.mp4` and `**/*{shot_name}*.mkv`
- For each video found, looks for a matching `.png` file in the same directory
- Example: For video `UTW_00A_01A_take1.mp4`, looks for `UTW_00A_01A_take1.png`

### Conflict Resolution

If files with the same name are found in different locations:
- The first file keeps its original name
- Subsequent files are renamed with a counter: `filename_copy2.png`, `filename_copy3.png`, etc.
- All changes are logged in the report

### Directory Structure

The script creates the following structure:

```
target_location/
├── shot_name_1/
│   ├── file1.png
│   ├── file2_copy2.png
│   └── video1.mp4
│   └── video1.png
├── shot_name_2/
│   ├── file3.png
│   └── file4.png
└── copy_report_{file_type}_{timestamp}.txt
```

## Output

### Console Output

The script provides real-time feedback:
```
Starting copy process...
Target location: Z:\Media_Productions\Davinci\Sirena_25\migrate_to_AIMMS\image_storyboard
File type: image
Source folder: Z:\Media_Productions\Davinci\Sirena_25\Raw_footage
Report will be saved to: Z:\Media_Productions\Davinci\Sirena_25\migrate_to_AIMMS\image_storyboard\copy_report_image_20251217_174150.txt
--------------------------------------------------------------------------------

[1/50] Processing shot: UTW_00A_01A
  Found 3 file(s)
    ✓ Copied: UTW_00A_01A_T01_underwater_00005_.png
    ✓ Copied (renamed): UTW_00A_01A_scene1.png -> UTW_00A_01A_scene1_copy2.png
    ✓ Copied: UTW_00A_01A_final.png

[2/50] Processing shot: UTW_00A_01B
  No files found for UTW_00A_01B

...

================================================================================
COPY PROCESS COMPLETE
================================================================================
Shots processed: 50
Shots with files: 35
Total files copied: 127
Files renamed: 8
Errors: 2
Report saved to: Z:\Media_Productions\Davinci\Sirena_25\migrate_to_AIMMS\image_storyboard\copy_report_image_20251217_174150.txt
================================================================================
```

### Report File

A detailed text report is created with:
- Timestamp and file type
- List of all errors encountered
- Complete copy log showing:
  - Shot names processed
  - Original file paths
  - Target file paths
  - Any renaming that occurred
- Summary statistics

## CSV File Format

The CSV file must contain a column named `shot_name`. Example:

```csv
shot_name,description,notes
UTW_00A_01A,Opening scene,
UTW_00A_01B,Establishing shot,
UTW_00A_01C,Character intro,
```

Supported delimiters:
- Comma (`,`) - most common
- Semicolon (`;`)
- Tab (`\t`)
- Pipe (`|`)

The script automatically detects the delimiter, but if detection fails, it tries common alternatives.

## Tips and Best Practices

1. **Test First**: Run the script on a small subset of data first to verify it works as expected

2. **Backup Important Data**: Always backup your source files before running the script

3. **Check CSV Format**: Ensure your CSV has the correct column name (`shot_name`) and uses a supported delimiter

4. **Monitor Console Output**: Watch for warnings about missing matching files or errors during copying

5. **Review Reports**: Check the generated report file to verify all files were copied correctly

6. **Handle Conflicts**: If many files are being renamed, consider organizing your source files better to avoid naming conflicts

## Troubleshooting

### Common Issues

**"Could not determine CSV delimiter"**
- Solution: Ensure your CSV uses a standard delimiter (comma, semicolon, tab, or pipe)
- Check that the file isn't corrupted or in a different format

**"shot_name column not found"**
- Solution: Verify your CSV has a column named exactly `shot_name` (case-sensitive)
- Check for extra spaces or special characters

**"No files found for [shot_name]"**
- This is normal if no files match that shot name
- Verify the shot name exists in your source files

**"Failed to copy [file_path]: [error]"**
- Check file permissions on source and target directories
- Ensure there's enough disk space
- Verify the file isn't open in another application

### Getting Help

If you encounter issues:
1. Check the console output for specific error messages
2. Review the generated report file for detailed information
3. Verify your CSV file format and delimiter
4. Ensure you have proper permissions for source and target directories