import type { APIRoute } from 'astro';
import { createAuthClient } from '@inneropen/marvin-sdk';
import { API_BASE_URL } from '@/lib/api/config';

export const POST: APIRoute = async ({ request }) => {
  try {
    const body = await request.json();

    const authClient = createAuthClient(API_BASE_URL);
    const user = await authClient.register(body);

    return new Response(JSON.stringify(user), {
      status: 201,
      headers: {
        'Content-Type': 'application/json',
      },
    });
  } catch (error: any) {
    console.error('[register] Error:', error);

    // Return error from SDK if available
    const errorResponse = error.body || { detail: error.message || 'Registration failed' };
    const status = error.status || 500;

    return new Response(JSON.stringify(errorResponse), {
      status,
      headers: {
        'Content-Type': 'application/json',
      },
    });
  }
};
