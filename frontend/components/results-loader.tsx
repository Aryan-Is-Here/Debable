"use client";

import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { SignInButton, useAuth } from "@clerk/nextjs";
import { AlertCircle, Loader2, Star } from "lucide-react";

import { AUTH_STALLED_HINT, useAuthReady } from "@/hooks/use-auth-ready";
import { Button } from "@/components/ui/button";
import { RatingForm } from "@/components/rating-form";
import { ApiError } from "@/services/api-client";
import { getRoom, matchKeys } from "@/services/match";
import { getRatingState, ratingKeys } from "@/services/ratings";

/**
 * Loads the real debate before showing the rating form.
 *
 * Until Phase 8 this screen rendered `mockDebateRoom` for **any** roomId, which made it the
 * most misleading mock left in the product: the form submitted, a toast appeared, and
 * nothing had been rated. Loading the room also means the backend's participant check
 * applies — a debate you were not in is a 403 rather than a form you can fill in.
 *
 * It also asks whether the caller has already rated, so a second visit shows the score they
 * gave instead of an empty form the server would refuse.
 */
export function ResultsLoader({ roomId }: { roomId: string }) {
  const router = useRouter();
  const { getToken } = useAuth();
  const { isLoaded, isSignedIn, signedIn, stalled } = useAuthReady();

  const room = useQuery({
    queryKey: matchKeys.room(roomId),
    queryFn: async () => getRoom(roomId, await getToken()),
    enabled: signedIn,
  });

  const rating = useQuery({
    queryKey: ratingKeys.state(roomId),
    queryFn: async () => getRatingState(roomId, await getToken()),
    enabled: signedIn,
  });

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
        <p className="font-medium">Sign in to rate this debate</p>
        <SignInButton mode="modal">
          <Button>Sign in</Button>
        </SignInButton>
      </Centered>
    );
  }

  const failure = room.error ?? rating.error;
  if (failure) {
    const forbidden = failure instanceof ApiError && failure.status === 403;
    return (
      <Centered>
        <AlertCircle className="size-8 text-destructive" />
        <p className="font-medium">
          {forbidden ? "This debate isn't yours" : "Couldn't load this debate"}
        </p>
        <p className="text-sm text-muted-foreground">
          {forbidden
            ? "Only the two people who debated can rate it."
            : failure instanceof Error
              ? failure.message
              : "Something went wrong."}
        </p>
        <Button variant="outline" onClick={() => router.push("/browse")}>
          Back to browse
        </Button>
      </Centered>
    );
  }

  if (!room.data || !rating.data) {
    return (
      <Centered>
        <Loader2 className="size-8 animate-spin text-primary" />
      </Centered>
    );
  }

  // Already rated: show what was given rather than a form that would be refused.
  if (rating.data.submitted && rating.data.rating) {
    const { score, comment } = rating.data.rating;
    return (
      <Centered>
        <div className="flex gap-1" aria-label={`You rated ${score} out of 5`}>
          {[1, 2, 3, 4, 5].map((value) => (
            <Star
              key={value}
              aria-hidden
              className={
                value <= score ? "size-6 fill-amber-400 text-amber-400" : "size-6 text-muted-foreground/40"
              }
            />
          ))}
        </div>
        <p className="font-medium">
          You rated {room.data.opponent.username} {score}/5
        </p>
        {comment && <p className="text-sm text-muted-foreground">“{comment}”</p>}
        <p className="text-sm text-muted-foreground">
          A debate can only be rated once, so this is final.
        </p>
        <Button variant="outline" onClick={() => router.push("/browse")}>
          Find another debate
        </Button>
      </Centered>
    );
  }

  return <RatingForm room={room.data} />;
}

function Centered({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center gap-3 text-center">
      {children}
    </div>
  );
}
