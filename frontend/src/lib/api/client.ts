import { getApiUrl, hasApiBackend, SITE_CLIENT_TOKEN } from "./config";

export class ApiRequestError extends Error {
  status: number;
  url: string;
  body?: unknown;

  constructor(message: string, status: number, url: string, body?: unknown) {
    super(message);
    this.name = "ApiRequestError";
    this.status = status;
    this.url = url;
    this.body = body;
  }
}

const DEV_MODE = import.meta.env.DEV;
const MAX_RETRIES = 2;
const RETRY_DELAY_MS = 1000;

/**
 * Sleep for specified milliseconds
 */
function sleep(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms));
}

/**
 * Check if error is retryable (network errors or 5xx)
 */
function isRetryable(error: unknown): boolean {
  if (error instanceof ApiRequestError) {
    return error.status >= 500;
  }
  return true; // Network errors are retryable
}

/**
 * Main API client function with retry logic and improved error handling
 */
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

  // Include credentials to send cookies with requests
  const fetchInit: RequestInit = {
    ...init,
    headers,
    credentials: 'include', // Send cookies with cross-origin requests
  };

  let lastError: Error | null = null;

  for (let attempt = 0; attempt <= MAX_RETRIES; attempt++) {
    try {
      if (DEV_MODE && attempt === 0) {
        console.debug(`[API] ${init.method || 'GET'} ${path}`);
      }

      const response = await fetch(url, fetchInit);

      // Handle 401 Unauthorized - redirect to login
      if (response.status === 401) {
        if (DEV_MODE) {
          console.warn('[API] 401 Unauthorized - user needs to login');
        }
        // In SSR context we can't redirect, throw error instead
        throw new ApiRequestError(
          'Unauthorized - please log in',
          response.status,
          url.toString()
        );
      }

      // Handle other errors
      if (!response.ok) {
        let errorBody;
        try {
          errorBody = await response.json();
        } catch {
          errorBody = await response.text();
        }

        const errorMessage = typeof errorBody === 'object' && errorBody !== null && 'detail' in errorBody
          ? String(errorBody.detail)
          : `API request failed with ${response.status}`;

        const error = new ApiRequestError(
          errorMessage,
          response.status,
          url.toString(),
          errorBody
        );

        // Retry on 5xx errors
        if (attempt < MAX_RETRIES && error.status >= 500) {
          if (DEV_MODE) {
            console.warn(`[API] Retrying after ${RETRY_DELAY_MS}ms (attempt ${attempt + 1}/${MAX_RETRIES})`);
          }
          await sleep(RETRY_DELAY_MS * (attempt + 1));
          continue;
        }

        throw error;
      }

      const data = await response.json() as T;

      if (DEV_MODE) {
        console.debug(`[API] ${init.method || 'GET'} ${path} -> OK`);
      }

      return data;

    } catch (error) {
      lastError = error instanceof Error ? error : new Error(String(error));

      // Don't retry on non-retryable errors
      if (!isRetryable(error)) {
        throw lastError;
      }

      // Don't retry on last attempt
      if (attempt === MAX_RETRIES) {
        throw lastError;
      }

      if (DEV_MODE) {
        console.warn(`[API] Request failed, retrying... (attempt ${attempt + 1}/${MAX_RETRIES})`);
      }

      await sleep(RETRY_DELAY_MS * (attempt + 1));
    }
  }

  throw lastError || new Error('Request failed after retries');
}
