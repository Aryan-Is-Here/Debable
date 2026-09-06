"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@clerk/nextjs";

/**
 * How long to wait for Clerk before deciding it is not coming.
 *
 * Generous: on a cold load with a slow connection, Clerk can legitimately take a few
 * seconds, and warning someone whose sign-in was merely slow is its own bug. This only has
 * to be shorter than a person's patience with a spinner that never resolves.
 */
const STALL_AFTER_MS = 8000;

export interface AuthReady {
  isLoaded: boolean;
  isSignedIn: boolean | undefined;
  /** Convenience for the common gate: definitely loaded, definitely signed in. */
  signedIn: boolean;
  /** Clerk never finished loading. Almost always a misconfigured origin — see below. */
  stalled: boolean;
}

/**
 * Clerk's auth state, plus the case Clerk itself does not report: never loading at all.
 *
 * `useAuth` has two honest states — loading, and loaded-with-an-answer — and no way to say
 * "this is not going to load". So a component written as
 * `!isLoaded ? spinner : isSignedIn ? app : signIn` renders a spinner **forever** when
 * something upstream is wrong, with no route to an explanation.
 *
 * That is not hypothetical. Opening the app on a LAN address (`172.16.0.2:3000`) rather
 * than `localhost:3000` leaves Clerk permanently unloaded, because a development instance is
 * bound to specific origins. The symptoms were an eternal spinner in the waiting room, a
 * header with neither an avatar nor a sign-in button, and a matchmaking poll that never ran
 * — three mysteries, one cause, and nothing on screen connecting them.
 *
 * The waiting room's dev readout made that *diagnosable*; this makes it *self-explaining*,
 * which is what `docs/PROJECT-HANDBOOK.md` §5.16 is actually asking for.
 */
export function useAuthReady(): AuthReady {
  const { isLoaded, isSignedIn } = useAuth();
  // Only ever set true, never reset. `stalled` is *derived* from it below, so a late arrival
  // clears the warning on its own — clearing this in an effect would be a synchronous
  // setState in an effect body, which is the lint rule in `docs/PROJECT-HANDBOOK.md` §5.3
  // and a real cause of cascading renders.
  const [timedOut, setTimedOut] = useState(false);

  useEffect(() => {
    if (isLoaded) return;

    const timer = setTimeout(() => setTimedOut(true), STALL_AFTER_MS);
    return () => clearTimeout(timer);
    // Depends on `isLoaded` alone. `useAuth`'s other values change identity as the session
    // settles, and an effect restarting on those would reset the timer forever — the shape
    // of trap that had the waiting room withdrawing itself from the queue in Phase 4.
  }, [isLoaded]);

  return {
    isLoaded,
    isSignedIn,
    signedIn: isLoaded && isSignedIn === true,
    stalled: !isLoaded && timedOut,
  };
}

/**
 * What to tell someone whose sign-in never loaded.
 *
 * The real cause is nearly always the address they opened, but that is only actionable in
 * development — in production the origin is whatever it is, and the useful advice is to
 * reload. So the specific hint is dev-only rather than a permanent lie.
 */
export const AUTH_STALLED_HINT =
  process.env.NODE_ENV === "development"
    ? "Sign-in is configured for http://localhost:3000 — check the address you opened. A LAN address or 127.0.0.1 will not work."
    : "Check your connection and reload the page.";
