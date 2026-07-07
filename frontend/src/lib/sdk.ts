/**
 * Marvin SDK Factory for Frontend
 *
 * Creates Platform API clients for use in Astro SSR contexts.
 * The SDK handles all HTTP communication, retry logic, and error handling.
 */

import { createPlatformClient } from '@inneropen/marvin-sdk/platform';
import type { PlatformClient } from '@inneropen/marvin-sdk/platform';
import { getApiUrl } from './api/config';

/**
 * Create a Platform API client for SSR contexts (Astro pages)
 *
 * @param authToken - User authentication token from Astro.cookies
 * @returns Configured Platform API client
 *
 * @example
 * ```typescript
 * // In an Astro page:
 * import { createSdkClient } from '../lib/sdk';
 * import { getAuthToken } from '../lib/api/client';
 *
 * const authToken = getAuthToken(Astro.cookies);
 * if (!authToken) throw new Error('Not authenticated');
 *
 * const sdk = createSdkClient(authToken);
 * const entries = await sdk.entries.list();
 * ```
 */
export function createSdkClient(authToken?: string): PlatformClient {
  // Get base API URL (strip any trailing path)
  const apiUrl = getApiUrl('');
  const baseUrl = (typeof apiUrl === 'string' ? apiUrl : apiUrl.toString()).replace(/\/+$/, '');

  return createPlatformClient({
    apiUrl: baseUrl,
    userToken: authToken,
    credentials: 'include', // Always include cookies for HttpOnly session
  });
}
