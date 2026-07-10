"""Platform workspace import/export endpoints."""

import json

from fastapi import APIRouter, Response
from fastapi.responses import JSONResponse

from marvin.repos.seed.workspace_exporter import WorkspaceExporter
from marvin.routes._base import BaseUserController, controller

router = APIRouter(prefix="/workspace")


@controller(router)
class WorkspaceController(BaseUserController):
    """Workspace import/export routes."""

    @router.get("/export", summary="Export Workspace")
    def export_workspace(self, include_system_types: bool = False) -> Response:
        """Export the current workspace to JSON format.

        This endpoint exports the complete workspace structure including:
        - Collections
        - Entry types (workspace-scoped by default)
        - Entries with their collection assignments

        The exported JSON can be used as a seed file for workspace restoration
        or migration to another instance.

        Args:
            include_system_types: Whether to include system entry types in export

        Returns:
            JSON response with workspace data
        """
        exporter = WorkspaceExporter(self.repos)
        export_data = exporter.export_workspace(include_system_types=include_system_types)

        # Return as downloadable JSON file
        return JSONResponse(
            content=export_data,
            headers={
                "Content-Disposition": 'attachment; filename="workspace-export.json"',
            },
        )

    @router.get("/export/pretty", summary="Export Workspace (Pretty)")
    def export_workspace_pretty(self, include_system_types: bool = False) -> Response:
        """Export workspace with pretty-printed JSON (for readability).

        Same as /export but with indented JSON formatting for easier reading
        and version control.

        Args:
            include_system_types: Whether to include system entry types

        Returns:
            Pretty-printed JSON response
        """
        exporter = WorkspaceExporter(self.repos)
        export_data = exporter.export_workspace(include_system_types=include_system_types)

        # Pretty print the JSON
        pretty_json = json.dumps(export_data, indent=2, ensure_ascii=False)

        return Response(
            content=pretty_json,
            media_type="application/json",
            headers={
                "Content-Disposition": 'attachment; filename="workspace-export.json"',
            },
        )
