import { defineMiddleware } from "astro:middleware";

/**
 * Turn a Response thrown during page rendering into that Response.
 *
 * The auth helpers signal "stop rendering, go here instead" by throwing the result of
 * Astro.redirect (see requireAuth in lib/auth.ts). Astro only unwraps a thrown Response in
 * endpoints and actions — thrown out of .astro frontmatter it is just an unhandled error, so
 * every protected page answered 500 instead of redirecting to /login. Catching it here keeps
 * the throw-to-redirect idiom working at all ~25 call sites.
 */
export const onRequest = defineMiddleware(async (_context, next) => {
  try {
    return await next();
  } catch (error) {
    if (error instanceof Response) {
      return error;
    }
    throw error;
  }
});
