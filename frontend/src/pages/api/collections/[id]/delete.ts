import type { APIRoute } from 'astro';
import { getAuthToken } from '@/lib/api/client';
import { deleteCollection } from '@/lib/api/collections';

export const POST: APIRoute = async ({ params, redirect, cookies }) => {
  try {
    const authToken = getAuthToken(cookies);
    if (!authToken) return new Response('Unauthorized', { status: 401 });
    const { id } = params;
    if (!id) throw new Error('Collection ID required');

    await deleteCollection(id, authToken);
    return redirect('/workspace/collections', 303);
  } catch (error) {
    console.error('[collections/delete] Error:', error);
    return new Response(JSON.stringify({ error: error instanceof Error ? error.message : 'Failed to delete collection' }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' }
    });
  }
};
