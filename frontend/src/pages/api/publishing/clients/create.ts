import type { APIRoute } from 'astro';
import { createSiteClient } from '@/lib/api/platform';
import { getAuthToken } from '@/lib/api/client';
import type { APIClientCreate } from '@/lib/api/types';

export const POST: APIRoute = async ({ request, cookies, redirect }) => {
  try {
    const formData = await request.formData();
    const authToken = getAuthToken(cookies);

    // Build permissions object from checkboxes
    const permissions: Record<string, boolean> = {
      read_published_entries: formData.get('read_published_entries') === 'on',
      read_collections: formData.get('read_collections') === 'on',
      read_assets: formData.get('read_assets') === 'on',
      read_resources: formData.get('read_resources') === 'on',
    };

    // Build create payload
    const data: APIClientCreate = {
      name: formData.get('name') as string,
      slug: (formData.get('slug') as string) || null,
      description: (formData.get('description') as string) || null,
      permissions,
    };

    // Create via backend API
    const result = await createSiteClient(data, authToken);

    // Redirect with token in query params (will be shown in modal on clients page)
    return redirect(
      `/publishing/clients?token=${encodeURIComponent(result.token)}&client_name=${encodeURIComponent(result.name)}`,
      303
    );
  } catch (error) {
    console.error('[clients/create] Error:', error);
    // TODO: Better error handling - could pass error message in query params
    return redirect('/publishing/clients/new?error=true', 303);
  }
};
