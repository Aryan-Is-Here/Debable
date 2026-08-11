import { clerkMiddleware } from "@clerk/nextjs/server";

/**
 * Attaches Clerk's auth context to every request.
 *
 * Named `proxy.ts` rather than `middleware.ts`: Next.js 16 deprecated the middleware file
 * convention in favour of this one.
 *
 * No routes are protected here on purpose: Browse and Home must work signed out, and the
 * only write endpoint is enforced by the backend, which is the boundary that actually
 * matters. Protecting routes here would hide the UI without securing anything.
 */
export default clerkMiddleware();

export const config = {
  matcher: [
    // Everything except Next internals and static files, unless they appear in a search param.
    "/((?!_next|[^?]*\\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest)).*)",
    "/(api|trpc)(.*)",
  ],
};
