import type { APIRoute } from 'astro';
import { getAuthToken } from '@/lib/api/client';
import { deleteEntry } from '@/lib/api/entries';

export const POST: APIRoute = async ({ params, redirect, cookies }) => {
  try {
    const { id } = params;
    if (!id) throw new Error('Entry ID required');

    const authToken = await getAuthToken(cookies);
    await deleteEntry(id, authToken);
    return redirect('/entries', 303);
  } catch (error) {
    console.error('[entries/delete] Error:', error);
    return new Response(JSON.stringify({ error: error instanceof Error ? error.message : 'Failed to delete entry' }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' }
    });
  }
};
