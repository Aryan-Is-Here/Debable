"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { SignInButton, useAuth } from "@clerk/nextjs";
import { AlertCircle, Loader2, Users } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { initials } from "@/lib/utils";
import { ApiError } from "@/services/api-client";
import { getMatchState, joinQueue, leaveQueue, matchKeys } from "@/services/match";

/** How often to ask the server whether an opponent has turned up. */
const POLL_INTERVAL_MS = 2000;

interface WaitingRoomProps {
  /** Topic to queue for, from the `?topic=` query parameter. */
  topicId: string;
}

/**
 * Waiting Room.
 *
 * Joins the server-side matchmaking queue on mount, then polls until someone else picks
 * the same topic. Leaving the page or pressing Cancel withdraws from the queue — otherwise
 * a user who wandered off would sit there as a phantom opponent.
 */
export function WaitingRoom({ topicId }: WaitingRoomProps) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { isLoaded, isSignedIn, getToken } = useAuth();
  const [now, setNow] = useState(() => Date.now());
  // Guards the one-shot join. A ref rather than state because it must not cause a render,
  // and it is only ever read inside effects.
  const joinRequested = useRef(false);
  // Whether leaving this page should withdraw us from the queue.
  const shouldDequeue = useRef(false);

  const {
    mutate: requestJoin,
    isSuccess: hasJoined,
    error: joinError,
  } = useMutation({
    mutationFn: async () => joinQueue(topicId, await getToken()),
    onSuccess: (state) => {
      shouldDequeue.current = state.status === "queued";
      queryClient.setQueryData(matchKeys.state, state);
    },
  });

  const { data: state, isError, error } = useQuery({
    queryKey: matchKeys.state,
    queryFn: async ({ signal }) => getMatchState(await getToken(), signal),
    // Only poll once we are actually in the queue.
    enabled: hasJoined,
    refetchInterval: (query) =>
      query.state.data?.status === "queued" ? POLL_INTERVAL_MS : false,
  });

  // Join once, as soon as Clerk knows who we are.
  useEffect(() => {
    if (!isLoaded || !isSignedIn || joinRequested.current) return;
    joinRequested.current = true;
    requestJoin();
  }, [isLoaded, isSignedIn, requestJoin]);

  // Tick for the elapsed counter. setState lives in the interval callback, not the effect
  // body, so it doesn't trigger the cascading render the lint rule guards against.
  useEffect(() => {
    const timer = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(timer);
  }, []);

  // Withdraw if the user navigates away while still queued — otherwise they linger as a
  // phantom opponent someone else would be matched with.
  useEffect(() => {
    return () => {
      if (shouldDequeue.current) {
        void getToken().then((token) => leaveQueue(token).catch(() => undefined));
      }
    };
  }, [getToken]);

  async function cancel() {
    shouldDequeue.current = false;
    await leaveQueue(await getToken()).catch(() => undefined);
    queryClient.removeQueries({ queryKey: matchKeys.state });
    router.push("/browse");
  }

  if (isLoaded && !isSignedIn) {
    return (
      <Centered>
        <p className="font-medium">Sign in to find an opponent</p>
        <p className="text-sm text-muted-foreground">
          Matchmaking pairs you with a specific person, so we need to know who you are.
        </p>
        <SignInButton mode="modal">
          <Button>Sign in</Button>
        </SignInButton>
      </Centered>
    );
  }

  const failure = joinError ?? (isError ? error : null);
  if (failure) {
    return (
      <Centered>
        <AlertCircle className="size-8 text-destructive" />
        <p className="font-medium">Couldn&apos;t join the queue</p>
        <p className="text-sm text-muted-foreground">
          {failure instanceof ApiError ? failure.message : "Something went wrong."}
        </p>
        <Button variant="outline" onClick={() => router.push("/browse")}>
          Back to browse
        </Button>
      </Centered>
    );
  }

  const topic = state?.topic ?? state?.room?.topic;
  const matched = state?.status === "matched" ? state.room : null;
  const elapsed = state?.queuedAt
    ? Math.max(0, Math.floor((now - new Date(state.queuedAt).getTime()) / 1000))
    : 0;

  return (
    <div className="mx-auto flex min-h-[70vh] w-full max-w-lg flex-col items-center justify-center gap-8 px-4 py-12 text-center">
      {topic && (
        <div className="space-y-2">
          <Badge variant="outline">{topic.category}</Badge>
          <h1 className="text-balance text-2xl font-semibold tracking-tight">{topic.title}</h1>
        </div>
      )}

      {!matched ? (
        <>
          <div className="flex flex-col items-center gap-4">
            <Loader2 className="size-10 animate-spin text-primary" />
            <div>
              <p className="font-medium">Finding you an opponent…</p>
              <p className="text-sm text-muted-foreground">
                Searching for someone to argue the other side · {elapsed}s
              </p>
              {state && state.waitingCount > 1 && (
                <p className="mt-1 text-sm text-muted-foreground">
                  {state.waitingCount} people waiting on this topic
                </p>
              )}
            </div>
          </div>
          <Button variant="ghost" onClick={cancel}>
            Cancel
          </Button>
        </>
      ) : (
        <>
          <div className="flex flex-col items-center gap-4">
            <Avatar className="size-16">
              {matched.opponent.avatarUrl && (
                <AvatarImage src={matched.opponent.avatarUrl} alt="" />
              )}
              <AvatarFallback>{initials(matched.opponent.username)}</AvatarFallback>
            </Avatar>
            <div>
              <p className="inline-flex items-center gap-1.5 font-medium">
                <Users className="size-4 text-primary" />
                Opponent found
              </p>
              <p className="text-sm text-muted-foreground">
                Matched with {matched.opponent.username}
              </p>
            </div>
          </div>
          <Button
            size="lg"
            onClick={() => {
              // Already in a room — the unmount cleanup must not dequeue anything.
              shouldDequeue.current = false;
              router.push(`/debate/${matched.id}`);
            }}
          >
            Enter debate
          </Button>
        </>
      )}
    </div>
  );
}

function Centered({ children }: { children: React.ReactNode }) {
  return (
    <div className="mx-auto flex min-h-[70vh] w-full max-w-lg flex-col items-center justify-center gap-3 px-4 py-12 text-center">
      {children}
    </div>
  );
}
