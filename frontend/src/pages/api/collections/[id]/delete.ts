import type { APIRoute } from 'astro';
import { deleteCollection } from '@/lib/api/collections';

export const POST: APIRoute = async ({ params, redirect }) => {
  try {
    const { id } = params;
    if (!id) throw new Error('Collection ID required');

    await deleteCollection(id);
    return redirect('/collections', 303);
  } catch (error) {
    console.error('[collections/delete] Error:', error);
    return new Response(JSON.stringify({ error: error instanceof Error ? error.message : 'Failed to delete collection' }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' }
    });
  }
};
