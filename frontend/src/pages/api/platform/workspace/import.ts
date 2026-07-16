import type { APIRoute } from 'astro';
import { getAuthToken } from '@/lib/api/client';
import { getApiUrl } from '@/lib/api/config';

export const POST: APIRoute = async ({ request, cookies }) => {
  const authToken = getAuthToken(cookies);

  if (!authToken) {
    return new Response(JSON.stringify({ error: 'Unauthorized' }), {
      status: 401,
      headers: { 'Content-Type': 'application/json' },
    });
  }

  const url = new URL(request.url);
  const overwrite = url.searchParams.get('overwrite') === 'true';
  const targetWorkspaceId = url.searchParams.get('target_workspace_id');

  const params = new URLSearchParams();
  if (overwrite) params.set('overwrite', 'true');
  if (targetWorkspaceId) params.set('target_workspace_id', targetWorkspaceId);
  const qs = params.toString() ? `?${params.toString()}` : '';

  const backendUrl = getApiUrl(`/api/platform/workspace/import${qs}`);

  const formData = await request.formData();

  const backendResponse = await fetch(backendUrl, {
    method: 'POST',
    headers: { Authorization: `Bearer ${authToken}` },
    body: formData,
  });

  const text = await backendResponse.text();
  return new Response(text, {
    status: backendResponse.status,
    headers: { 'Content-Type': 'application/json' },
  });
};
