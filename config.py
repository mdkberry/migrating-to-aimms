"""
Configuration Management Module

Handles configuration settings and validation for the migration tool.
"""

import os
import logging
from pathlib import Path
from typing import Optional

class MigrationConfig:
    """Configuration class for migration settings."""
    
    def __init__(
        self,
        mode: str,
        source_path: Optional[str] = None,
        target_path: Optional[str] = None,
        csv_path: Optional[str] = None,
        restore_path: Optional[str] = None,
        create_backup: bool = False
    ):
        """
        Initialize migration configuration.
        
        Args:
            mode: Migration mode (option1, option2, option3, option4)
            source_path: Source project directory
            target_path: Target project directory
            csv_path: CSV file path for option2
            restore_path: Restore file path for option3
            create_backup: Whether to create backup before migration
        """
        self.logger = logging.getLogger(__name__)
        
        # Validate migration mode
        self._validate_mode(mode)
        self.mode = mode
        
        # Set paths with different requirements for each mode
        if mode == 'option4':
            # Option 4: source is required (aimms_import folder), target is required
            self.source_path = self._validate_path(source_path, required=True)
            self.target_path = self._validate_path(target_path, required=True)
            self.csv_path = None  # Not used in option4
            self.restore_path = None  # Not used in option4
        else:
            # Other modes: use original logic
            self.source_path = self._validate_path(source_path, required=self.mode != 'option2')
            self.target_path = self._validate_path(target_path, required=True)
            self.csv_path = self._validate_path(csv_path, required=self.mode == 'option2')
            self.restore_path = self._validate_path(restore_path, required=self.mode == 'option3')
        
        self.create_backup = create_backup
        
        # Set up derived paths
        self.data_path = os.path.join(self.target_path, 'data')
        self.media_path = os.path.join(self.target_path, 'media')
        self.report_path = os.path.join(self.target_path, 'migration_reports')
        
        self.logger.debug(f"Configuration loaded: mode={mode}, source={source_path}, target={target_path}")
    
    def _validate_mode(self, mode: str):
        """Validate migration mode."""
        valid_modes = ['option1', 'option2', 'option3', 'option4']
        if mode not in valid_modes:
            raise ValueError(f"Invalid migration mode: {mode}. Valid modes: {valid_modes}")
    
    def _validate_path(self, path: Optional[str], required: bool = False) -> Optional[str]:
        """
        Validate and normalize file/directory path.
        
        Args:
            path: Path to validate
            required: Whether path is required
            
        Returns:
            Normalized path or None if not provided and not required
        """
        if path is None:
            if required:
                raise ValueError("Required path parameter is missing")
            return None
        
        # Normalize path
        normalized_path = os.path.normpath(path)
        
        # Check if path is absolute
        if not os.path.isabs(normalized_path):
            # Convert to absolute path relative to current directory
            normalized_path = os.path.abspath(normalized_path)
        
        return normalized_path
    
    def validate_source_exists(self):
        """Validate that source path exists (if applicable)."""
        if self.source_path and not os.path.exists(self.source_path):
            raise FileNotFoundError(f"Source path does not exist: {self.source_path}")
    
    def validate_target_writable(self):
        """Validate that target directory is writable."""
        try:
            # Try to create target directory if it doesn't exist
            os.makedirs(self.target_path, exist_ok=True)
            
            # Test write permissions
            test_file = os.path.join(self.target_path, '.write_test')
            with open(test_file, 'w') as f:
                f.write('test')
            os.remove(test_file)
            
        except Exception as e:
            raise PermissionError(f"Cannot write to target directory: {e}")
    
    def validate_csv_file(self):
        """Validate CSV file for option2."""
        if self.mode == 'option2':
            if not self.csv_path:
                raise ValueError("CSV file path is required for option2")
            
            if not os.path.exists(self.csv_path):
                raise FileNotFoundError(f"CSV file not found: {self.csv_path}")
    
    def validate_restore_file(self):
        """Validate restore file for option3."""
        if self.mode == 'option3':
            if not self.restore_path:
                raise ValueError("Restore file path is required for option3")
            
            if not os.path.exists(self.restore_path):
                raise FileNotFoundError(f"Restore file not found: {self.restore_path}")
    
    def validate_source_exists(self):
        """Validate that source path exists (with mode-specific logic)."""
        if self.mode == 'option4':
            # For option4, validate aimms_import structure
            if not self.source_path:
                raise ValueError("Source path is required for option4")
            
            if not os.path.exists(self.source_path):
                raise FileNotFoundError(f"Source path does not exist: {self.source_path}")
            
            # Check for required subdirectories
            image_storyboard = os.path.join(self.source_path, 'image_storyboard')
            video_storyboard = os.path.join(self.source_path, 'video_storyboard')
            
            if not os.path.exists(image_storyboard):
                self.logger.warning(f"image_storyboard directory not found: {image_storyboard}")
            
            if not os.path.exists(video_storyboard):
                self.logger.warning(f"video_storyboard directory not found: {video_storyboard}")
        else:
            # For other modes, use original logic
            if self.source_path and not os.path.exists(self.source_path):
                raise FileNotFoundError(f"Source path does not exist: {self.source_path}")
    
    def get_source_db_path(self) -> Optional[str]:
        """Get path to source database file."""
        if self.source_path:
            return os.path.join(self.source_path, 'data', 'shots.db')
        return None
    
    def get_target_db_path(self) -> str:
        """Get path to target database file."""
        return os.path.join(self.data_path, 'shots.db')
    
    def get_source_media_path(self) -> Optional[str]:
        """Get path to source media directory."""
        if self.source_path:
            return os.path.join(self.source_path, 'media')
        return None
    
    def get_target_media_path(self) -> str:
        """Get path to target media directory."""
        return self.media_path
    
    def get_migration_mode_description(self) -> str:
        """Get description of current migration mode."""
        descriptions = {
            'option1': 'Migrate from old project to new schema',
            'option2': 'Import project from CSV file',
            'option3': 'Restore from backup file',
            'option4': 'Import media files to new project'
        }
        return descriptions.get(self.mode, 'Unknown migration mode')
    
    def __str__(self) -> str:
        """String representation of configuration."""
        return (f"MigrationConfig(mode={self.mode}, "
                f"source={self.source_path}, "
                f"target={self.target_path}, "
                f"backup={self.create_backup})")