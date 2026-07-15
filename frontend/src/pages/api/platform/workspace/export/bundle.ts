import type { APIRoute } from 'astro';
import { getAuthToken } from '@/lib/api/client';
import { getApiUrl } from '@/lib/api/config';

export const GET: APIRoute = async ({ cookies }) => {
  const authToken = getAuthToken(cookies);

  if (!authToken) {
    return new Response(JSON.stringify({ error: 'Unauthorized' }), {
      status: 401,
      headers: { 'Content-Type': 'application/json' },
    });
  }

  const backendUrl = getApiUrl('/api/platform/workspace/export/bundle');

  const backendResponse = await fetch(backendUrl, {
    headers: { Authorization: `Bearer ${authToken}` },
  });

  if (!backendResponse.ok) {
    const text = await backendResponse.text();
    return new Response(text, {
      status: backendResponse.status,
      headers: { 'Content-Type': 'application/json' },
    });
  }

  return new Response(backendResponse.body, {
    status: 200,
    headers: {
      'Content-Type': 'application/zip',
      'Content-Disposition': 'attachment; filename="workspace-export.zip"',
    },
  });
};
