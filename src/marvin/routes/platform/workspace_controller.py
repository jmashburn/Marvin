"""Platform workspace import/export endpoints."""

import json
from typing import Annotated

from fastapi import APIRouter, Depends, Response
from fastapi.responses import JSONResponse

from marvin.repos.all_repositories import get_repositories
from marvin.repos.repository_factory import AllRepositories
from marvin.repos.seed.workspace_exporter import WorkspaceExporter
from marvin.routes._base.base_controllers import controller
from marvin.routes._base.controller_dependencies import get_logged_in_user
from marvin.schemas.user.user import PrivateUser

router = APIRouter(prefix="/api/platform/workspace", tags=["Platform: Workspace"])


@router.get("/export")
@controller
def export_workspace(
    repos: Annotated[AllRepositories, Depends(get_repositories)],
    user: Annotated[PrivateUser, Depends(get_logged_in_user)],
    include_system_types: bool = False,
) -> Response:
    """Export the current workspace to JSON format.

    This endpoint exports the complete workspace structure including:
    - Collections
    - Entry types (workspace-scoped by default)
    - Entries with their collection assignments

    The exported JSON can be used as a seed file for workspace restoration
    or migration to another instance.

    Args:
        repos: Repository factory
        user: Current authenticated user
        include_system_types: Whether to include system entry types in export

    Returns:
        JSON response with workspace data
    """
    exporter = WorkspaceExporter(repos)
    export_data = exporter.export_workspace(include_system_types=include_system_types)

    # Return as downloadable JSON file
    return JSONResponse(
        content=export_data,
        headers={
            "Content-Disposition": f'attachment; filename="workspace-export.json"',
        },
    )


@router.get("/export/pretty")
@controller
def export_workspace_pretty(
    repos: Annotated[AllRepositories, Depends(get_repositories)],
    user: Annotated[PrivateUser, Depends(get_logged_in_user)],
    include_system_types: bool = False,
) -> Response:
    """Export workspace with pretty-printed JSON (for readability).

    Same as /export but with indented JSON formatting for easier reading
    and version control.

    Args:
        repos: Repository factory
        user: Current authenticated user
        include_system_types: Whether to include system entry types

    Returns:
        Pretty-printed JSON response
    """
    exporter = WorkspaceExporter(repos)
    export_data = exporter.export_workspace(include_system_types=include_system_types)

    # Pretty print the JSON
    pretty_json = json.dumps(export_data, indent=2, ensure_ascii=False)

    return Response(
        content=pretty_json,
        media_type="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="workspace-export.json"',
        },
    )
