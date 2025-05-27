"""
This module defines the FastAPI controller for administrative maintenance tasks
within the Marvin application.

It provides endpoints for administrators to get storage usage summaries,
details about specific directory sizes, and to perform cleanup operations
like clearing the temporary directory. It also includes a utility function
for tailing log files (though not currently exposed via an HTTP endpoint).
"""

import shutil  # For directory removal (rmtree)
from pathlib import Path  # For path manipulation

from fastapi import APIRouter, HTTPException, status  # Added status for HTTPException

# Marvin specific imports
from marvin.pkgs.stats import fs_stats  # Filesystem statistics utilities
from marvin.routes._base import BaseAdminController, controller  # Base admin controller
from marvin.schemas.admin import MaintenanceSummary  # Pydantic schema for maintenance summary
from marvin.schemas.admin.maintenance import MaintenanceStorageDetails  # Schema for storage details
from marvin.schemas.response import ErrorResponse, SuccessResponse  # Standardized response schemas

# APIRouter for admin maintenance section, prefixed with /maintenance
# All routes here will be under /admin/maintenance.
router = APIRouter(prefix="/maintenance")


def tail_log(log_file: Path, n: int) -> list[str]:
    """
    Reads the last N lines from a log file.

    Args:
        log_file (Path): The Path object pointing to the log file.
        n (int): The number of lines to read from the end of the file.

    Returns:
        list[str]: A list of the last N lines from the file, or a list
                   containing a "no log file found" message if the file
                   does not exist.
    """
    try:
        with open(log_file, encoding="utf-8") as f:  # Added encoding for robustness
            lines = f.readlines()
    except FileNotFoundError:
        return [f"Log file not found: {log_file}"]  # More informative message
    except Exception as e:  # Catch other potential read errors
        return [f"Error reading log file {log_file}: {e}"]

    return lines[-n:]  # Return the last n lines


@controller(router)
class AdminMaintenanceController(BaseAdminController):
    """
    Controller for administrative maintenance operations.

    Provides endpoints for viewing storage statistics and performing cleanup tasks.
    All operations require administrator privileges.
    """

    @router.get("", response_model=MaintenanceSummary, summary="Get Maintenance Summary")
    def get_maintenance_summary(self) -> MaintenanceSummary:
        """
        Retrieves a summary of maintenance-related information.

        Currently, this includes the total size of the main application data directory.
        Accessible only by administrators.

        Returns:
            MaintenanceSummary: A Pydantic model containing the data directory size.
        """
        data_dir = self.directories.DATA_DIR  # Access DATA_DIR via base controller
        return MaintenanceSummary(
            data_dir_size=fs_stats.pretty_size(fs_stats.get_dir_size(data_dir)),
        )

    @router.get("/storage", response_model=MaintenanceStorageDetails, summary="Get Storage Details")
    def get_storage_details(self) -> MaintenanceStorageDetails:
        """
        Retrieves detailed storage usage for various application directories.

        This includes the size of the temporary, backups, seeds, and plugins directories.
        Sizes are returned in a human-readable format (e.g., MB, GB).
        Accessible only by administrators.

        Returns:
            MaintenanceStorageDetails: A Pydantic model containing the sizes of key directories.
        """
        dirs = self.directories  # Access application directories via base controller
        return MaintenanceStorageDetails(
            temp_dir_size=fs_stats.pretty_size(fs_stats.get_dir_size(dirs.TEMP_DIR)),
            backups_dir_size=fs_stats.pretty_size(fs_stats.get_dir_size(dirs.BACKUP_DIR)),
            seeds_dir_size=fs_stats.pretty_size(fs_stats.get_dir_size(dirs.SEED_DIR)),
            plugin_dir_size=fs_stats.pretty_size(fs_stats.get_dir_size(dirs.PLUGIN_DIR)),
        )

    @router.post("/clean/temp", response_model=SuccessResponse, summary="Clean Temporary Directory")
    def clean_temp(self) -> SuccessResponse:
        """
        Cleans the temporary application directory.

        This operation removes all contents of the `.temp` directory located within
        the application's data directory and then recreates it as an empty directory.
        Accessible only by administrators.

        Returns:
            SuccessResponse: A Pydantic model indicating the success of the operation.

        Raises:
            HTTPException (500 Internal Server Error): If an error occurs during
                                                      the directory cleaning process.
        """
        temp_dir = self.directories.TEMP_DIR  # Path to the temporary directory
        try:
            if temp_dir.exists():
                # Remove the entire temporary directory tree
                shutil.rmtree(temp_dir)
                self.logger.info(f"Successfully removed temporary directory: {temp_dir}")

            # Recreate the temporary directory
            temp_dir.mkdir(parents=True, exist_ok=True)
            self.logger.info(f"Successfully recreated temporary directory: {temp_dir}")
        except Exception as e:
            self.logger.error(f"Failed to clean temporary directory {temp_dir}: {e}")
            # Raise an HTTPException if any error occurs during the process
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,  # Use 500 for server-side file system errors
                detail=ErrorResponse.respond(message="Failed to clean temporary directory.", exception=str(e)),
            ) from e

        return SuccessResponse.respond("Temporary (.temp) directory has been cleaned successfully.")
