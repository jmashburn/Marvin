/**
 * Workspace settings API client
 */

import { fetchApi } from "./client";
import type { GroupRead, GroupAdminUpdate } from "./types";

/**
 * Get workspace settings
 */
export async function getWorkspaceSettings(workspaceId: string): Promise<GroupRead> {
  return fetchApi<GroupRead>(`/api/admin/groups/${workspaceId}`);
}

/**
 * Update workspace settings
 */
export async function updateWorkspaceSettings(workspaceId: string, data: GroupAdminUpdate): Promise<GroupRead> {
  return fetchApi<GroupRead>(`/api/admin/groups/${workspaceId}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
}
