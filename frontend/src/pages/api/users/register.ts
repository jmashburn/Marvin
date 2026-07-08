import type { APIRoute } from 'astro';
import { API_BASE_URL } from '@/lib/api/config';

export const POST: APIRoute = async ({ request }) => {
  try {
    const body = await request.json();

    const backendUrl = `${API_BASE_URL}/users/register`;

    const response = await fetch(backendUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
    });

    const data = await response.json();

    if (!response.ok) {
      return new Response(JSON.stringify(data), {
        status: response.status,
        headers: {
          'Content-Type': 'application/json',
        },
      });
    }

    return new Response(JSON.stringify(data), {
      status: 201,
      headers: {
        'Content-Type': 'application/json',
      },
    });
  } catch (error) {
    console.error('[register] Error:', error);
    return new Response(JSON.stringify({ detail: 'Registration failed' }), {
      status: 500,
      headers: {
        'Content-Type': 'application/json',
      },
    });
  }
};
