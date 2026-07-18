"""
Admin Scheduled Tasks controller.

Provides endpoints for administrators to manage ALL scheduled tasks across
all workspaces (and system-level tasks with group_id=NULL).
"""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Path, status
from pydantic import UUID4

from marvin.routes._base import BaseAdminController, controller
from marvin.schemas.platform.scheduled_tasks import (
    ScheduledTaskCreate,
    ScheduledTaskExecutionLogRead,
    ScheduledTaskRead,
    ScheduledTaskUpdate,
)

router = APIRouter(prefix="/scheduled-tasks")


@controller(router)
class AdminScheduledTasksController(BaseAdminController):
    """Controller for admin-level management of all scheduled tasks."""

    @router.get("/task-types")
    def list_task_types(self, detailed: bool = False):
        """List all available task types."""
        from marvin.services.scheduled_tasks import TaskHandlerRegistry

        if detailed:
            return TaskHandlerRegistry.get_task_type_info()
        return TaskHandlerRegistry.list_registered_types()

    @router.get("", response_model=list[ScheduledTaskRead])
    def list_tasks(self):
        """List all scheduled tasks across all workspaces (including system tasks)."""
        return self.repos.scheduled_tasks.get_all(order_by="name")

    @router.get("/log", response_model=list[ScheduledTaskExecutionLogRead])
    def get_global_log(self, limit: int = 100):
        """Get global execution log across all tasks and workspaces."""
        return self.repos.scheduled_task_executions.get_workspace_log(limit=limit)

    @router.post("", response_model=ScheduledTaskRead, status_code=status.HTTP_201_CREATED)
    def create_task(self, data: ScheduledTaskCreate):
        """Create a system-level scheduled task (group_id=NULL)."""
        return self.repos.scheduled_tasks.create(data)

    @router.get("/{task_id}", response_model=ScheduledTaskRead)
    def get_task(self, task_id: Annotated[UUID4, Path()]):
        """Get any scheduled task by ID."""
        task = self.repos.scheduled_tasks.get_one(task_id)
        if not task:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
        return task

    @router.patch("/{task_id}", response_model=ScheduledTaskRead)
    def update_task(self, task_id: Annotated[UUID4, Path()], data: ScheduledTaskUpdate):
        """Update any scheduled task."""
        task = self.repos.scheduled_tasks.get_one(task_id)
        if not task:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
        return self.repos.scheduled_tasks.update(task_id, data)

    @router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
    def delete_task(self, task_id: Annotated[UUID4, Path()]):
        """Delete any scheduled task."""
        task = self.repos.scheduled_tasks.get_one(task_id)
        if not task:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
        self.repos.scheduled_tasks.delete(task_id)

    @router.post("/{task_id}/execute", status_code=status.HTTP_202_ACCEPTED)
    def execute_task(self, task_id: Annotated[UUID4, Path()]):
        """Manually trigger any task execution."""
        from marvin.services.event_bus_service.event_types import EventScheduledTaskData, EventTypes

        task = self.repos.scheduled_tasks.get_one(task_id)
        if not task:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

        self.event_bus.dispatch(
            integration_id="admin_api",
            group_id=task.group_id,
            event_type=EventTypes.scheduled_task_triggered,
            document_data=EventScheduledTaskData.from_model(task),
            message=f"Scheduled task '{task.name}' manually triggered by admin",
            entity_id=task.id,
            entity_type="scheduled_task",
        )
        return {"message": f"Task '{task.name}' execution triggered"}

    @router.get("/{task_id}/history", response_model=list[ScheduledTaskExecutionLogRead])
    def get_task_history(self, task_id: Annotated[UUID4, Path()], limit: int = 50):
        """Get execution history for any task."""
        task = self.repos.scheduled_tasks.get_one(task_id)
        if not task:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
        return self.repos.scheduled_task_executions.get_task_history(task_id, limit=limit)
