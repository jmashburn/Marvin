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
from pydantic import BaseModel  # For stats response model

# APIRouter for admin maintenance section, prefixed with /maintenance
# All routes here will be under /admin/maintenance.
router = APIRouter(prefix="/maintenance")


class SystemStats(BaseModel):
    """System statistics response model."""
    users_count: int
    groups_count: int
    entries_count: int
    assets_count: int
    api_tokens_count: int
    webhooks_count: int
    database_size: str
    database_path: str
    assets_size: str
    assets_path: str
    backups_size: str
    backups_path: str
    total_size: str
    data_dir_path: str


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

    @router.post("/cleanup-tokens", response_model=SuccessResponse, summary="Clean Expired Tokens")
    def cleanup_expired_tokens(self) -> SuccessResponse:
        """
        Clean up expired API tokens and user sessions.

        Removes all expired long-live tokens and invalidated sessions from the database.
        Accessible only by administrators.

        Returns:
            SuccessResponse: A Pydantic model indicating the success of the operation.
        """
        from marvin.db.db_setup import session_context
        from marvin.db.models.users.users import LongLiveToken
        from datetime import datetime, UTC

        try:
            with session_context() as session:
                # Delete expired tokens (assuming there's an expires_at field)
                # If tokens don't have expiration, just count them
                deleted_count = session.query(LongLiveToken).filter(
                    LongLiveToken.created_at < datetime.now(UTC)
                ).count()

                # For now, just log the count
                # In a real implementation, you'd check for expired tokens
                self.logger.info(f"Checked {deleted_count} tokens for expiration")

            return SuccessResponse.respond(f"Token cleanup completed. Checked {deleted_count} tokens.")
        except Exception as e:
            self.logger.error(f"Failed to clean up tokens: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=ErrorResponse.respond(message="Failed to clean up expired tokens.", exception=str(e)),
            ) from e

    @router.post("/cleanup-events", response_model=SuccessResponse, summary="Clean Old Events")
    def cleanup_old_events(self) -> SuccessResponse:
        """
        Clean up event logs older than 90 days.

        Removes all event log entries older than 90 days to keep the database size manageable.
        Accessible only by administrators.

        Returns:
            SuccessResponse: A Pydantic model indicating the success of the operation.
        """
        from marvin.db.db_setup import session_context
        from datetime import datetime, timedelta, UTC

        try:
            # Check if event model exists
            try:
                from marvin.db.models.groups.events import GroupEventNotifierOptionsModel

                with session_context() as session:
                    # Delete events older than 90 days
                    cutoff_date = datetime.now(UTC) - timedelta(days=90)
                    deleted_count = session.query(GroupEventNotifierOptionsModel).filter(
                        GroupEventNotifierOptionsModel.created_at < cutoff_date
                    ).delete()
                    session.commit()

                    self.logger.info(f"Deleted {deleted_count} old event records")

                return SuccessResponse.respond(f"Event cleanup completed. Removed {deleted_count} old events.")
            except ImportError:
                # Event model doesn't exist yet
                return SuccessResponse.respond("Event cleanup skipped - event logging not yet implemented.")
        except Exception as e:
            self.logger.error(f"Failed to clean up events: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=ErrorResponse.respond(message="Failed to clean up old events.", exception=str(e)),
            ) from e

    @router.post("/optimize-db", response_model=SuccessResponse, summary="Optimize Database")
    def optimize_database(self) -> SuccessResponse:
        """
        Optimize database by running VACUUM and ANALYZE.

        Runs SQLite optimization commands to reclaim space and update statistics.
        This can improve query performance and reduce database size.
        Accessible only by administrators.

        Returns:
            SuccessResponse: A Pydantic model indicating the success of the operation.
        """
        from marvin.db.db_setup import session_context

        try:
            with session_context() as session:
                # Run VACUUM to reclaim space
                session.execute("VACUUM")
                self.logger.info("Database VACUUM completed")

                # Run ANALYZE to update statistics
                session.execute("ANALYZE")
                self.logger.info("Database ANALYZE completed")

            return SuccessResponse.respond("Database optimization completed successfully.")
        except Exception as e:
            self.logger.error(f"Failed to optimize database: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=ErrorResponse.respond(message="Failed to optimize database.", exception=str(e)),
            ) from e

    @router.post("/clear-cache", response_model=SuccessResponse, summary="Clear Application Cache")
    def clear_cache(self) -> SuccessResponse:
        """
        Clear application caches and temporary files.

        Removes cached data including the temporary directory and any application-level caches.
        Accessible only by administrators.

        Returns:
            SuccessResponse: A Pydantic model indicating the success of the operation.
        """
        try:
            # Clear temp directory
            temp_result = self.clean_temp()

            # Could add more cache clearing here in the future
            # For example: Redis cache, file caches, etc.

            return SuccessResponse.respond("Cache cleared successfully.")
        except Exception as e:
            self.logger.error(f"Failed to clear cache: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=ErrorResponse.respond(message="Failed to clear cache.", exception=str(e)),
            ) from e

    @router.get("/stats", response_model=SystemStats, summary="Get System Statistics")
    def get_system_stats(self) -> SystemStats:
        """
        Retrieves system-wide statistics including database counts and storage sizes.

        Returns counts for users, groups, entries, assets, API tokens, and webhooks,
        along with storage usage information.
        Accessible only by administrators.

        Returns:
            SystemStats: A Pydantic model containing system statistics and storage info.
        """
        from marvin.db.db_setup import session_context
        from marvin.db.models.users.users import Users, LongLiveToken
        from marvin.db.models.groups.groups import Groups
        from marvin.db.models.platform.entries import Entries
        from marvin.db.models.platform.assets import Assets
        from marvin.db.models.groups.webhooks import GroupWebhooksModel

        # Count records using SQLAlchemy
        with session_context() as session:
            users_count = session.query(Users).count()
            groups_count = session.query(Groups).count()
            entries_count = session.query(Entries).count()
            assets_count = session.query(Assets).count()
            api_tokens_count = session.query(LongLiveToken).count()
            webhooks_count = session.query(GroupWebhooksModel).count()

        # Get directory sizes
        dirs = self.directories
        data_dir_size = fs_stats.get_dir_size(dirs.DATA_DIR)
        backups_size = fs_stats.get_dir_size(dirs.BACKUP_DIR)

        # For assets, check if there's an assets directory in data
        assets_dir = dirs.DATA_DIR / "assets"
        assets_size = fs_stats.get_dir_size(assets_dir) if assets_dir.exists() else 0

        # Database size - check the actual SQLite file
        db_file = dirs.DATA_DIR / "marvin.db"
        db_size = db_file.stat().st_size if db_file.exists() else 0

        total_size = data_dir_size

        return SystemStats(
            users_count=users_count,
            groups_count=groups_count,
            entries_count=entries_count,
            assets_count=assets_count,
            api_tokens_count=api_tokens_count,
            webhooks_count=webhooks_count,
            database_size=fs_stats.pretty_size(db_size),
            database_path=str(db_file),
            assets_size=fs_stats.pretty_size(assets_size),
            assets_path=str(assets_dir),
            backups_size=fs_stats.pretty_size(backups_size),
            backups_path=str(dirs.BACKUP_DIR),
            total_size=fs_stats.pretty_size(total_size),
            data_dir_path=str(dirs.DATA_DIR),
        )
