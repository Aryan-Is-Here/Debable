"use client";

import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { SignInButton, useAuth } from "@clerk/nextjs";
import { AlertCircle, Loader2 } from "lucide-react";

import { AUTH_STALLED_HINT, useAuthReady } from "@/hooks/use-auth-ready";
import { Button } from "@/components/ui/button";
import { DebateRoomView } from "@/components/debate-room-view";
import { ApiError } from "@/services/api-client";
import { getRoom, matchKeys } from "@/services/match";

/**
 * Loads a real debate room by id, then hands it to the view.
 *
 * Client-side rather than a server fetch because the request needs the caller's Clerk
 * token: rooms are private to their two participants, and the backend enforces that with a
 * 403. Chat opens its own socket from inside the view, once the room is known.
 */
export function DebateRoomLoader({ roomId }: { roomId: string }) {
  const router = useRouter();
  const { getToken } = useAuth();
  const { isLoaded, isSignedIn, signedIn, stalled } = useAuthReady();

  const { data: room, isPending, isError, error } = useQuery({
    queryKey: matchKeys.room(roomId),
    queryFn: async () => getRoom(roomId, await getToken()),
    enabled: signedIn,
  });

  // Ahead of the signed-out branch: if Clerk never loads, `isLoaded` stays false and this
  // screen would otherwise spin forever with nothing explaining why.
  if (stalled) {
    return (
      <Centered>
        <AlertCircle className="size-8 text-destructive" />
        <p className="font-medium">Sign-in isn&apos;t loading</p>
        <p className="text-sm text-muted-foreground">{AUTH_STALLED_HINT}</p>
        <Button variant="outline" onClick={() => window.location.reload()}>
          Reload
        </Button>
      </Centered>
    );
  }

  if (isLoaded && !isSignedIn) {
    return (
      <Centered>
        <p className="font-medium">Sign in to join this debate</p>
        <p className="text-sm text-muted-foreground">
          Debate rooms are private to the two people in them.
        </p>
        <SignInButton mode="modal">
          <Button>Sign in</Button>
        </SignInButton>
      </Centered>
    );
  }

  if (isError) {
    const forbidden = error instanceof ApiError && error.status === 403;
    const missing = error instanceof ApiError && error.status === 404;
    return (
      <Centered>
        <AlertCircle className="size-8 text-destructive" />
        <p className="font-medium">
          {forbidden
            ? "This debate isn't yours"
            : missing
              ? "That debate doesn't exist"
              : "Couldn't load this debate"}
        </p>
        <p className="text-sm text-muted-foreground">
          {forbidden
            ? "Only the two people debating can open this room."
            : error instanceof Error
              ? error.message
              : "Something went wrong."}
        </p>
        <Button variant="outline" onClick={() => router.push("/browse")}>
          Back to browse
        </Button>
      </Centered>
    );
  }

  if (isPending || !room) {
    return (
      <Centered>
        <Loader2 className="size-8 animate-spin text-primary" />
        <p className="text-sm text-muted-foreground">Loading debate…</p>
      </Centered>
    );
  }

  return <DebateRoomView room={room} />;
}

function Centered({ children }: { children: React.ReactNode }) {
  return (
    <div className="mx-auto flex min-h-[70vh] w-full max-w-lg flex-col items-center justify-center gap-3 px-4 py-12 text-center">
      {children}
    </div>
  );
}
