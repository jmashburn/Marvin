import contextlib
from collections.abc import Generator

from pytest import MonkeyPatch, fixture

mp = MonkeyPatch()
mp.setenv("PRODUCTION", "True")
mp.setenv("TESTING", "True")
from pathlib import Path

from fastapi.testclient import TestClient

from marvin.app import app
from marvin.core import config
