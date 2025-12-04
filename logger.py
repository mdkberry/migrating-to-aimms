"""
Logging Configuration Module

Sets up comprehensive logging for the migration tool with multiple levels and outputs.
"""

import logging
import sys
import os
from datetime import datetime
from typing import Optional

def setup_logging(verbose: bool = False, log_file: Optional[str] = None):
    """
    Configure logging for the migration tool.
    
    Args:
        verbose: Enable verbose logging (DEBUG level)
        log_file: Optional path to log file
    """
    log_level = logging.DEBUG if verbose else logging.INFO
    
    console_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.handlers.clear()
    
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)
    
    if log_file:
        log_dir = os.path.dirname(log_file)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)
        
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(log_level)
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)
    
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)
    
    logger = logging.getLogger('aimms_migration')
    logger.info(f"Logging initialized - Level: {logging.getLevelName(log_level)}")
    
    return logger

def create_migration_logger(name: str) -> logging.Logger:
    """
    Create a logger for migration-specific modules.
    
    Args:
        name: Module name for logger
        
    Returns:
        Configured logger instance
    """
    return logging.getLogger(f'aimms_migration.{name}')

def log_migration_start(config) -> None:
    """Log the start of migration process."""
    logger = logging.getLogger('aimms_migration')
    logger.info("=" * 60)
    logger.info("AIMMS Migration Tool Started")
    logger.info(f"Migration Mode: {config.get_migration_mode_description()}")
    logger.info(f"Source: {config.source_path or 'N/A'}")
    logger.info(f"Target: {config.target_path}")
    logger.info(f"Backup: {'Yes' if config.create_backup else 'No'}")
    logger.info("=" * 60)

def log_migration_end(success: bool, duration: float) -> None:
    """Log the end of migration process."""
    logger = logging.getLogger('aimms_migration')
    status = "SUCCESS" if success else "FAILED"
    logger.info("=" * 60)
    logger.info(f"Migration {status}")
    logger.info(f"Duration: {duration:.2f} seconds")
    logger.info("=" * 60)

class MigrationLogger:
    """Enhanced logger for migration operations."""
    
    def __init__(self, name: str):
        self.logger = create_migration_logger(name)
    
    def start_operation(self, operation: str, details: str = "") -> None:
        """Log start of an operation."""
        msg = f"Starting {operation}"
        if details:
            msg += f" - {details}"
        self.logger.info(msg)
    
    def end_operation(self, operation: str, success: bool, details: str = "") -> None:
        """Log end of an operation."""
        status = "completed" if success else "failed"
        msg = f"{operation} {status}"
        if details:
            msg += f" - {details}"
        if success:
            self.logger.info(msg)
        else:
            self.logger.error(msg)
    
    def progress(self, current: int, total: int, operation: str = "") -> None:
        """Log progress percentage."""
        if total > 0:
            percentage = (current / total) * 100
            msg = f"Progress: {percentage:.1f}% ({current}/{total})"
            if operation:
                msg += f" - {operation}"
            self.logger.info(msg)
    
    def warning_with_suggestion(self, message: str, suggestion: str) -> None:
        """Log warning with actionable suggestion."""
        self.logger.warning(f"{message} - Suggestion: {suggestion}")
    
    def error_with_context(self, message: str, context: dict) -> None:
        """Log error with additional context."""
        self.logger.error(f"{message} - Context: {context}")
    
    def debug_data(self, data: dict, label: str = "Data") -> None:
        """Log data dictionary for debugging."""
        self.logger.debug(f"{label}: {data}")

def log_performance(func):
    """Decorator to log function execution time."""
    def wrapper(*args, **kwargs):
        logger = logging.getLogger('aimms_migration.performance')
        start_time = datetime.now()
        
        try:
            result = func(*args, **kwargs)
            duration = (datetime.now() - start_time).total_seconds()
            logger.info(f"{func.__name__} completed in {duration:.2f} seconds")
            return result
        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            logger.error(f"{func.__name__} failed after {duration:.2f} seconds: {e}")
            raise
    
    return wrapper

class OperationTimer:
    """Context manager for timing operations."""
    
    def __init__(self, operation_name: str):
        self.operation_name = operation_name
        self.start_time = None
        self.logger = logging.getLogger('aimms_migration.performance')
    
    def __enter__(self):
        self.start_time = datetime.now()
        self.logger.info(f"Starting {self.operation_name}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = (datetime.now() - self.start_time).total_seconds()
        if exc_type is None:
            self.logger.info(f"{self.operation_name} completed in {duration:.2f} seconds")
        else:
            self.logger.error(f"{self.operation_name} failed after {duration:.2f} seconds: {exc_val}")