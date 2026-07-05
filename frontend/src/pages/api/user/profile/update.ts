import type { APIRoute } from 'astro';
import { fetchApi, getAuthToken } from '@/lib/api/client';

export const POST: APIRoute = async ({ request, cookies, redirect }) => {
  try {
    const formData = await request.formData();
    const authToken = getAuthToken(cookies);

    await fetchApi(`/api/users/${formData.get('user_id')}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        full_name: formData.get('full_name'),
        email: formData.get('email'),
        username: formData.get('username'),
      }),
    }, authToken);

    return redirect('/user/profile?success=true', 303);
  } catch (error) {
    return redirect('/user/profile?error=true', 303);
  }
};
