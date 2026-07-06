/**
 * Authentication utilities for Astro pages
 */

import type { AstroCookies } from 'astro';
import { fetchApi } from './api/client';

export interface User {
  id: string;
  username: string;
  email?: string;
  admin?: boolean;
  groupId?: string;
}

/**
 * Check if user is authenticated and get current user data
 * @param cookies - Astro cookies object
 * @returns User data if authenticated, null otherwise
 */
export async function getCurrentUser(cookies: AstroCookies): Promise<User | null> {
  const token = cookies.get('marvin.access_token');

  if (!token?.value) {
    return null;
  }

  try {
    const user = await fetchApi<User>('/api/self', {}, token.value);
    return user;
  } catch (error) {
    // Token is invalid or expired
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

    return redirect(loginUrl);
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
    return redirect('/');
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
