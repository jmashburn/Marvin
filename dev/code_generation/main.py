from pathlib import Path
import dev.code_generation.gen_py_schema_exports as gen_py_schema_exports, gen_py_pytest_data_paths
from utils import log

CWD = Path(__file__).parent


def main():
    """
    This script generates the Python schema files for the Marvin app.
    It uses the `gen_py_schema_exports` module to generate the files.
    """
    log.info("Generating Python schema files...")
    items = [
        (gen_py_schema_exports.main, "Schema Exports"),
        (gen_py_pytest_data_paths.main, "Test data paths"),
        # (gen_py_pytest_routes.main, "pytest routes"),
    ]

    for item in items:
        func, name = item
        log.info(f"Generating {name}...")
        try:
            func()
        except Exception as e:
            log.error(f"Error generating {name}: {e}")
            continue

    log.info("Python schema files generated successfully.")


if __name__ == "__main__":
    main()
