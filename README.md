# AIMMS Migration Tool

***NOTE: this is currently a work in progress. It's recommended you do not download or fork it at this time until the launch of AIMMS Version 1.0 (Storm) Storyboard Management software in Q1 2026***

## Roadmap

- additional migration modes:
   - Restore from .aimms backup file
   - Import non-AIMMS media files to new AIMMS project (Option 4 - **NOW AVAILABLE**)

- GUI based web interface

## Description

A comprehensive Python-based tool for migrating AIMMS projects from older formats to AIMMS 1.0 with a new database schema and file structure.

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Installation](#installation)
- [Usage](#usage)
- [Utility Scripts](#utility-scripts)
- [Integrity Test](#integrity-test)
- [Aimms Project Structure](#aimms-project-structure)
- [Supporting Files](#supporting-files-required)
- [Migration Tool Folder Structure](#migration-tool-folder-structure)
- [Media File Naming Conventions](#media-file-naming-conventions-for-aimms-version-10)
- [Error Handling](#error-handling-in-migration-logs)
- [License](#license)
- [Support](#support)

## Overview

The AIMMS Migration Tool addresses the challenge of migrating projects from older AIMMS formats to the new AIMMS 1.0 schema. The tool provides:

- **Database Schema Migration**: Converts from `shot_name` primary key to `shot_id` AUTOINCREMENT
- **Media File Reorganization**: Moves from `media/{shot_name}` to `media/{shot_id}` structure
- **Data Integrity Validation**: Ensures consistency between database and media files
- **Comprehensive Reporting**: Generates user-friendly and developer reports
- **Error Recovery**: Provides detailed error information and recovery suggestions

## Features

### Core Features
- ✅ **Multiple Migration Modes**: Support for different migration scenarios
- ✅ **Schema Transformation**: Automatic database schema conversion
- ✅ **Media Migration**: Intelligent file organization and validation
- ✅ **Progress Tracking**: Real-time migration progress updates
- ✅ **Comprehensive Logging**: Detailed logging for troubleshooting
- ✅ **Validation Engine**: Multi-level validation and consistency checks
- ✅ **Report Generation**: User-friendly and technical reports


## Installation

### Prerequisites
- Python 3.12 or higher (may work on earlier versions)
- Windows 10 (primary development platform)

### Quick Start

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd AIMMS_Migration_Tool
   ```

2. **Create virtual environment** (recommended or use conda):
   ```bash
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On Linux/Mac:
   source venv/bin/activate
   ```

3. **Install dependencies (not needed currently)**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Verify installation**:
   ```bash
   python main.py --help
   ```

## Usage

### Migration Modes

1. **Option 1**: Migrate from old project to new schema *(see [Option 1 Guide](guides/OPTION1_GUIDE.md))*
2. **Option 2**: Create new project from CSV file (do this inside AIMMS 1.0 application)
3. **Option 3**: Restore from .aimms backup file (planned)
4. **Option 4**: Import non-AIMMS media files to new AIMMS project **(NOW AVAILABLE)** *(see [Option 4 Guide](guides/OPTION4_GUIDE.md))*

### Option 4: Import Non-AIMMS Media Files

Option 4 allows you to import media files from non-AIMMS sources into a valid AIMMS version 1.0 project. This is perfect when you have organized media files and want to create a new AIMMS project.

**Requirements**:
- Source directory with CSV file and media folders
- `image_storyboard/` folder with PNG files organized by shot_name
- `video_storyboard/` folder with matching video+PNG pairs organized by shot_name
- CSV file with `order_number` and `shot_name` columns

**Usage**:
```bash
python main.py --mode option4 --source aimms_import --project-name YourProjectName --verbose
```

**Features**:
- ✅ Comprehensive validation (ERROR/WARNING/INFO logging)
- ✅ Automatic project structure creation
- ✅ Database schema generation from current AIMMS schema
- ✅ Media file organization and renaming
- ✅ Shot mapping and takes table population
- ✅ Detailed migration.log generation

For detailed documentation, see [OPTION4_GUIDE.md](OPTION4_GUIDE.md).

### Basic Migration

```bash
# Migrate from old project to new schema (will create folder "YourProjectName")
python main.py --mode option1 --source old_project --project-name YourProjectName

# Alternative: using target directory (uses existing transfer_folder)
python main.py --mode option1 --source old_project --target transfer_folder

# With backup creation
python main.py --mode option1 --source old_project --project-name YourProjectName --backup

# Verbose output
python main.py --mode option1 --source old_project --project-name YourProjectName --verbose

# Option 4: Import non-AIMMS media files to new AIMMS project
python main.py --mode option4 --source aimms_import --project-name project_Footprints_25 --verbose
```

### Project Name vs Target Directory

The migration tool supports two ways to specify the output location:

- **`--project-name`**: Creates a project-specific folder (recommended)
  - Example: `--project-name YourProjectName` creates folder `YourProjectName`
  
- **`--target`**: Uses the specified directory path (existing folder)
  - Example: `--target transfer_folder` uses folder `transfer_folder`

### Command Line Options

| Option | Description | Required |
|--------|-------------|----------|
| `--mode` | Migration mode (option1, option2, option3, option4) | Yes |
| `--source` | Source project directory | Depends on mode |
| `--target` | Target project directory | Yes |
| `--csv` | CSV file path (for option2) | For option2 |
| `--restore` | Restore file path (for option3) | For option3 |
| `--backup` | Create backup before migration | No |
| `--verbose` | Enable verbose logging | No |

### Option 4 Usage

**Import non-AIMMS media files to new AIMMS project:**

```bash
# Basic usage
python main.py --mode option4 --source aimms_import --project-name YourProjectName

# With verbose output
python main.py --mode option4 --source aimms_import --project-name YourProjectName --verbose
```

**Requirements:**
- CSV file in `aimms_import` folder (e.g., `project_Footprints_25.csv`)
- `image_storyboard/` and `video_storyboard/` directories with shot folders
- Required CSV columns: `order_number`, `shot_name`

**Features:**
- ✅ Validates CSV structure and required columns
- ✅ Validates media integrity (matching video/PNG pairs, orphaned files)
- ✅ Creates complete AIMMS 1.0 project structure
- ✅ Generates comprehensive migration.log with ERROR/WARNING/INFO messages
- ✅ Uses UUID take_id generation (matching Option 1)
- ✅ Enhanced validation for shot_name entries

For detailed information, see the [Option 4 Guide](guides/OPTION4_GUIDE.md).
| `--help` | Show help message | No |


## Utility Scripts

### Create Shot Subfolders

A utility script for creating shot subfolders from a CSV file:

```bash
python create-shot-subfolders.py csv-file-location target-folder
```

This script reads shot names from a CSV file and creates corresponding subfolders in the target directory. Useful for organizing media files or preparing project structures.

## Integrity Test

After migration, run the integrity test to validate the migrated project:

```bash
# Basic integrity test
python integrity_test.py project_folder_path

# With verbose output
python integrity_test.py project_folder_path --verbose
```

### Output

- **Console**: Test progress and summary
- **Report**: Detailed markdown report saved to `integrity_reports/integrity_report_{project_name}_{timestamp}.md`
- **Log**: Detailed logs saved to project folder when using `--verbose` flag

### Validation Checks

- ✅ Project structure and required files
- ✅ Database schema against [`schema/aimms-shot-db-schema.json`](schema/aimms-shot-db-schema.json)
- ✅ Database content and data integrity
- ✅ Meta table entries (author, project_name, description, etc.)
- ✅ Media files and naming conventions
- ✅ Cross-consistency between database and files
- ⚠️  Asset subdirectories (characters, locations, other)
- ⚠️  Zero-size placeholder files
- ⚠️  Orphaned files and references

## AIMMS Project Structure

The migration tool creates a valid AIMMS version 1.0 project structure:

```
YourProjectName/
├── 📄 project_config.json              # Project configuration
├── 📄 shot_name_mapping.json           # Shot name to ID mapping (root level)
├── 📁 data/                            # Database and data files
│   ├── 📄 shots.db                     # SQLite database
│   ├── 📄 shot_name_mapping.json       # Shot name to ID mapping (data folder)
│   ├── 📁 csv/                         # CSV import/export files
│   ├── 📁 backup/                      # Database backup files
│   └── 📁 saves/                       # Saved .aimms recovery files
├── 📁 media/                           # Media files organized by shot_id
│   ├── 1/                              # Shot ID 1
│   │   ├── video_01.mp4
│   │   ├── video_01.png
│   │   └── base_01.png
│   ├── 2/                              # Shot ID 2
│   │   └── ...
│   ├── characters/                     # Character assets
│   ├── locations/                      # Location assets
│   └── other/                          # Other assets
├── 📁 logs/                            # Log files and reports
│   ├── 📄 project_log.log              # Project activity log
│   └── 📁 migration_reports/           # Migration reports
│       ├── migration_report.md         # User-friendly report
│       ├── developer_report.md         # Technical report
│       └── migration_report.json       # Machine-readable report
└── 📄 migration.log                    # Migration process log
```

## Supporting Files (required)

### project_config.json
Contains project configuration settings:
```json
{
  "last_selected_workflow": "",
  "project_start_date": "2025-12-03",
  "last_selected_section": "All Sections"
}
```

If an existing `project_config.json` is found, the tool preserves the `project_start_date` and adds the missing fields.

### shot_name_mapping.json
Tracks the relationship mapping between shot names and shot IDs:
```json
{
  "version": "1.0",
  "created": "2025-12-04T07:47:00Z",
  "mapping": {}
}
```

Two copies are created:
- **Root level**: For project-level reference
- **Data folder**: For database-related operations

### Data Subfolders (used by AIMMS version 1.0 Storyboard Management software)
- **csv/**: For CSV import/export operations
- **backup/**: For database backup files
- **saves/**: For saved project states

### Logs Structure
- **project_log.log**: AIMMS version 1.0 activity logging
- **migration_reports/**: All migration-related reports and logs


## Migration Tool Folder Structure

```
AIMMS_Migration_Tool/
├── 📄 README.md               # 📖 Project documentation
├── 📄 requirements.txt        # 📦 Python dependencies
├── 📄 LICENSE                 # 📄 License file
├── 📄 .gitignore              # 📝 Git ignore rules
├── 📁 old_project/            # 📂 Source project (example)
│   └── put-you-old-project-in-here-delete-this-info-file
├── 📁 transfer_folder/        # 📂 Migration workspace
│   └── use-this-folder-as-migration-folder-or-name-your-own
├── 📁 schema/                 # 🗃️  Database schema definitions
│   ├── aimms-shot-db-schema.json  # Database schema for version control
│   └── aimms-meta-entries.json    # Meta table entries configuration
├── 📁 integrity_reports/      # 📊 Integrity test reports
│   └── integrity-test-reports-saved-here
├── 📄 main.py                 # 🚀 CLI entry point
├── 📄 migration_engine.py     # ⚙️  Migration orchestrator
├── 📄 config.py               # ⚙️  Configuration management
├── 📄 database.py             # 🗄️  Database migration
├── 📄 schema_manager.py       # 🗃️  Schema management module
├── 📄 media.py                # 📁 Media file migration
├── 📄 validation.py           # ✅ Validation engine
├── 📄 integrity_test.py       # 🔍 Standalone integrity test tool
├── 📄 reporting.py            # 📊 Report generation
├── 📄 logger.py               # 📝 Logging configuration
├── 📄 utils.py                # 🔧 Utility functions
└── 📄 models.py               # 📋 Data models
```

### Schema Management

The migration tool uses a schema file (`schema/aimms-shot-db-schema.json`) to manage database structure and ensure consistency across versions. This JSON file contains the complete database schema including table definitions, column specifications, and indexes. When new AIMMS versions are released with database schema changes, this file should be updated with the schema from a current `shots.db` file to ensure proper migration.

## Media File Naming Conventions For AIMMS version 1.0

### **Take Types (in media/{shot_id}):**

| File Pattern | Extension | Take Type | Description |
|--------------|-----------|-----------|-------------|
| `video_xx.mp4` | .mp4 | `final_video` | Final video takes |
| `video_xx.png` | .png | `video_workflow` | Video thumbnails/workflow images |
| `base_xx.png` | .png | `base_image` | Base image placeholders |

### **Asset Types (in media/characters/, media/locations/, media/other/):**
- **Naming**: User-defined (no standard prefix required)
- **Take Type**: `asset`
- **Location**: Organized in subdirectories by category


## Error Handling In Migration Logs

### Log Files and Error Checking

Logs are written to:
- **Console**: Real-time progress and status updates
- **File**: Detailed logs for troubleshooting (when `--verbose` is used)

#### **🔍 Critical: Check for ERRORS in migration.log**

**Before testing your migrated project in AIMMS 1.0, you MUST check the migration log for ERROR messages and address all of them:**

Recommend using a simple text editor and search for "ERROR".

**Migration will NOT complete until ALL errors are resolved!**

e.g. `video_workflow` take_type entries in `takes` table of `shots.db` cannot be created until all ERROR messages are resolved. This will require fixing errors, then running the migration tool again (deleting the erroneous resulting files first). This approach is standard practice.

#### **📋 ERROR vs WARNING - What to prioritize:**

| Log Level | Action Required | Description |
|-----------|----------------|-------------|
| **ERROR** | **🔴 MUST FIX** | Critical issues that prevent proper migration |
| **WARNING** | 🟡 Review at discretion | Informational messages, may indicate issues |

#### **🎯 Error Resolution Priority:**

1. **🔴 CRITICAL ERRORS** (Fix immediately):
   - "Take file not found"
   - "Asset file not found"
   - "Database migration failed"
   - "Media migration failed"

2. **🟡 WARNINGS** (Review as needed):
   - "Zero-size file" (expected as placeholders)
   - "Source folder not found"
   - "Orphaned asset file"
   - "Missing video thumbnails"

#### **✅ Migration Completion Checklist:**

- [ ] **No ERROR messages** in migration.log
- [ ] All critical files migrated successfully
- [ ] Database validation passed
- [ ] Media validation passed
- [ ] Integrity test (standalone) passed
- [ ] Project loads successfully in AIMMS 1.0 and tests working

**⚠️ WARNING messages can typically be treated as reference information, but review them at your discretion based on your project requirements.**


## License

*(AIMMS version 1.0 (Storm) Storyboard Management software application will be released in Q1 2026 as closed source software and will require a license to run.)*

This project is the AIMMS version 1.0 migration tool only. It is licensed under **GPL‑3.0**:

- ✅ You can use, modify, and share the code freely.  
- ✅ You can use it for personal, educational, or commercial projects.  
- ⚠️ If you distribute modified versions, you **must also share your source code** under GPL‑3.0.  
- ⚠️ You must keep the original license and copyright notice.  
- ❌ No warranty is provided — use at your own risk.
- see the [LICENSE](LICENSE) file for details.

## Support

### Documentation

Documentation on **AIMMS version 1.0 (Storm) Storyboard Management Software** will be published to [https://mdkberry.github.io/aimms-docs/](https://mdkberry.github.io/aimms-docs/) before application launch in Q1 of 2026. 

The AIMMS Migration Tool is available now on GitHub at [https://github.com/mdkberry/migrating-to-aimms](https://github.com/mdkberry/migrating-to-aimms) .

### Getting Help
1. Check the [FAQ](#faq) section below
2. Check existing [issues](../../issues)
3. Create a new issue with detailed information

### FAQ

**Q: What Python version is required for the migration tool?**
A: Python 3.12 or higher is recommended but older versions may work.

**Q: Can I migrate projects from different AIMMS versions?**
A: The tool is currently designed for migrating old AIMMS projects to AIMMS 1.0 schema. Future migration methods are planned.

**Q: What happens if the migration fails?**
A: It's recommended you make a backup of your original project before attempting a migration. When migrating, run the migration tool, then check for ERROR entries in the log, if you find errors then delete the newly created migration folder and its contents, fix the errors, and run the migration tool again. Repeat this until the migration is completing without ERROR entries in `migration.log` (WARNINGS are fine but be sure you understand their meaning). Then test opening in AIMMS 1.0 application.

**Q: How long does migration take?**
A: Migration time depends on project size. Large projects with many media files will take longer. Likely done in seconds in most cases for projects with a hundred shots and multiple shot takes.

**Q: Can I resume a failed migration?**
A: It is best to delete the failed migration folder and run the migration process again. Repeat this until all ERROR messages in the migration.log are fixed.

## 📝 Changelog

*Versioning will not begin until the launch of AIMMS Version 1.0 (Storm) Storyboard Management software in Q1 2026.*

### Version 1.0.0 (Current)
- Initial release
- Support for up to four migration modes
- Complete database and media migration
- Comprehensive validation and reporting

## 🙏 Acknowledgments

- AIMMS development team for the original project structure
- Contributors and testers for feedback and improvements
- [YT Channel](https://www.youtube.com/@markdkberry) subscribers for their ongoing support and encouragement to keep working on *AIMMS Version 1.0 (Storm) Storyboard Management software*

---

**Note**: ***Always backup your original data before performing migrations***. Use this tool at your own discretion, we cannot be held responsible for loss of data it might cause.
