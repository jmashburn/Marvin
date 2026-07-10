#!/usr/bin/env python3
"""
Script to seed the database with event notifier options.

This script can be run standalone to populate or refresh the event_notifier_options
table with all the event types defined in the notifier_options.json file.

Usage:
    python scripts/seed_notifier_options.py
"""

import sys
from pathlib import Path

# Add the src directory to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from marvin.db.db_setup import session_context
from marvin.repos.all_repositories import get_repositories
from marvin.services.seeders.seeder_service import SeederService


def main():
    """Run the notifier options seeder."""
    print("Starting event notifier options seeding...")

    with session_context() as session:
        # Get repositories without group context (admin/system level)
        repos = get_repositories(session, group_id=None)

        # Create seeder service and run the seeder
        seeder_service = SeederService(repos)
        seeder_service.seed_notifier_options("notifier_options")

    print("✓ Event notifier options seeding completed successfully!")
    print(f"  Loaded event types from: {project_root}/src/marvin/repos/seed/resources/notifier_options/notifier_options.json")


if __name__ == "__main__":
    main()
