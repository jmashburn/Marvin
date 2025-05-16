from marvin.schemas._marvin import _MarvinModel


class MaintenanceSummary(_MarvinModel):
    data_dir_size: str


class MaintenanceStorageDetails(_MarvinModel):
    temp_dir_size: str
    backups_dir_size: str
    seeds_dir_size: str
    plugin_dir_size: str


class MaintenanceLogs(_MarvinModel):
    logs: list[str]
