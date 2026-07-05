export const API_BASE_URL = import.meta.env.MARVIN_API_URL?.replace(/\/$/, "") ?? "";
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
