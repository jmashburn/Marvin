/**
 * Marvin SDK Configuration
 */

export interface MarvinConfig {
  apiUrl: string;
  siteClientToken: string;
  workspaceSlug: string;
  /** Enable automatic initialization on client creation */
  autoInitialize?: boolean;
  /** Cache duration in milliseconds (default: 5 minutes) */
  cacheDuration?: number;
}

export function validateConfig(config: MarvinConfig): void {
  if (!config.apiUrl) {
    throw new Error('MARVIN_API_URL is required');
  }
  if (!config.siteClientToken) {
    throw new Error('MARVIN_SITE_CLIENT_TOKEN is required');
  }
  if (!config.workspaceSlug) {
    throw new Error('MARVIN_WORKSPACE_SLUG is required');
  }
}

export function createConfigFromEnv(overrides?: Partial<MarvinConfig>): MarvinConfig {
  return {
    apiUrl: overrides?.apiUrl || process.env.MARVIN_API_URL || '',
    siteClientToken: overrides?.siteClientToken || process.env.MARVIN_SITE_CLIENT_TOKEN || '',
    workspaceSlug: overrides?.workspaceSlug || process.env.MARVIN_WORKSPACE_SLUG || '',
    autoInitialize: overrides?.autoInitialize ?? false,
    cacheDuration: overrides?.cacheDuration ?? 5 * 60 * 1000, // 5 minutes
  };
}
