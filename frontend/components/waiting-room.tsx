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

/** How many times to re-join if we find ourselves unexpectedly out of the queue. */
const MAX_REJOIN_ATTEMPTS = 3;

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
  const rejoinAttempts = useRef(0);

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

  const {
    data: state,
    isError,
    error,
    dataUpdatedAt,
    errorUpdatedAt,
    fetchStatus,
    refetch,
  } = useQuery({
    queryKey: matchKeys.state,
    queryFn: async ({ signal }) => getMatchState(await getToken(), signal),
    enabled: hasJoined,
    // Deliberately no refetchInterval. The declarative interval never fired on this screen
    // and three isolated reproductions failed to explain why — its behaviour depends on the
    // interaction of `enabled`, staleTime, window focus and a cache seeded before the query
    // was enabled. This loop is the one thing on the screen that must not silently stop
    // working, so it is driven explicitly below where the behaviour is plain to read.
    refetchOnWindowFocus: true,
    staleTime: 0,
  });

  const matched = state?.status === "matched" ? state.room : null;

  // The poll loop. Also the server-side heartbeat that keeps our queue entry alive, so it
  // runs until we are actually matched. refetch() always hits the network, regardless of
  // staleness.
  useEffect(() => {
    if (!hasJoined || matched) return;
    const poll = () => void refetch();
    const timer = setInterval(poll, POLL_INTERVAL_MS);
    // Browsers throttle timers in hidden windows to roughly once a minute, and matchmaking
    // is inherently a two-window activity — so also poll the moment this one is looked at.
    document.addEventListener("visibilitychange", poll);
    return () => {
      clearInterval(timer);
      document.removeEventListener("visibilitychange", poll);
    };
  }, [hasJoined, matched, refetch]);

  // Join once, as soon as Clerk knows who we are.
  useEffect(() => {
    if (!isLoaded || !isSignedIn || joinRequested.current) return;
    joinRequested.current = true;
    requestJoin();
  }, [isLoaded, isSignedIn, requestJoin]);

  // Recover if we somehow lost our place in the queue while still sitting here. Bounded,
  // so a persistent server-side refusal surfaces as a stuck spinner rather than a loop.
  useEffect(() => {
    if (state?.status !== "idle" || rejoinAttempts.current >= MAX_REJOIN_ATTEMPTS) return;
    rejoinAttempts.current += 1;
    requestJoin();
  }, [state?.status, requestJoin]);

  // Tick for the elapsed counter. setState lives in the interval callback, not the effect
  // body, so it doesn't trigger the cascading render the lint rule guards against.
  //
  // Browsers throttle timers in hidden windows to roughly once a minute, so the counter
  // freezes while the window is in the background. Recomputing on visibilitychange means
  // it shows the true elapsed time the instant the user looks at it again, rather than
  // resuming from wherever it stalled.
  useEffect(() => {
    const tick = () => setNow(Date.now());
    const timer = setInterval(tick, 1000);
    document.addEventListener("visibilitychange", tick);
    return () => {
      clearInterval(timer);
      document.removeEventListener("visibilitychange", tick);
    };
  }, []);

  // Keep the newest getToken reachable from the unmount cleanup without making it a
  // dependency of that effect. Clerk memoises getToken on its context object, so its
  // identity changes as the session settles — depending on it made React run the cleanup
  // mid-session and silently withdraw the user from the queue they were watching.
  const getTokenRef = useRef(getToken);
  useEffect(() => {
    getTokenRef.current = getToken;
  });

  // Withdraw on leaving the page. Empty deps: this must fire on unmount and nothing else.
  // A closed tab cannot be relied on to reach here at all — that case is covered server
  // side by the heartbeat, which expires entries that stop polling.
  useEffect(() => {
    return () => {
      if (shouldDequeue.current) {
        void getTokenRef.current().then((token) => leaveQueue(token).catch(() => undefined));
      }
    };
  }, []);

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
          <PollDiagnostics
            joined={hasJoined}
            status={state?.status}
            fetchStatus={fetchStatus}
            dataUpdatedAt={dataUpdatedAt}
            errorUpdatedAt={errorUpdatedAt}
            now={now}
          />
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

/**
 * Development-only readout of the polling loop.
 *
 * Matchmaking bugs are invisible from the outside — a spinner looks identical whether the
 * client is polling happily, silently failing, or not polling at all. Showing when the last
 * poll landed turns "it just sits there" into a diagnosable report. Hidden in production.
 */
function PollDiagnostics({
  joined,
  status,
  fetchStatus,
  dataUpdatedAt,
  errorUpdatedAt,
  now,
}: {
  joined: boolean;
  status?: string;
  fetchStatus: string;
  dataUpdatedAt: number;
  errorUpdatedAt: number;
  now: number;
}) {
  if (process.env.NODE_ENV === "production") return null;

  const last = Math.max(dataUpdatedAt, errorUpdatedAt);
  const ago = last ? `${Math.round((now - last) / 1000)}s ago` : "never";
  const stalled = last === 0 || now - last > 15_000;

  return (
    <p
      className={`font-mono text-xs ${stalled ? "text-destructive" : "text-muted-foreground/60"}`}
    >
      dev · joined={String(joined)} · status={status ?? "—"} · fetch={fetchStatus} · last poll{" "}
      {ago}
      {stalled && " · POLLING STALLED"}
    </p>
  );
}

function Centered({ children }: { children: React.ReactNode }) {
  return (
    <div className="mx-auto flex min-h-[70vh] w-full max-w-lg flex-col items-center justify-center gap-3 px-4 py-12 text-center">
      {children}
    </div>
  );
}
