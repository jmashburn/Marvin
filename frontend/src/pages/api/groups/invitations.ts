import type { APIRoute } from 'astro';
import { API_BASE_URL } from '@/lib/api/config';

export const POST: APIRoute = async ({ request, cookies }) => {
  try {
    const body = await request.json();
    const authToken = cookies.get('marvin.access_token')?.value;

    if (!authToken) {
      return new Response(JSON.stringify({ detail: 'Not authenticated' }), {
        status: 401,
        headers: {
          'Content-Type': 'application/json',
        },
      });
    }

    const backendUrl = `${API_BASE_URL}/api/groups/invitations`;

    const response = await fetch(backendUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${authToken}`,
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
    console.error('[invitations] Error:', error);
    return new Response(JSON.stringify({ detail: 'Failed to create invitation' }), {
      status: 500,
      headers: {
        'Content-Type': 'application/json',
      },
    });
  }
};
