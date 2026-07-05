/**
 * Workspace activation endpoint
 * Handles POST requests to switch the active workspace
 */

import type { APIRoute } from 'astro';
import { activateWorkspace } from '@/lib/api/workspaces';

export const POST: APIRoute = async ({ request, redirect }) => {
  try {
    const formData = await request.formData();
    const workspaceId = formData.get('workspace_id');

    if (!workspaceId || typeof workspaceId !== 'string') {
      return new Response(
        JSON.stringify({ error: 'workspace_id is required' }),
        {
          status: 400,
          headers: { 'Content-Type': 'application/json' }
        }
      );
    }

    // Activate the workspace via backend API
    await activateWorkspace(workspaceId);

    // Redirect to dashboard to refresh with new workspace data
    return redirect('/', 303);

  } catch (error) {
    console.error('[workspace/activate] Error:', error);

    const message = error instanceof Error ? error.message : 'Failed to activate workspace';

    return new Response(
      JSON.stringify({ error: message }),
      {
        status: 500,
        headers: { 'Content-Type': 'application/json' }
      }
    );
  }
};
