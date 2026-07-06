/**
 * Workspace management API client
 */

import { fetchApi } from "./client";
import type {
  GroupRead,
  GroupCreate,
  GroupAdminUpdate,
  WorkspaceWithMembership,
  WorkspaceActivationRequest,
} from "./types";

/**
 * Get the user's currently active workspace
 */
export async function getCurrentWorkspace(authToken?: string): Promise<GroupRead> {
  return fetchApi<GroupRead>('/api/self/workspaces/current', {}, authToken);
}

/**
 * List all workspaces accessible to the current user
 * For SUPER_ADMIN: Returns all workspaces
 * For regular users: Returns only workspaces they're members of
 */
export async function listWorkspaces(authToken?: string): Promise<WorkspaceWithMembership[]> {
  return fetchApi<WorkspaceWithMembership[]>('/api/self/workspaces', {}, authToken);
}

/**
 * Activate a workspace (make it the current active workspace)
 */
export async function activateWorkspace(workspaceId: string, authToken?: string): Promise<GroupRead> {
  const body: WorkspaceActivationRequest = { workspace_id: workspaceId };
  return fetchApi<GroupRead>('/api/self/workspaces/current', {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  }, authToken);
}

/**
 * Create a new workspace (requires SUPER_ADMIN)
 */
export async function createWorkspace(data: GroupCreate): Promise<GroupRead> {
  return fetchApi<GroupRead>('/api/admin/groups', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
}

/**
 * Update workspace settings (requires ADMIN or OWNER)
 */
export async function updateWorkspace(id: string, data: GroupAdminUpdate): Promise<GroupRead> {
  return fetchApi<GroupRead>(`/api/admin/groups/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
}

/**
 * Delete a workspace (requires SUPER_ADMIN)
 */
export async function deleteWorkspace(id: string, force: boolean = false): Promise<void> {
  const queryParams = force ? '?force=true' : '';
  return fetchApi<void>(`/api/admin/groups/${id}${queryParams}`, {
    method: 'DELETE',
  });
}
