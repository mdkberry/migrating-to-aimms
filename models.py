"""
Data Models Module

Defines data structures and named tuples used throughout the migration tool.
"""

from typing import Dict, List, NamedTuple, Optional, Any
from datetime import datetime

class MigrationResult(NamedTuple):
    """Result of a migration operation."""
    success: bool
    shot_mapping: Dict[str, int]
    errors: List[str]
    warnings: List[str]

class ValidationResult(NamedTuple):
    """Result of a validation operation."""
    success: bool
    errors: List[str]
    warnings: List[str]

class MediaResult(NamedTuple):
    """Result of a media migration operation."""
    success: bool
    errors: List[str]
    warnings: List[str]

class DatabaseInfo(NamedTuple):
    """Information about a database."""
    path: str
    exists: bool
    schema_version: Optional[str]
    app_version: Optional[str]
    shot_count: int
    take_count: int

class ShotInfo(NamedTuple):
    """Information about a shot."""
    shot_id: Optional[int]
    order_number: int
    shot_name: str
    section: Optional[str]
    description: Optional[str]
    image_prompt: Optional[str]
    colour_scheme_image: Optional[str]
    time_of_day: Optional[str]
    location: Optional[str]
    country: Optional[str]
    year: Optional[str]
    video_prompt: Optional[str]
    created_date: Optional[str]

class TakeInfo(NamedTuple):
    """Information about a take."""
    take_id: str
    shot_id: int
    take_type: str
    file_path: str
    starred: int
    created_date: Optional[str]

class AssetInfo(NamedTuple):
    """Information about an asset."""
    id_key: str
    asset_name: str
    asset_type: str
    file_path: str
    starred: int
    created_date: Optional[str]

class FileInfo(NamedTuple):
    """Information about a file."""
    path: str
    exists: bool
    size: int
    size_mb: float
    is_zero_size: bool
    file_type: str

class MigrationConfigData(NamedTuple):
    """Migration configuration data."""
    mode: str
    source_path: Optional[str]
    target_path: str
    csv_path: Optional[str]
    restore_path: Optional[str]
    create_backup: bool
    data_path: str
    media_path: str
    report_path: str

class ProgressInfo(NamedTuple):
    """Progress information for long-running operations."""
    current: int
    total: int
    percentage: float
    operation: str
    elapsed_time: float
    estimated_remaining: float

class ErrorInfo(NamedTuple):
    """Error information with context."""
    message: str
    error_type: str
    context: Dict[str, Any]
    timestamp: datetime

class ShotMapping(NamedTuple):
    """Mapping between old and new shot identifiers."""
    old_shot_name: str
    new_shot_id: int
    order_number: int

class MediaFolderInfo(NamedTuple):
    """Information about a media folder."""
    shot_id: int
    folder_path: str
    exists: bool
    file_count: int
    video_files: List[str]
    thumbnail_files: List[str]
    orphaned_thumbnails: List[str]
    missing_thumbnails: List[str]

class DatabaseSchema(NamedTuple):
    """Database schema information."""
    shots_table: List[str]  # Column names
    takes_table: List[str]  # Column names
    assets_table: List[str]  # Column names
    meta_table: List[str]   # Column names
    indexes: List[str]      # Index names

class MigrationStats(NamedTuple):
    """Statistics about migration operation."""
    start_time: datetime
    end_time: Optional[datetime]
    total_shots: int
    migrated_shots: int
    failed_shots: int
    total_takes: int
    migrated_takes: int
    failed_takes: int
    total_assets: int
    migrated_assets: int
    failed_assets: int
    total_media_files: int
    copied_media_files: int
    failed_media_files: int
    errors: List[ErrorInfo]
    warnings: List[str]

class ReportData(NamedTuple):
    """Data for generating reports."""
    migration_info: Dict[str, Any]
    shot_mapping: Dict[str, int]
    file_structure: Dict[str, str]
    validation_results: ValidationResult
    migration_stats: MigrationStats
    errors: List[ErrorInfo]
    warnings: List[str]

class CSVRecord(NamedTuple):
    """Record from CSV file for option2."""
    order_number: int
    shot_name: str
    section: Optional[str]
    description: Optional[str]
    image_prompt: Optional[str]
    colour_scheme_image: Optional[str]
    time_of_day: Optional[str]
    location: Optional[str]
    country: Optional[str]
    year: Optional[str]
    video_prompt: Optional[str]

