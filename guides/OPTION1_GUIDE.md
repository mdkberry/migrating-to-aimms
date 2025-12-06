# Option 1: Migrate from Old Project to New Schema

This guide provides comprehensive information about Option 1, which allows you to migrate AIMMS projects from older formats to AIMMS version 1.0 with a new database schema and file structure.

## Overview

Option 1 is designed to migrate existing AIMMS projects from older formats to the new AIMMS version 1.0 schema. This migration addresses the challenge of converting projects from `shot_name` primary key to `shot_id` AUTOINCREMENT, reorganizing media files, and ensuring data integrity.

## Migration Process

### Phase 1: Preparation

1. **Configuration Validation**
   - Validates source project directory exists
   - Validates target directory is writable
   - Creates backup if requested (`--backup` flag)

2. **Directory Structure Creation**
   - Creates target project directories:
     ```
     YourProjectName/
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
     │   ├── characters/
     │   ├── locations/
     │   └── other/
     └── logs/
         ├── project_log.log
         └── migration_reports/
     ```
   - Copies existing `project_config.json` (preserves `project_start_date`)
   - Creates `shot_name_mapping.json` files

3. **Backup Creation** (if `--backup` flag used)
   - Creates timestamped backup of source project
   - Format: `{source_path}_backup_{timestamp}`

### Phase 2: Database Migration

1. **Schema Transformation**
   - Loads new schema from `schema/aimms-shot-db-schema.json`
   - Creates new database with updated schema
   - Creates all required tables and indexes
   - Populates meta table with default entries

2. **Data Migration**
   - Reads old database (`source_path/data/shots.db`)
   - Maps `shot_name` to new `shot_id` (AUTOINCREMENT)
   - Migrates all shot data preserving relationships
   - Creates shot mapping for media migration

3. **Shot Mapping Generation**
   - Creates mapping between old `shot_name` and new `shot_id`
   - Stored in `shot_name_mapping.json` files (root and data folder)
   - Used for media file reorganization

### Phase 3: Media Migration

1. **File Organization**
   - Moves files from `media/{shot_name}/` to `media/{shot_id}/`
   - Renames files to follow new naming conventions:
     - `base_xx.png` for base images
     - `video_xx.mp4` for final videos
     - `video_xx.png` for video workflows
     - Asset files in appropriate subdirectories

2. **Asset Management**
   - Organizes character, location, and other assets
   - Maintains asset relationships in database
   - Creates asset directories: `characters/`, `locations/`, `other/`

3. **Take Record Updates**
   - Updates `takes` table with new file paths
   - Generates UUID take_id values (format: `str(uuid.uuid4())`)
   - Maintains take_type associations (`base_image`, `final_video`, `video_workflow`, `asset`)

### Phase 4: Validation

1. **Database Validation**
   - Validates schema matches current AIMMS version
   - Checks data integrity and relationships
   - Verifies meta table entries
   - Validates shot and take records

2. **Media Validation**
   - Verifies all media files exist in new locations
   - Checks file naming conventions
   - Validates asset organization
   - Cross-checks database references with actual files

3. **Cross-Consistency Checks**
   - Ensures database and file system consistency
   - Validates shot_name to shot_id mapping
   - Checks for orphaned files or database entries

### Phase 5: Reporting

1. **Report Generation**
   - Creates user-friendly migration report
   - Generates technical developer report
   - Produces machine-readable JSON report
   - All reports saved to `logs/migration_reports/`

2. **Logging**
   - Comprehensive logging throughout migration
   - Progress tracking and status updates
   - Error and warning documentation

## Command Line Usage

### Basic Migration

```bash
# Migrate from old project to new schema (creates folder "YourProjectName")
python main.py --mode option1 --source old_project --project-name YourProjectName
```

### Using Target Directory

```bash
# Alternative: using target directory (uses existing transfer_folder)
python main.py --mode option1 --source old_project --target transfer_folder
```

### With Backup Creation

```bash
# Create backup before migration
python main.py --mode option1 --source old_project --project-name YourProjectName --backup
```

### Verbose Output

