/**
 * Authentication utilities for Astro pages
 */

import type { AstroCookies } from 'astro';
import type { UserProfile } from '@inneropen/marvin-sdk/platform';
import { createSdkClient } from './sdk';
import { getAuthToken } from './api/client';

export type User = UserProfile;

/**
 * Check if user is authenticated and get current user data
 * @param cookies - Astro cookies object
 * @returns User data if authenticated, null otherwise
 */
export async function getCurrentUser(cookies: AstroCookies): Promise<User | null> {
  const token = getAuthToken(cookies);

  if (!token) {
    return null;
  }

  try {
    const sdk = createSdkClient(token);
    return await sdk.user.getProfile();
  } catch (error) {
    return null;
  }
}

/**
 * Require authentication - redirect to login if not authenticated
 * Use this at the top of protected pages
 *
 * @param cookies - Astro cookies object
 * @param redirect - Astro redirect function
 * @param currentPath - Current page path (for redirect after login)
 * @returns User data if authenticated, never returns if not authenticated
 *
 * @example
 * ```astro
 * ---
 * import { requireAuth } from '@/lib/auth';
 * const user = await requireAuth(Astro.cookies, Astro.redirect, Astro.url.pathname);
 * ---
 * ```
 */
export async function requireAuth(
  cookies: AstroCookies,
  redirect: (path: string) => Response,
  currentPath?: string
): Promise<User> {
  const user = await getCurrentUser(cookies);

  if (!user) {
    // Build login URL with return path
    const loginUrl = currentPath && currentPath !== '/'
      ? `/login?return=${encodeURIComponent(currentPath)}`
      : '/login';

    redirect(loginUrl);
    // TypeScript doesn't know redirect throws, so add a return that never executes
    throw new Error('Redirect should have thrown');
  }

  return user;
}

/**
 * Require admin authentication - redirect to home if not admin
 *
 * @param cookies - Astro cookies object
 * @param redirect - Astro redirect function
 * @param currentPath - Current page path (for redirect after login)
 * @returns User data if authenticated admin, never returns otherwise
 *
 * @example
 * ```astro
 * ---
 * import { requireAdmin } from '@/lib/auth';
 * const user = await requireAdmin(Astro.cookies, Astro.redirect, Astro.url.pathname);
 * ---
 * ```
 */
export async function requireAdmin(
  cookies: AstroCookies,
  redirect: (path: string) => Response,
  currentPath?: string
): Promise<User> {
  const user = await requireAuth(cookies, redirect, currentPath);

  if (!user.admin) {
    redirect('/');
    // TypeScript doesn't know redirect throws, so add a return that never executes
    throw new Error('Redirect should have thrown');
  }

  return user;
}

/**
 * Check if user is authenticated (returns boolean)
 * Use this for conditional rendering or optional auth
 *
 * @param cookies - Astro cookies object
 * @returns true if authenticated, false otherwise
 */
export async function isAuthenticated(cookies: AstroCookies): Promise<boolean> {
  const user = await getCurrentUser(cookies);
  return user !== null;
}

/**
 * Check if user is admin (returns boolean)
 *
 * @param cookies - Astro cookies object
 * @returns true if authenticated and admin, false otherwise
 */
export async function isAdmin(cookies: AstroCookies): Promise<boolean> {
  const user = await getCurrentUser(cookies);
  return user?.admin === true;
}
