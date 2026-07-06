import type { APIRoute } from 'astro';
import { createEntryType } from '@/lib/api/entryTypes';

export const POST: APIRoute = async ({ request, redirect }) => {
  try {
    const formData = await request.formData();

    await createEntryType({
      name: formData.get('name') as string,
      // slug is auto-generated from name on the backend
      icon: (formData.get('icon') as string) || null,
      color: (formData.get('color') as string) || null,
      description: (formData.get('description') as string) || null,
      sort_order: parseInt(formData.get('sort_order') as string) || 0,
    });

    return redirect('/entry-types', 303);
  } catch (error) {
    console.error('[entry-types/create] Error:', error);
    return new Response(JSON.stringify({ error: error instanceof Error ? error.message : 'Failed to create entry type' }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' }
    });
  }
};
