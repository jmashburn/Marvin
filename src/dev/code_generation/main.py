import argparse
from pathlib import Path

import gen_module
import gen_py_pytest_data_paths
import gen_py_schema_exports
from utils import log

CWD = Path(__file__).parent


def cmd_generate(_args: argparse.Namespace) -> None:
    items = [
        (gen_py_schema_exports.main, "Schema Exports"),
        (gen_py_pytest_data_paths.main, "Test data paths"),
    ]

    for func, name in items:
        log.info(f"Generating {name}...")
        try:
            func()
        except Exception as e:
            log.error(f"Error generating {name}: {e}")
            continue

    log.info("Generation complete.")


def cmd_create_module(args: argparse.Namespace) -> None:
    gen_module.main(
        entity=args.entity_name,
        plural_override=args.plural,
        dry_run=args.dry_run,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Marvin code generation tools")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("generate", help="Run all standard generators (schema exports, test data paths)")

    module_parser = sub.add_parser("create-module", help="Scaffold a new CRUD module")
    module_parser.add_argument("entity_name", help="Singular entity name (e.g. product)")
    module_parser.add_argument("--plural", default=None, help="Override auto-pluralization")
    module_parser.add_argument("--dry-run", action="store_true", help="Print plan without writing files")

    args = parser.parse_args()

    if args.command == "generate":
        cmd_generate(args)
    elif args.command == "create-module":
        cmd_create_module(args)


if __name__ == "__main__":
    main()