class RestoreInfo(NamedTuple):
    """Information about restore operation."""
    restore_file: str
    restore_type: str  # 'database', 'media', 'full'
    extracted_files: List[str]
    restore_time: datetime

class BackupInfo(NamedTuple):
    """Information about backup operation."""
    backup_path: str
    backup_type: str  # 'full', 'database', 'media'
    created_time: datetime
    size_mb: float
    included_files: List[str]

class PerformanceMetrics(NamedTuple):
    """Performance metrics for operations."""
    operation_name: str
    duration_seconds: float
    items_processed: int
    throughput_items_per_second: float
    memory_usage_mb: float
    timestamp: datetime

class ConsistencyCheck(NamedTuple):
    """Result of consistency check."""
    check_name: str
    passed: bool
    details: Dict[str, Any]
    errors: List[str]
    warnings: List[str]

class FileValidationResult(NamedTuple):
    """Result of file validation."""
    file_path: str
    exists: bool
    is_readable: bool
    is_writable: bool
    size: int
    checksum: Optional[str]
    errors: List[str]
    warnings: List[str]

class DatabaseIntegrityResult(NamedTuple):
    """Result of database integrity check."""
    table_counts: Dict[str, int]
    foreign_key_violations: List[Dict[str, Any]]
    orphaned_records: List[Dict[str, Any]]
    data_consistency_issues: List[Dict[str, Any]]
    overall_status: str  # 'PASS', 'WARN', 'FAIL'

class MigrationMode(NamedTuple):
    """Information about a migration mode."""
    mode: str
    description: str
    requires_source: bool
    requires_target: bool
    requires_csv: bool
    requires_restore: bool
    supported_operations: List[str]

# Common migration modes
MIGRATION_MODES = {
    'option1': MigrationMode(
        mode='option1',
        description='Migrate from old project to new schema',
        requires_source=True,
        requires_target=True,
        requires_csv=False,
        requires_restore=False,
        supported_operations=['database', 'media', 'validation']
    ),
    'option2': MigrationMode(
        mode='option2',
        description='Import project from CSV file',
        requires_source=False,
        requires_target=True,
        requires_csv=True,
        requires_restore=False,
        supported_operations=['database', 'media_creation']
    ),
    'option3': MigrationMode(
        mode='option3',
        description='Restore from backup file',
        requires_source=False,
        requires_target=True,
        requires_csv=False,
        requires_restore=True,
        supported_operations=['extract', 'database', 'media']
    ),
    'option4': MigrationMode(
        mode='option4',
        description='Import media files to new project',
        requires_source=True,
        requires_target=True,
        requires_csv=False,
        requires_restore=False,
        supported_operations=['media', 'database_update']
    )
}

def create_empty_migration_result() -> MigrationResult:
    """Create an empty migration result."""
    return MigrationResult(
        success=True,
        shot_mapping={},
        errors=[],
        warnings=[]
    )

def create_empty_validation_result() -> ValidationResult:
    """Create an empty validation result."""
    return ValidationResult(
        success=True,
        errors=[],
        warnings=[]
    )

def create_empty_media_result() -> MediaResult:
    """Create an empty media result."""
    return MediaResult(
        success=True,
        errors=[],
        warnings=[]
    )

def format_migration_stats(stats: MigrationStats) -> Dict[str, Any]:
    """Format migration statistics for reporting."""
    duration = (stats.end_time - stats.start_time).total_seconds() if stats.end_time else 0
    
    return {
        'duration_seconds': duration,
        'success_rate': {
            'shots': safe_divide(stats.migrated_shots, stats.total_shots) * 100,
            'takes': safe_divide(stats.migrated_takes, stats.total_takes) * 100,
            'assets': safe_divide(stats.migrated_assets, stats.total_assets) * 100,
            'media_files': safe_divide(stats.copied_media_files, stats.total_media_files) * 100
        },
        'totals': {
            'shots': stats.total_shots,
            'takes': stats.total_takes,
            'assets': stats.total_assets,
            'media_files': stats.total_media_files
        },
        'migrated': {
            'shots': stats.migrated_shots,
            'takes': stats.migrated_takes,
            'assets': stats.migrated_assets,
            'media_files': stats.copied_media_files
        },
        'failed': {
            'shots': stats.failed_shots,
            'takes': stats.failed_takes,
            'assets': stats.failed_assets,
            'media_files': stats.failed_media_files
        }
    }

def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """Safely divide two numbers."""
    try:
        if denominator == 0:
            return default
        return numerator / denominator
    except (TypeError, ValueError):
        return default