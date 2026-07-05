export const API_BASE_URL = import.meta.env.MARVIN_API_URL?.replace(/\/$/, "") ?? "";
export const GROUP_SLUG = import.meta.env.MARVIN_GROUP_SLUG ?? "home";
export const SITE_CLIENT_TOKEN = import.meta.env.MARVIN_SITE_CLIENT_TOKEN ?? "";

export function hasApiBackend() {
  return API_BASE_URL.length > 0;
}

export function getApiUrl(path: string) {
  if (!hasApiBackend()) {
    throw new Error("MARVIN_API_URL is not configured.");
  }

  return new URL(path.replace(/^\//, ""), `${API_BASE_URL}/`);
}
