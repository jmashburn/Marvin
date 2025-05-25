"""
This module provides functionality to check for the latest release of a GitHub repository.

It uses the GitHub API to fetch release information and caches the result to avoid
excessive API calls. The cache is reset periodically to ensure the information
stays up-to-date.
"""
from datetime import datetime, timezone
from functools import lru_cache

import requests

_LAST_RESET: datetime | None = None


@lru_cache(maxsize=1)
def get_latest_github_release(url: str) -> str:
    """
    Gets the latest release from GitHub.

    Returns:
        str: The latest release from GitHub.
    """

    url = url
    response = requests.get(url)
    response.raise_for_status()
    return response.json()["tag_name"]


def get_latest_version(url: str) -> str:
    """
    Gets the latest release version.

    Returns:
        str: The latest release version.
    """
    MAX_DAYS_OLD = 1  # reset cache after 1 day

    global _LAST_RESET

    now = datetime.now(timezone.utc)

    if not _LAST_RESET or now - _LAST_RESET > datetime.timedelta(days=MAX_DAYS_OLD):
        _LAST_RESET = now
        get_latest_github_release.cache_clear()

    try:
        return get_latest_github_release(url)
    except requests.RequestException:
        return "error fetching version"
    except KeyError:
        return "error parsing response"
    except Exception:
        return "unknown error"
