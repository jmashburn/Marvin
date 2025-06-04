"""
This module defines static application-level constants.

These constants include the application version and base directory paths.
They are intended to be immutable and provide fundamental information
about the application's structure and version.
"""

import os
from pathlib import Path

from marvin import __version__

APP_VERSION = __version__
"""The current version of the Marvin application."""

CWD = Path(__file__).parent
"""The current working directory of this settings file."""

BASE_DIR = Path(os.getenv("BASE_DIR", CWD.parent.parent))
"""The base directory of the Marvin application project."""
