/**
 * Notifications API
 * Migrated to use @inneropen/marvin-sdk
 */

import { createSdkClient } from '../sdk';
import type {
  Notification,
  NotificationCreate,
  NotificationUpdate,
} from '@inneropen/marvin-sdk/platform';

export type { Notification, NotificationCreate, NotificationUpdate };

/**
 * List all notifications in the workspace
 */
export async function listNotifications(authToken: string): Promise<Notification[]> {
  const sdk = createSdkClient(authToken);
  return sdk.notifications.list();
}

/**
 * Get a notification by ID
 */
export async function getNotification(id: string, authToken: string): Promise<Notification> {
  const sdk = createSdkClient(authToken);
  return sdk.notifications.get(id);
}

/**
 * Create a new notification
 */
export async function createNotification(data: NotificationCreate, authToken: string): Promise<Notification> {
  const sdk = createSdkClient(authToken);
  return sdk.notifications.create(data);
}

/**
 * Update a notification
 */
export async function updateNotification(id: string, data: NotificationUpdate, authToken: string): Promise<Notification> {
  const sdk = createSdkClient(authToken);
  return sdk.notifications.update(id, data);
}

/**
 * Delete a notification
 */
export async function deleteNotification(id: string, authToken: string): Promise<void> {
  const sdk = createSdkClient(authToken);
  return sdk.notifications.delete(id);
}

/**
 * Test a notification
 */
export async function testNotification(id: string, authToken: string): Promise<{ success: boolean; message?: string }> {
  const sdk = createSdkClient(authToken);
  return sdk.notifications.test(id);
}
