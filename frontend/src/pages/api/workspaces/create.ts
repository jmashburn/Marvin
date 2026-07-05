import type { APIRoute } from 'astro';
import { createWorkspace, activateWorkspace } from '@/lib/api/workspaces';

export const POST: APIRoute = async ({ request, redirect }) => {
  try {
    const formData = await request.formData();

    const workspace = await createWorkspace({
      name: formData.get('name') as string,
    });

    // Auto-activate the new workspace
    await activateWorkspace(workspace.id);

    return redirect('/', 303);
  } catch (error) {
    console.error('[workspaces/create] Error:', error);
    return new Response(JSON.stringify({ error: error instanceof Error ? error.message : 'Failed to create workspace' }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' }
    });
  }
};
