/**
 * Login endpoint - proxies authentication to backend API
 */

import type { APIRoute } from 'astro';
import { API_BASE_URL } from '@/lib/api/config';

export const POST: APIRoute = async ({ request, cookies, redirect }) => {
  try {
    const formData = await request.formData();
    const username = formData.get('username');
    const password = formData.get('password');

    if (!username || !password) {
      return redirect('/login?error=missing', 303);
    }

    const backendUrl = `${API_BASE_URL}/api/auth/token`;
    console.log('[auth/login] Attempting login to:', backendUrl);
    console.log('[auth/login] API_BASE_URL:', API_BASE_URL);

    // Call backend /api/auth/token endpoint
    const response = await fetch(backendUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: new URLSearchParams({
        username: username.toString(),
        password: password.toString(),
      }),
    });

    if (!response.ok) {
      console.error('[auth/login] Backend auth failed:', response.status);
      return redirect('/login?error=invalid', 303);
    }

    const data = await response.json();
    const accessToken = data.access_token;

    if (!accessToken) {
      console.error('[auth/login] No access token in response');
      return redirect('/login?error=invalid', 303);
    }

    // Set the access token cookie (matching backend format)
    cookies.set('marvin.access_token', accessToken, {
      path: '/',
      httpOnly: true,
      secure: import.meta.env.PROD,
      sameSite: 'lax',
      maxAge: 60 * 60 * 24 * 7, // 7 days
    });

    // Successfully logged in, redirect to dashboard
    return redirect('/', 303);

  } catch (error) {
    console.error('[auth/login] Error:', error);
    return redirect('/login?error=server', 303);
  }
};
