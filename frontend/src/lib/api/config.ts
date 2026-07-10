/**
 * Get API base URL from environment
 * Supports both PUBLIC_ prefixed vars (client-side) and server-side env vars
 */
function getApiBaseUrl(): string {
  // Try PUBLIC_ prefixed version first (client-side accessible)
  if (import.meta.env.PUBLIC_MARVIN_API_URL) {
    return import.meta.env.PUBLIC_MARVIN_API_URL.replace(/\/$/, "");
  }

  // Try unprefixed version (SSR only)
  if (import.meta.env.MARVIN_API_URL) {
    return import.meta.env.MARVIN_API_URL.replace(/\/$/, "");
  }

  // Fallback to localhost for development
  return "http://localhost:8080";
}

export const API_BASE_URL = getApiBaseUrl();
export const SITE_CLIENT_TOKEN = import.meta.env.MARVIN_SITE_CLIENT_TOKEN ?? "";

/**
 * Check if API backend is configured
 */
export function hasApiBackend(): boolean {
  return API_BASE_URL.length > 0;
}

/**
 * Construct full API URL from a path
 */
export function getApiUrl(path: string): URL {
  if (!hasApiBackend()) {
    throw new Error("MARVIN_API_URL is not configured.");
  }

  return new URL(path.replace(/^\//, ""), `${API_BASE_URL}/`);
}
