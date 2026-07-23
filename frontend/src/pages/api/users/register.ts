import type { APIRoute } from "astro";
import { API_BASE_URL } from "@/lib/api/config";

export const POST: APIRoute = async ({ request }) => {
  try {
    const body = await request.json();

    // Call backend registration endpoint directly
    const response = await fetch(`${API_BASE_URL}/api/users/register`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(body),
    });

    if (!response.ok) {
      const errorData = await response.json();
      return new Response(JSON.stringify(errorData), {
        status: response.status,
        headers: {
          "Content-Type": "application/json",
        },
      });
    }

    const user = await response.json();

    return new Response(JSON.stringify(user), {
      status: 201,
      headers: {
        "Content-Type": "application/json",
      },
    });
  } catch (error: any) {
    console.error("[register] Error:", error);

    return new Response(JSON.stringify({ detail: error.message || "Registration failed" }), {
      status: 500,
      headers: {
        "Content-Type": "application/json",
      },
    });
  }
};
