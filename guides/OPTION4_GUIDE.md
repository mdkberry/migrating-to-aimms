# Option 4: Import Non-AIMMS Media Files to New AIMMS Project

This guide explains how to use Option 4 of the AIMMS Migration Tool to import non-AIMMS media files into a valid AIMMS version 1.0 project structure.

## Overview

Option 4 allows you to migrate media files from non-AIMMS sources (images, videos, etc.) into a properly structured AIMMS project with a valid database schema. This is useful when you have media files organized outside of AIMMS and want to import them into the AIMMS ecosystem.

## Prerequisites

1. **Source Directory Structure**: Your source directory (e.g., `aimms_import`) must contain:
   - A CSV file (e.g., `project_Footprints_25.csv`)
   - An `image_storyboard/` folder
   - A `video_storyboard/` folder

2. **CSV File Requirements**:
   - Must contain `order_number` and `shot_name` columns (required)
   - Can include optional columns: `section`, `description`, `image_prompt`, `colour_scheme_image`, `time_of_day`, `location`, `country`, `year`, `video_prompt`, `created_date`
   - The CSV filename will be used as the project name (or specify it when using Option4 with the `--project-name` switch)

3. **Media File Requirements**:
   - **Image Storyboard**: Each shot folder should contain PNG files (each PNG = one take)
   - **Video Storyboard**: Each shot folder should contain matching pairs of video files (MP4/MKV) and PNG files (each pair = one take)
   - Shot folders in both storyboards should be named using `shot_name` from the CSV (there is a utility script `create-shot-subfolders.py` to do this for you using the csv `shot_name` column. Run it twice - once on each storyboard subfolder).

## Usage

### Command Line

```bash
python main.py --mode option4 --source aimms_import --project-name YourProjectName --verbose
```

**Parameters**:
- `--mode option4`: Specifies Option 4 migration
- `--source aimms_import`: Path to source directory containing media and CSV
- `--project-name YourProjectName`: Name of the new AIMMS project (creates folder)
- `--verbose`: Enable verbose logging (optional)

### Example Directory Structure

*(NOTE: both storyboard folders will usually have the same `shot_name` folders due to how AIMMS works with both storyboards in parallel. But this isnt strictly required, just best practice.)*

```
aimms_import/
├── project_Footprints_25.csv
├── image_storyboard/
│   ├── NN_01A_01A_train_2/
│   │   └── NN_01A_01A_train_2.png
│   ├── NN_08A_01C_shadow_1/
│   │   └── NN_08A_01C_shadow_1.png
│   └── ...
├── video_storyboard/
│   ├── NN_10B_01G_thekey_1/
│   │   ├── NN_10B_01G_thekey_1_FINAL_64fps.mp4
│   │   └── NN_10B_01G_thekey_1_FINAL_64fps.png
│   ├── NN_13A_01A_prisonfight_1/
│   │   ├── NN_13A_01A_prisonfight_1_FINAL_64fps.mp4
│   │   └── NN_13A_01A_prisonfight_1_FINAL_64fps.png
│   └── ...
```

## Migration Process

### Phase 1: CSV Validation
- Finds and validates the CSV file in the source directory
- Checks for required columns: `order_number` and `shot_name`
- Uses CSV filename as project name unless `--project-name` flag is used in call.

### Phase 2: Media Integrity Validation
- Validates that `image_storyboard/` and `video_storyboard/` directories exist
- Checks each shot folder for media files
- **ERROR**: If both storyboard folders are empty for a shot
- **WARNING**: If only one storyboard folder is empty for a shot
- **ERROR**: If video storyboard contains orphaned files (video without matching PNG or PNG without matching video)
- **ERROR**: If shot_name exists in CSV but no corresponding folder found in storyboard directories

### Phase 3: Project Structure Creation
Creates the AIMMS Version 1.0 project directory structure and schema:
```
project_Footprints_25/
├── project_config.json
├── shot_name_mapping.json (root)
├── data/
│   ├── shots.db
│   ├── shot_name_mapping.json (data folder)
│   ├── csv/
│   ├── backup/
│   └── saves/
├── media/
│   ├── 1/ (shot_id folders)
│   │   ├── base_01.png
│   │   ├── video_01.mp4
│   │   ├── video_01.png
│   │   └── ...
│   ├── characters/
│   ├── locations/
│   └── other/
└── logs/
    └── project_log.log
```

### Phase 4: Database Creation
- Creates `shots.db` using the current AIMMS schema
- Populates `meta` table with default entries
- Inserts shots from CSV data into the `shots` table
- Generates `shot_id` values (AUTOINCREMENT)

### Phase 5: Media Migration
- **Image Storyboard**: Copies PNG files to `media/{shot_id}/` as `base_XX.png`
- **Video Storyboard**: Copies matching pairs as `video_XX.mp4` and `video_XX.png`
- Updates `takes` table with file paths and take types:
  - `base_image`: For image storyboard files
  - `final_video`: For video storyboard video files
  - `video_workflow`: For video storyboard PNG files

