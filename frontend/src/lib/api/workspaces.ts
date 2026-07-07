/**
 * Workspace management API client
 * Note: SDK doesn't have workspaces module yet, using direct API calls
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
export async function getCurrentWorkspace(authToken: string): Promise<GroupRead> {
  return fetchApi<GroupRead>('/api/self/workspaces/current', {}, authToken);
}

/**
 * List all workspaces accessible to the current user
 * For SUPER_ADMIN: Returns all workspaces
 * For regular users: Returns only workspaces they're members of
 */
export async function listWorkspaces(authToken: string): Promise<WorkspaceWithMembership[]> {
  return fetchApi<WorkspaceWithMembership[]>('/api/self/workspaces', {}, authToken);
}

/**
 * Activate a workspace (make it the current active workspace)
 */
export async function activateWorkspace(workspaceId: string, authToken: string): Promise<GroupRead> {
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
export async function createWorkspace(data: GroupCreate, authToken: string): Promise<GroupRead> {
  return fetchApi<GroupRead>('/api/admin/groups', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  }, authToken);
}

/**
 * Update workspace settings (requires ADMIN or OWNER)
 */
export async function updateWorkspace(id: string, data: GroupAdminUpdate, authToken: string): Promise<GroupRead> {
  return fetchApi<GroupRead>(`/api/admin/groups/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  }, authToken);
}

/**
 * Delete a workspace (requires SUPER_ADMIN)
 */
export async function deleteWorkspace(id: string, authToken: string, force: boolean = false): Promise<void> {
  const queryParams = force ? '?force=true' : '';
  return fetchApi<void>(`/api/admin/groups/${id}${queryParams}`, {
    method: 'DELETE',
  }, authToken);
}

// Type re-exports for compatibility (these are not from SDK)
export type WorkspaceRead = GroupRead;
export type WorkspaceCreate = GroupCreate;
export type WorkspaceUpdate = GroupAdminUpdate;

/**
 * Get a single workspace by ID
 */
export async function getWorkspace(id: string, authToken: string): Promise<WorkspaceRead> {
  return fetchApi<GroupRead>(`/api/admin/groups/${id}`, {}, authToken);
}

/**
 * Set the active workspace
 */
export async function setActiveWorkspace(slug: string, authToken: string): Promise<WorkspaceRead> {
  // This uses workspace ID, not slug - need to find workspace by slug first
  const workspaces = await listWorkspaces(authToken);
  const workspace = workspaces.find(w => w.workspace.slug === slug);
  if (!workspace) {
    throw new Error(`Workspace with slug "${slug}" not found`);
  }
  return activateWorkspace(workspace.workspace.id, authToken);
}
