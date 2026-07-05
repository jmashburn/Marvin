import { getApiUrl, hasApiBackend, SITE_CLIENT_TOKEN } from "./config";

export class ApiRequestError extends Error {
  status: number;
  url: string;

  constructor(message: string, status: number, url: string) {
    super(message);
    this.name = "ApiRequestError";
    this.status = status;
    this.url = url;
  }
}

export async function fetchApi<T>(path: string, init: RequestInit = {}): Promise<T> {
  if (!hasApiBackend()) {
    throw new Error("MARVIN_API_URL is not configured.");
  }

  const url = getApiUrl(path);
  const headers = new Headers(init.headers);
  headers.set("Accept", "application/json");

  if (SITE_CLIENT_TOKEN && !headers.has("Authorization")) {
    headers.set("Authorization", `Bearer ${SITE_CLIENT_TOKEN}`);
  }

  const response = await fetch(url, {
    ...init,
    headers,
  });

  if (!response.ok) {
    throw new ApiRequestError(`API request failed with ${response.status}`, response.status, url.toString());
  }

  return response.json() as Promise<T>;
}
