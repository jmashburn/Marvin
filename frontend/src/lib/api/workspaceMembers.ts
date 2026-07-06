/**
 * Workspace Members API - manage workspace access and roles
 */

import { fetchApi } from "./client";
import type { WorkspaceMembershipRead, WorkspaceMemberCreate, WorkspaceMemberUpdate } from "./types";

/**
 * List all members of a workspace
 * Auth: Workspace ADMIN/OWNER required
 */
export async function listWorkspaceMembers(
  workspaceId: string,
  authToken?: string
): Promise<WorkspaceMembershipRead[]> {
  return fetchApi<WorkspaceMembershipRead[]>(
    `/api/platform/workspaces/${workspaceId}/members`,
    {},
    authToken
  );
}

/**
 * Add a user to a workspace with a specific role
 * Auth: Workspace ADMIN/OWNER required
 */
export async function addWorkspaceMember(
  workspaceId: string,
  data: WorkspaceMemberCreate,
  authToken?: string
): Promise<WorkspaceMembershipRead> {
  return fetchApi<WorkspaceMembershipRead>(
    `/api/platform/workspaces/${workspaceId}/members`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    },
    authToken
  );
}

/**
 * Get details of a specific workspace member
 * Auth: Any workspace member can view
 */
export async function getWorkspaceMember(
  workspaceId: string,
  userId: string,
  authToken?: string
): Promise<WorkspaceMembershipRead> {
  return fetchApi<WorkspaceMembershipRead>(
    `/api/platform/workspaces/${workspaceId}/members/${userId}`,
    {},
    authToken
  );
}

/**
 * Update a workspace member's role
 * Auth: Workspace ADMIN/OWNER required
 * Restrictions: Cannot change own role, cannot demote last OWNER
 */
export async function updateWorkspaceMemberRole(
  workspaceId: string,
  userId: string,
  data: WorkspaceMemberUpdate,
  authToken?: string
): Promise<WorkspaceMembershipRead> {
  return fetchApi<WorkspaceMembershipRead>(
    `/api/platform/workspaces/${workspaceId}/members/${userId}`,
    {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    },
    authToken
  );
}

/**
 * Remove a user from a workspace
 * Auth: Workspace ADMIN/OWNER required
 * Restrictions: Cannot remove yourself, cannot remove last OWNER
 */
export async function removeWorkspaceMember(
  workspaceId: string,
  userId: string,
  authToken?: string
): Promise<void> {
  return fetchApi<void>(
    `/api/platform/workspaces/${workspaceId}/members/${userId}`,
    { method: 'DELETE' },
    authToken
  );
}
