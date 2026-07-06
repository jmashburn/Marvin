/**
 * Client-side authentication helper
 * Reads auth token from cookies in browser JavaScript
 */
export function getAuthToken(): string | undefined {
  if (typeof document === 'undefined') {
    // Not in browser context
    return undefined;
  }

  const cookies = document.cookie.split(';');
  const authCookie = cookies.find(c => c.trim().startsWith('marvin.access_token='));

  if (!authCookie) {
    return undefined;
  }

  return authCookie.split('=')[1];
}
