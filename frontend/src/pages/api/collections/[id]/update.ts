import type { APIRoute } from 'astro';
import { updateCollection } from '@/lib/api/collections';

export const POST: APIRoute = async ({ params, request, redirect }) => {
  try {
    const { id } = params;
    if (!id) throw new Error('Collection ID required');

    const formData = await request.formData();

    await updateCollection(id, {
      name: formData.get('name') as string,
      slug: formData.get('slug') as string,
      icon: (formData.get('icon') as string) || null,
      color: (formData.get('color') as string) || null,
      description: (formData.get('description') as string) || null,
      sort_order: parseInt(formData.get('sort_order') as string) || 0,
    });

    return redirect(`/collections/${id}`, 303);
  } catch (error) {
    console.error('[collections/update] Error:', error);
    return new Response(JSON.stringify({ error: error instanceof Error ? error.message : 'Failed to update collection' }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' }
    });
  }
};
