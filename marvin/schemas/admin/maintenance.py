from marvin.schemas._marvin import _MarvinModel


class MaintenanceSummary(_MarvinModel):
    pass


class MaintenanceStorageDetails(_MarvinModel):
    pass


class MaintenanceLogs(_MarvinModel):
    logs: list[str]
