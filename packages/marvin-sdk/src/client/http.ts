/**
 * HTTP Client for Marvin API
 */

import type { MarvinConfig } from './config';

export class MarvinHttpClient {
  constructor(private config: MarvinConfig) {}

  async fetch<T>(endpoint: string): Promise<T> {
    const url = `${this.config.apiUrl}${endpoint}`;

    try {
      const response = await fetch(url, {
        headers: {
          'Authorization': `Bearer ${this.config.siteClientToken}`,
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(
          `Marvin API error: ${response.status} ${response.statusText} at ${endpoint}\n${errorText}`
        );
      }

      return await response.json();
    } catch (error) {
      if (error instanceof Error) {
        // Don't leak the token in error messages
        const safeMessage = error.message.replace(
          this.config.siteClientToken,
          '[REDACTED]'
        );
        throw new Error(safeMessage);
      }
      throw error;
    }
  }

  buildQueryString(params: Record<string, string | number | undefined>): string {
    const filtered = Object.entries(params)
      .filter(([_, value]) => value !== undefined)
      .map(([key, value]) => `${key}=${encodeURIComponent(String(value))}`);

    return filtered.length > 0 ? `?${filtered.join('&')}` : '';
  }
}
