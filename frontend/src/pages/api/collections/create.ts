import type { APIRoute } from 'astro';
import { createCollection } from '@/lib/api/collections';

export const POST: APIRoute = async ({ request, redirect }) => {
  try {
    const formData = await request.formData();

    await createCollection({
      name: formData.get('name') as string,
      slug: formData.get('slug') as string,
      icon: (formData.get('icon') as string) || null,
      color: (formData.get('color') as string) || null,
      description: (formData.get('description') as string) || null,
      sort_order: parseInt(formData.get('sort_order') as string) || 0,
      is_smart: formData.get('is_smart') === 'true',
    });

    return redirect('/collections', 303);
  } catch (error) {
    console.error('[collections/create] Error:', error);
    return new Response(JSON.stringify({ error: error instanceof Error ? error.message : 'Failed to create collection' }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' }
    });
  }
};
