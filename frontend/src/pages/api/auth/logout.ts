/**
 * Logout endpoint - clears authentication cookie
 */

import type { APIRoute } from "astro";

export const POST: APIRoute = async ({ cookies, redirect }) => {
  // Delete the access token cookie
  cookies.delete("marvin.access_token", {
    path: "/",
  });

  // Redirect to login page
  return redirect("/login", 303);
};
