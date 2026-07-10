import type { APIRoute } from 'astro';
import { createSiteClient } from '@/lib/api/platform';
import { getAuthToken } from '@/lib/api/client';
import type { APIClientCreate } from '@/lib/api/types';

export const POST: APIRoute = async ({ request, cookies, redirect }) => {
  try {
    const formData = await request.formData();
    const authToken = getAuthToken(cookies);

    // Build create payload
    const data: APIClientCreate = {
      name: formData.get('name') as string,
      description: (formData.get('description') as string) || null,
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