```bash
# Enable verbose logging
python main.py --mode option1 --source old_project --project-name YourProjectName --verbose
```

## Command Line Options

| Option | Description | Required |
|--------|-------------|----------|
| `--mode option1` | Specifies Option 1 migration | Yes |
| `--source old_project` | Source project directory | Yes |
| `--target YourProjectName` | Target project directory | Yes |
| `--backup` | Create backup before migration | No |
| `--verbose` | Enable verbose logging | No |

## Project Name vs Target Directory

The migration tool supports two ways to specify the output location:

- **`--project-name`**: Creates a project-specific folder (recommended)
  - Example: `--project-name YourProjectName` creates folder `YourProjectName`
  
- **`--target`**: Uses the specified directory path (existing folder)
  - Example: `--target transfer_folder` uses folder `transfer_folder`

## Database Schema Changes

### Old Schema (Pre-1.0)
- **Primary Key**: `shot_name` (TEXT)
- **Media Path**: `media/{shot_name}/`
- **Take References**: By shot_name

### New Schema (1.0+)
- **Primary Key**: `shot_id` (INTEGER AUTOINCREMENT)
- **Media Path**: `media/{shot_id}/`
- **Take References**: By shot_id
- **Mapping**: `shot_name_mapping.json` maintains relationship

### Schema Components

1. **Tables Created**:
   - `assets`: Character, location, and other assets
   - `deleted_shots`: Tracking for deleted shots
   - `meta`: Database metadata and configuration
   - `shots`: Main shot information
   - `takes`: Take records with file references

2. **Indexes Created**:
   - `idx_deleted_shots_old_id`
   - `idx_shots_order`
   - `idx_shots_section`
   - `idx_shots_shot_name`
   - `idx_takes_shot_id`
   - `idx_takes_shot_type`
   - `idx_takes_starred`
   - `idx_takes_type`

3. **Meta Entries**:
   - `schema_version`: Database schema version
   - `app_version`: Application version
   - `created_at`: Database creation timestamp
   - `migration_date`: Last migration timestamp
   - `author`: Project author name
   - `project_name`: Project name
   - `description`: Project description

## File Naming Conventions

### Media Files (in `media/{shot_id}/`)

| File Type | Pattern | Example |
|-----------|---------|---------|
| Base Image | `base_xx.png` | `base_01.png`, `base_02.png` |
| Final Video | `video_xx.mp4` | `video_01.mp4`, `video_02.mp4` |
| Video Workflow | `video_xx.png` | `video_01.png`, `video_02.png` |

### Asset Files (in `media/characters/`, `media/locations/`, `media/other/`)

- **Naming**: User-defined (no standard prefix required)
- **Take Type**: `asset`
- **Location**: Organized in subdirectories by category

## Error Handling

### ERROR Conditions (Migration Stops)

- Source project directory not found
- Target directory not writable
- Database schema creation failure
- Media file migration failure
- Validation failures

### WARNING Conditions (Migration Continues)

- Missing optional files
- Zero-size placeholder files
- Orphaned asset files
- Missing video thumbnails

### INFO Messages

- Migration progress updates
- Files processed
- Database records created

## Migration Reports

### User Report (`migration_report.md`)

- Migration summary
- Success/failure status
- Key statistics
- User actions required (if any)

### Developer Report (`developer_report.md`)

- Technical migration details
- Database changes
- File system changes
- Error analysis

### JSON Report (`migration_report.json`)

- Machine-readable migration data
- Statistics and metrics
- Error/warning details
- File and database counts

## Validation Checks

### Database Validation

1. **Schema Validation**
   - Table existence and structure
   - Index creation
   - Column definitions

2. **Data Integrity**
   - Primary key constraints
   - Foreign key relationships
   - Data type validation

3. **Content Validation**
   - Meta table entries
   - Shot and take records
   - Asset references

### Media Validation

1. **File Existence**
   - All referenced files exist
   - Correct file paths
   - Proper file naming

2. **File Organization**
   - Correct directory structure
   - Asset categorization
   - Shot ID folder organization

