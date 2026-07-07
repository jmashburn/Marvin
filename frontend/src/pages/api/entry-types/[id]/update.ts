import type { APIRoute } from 'astro';
import { getAuthToken } from '@/lib/api/client';
import { updateEntryType } from '@/lib/api/entryTypes';

export const POST: APIRoute = async ({ params, request, redirect, cookies }) => {
  try {
    const { id } = params;
    if (!id) throw new Error('Entry type ID required');

    const formData = await request.formData();
    const authToken = await getAuthToken(cookies);

    await updateEntryType(id, {
      name: formData.get('name') as string,
      // slug is auto-regenerated from name on the backend
      icon: (formData.get('icon') as string) || undefined,
      color: (formData.get('color') as string) || undefined,
      description: (formData.get('description') as string) || undefined,
      sortOrder: parseInt(formData.get('sort_order') as string) || 0,
    }, authToken);

    return redirect('/entry-types', 303);
  } catch (error) {
    console.error('[entry-types/update] Error:', error);
    return new Response(JSON.stringify({ error: error instanceof Error ? error.message : 'Failed to update entry type' }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' }
    });
  }
};
