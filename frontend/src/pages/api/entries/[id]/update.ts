import type { APIRoute } from 'astro';
import { updateEntry } from '@/lib/api/entries';

export const POST: APIRoute = async ({ params, request, redirect }) => {
  try {
    const { id } = params;
    if (!id) throw new Error('Entry ID required');

    const formData = await request.formData();
    const updates: Record<string, unknown> = {};

    // Collect all form fields
    const fields = ['title', 'slug', 'entry_type_id', 'summary', 'description', 'content_markdown', 'status', 'published_at'];
    for (const field of fields) {
      const value = formData.get(field);
      if (value !== null) {
        updates[field] = value === '' ? null : value;
      }
    }

    await updateEntry(id, updates);
    return redirect(`/entries/${id}`, 303);
  } catch (error) {
    console.error('[entries/update] Error:', error);
    return new Response(JSON.stringify({ error: error instanceof Error ? error.message : 'Failed to update entry' }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' }
    });
  }
};