### Phase 6: Logging
- Creates `migration.log` with detailed ERROR, WARNING, and INFO messages
- Summarizes migration results
- Lists all shots, errors, warnings, and info messages

## File Naming Conventions

### Migrated Media Files
- **Images**: `base_01.png`, `base_02.png`, etc.
- **Videos**: `video_01.mp4`, `video_02.mp4`, etc.
- **Video Workflows**: `video_01.png`, `video_02.png`, etc.

### Database Entries
- **Shots**: `shot_id` (AUTOINCREMENT), `shot_name` (from CSV)
- **Takes**: `take_id` format: **UUID**

## Enhanced Validation Features

### Shot Name Validation

**NEW**: Option 4 now validates that every `shot_name` in the CSV file has a corresponding folder in either `image_storyboard/` or `video_storyboard/` directories.

**ERROR Example** (when shot exists in CSV but no folder found):
```
ERROR MESSAGES:
------------------------------
❌ Shot 'NN_10B_01K_knife_extended' in CSV but no corresponding folder found in storyboard directories
❌ Shot 'NN_15A_01P_train_gone_crane' in CSV but no corresponding folder found in storyboard directories
```

This forces users to either:
1. **Resolve the media**: Create missing storyboard folder and add appropriate media files, OR
2. **Remove from CSV**: Delete the shot entry from the CSV file if not needed

## Error Handling

### ERROR Conditions (Migration Stops)
1. **Missing CSV file**: No CSV found in source directory
2. **Missing required columns**: CSV missing `order_number` or `shot_name`
3. **Empty storyboard folders**: Both `image_storyboard` and `video_storyboard` folders empty for a shot
4. **Orphaned video files**: Video files without matching PNG files
5. **Orphaned PNG files**: PNG files without matching video files
6. **Missing shot folders**: Shot_name exists in CSV but no corresponding folder found in storyboard directories
7. **Database creation failure**: Schema loading or database creation errors

### WARNING Conditions (Migration Continues)
1. **Empty image storyboard**: Only `image_storyboard` folder empty for a shot
2. **Empty video storyboard**: Only `video_storyboard` folder empty for a shot
3. **Missing project_config.json**: Existing config not found (uses defaults)

### INFO Messages
1. **CSV file used**: Name of the CSV file being processed
2. **Shots inserted**: Number of shots successfully inserted from CSV
3. **Media files migrated**: Number of media files successfully copied

## Migration Log Example

```
AIMMS Migration Tool - Option 4 Log
Generated: 2025-12-06 13:45:55
============================================================

INFO MESSAGES:
------------------------------
• Using CSV file: project_Footprints_25.csv

WARNING MESSAGES:
------------------------------
⚠ One storyboard folder empty for shot 'NN_14A_01C_boarding_2'
⚠ One storyboard folder empty for shot 'NN_16A_01H_Legend_Fight_4'

ERROR MESSAGES:
------------------------------
❌ Both storyboard folders empty for shot 'NN_10B_01K_knife_extended'
❌ Both storyboard folders empty for shot 'NN_15A_01P_train_gone_crane'

MIGRATION SUMMARY:
------------------------------
Shots created: 124
Errors: 2
Warnings: 18
Info: 1

❌ MIGRATION FAILED - Please fix the errors above and retry.
```

## Production Ready

The implementation is **production-ready** and provides comprehensive validation to ensure data integrity. Users can now successfully import non-AIMMS media files into AIMMS projects using Option 4.

## Troubleshooting

### Common Issues

1. **"No CSV file found"**
   - Ensure CSV file exists in source directory
   - Check file extension (.csv)

2. **"Missing required columns"**
   - Verify CSV contains `order_number` and `shot_name` columns
   - Check column names match exactly (case-sensitive)

3. **"Both storyboard folders empty"**
   - Add media files to at least one storyboard folder for the shot
   - Or remove the shot from the CSV if not needed

4. **"Orphaned video/PNG files"**
   - Ensure video files have matching PNG files with same stem name
   - Remove orphaned files or add missing pairs

5. **"Migration failed"**
   - Check `migration.log` for specific error messages
   - Fix all ERROR conditions before retrying
   - Delete the target project folder and retry after fixes

### Best Practices

1. **Organize media files**:
   - Use consistent naming conventions
   - Group files by shot_name in separate folders
   - Ensure video-PNG pairs have matching names

2. **CSV file**:
   - Use UTF-8 encoding
   - Include all required columns
   - Use consistent shot_name values

3. **Migration workflow**:
   - Run migration and check `migration.log`
   - Fix all ERROR conditions
   - Delete target folder and retry
   - Repeat until no errors remain

## Integration with AIMMS 1.0

Once migration completes successfully:
1. The new project folder can be loaded into AIMMS 1.0 application
2. All media files will be properly organized
3. Database schema will be compatible with AIMMS 1.0
4. Shot and take data will be available in the application

## Notes

- **Schema**: Uses current AIMMS schema from `schema/aimms-shot-db-schema.json`