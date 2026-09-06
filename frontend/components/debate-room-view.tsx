"use client";

import { useRouter } from "next/navigation";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "@clerk/nextjs";
import { Loader2, PhoneOff } from "lucide-react";

import type { DebateRoom } from "@/lib/types";
import { useDebateChat } from "@/hooks/use-debate-chat";
import { requestFactCheck } from "@/services/fact-check";
import { endRoom, matchKeys } from "@/services/match";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ChatPanel } from "@/components/chat-panel";
import { DebateVideo } from "@/components/debate-video";
import { ReportDialog } from "@/components/report-dialog";

interface DebateRoomViewProps {
  room: DebateRoom;
}

/**
 * Debate Room orchestrator: owns the controls and wires the fact-check flow.
 *
 * Everything on screen is now server state. The transcript and the AI verdicts both arrive
 * through `useDebateChat` — verdicts are pushed over the same socket, so they appear in
 * both windows at once rather than only for whoever asked.
 */
export function DebateRoomView({ room }: DebateRoomViewProps) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { getToken } = useAuth();
  const chat = useDebateChat(room.id);

  const { mutate: endDebate, isPending: isEnding } = useMutation({
    mutationFn: async () => endRoom(room.id, await getToken()),
    // Navigate either way: if the room was already closed by the opponent, the debate is
    // over regardless and stranding the user here would be worse than a silent failure.
    onSettled: () => {
      queryClient.removeQueries({ queryKey: matchKeys.state });
      router.push(`/debate/${room.id}/results`);
    },
  });

  async function handleFactCheck(claim: string) {
    // The verdict is not appended here. The server broadcasts it over the chat socket, so
    // it arrives the same way for both debaters — including the one who asked. One source
    // of truth beats an optimistic copy that can disagree with what the other side sees.
    await requestFactCheck(room.id, claim, await getToken());
  }

  return (
    <div className="mx-auto flex min-h-[calc(100dvh-4rem)] w-full max-w-6xl flex-col gap-4 px-4 py-6 sm:px-6">
      {/* Room header */}
      <header className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex min-w-0 items-center gap-2">
          <Badge variant="outline">{room.topic.category}</Badge>
          <h1 className="truncate font-medium">{room.topic.title}</h1>
        </div>
        <div className="flex items-center gap-2">
          {/*
            Reachable during the debate, not only after it. A report action with no entry
            point would be this project's third instance of shipping working code that
            nothing navigates to — see PROJECT-HANDBOOK §5.28.
          */}
          <ReportDialog roomId={room.id} opponentName={room.opponent.username} />
          <Button
            variant="destructive"
            size="sm"
            disabled={isEnding}
            onClick={() => endDebate()}
          >
            {isEnding ? (
              <Loader2 className="size-4 animate-spin" />
            ) : (
              <PhoneOff className="size-4" />
            )}
            End debate
          </Button>
        </div>
      </header>

      {/* Video + chat */}
      <div className="grid min-h-0 flex-1 gap-4 lg:grid-cols-[2fr_1fr]">
        <DebateVideo room={room} onFactCheck={handleFactCheck} />

        <ChatPanel
          room={room}
          messages={chat.messages}
          onSend={chat.send}
          status={chat.status}
          error={chat.error}
          debug={chat.debug}
          className="min-h-[24rem] lg:min-h-0"
        />
      </div>
    </div>
  );
}
