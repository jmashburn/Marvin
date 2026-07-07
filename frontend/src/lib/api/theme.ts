/**
 * Theme API
 * Migrated to use @inneropen/marvin-sdk
 */

import { createSdkClient } from '../sdk';
import type { AppTheme } from '@inneropen/marvin-sdk/platform';

export type { AppTheme };

/**
 * Get application theme colors
 */
export async function getTheme(authToken: string): Promise<AppTheme> {
  const sdk = createSdkClient(authToken);
  return sdk.theme.getTheme();
}
