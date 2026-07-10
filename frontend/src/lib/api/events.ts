/**
 * Events API
 * Migrated to use @inneropen/marvin-sdk
 */

import { createSdkClient } from '../sdk';
import type { EventOption } from '@inneropen/marvin-sdk/platform';

export type { EventOption };

/**
 * Get available event types for webhooks and notifications
 */
export async function getEventOptions(authToken: string): Promise<EventOption[]> {
  const sdk = createSdkClient(authToken);
  return sdk.events.getOptions();
}
