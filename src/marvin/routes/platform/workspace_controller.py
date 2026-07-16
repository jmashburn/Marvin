"""Platform workspace import/export endpoints."""

import json
from uuid import uuid4

from fastapi import APIRouter, File, Query, Response, UploadFile
from fastapi.responses import FileResponse, JSONResponse

from marvin.repos.seed.workspace_exporter import WorkspaceExporter
from marvin.repos.seed.workspace_seed_loader import WorkspaceSeedLoader
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

    @router.get("/export/bundle", summary="Export Workspace Bundle")
    def export_workspace_bundle(self, include_system_types: bool = False) -> Response:
        """Export the workspace as a zip bundle containing JSON metadata and asset binaries.

        The zip contains:
        - workspace-export.json: full metadata (same format as /export)
        - files/{storage_key}: binary file for each asset

        Args:
            include_system_types: Whether to include system entry types

        Returns:
            Zip file download
        """
        exporter = WorkspaceExporter(self.repos)
        zip_path = exporter.export_workspace_bundle(
            include_system_types=include_system_types,
            temp_dir=self.directories.BACKUP_DIR,
        )

        return FileResponse(
            path=str(zip_path),
            media_type="application/zip",
            filename=zip_path.name,
        )

    @router.post("/import", summary="Import Workspace Bundle")
    async def import_workspace(
        self,
        file: UploadFile = File(...),
        overwrite: bool = Query(
            False,
            description=(
                "When true, existing records matched by slug are updated with bundle data. "
                "⚠️ This will overwrite entries, collections, resources, and assets "
                "that exist in the workspace. Entry junction rows (→asset, →collection, "
                "→resource) are cleared and rebuilt from the bundle."
            ),
        ),
    ) -> dict:
        """Import a workspace bundle into the current workspace.

        Always imports into the caller's active workspace — the workspace block
        in the bundle is ignored for routing. Requires workspace **OWNER** or
        **SUPER_ADMIN** role. Super admins who need to import into a specific
        workspace should use the Admin Dashboard import.

        **overwrite=false (default)**: existing records are skipped — safe for
        seeding into a live workspace without disrupting existing content.

        **overwrite=true**: existing records are updated from the bundle. ⚠️ Can
        replace entry content and assignments. Entry junction rows (→asset,
        →collection, →resource) are cleared and rebuilt from the bundle.

        Args:
            file: Zip bundle file (from /export/bundle)
            overwrite: When True, existing records matched by slug are updated

        Returns:
            Import counts by type
        """
        from fastapi import status as http_status

        from marvin.db.models.users.roles import PlatformRole, WorkspaceRole

        is_super_admin = self.user.platform_role == PlatformRole.SUPER_ADMIN
        is_owner = self.user.has_workspace_role(self.group_id, WorkspaceRole.OWNER)

        if not (is_super_admin or is_owner):
            from fastapi import HTTPException

            raise HTTPException(
                status_code=http_status.HTTP_403_FORBIDDEN,
                detail="Importing a workspace bundle requires OWNER or SUPER_ADMIN role.",
            )

        zip_path = self.directories.TEMP_DIR / f"{uuid4()}-import.zip"
        try:
            content = await file.read()
            zip_path.write_bytes(content)

            from marvin.repos.all_repositories import get_repositories

            instance_repos = get_repositories(self.repos.session, group_id=None)
            loader = WorkspaceSeedLoader(instance_repos)
            results = loader.load_seed_zip(zip_path, overwrite=overwrite, target_group_id=self.group_id)

            return {"imported": results}
        finally:
            zip_path.unlink(missing_ok=True)

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
