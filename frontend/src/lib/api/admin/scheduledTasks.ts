/**
 * Admin Scheduled Tasks API - manage system and workspace tasks
 */

import { fetchApi } from '../client';

export interface ScheduledTaskRead {
  id: string;
  group_id: string | null;
  name: string;
  slug: string;
  description: string | null;
  enabled: boolean;
  schedule_type: string;
  schedule_config: Record<string, any>;
  task_type: string;
  task_config: Record<string, any>;
  last_run_at: string | null;
  next_run_at: string | null;
  last_status: string | null;
  last_duration_ms: number | null;
  failure_count: number;
}

export interface ScheduledTaskCreate {
  name: string;
  description?: string | null;
  task_type: string;
  task_config?: Record<string, any>;
  schedule_type: string;
  schedule_config: Record<string, any>;
  enabled?: boolean;
}

export interface ScheduledTaskUpdate {
  name?: string;
  description?: string | null;
  task_type?: string;
  task_config?: Record<string, any>;
  schedule_type?: string;
  schedule_config?: Record<string, any>;
  enabled?: boolean;
}

export interface ScheduledTaskExecutionLogRead {
  id: string;
  task_id: string;
  group_id: string | null;
  executed_at: string;
  status: string;
  duration_ms: number | null;
  error_message: string | null;
  retry_attempt: number;
}

export async function listAllTasks(authToken?: string): Promise<ScheduledTaskRead[]> {
  return fetchApi<ScheduledTaskRead[]>(
    '/api/admin/scheduled-tasks',
    { method: 'GET' },
    authToken
  );
}

export async function createSystemTask(
  data: ScheduledTaskCreate,
  authToken?: string
): Promise<ScheduledTaskRead> {
  return fetchApi<ScheduledTaskRead>(
    '/api/admin/scheduled-tasks',
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    },
    authToken
  );
}

export async function getSystemTask(id: string, authToken?: string): Promise<ScheduledTaskRead> {
  return fetchApi<ScheduledTaskRead>(
    `/api/admin/scheduled-tasks/${id}`,
    { method: 'GET' },
    authToken
  );
}

export async function updateSystemTask(
  id: string,
  data: ScheduledTaskUpdate,
  authToken?: string
): Promise<ScheduledTaskRead> {
  return fetchApi<ScheduledTaskRead>(
    `/api/admin/scheduled-tasks/${id}`,
    {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    },
    authToken
  );
}

export async function deleteSystemTask(id: string, authToken?: string): Promise<void> {
  await fetchApi<void>(
    `/api/admin/scheduled-tasks/${id}`,
    { method: 'DELETE' },
    authToken
  );
}

export async function executeSystemTask(
  id: string,
  authToken?: string
): Promise<{ message: string }> {
  return fetchApi<{ message: string }>(
    `/api/admin/scheduled-tasks/${id}/execute`,
    { method: 'POST' },
    authToken
  );
}

export async function getSystemTaskHistory(
  id: string,
  limit = 50,
  authToken?: string
): Promise<ScheduledTaskExecutionLogRead[]> {
  return fetchApi<ScheduledTaskExecutionLogRead[]>(
    `/api/admin/scheduled-tasks/${id}/history?limit=${limit}`,
    { method: 'GET' },
    authToken
  );
}

export async function getGlobalLog(
  limit = 100,
  authToken?: string
): Promise<ScheduledTaskExecutionLogRead[]> {
  return fetchApi<ScheduledTaskExecutionLogRead[]>(
    `/api/admin/scheduled-tasks/log?limit=${limit}`,
    { method: 'GET' },
    authToken
  );
}
