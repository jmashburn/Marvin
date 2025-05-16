import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, HTTPException

from marvin.routes._base import BaseAdminController, controller
from marvin.schemas.admin import MaintenanceSummary
from marvin.schemas.admin.maintenance import MaintenanceStorageDetails
from marvin.schemas.response import ErrorResponse, SuccessResponse
from marvin.pkgs.stats import fs_stats

router = APIRouter(prefix="/maintenance")


def tail_log(log_file: Path, n: int) -> list[str]:
    try:
        with open(log_file) as f:
            lines = f.readlines()
    except FileNotFoundError:
        return ["no log file found"]

    return lines[-n:]


@controller(router)
class AdminMaintenanceController(BaseAdminController):
    @router.get("", response_model=MaintenanceSummary)
    def get_maintenance_summary(self):
        """
        Get the maintenance summary
        """

        return MaintenanceSummary(
            data_dir_size=fs_stats.pretty_size(fs_stats.get_dir_size(self.directories.DATA_DIR)),
        )

    @router.get("/storage", response_model=MaintenanceStorageDetails)
    def get_storage_details(self):
        return MaintenanceStorageDetails(
            temp_dir_size=fs_stats.pretty_size(fs_stats.get_dir_size(self.directories.TEMP_DIR)),
            backups_dir_size=fs_stats.pretty_size(fs_stats.get_dir_size(self.directories.BACKUP_DIR)),
            seeds_dir_size=fs_stats.pretty_size(fs_stats.get_dir_size(self.directories.SEED_DIR)),
            plugin_dir_size=fs_stats.pretty_size(fs_stats.get_dir_size(self.directories.PLUGIN_DIR)),
        )

    @router.post("/clean/temp", response_model=SuccessResponse)
    def clean_temp(self):
        try:
            if self.directories.TEMP_DIR.exists():
                shutil.rmtree(self.directories.TEMP_DIR)

            self.directories.TEMP_DIR.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            raise HTTPException(status_code=500, detail=ErrorResponse.respond("Failed to clean temp")) from e

        return SuccessResponse.respond("'.temp' directory cleaned")
