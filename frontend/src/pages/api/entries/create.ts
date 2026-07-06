import type { APIRoute } from 'astro';
import { createEntry } from '@/lib/api/entries';

export const POST: APIRoute = async ({ request, redirect }) => {
  try {
    const formData = await request.formData();

    const entry = await createEntry({
      entry_type_id: formData.get('entry_type_id') as string,
      title: formData.get('title') as string,
      // slug is auto-generated from title on the backend
      summary: (formData.get('summary') as string) || null,
      description: (formData.get('description') as string) || null,
      status: (formData.get('status') as string) || 'draft',
    });

    return redirect(`/entries/${entry.id}`, 303);
  } catch (error) {
    console.error('[entries/create] Error:', error);
    return new Response(JSON.stringify({ error: error instanceof Error ? error.message : 'Failed to create entry' }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' }
    });
  }
};
