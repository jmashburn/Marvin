/**
 * Workspaces API client - SDK wrapper
 * Migrated to use @inneropen/marvin-sdk
 */

import { createSdkClient } from '../sdk';
import type {
  PlatformWorkspace,
  PlatformWorkspaceCreate,
  PlatformWorkspaceUpdate,
} from '@inneropen/marvin-sdk/platform';

// Re-export SDK types with legacy names for backward compatibility
export type WorkspaceRead = PlatformWorkspace;
export type WorkspaceCreate = PlatformWorkspaceCreate;
export type WorkspaceUpdate = PlatformWorkspaceUpdate;

/**
 * List all workspaces the current user can access
 */
export async function listWorkspaces(authToken: string): Promise<WorkspaceRead[]> {
  const sdk = createSdkClient(authToken);
  return sdk.workspaces.list();
}

/**
 * Get a single workspace by ID
 */
export async function getWorkspace(id: string, authToken: string): Promise<WorkspaceRead> {
  const sdk = createSdkClient(authToken);
  return sdk.workspaces.get(id);
}

/**
 * Create a new workspace
 */
export async function createWorkspace(data: WorkspaceCreate, authToken: string): Promise<WorkspaceRead> {
  const sdk = createSdkClient(authToken);
  return sdk.workspaces.create(data);
}

/**
 * Update an existing workspace
 */
export async function updateWorkspace(id: string, data: WorkspaceUpdate, authToken: string): Promise<WorkspaceRead> {
  const sdk = createSdkClient(authToken);
  return sdk.workspaces.update(id, data);
}

/**
 * Delete a workspace
 */
export async function deleteWorkspace(id: string, authToken: string): Promise<void> {
  const sdk = createSdkClient(authToken);
  return sdk.workspaces.delete(id);
}

/**
 * Get the current active workspace
 * Note: This is determined by server-side session state
 */
export async function getCurrentWorkspace(authToken: string): Promise<WorkspaceRead> {
  const sdk = createSdkClient(authToken);
  return sdk.workspaces.getCurrent();
}

/**
 * Set the active workspace
 * Note: This updates server-side session state
 */
export async function setActiveWorkspace(slug: string, authToken: string): Promise<WorkspaceRead> {
  const sdk = createSdkClient(authToken);
  return sdk.workspaces.setActive(slug);
}
