import type { APIRoute } from 'astro';
import { getAuthToken } from '@/lib/api/client';
import { updateWorkspace } from '@/lib/api/workspaces';

export const POST: APIRoute = async ({ params, request, redirect, cookies }) => {
  try {
    const { id } = params;
    if (!id) throw new Error('Workspace ID required');

    const formData = await request.formData();
    const authToken = await getAuthToken(cookies);

    await updateWorkspace(id, {
      name: formData.get('name') as string,
      // TODO: Re-add preferences support once SDK is updated
      // preferences: {
      //   private_group: formData.get('private_group') === 'on',
      //   first_day_of_week: parseInt(formData.get('first_day_of_week') as string) || 0,
      // },
    }, authToken);

    return redirect('/settings/workspace', 303);
  } catch (error) {
    console.error('[workspaces/update] Error:', error);
    return new Response(JSON.stringify({ error: error instanceof Error ? error.message : 'Failed to update workspace' }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' }
    });
  }
};
