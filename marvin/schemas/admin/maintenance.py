"""
This module defines Pydantic schemas for representing administrative maintenance
information within the Marvin application.

These schemas are used as response models for endpoints that provide details
about storage usage and potentially application logs.
"""
from marvin.schemas._marvin import _MarvinModel # Base Pydantic model for Marvin schemas


class MaintenanceSummary(_MarvinModel):
    """
    Schema for a summary of maintenance information, currently focused on data directory size.
    """
    data_dir_size: str # The total size of the main application data directory, presented as a human-readable string (e.g., "1.2 GB").


class MaintenanceStorageDetails(_MarvinModel):
    """
    Schema providing detailed storage usage for various key application directories.
    All sizes are presented as human-readable strings.
    """
    temp_dir_size: str # Size of the temporary directory.
    backups_dir_size: str # Size of the backups directory.
    seeds_dir_size: str # Size of the seeds directory (for initial data).
    plugin_dir_size: str # Size of the plugins directory.


class MaintenanceLogs(_MarvinModel):
    """
    Schema for returning a list of log entries.
    This might be used if an endpoint provides access to recent log lines.
    """
    logs: list[str] # A list of strings, where each string is a log entry.
