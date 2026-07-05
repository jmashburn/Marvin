import type { APIRoute } from 'astro';
import { updateWorkspace } from '@/lib/api/workspaces';

export const POST: APIRoute = async ({ params, request, redirect }) => {
  try {
    const { id } = params;
    if (!id) throw new Error('Workspace ID required');

    const formData = await request.formData();

    await updateWorkspace(id, {
      id,
      name: formData.get('name') as string,
      preferences: {
        private_group: formData.get('private_group') === 'on',
        first_day_of_week: parseInt(formData.get('first_day_of_week') as string) || 0,
      },
    });

    return redirect('/settings/workspace', 303);
  } catch (error) {
    console.error('[workspaces/update] Error:', error);
    return new Response(JSON.stringify({ error: error instanceof Error ? error.message : 'Failed to update workspace' }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' }
    });
  }
};
