"""Admin workspace backup/restore endpoints — super admin can target any workspace by ID."""

from uuid import uuid4

from fastapi import APIRouter, File, HTTPException, Query, Response, UploadFile, status
from fastapi.responses import FileResponse
from pydantic import UUID4
from starlette.background import BackgroundTask

from marvin.repos.seed.workspace_exporter import WorkspaceExporter
from marvin.repos.seed.workspace_seed_loader import WorkspaceSeedLoader
from marvin.routes._base import BaseAdminController, controller

router = APIRouter(prefix="/backups")


@controller(router)
class AdminBackupsController(BaseAdminController):
    """Admin-level workspace export and import — targets any workspace by ID."""

    @router.get("/workspaces/{workspace_id}/export/bundle", summary="Admin: Export Workspace Bundle")
    def export_workspace_bundle(self, workspace_id: UUID4) -> Response:
        """Export any workspace as a zip bundle (JSON metadata + asset binaries).

        Args:
            workspace_id: ID of the workspace to export

        Returns:
            Zip file download
        """
        from marvin.repos.all_repositories import get_repositories

        workspace_repos = get_repositories(self.repos.session, group_id=workspace_id)
        workspace = workspace_repos.groups.get_one(workspace_id)
        if not workspace:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")

        exporter = WorkspaceExporter(workspace_repos)
        zip_path = exporter.export_workspace_bundle(temp_dir=self.directories.TEMP_DIR)

        safe_slug = getattr(workspace, "slug", str(workspace_id))
        return FileResponse(
            path=str(zip_path),
            media_type="application/zip",
            filename=f"{safe_slug}-export.zip",
            background=BackgroundTask(zip_path.unlink, missing_ok=True),
        )

    @router.post("/workspaces/{workspace_id}/import", summary="Admin: Import Workspace Bundle")
    async def import_workspace_bundle(
        self,
        workspace_id: UUID4,
        file: UploadFile = File(...),
        overwrite: bool = Query(
            False,
            description=(
                "When true, existing records matched by slug are updated. "
                "⚠️ Overwrites entries, collections, resources, and assets. "
                "Junction rows are cleared and rebuilt from the bundle."
            ),
        ),
    ) -> dict:
        """Import a workspace bundle into a specific workspace.

        The bundle's workspace block is ignored — content always lands in
        the workspace identified by workspace_id.

        Args:
            workspace_id: ID of the target workspace
            file: Zip bundle file (from export/bundle)
            overwrite: When True, existing records matched by slug are updated

        Returns:
            Import counts by type
        """
        from marvin.repos.all_repositories import get_repositories

        workspace_repos = get_repositories(self.repos.session, group_id=None)
        workspace = workspace_repos.groups.get_one(workspace_id)
        if not workspace:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")

        zip_path = self.directories.TEMP_DIR / f"{uuid4()}-admin-import.zip"
        try:
            content = await file.read()
            zip_path.write_bytes(content)

            loader = WorkspaceSeedLoader(workspace_repos)
            results = loader.load_seed_zip(zip_path, overwrite=overwrite, target_group_id=str(workspace_id))

            return {"imported": results}
        finally:
            zip_path.unlink(missing_ok=True)