3. **Cross-Consistency**
   - Database references match files
   - Shot mapping accuracy
   - Take record validity

## Best Practices

### Before Migration

1. **Backup Source Project**
   ```bash
   python main.py --mode option1 --source old_project --project-name YourProjectName --backup
   ```

2. **Verify Source Integrity**
   - Run integrity test on source project
   - Check for missing or corrupted files
   - Validate database consistency

3. **Check Disk Space**
   - Ensure sufficient space for new project
   - Account for backup size if using `--backup`

### During Migration

1. **Use Verbose Mode**
   ```bash
   python main.py --mode option1 --source old_project --project-name YourProjectName --verbose
   ```

2. **Monitor Progress**
   - Watch console output for errors
   - Check log files for detailed information
   - Be prepared to interrupt if serious errors occur

### After Migration

1. **Run Integrity Test**
   ```bash
   python integrity_test.py YourProjectName
   ```

2. **Verify Project in AIMMS 1.0**
   - Load project in AIMMS application
   - Test core functionality
   - Verify media files display correctly

3. **Review Reports**
   - Check migration reports for issues
   - Address any warnings or errors
   - Document any manual fixes needed

## Troubleshooting

### Common Issues

1. **"Source path does not exist"**
   - Verify source project directory path
   - Check directory permissions

2. **"Cannot write to target directory"**
   - Check write permissions
   - Ensure disk space is available
   - Verify directory path is correct

3. **"Database migration failed"**
   - Check source database integrity
   - Verify schema file exists
   - Check for database corruption

4. **"Media migration failed"**
   - Verify source media files exist
   - Check file permissions
   - Ensure target directory is writable

### Recovery Procedures

1. **Migration Failure**
   - Delete incomplete target project
   - Fix identified issues
   - Retry migration

2. **Data Loss**
   - Restore from backup (if created)
   - Re-run migration with `--backup` flag
   - Verify source project integrity

3. **Corruption Issues**
   - Run integrity test on source
   - Check migration logs for errors
   - Consider manual recovery if needed

## Integration with AIMMS 1.0

Once migration is complete, the resulting project structure is fully compatible with AIMMS version 1.0:

```
YourProjectName/
├── project_config.json              # Project configuration
├── shot_name_mapping.json           # Shot name to ID mapping
├── data/
│   ├── shots.db                     # SQLite database
│   ├── shot_name_mapping.json       # Database shot mapping
│   ├── csv/                         # CSV import/export
│   ├── backup/                      # Database backups
│   └── saves/                       # Saved states
├── media/                           # Organized media files
│   ├── 1/                           # Shot ID 1
│   │   ├── base_01.png              # Base image
│   │   ├── video_01.mp4             # Final video
│   │   └── video_01.png             # Video workflow
│   ├── 2/                           # Shot ID 2
│   ├── characters/                  # Character assets
│   ├── locations/                   # Location assets
│   └── other/                       # Other assets
├── logs/
│   ├── project_log.log              # Project activity log
│   └── migration_reports/           # Migration reports
│       ├── migration_report.md      # User report
│       ├── developer_report.md      # Technical report
│       └── migration_report.json    # Machine-readable report
└── migration.log                    # Migration log
```

This structure can be loaded directly into AIMMS version 1.0 application.

## Notes

- **File Paths**: All file paths in the migrated database use forward slashes (e.g., `media/1/video_01.mp4`)
- **Relative Paths**: Only relative paths are stored in the database (no full file paths)
- **Shot Mapping**: `shot_name` to `shot_id` mapping is maintained in `shot_name_mapping.json`
- **Backup**: Use `--backup` flag to create backup before migration
- **Schema**: Uses current AIMMS schema from `schema/aimms-shot-db-schema.json`
- **UUID Take IDs**: Take records use UUID format for take_id (matches Option 4 implementation)

## Production Considerations

- **Test Migration**: Always test migration on a copy first
- **Backup Strategy**: Use backup flag and maintain source backups
- **Validation**: Run integrity tests after migration
- **Documentation**: Keep migration logs and reports for reference
- **Rollback Plan**: Have a plan for reverting if issues occur