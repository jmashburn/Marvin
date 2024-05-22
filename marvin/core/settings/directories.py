from pathlib import Path


class AppDirectories:
    def __init__(self, data_dir: Path) -> None:
        self.DATA_DIR = data_dir
        self.BACKUP_DIR = data_dir.joinpath("backups")

        self._TEMP_DIR = data_dir.joinpath(".temp")
        self.ensure_directories()

    @property
    def TEMP_DIR(self):
        return self._TEMP_DIR

    def ensure_directories(self):
        required_dirs = [
            self.BACKUP_DIR,
        ]
        for dir in required_dirs:
            dir.mkdir(parents=True, exist_ok=True)
