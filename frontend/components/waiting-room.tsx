"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Loader2, Users } from "lucide-react";

import type { Topic, UserSummary } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { initials } from "@/lib/utils";

interface WaitingRoomProps {
  topic: Topic;
  /** The opponent revealed once a match is (mock) found. */
  opponent: UserSummary;
  /** Room to enter after matching. */
  roomId: string;
}

/** Simulated matchmaking delay before a match is "found" (ms). */
const MATCH_DELAY_MS = 4000;

/**
 * Waiting Room. In Phase 1 this simulates matchmaking with a timer: it shows a
 * searching state, then reveals a matched opponent and a CTA into the debate
 * room. Real queue/matchmaking arrives in Phase 4.
 */
export function WaitingRoom({ topic, opponent, roomId }: WaitingRoomProps) {
  const router = useRouter();
  const [matched, setMatched] = useState(false);
  const [seconds, setSeconds] = useState(0);

  useEffect(() => {
    const tick = setInterval(() => setSeconds((s) => s + 1), 1000);
    const match = setTimeout(() => setMatched(true), MATCH_DELAY_MS);
    return () => {
      clearInterval(tick);
      clearTimeout(match);
    };
  }, []);

  return (
    <div className="mx-auto flex min-h-[70vh] w-full max-w-lg flex-col items-center justify-center gap-8 px-4 py-12 text-center">
      {/* Topic context */}
      <div className="space-y-2">
        <Badge variant="outline">{topic.category}</Badge>
        <h1 className="text-balance text-2xl font-semibold tracking-tight">
          {topic.title}
        </h1>
      </div>

      {!matched ? (
        <>
          <div className="flex flex-col items-center gap-4">
            <Loader2 className="size-10 animate-spin text-primary" />
            <div>
              <p className="font-medium">Finding you an opponent…</p>
              <p className="text-sm text-muted-foreground">
                Searching for someone to argue the other side · {seconds}s
              </p>
            </div>
          </div>
          <Button variant="ghost" onClick={() => router.push("/browse")}>
            Cancel
          </Button>
        </>
      ) : (
        <>
          <div className="flex flex-col items-center gap-4">
            <Avatar className="size-16">
              <AvatarFallback>{initials(opponent.username)}</AvatarFallback>
            </Avatar>
            <div>
              <p className="inline-flex items-center gap-1.5 font-medium">
                <Users className="size-4 text-primary" />
                Opponent found
              </p>
              <p className="text-sm text-muted-foreground">
                Matched with {opponent.username}
              </p>
            </div>
          </div>
          <Button size="lg" onClick={() => router.push(`/debate/${roomId}`)}>
            Enter debate
          </Button>
        </>
      )}
    </div>
  );
}
